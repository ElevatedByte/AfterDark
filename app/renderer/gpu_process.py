"""Experimental renderer process and bounded, versioned camera/pose mailbox.

Only head sprites and visitor cues have been migrated. The complete CPU show
remains the default. No browser or HTTP transport participates in frame delivery.
"""

import json
import multiprocessing as mp
import queue
import time

import numpy as np

from app.renderer.metrics import StageMetrics

PROTOCOL_VERSION = 1
HEADS = ("pumpkin_head", "witch", "frankenstein", "vampire", "mummy")


class RenderMailbox:
    """One atomic latest frame + descriptor, BGR8/sRGB/top-left/tightly packed.

    A producer drops a publication if the consumer is copying. The consumer also
    uses a nonblocking lock, retaining its last complete input on contention.
    Camera data and JSON metadata always share one lock and one sequence.
    """

    def __init__(self, context, width=1280, height=720):
        self.capacity = width * height * 3
        self.pixels = context.RawArray("B", self.capacity)
        self.metadata = context.RawArray("B", 65536)
        self.header = context.Array("q", [0, 0, 0, 0], lock=False)
        self.lock = context.Lock()
        self.dropped = 0

    def publish(self, frame, descriptor):
        if frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("Expected a BGR8 frame")
        if frame.size > self.capacity:
            raise ValueError("Camera frame exceeds mailbox capacity")
        payload = dict(
            descriptor,
            protocol_version=PROTOCOL_VERSION,
            timestamp=time.monotonic(),
            pixel_format="BGR8",
            color_space="sRGB",
            stride=frame.shape[1] * 3,
        )
        data = json.dumps(payload, allow_nan=False).encode()
        if len(data) > len(self.metadata):
            raise ValueError("Renderer descriptor exceeds 64 KiB")
        if not self.lock.acquire(False):
            self.dropped += 1
            return False
        try:
            np.frombuffer(self.pixels, np.uint8, frame.size)[:] = frame.reshape(-1)
            np.frombuffer(self.metadata, np.uint8, len(data))[:] = np.frombuffer(
                data, np.uint8
            )
            sequence = self.header[0] + 1
            self.header[:] = sequence, frame.shape[0], frame.shape[1], len(data)
        finally:
            self.lock.release()
        return True

    def latest(self, after_sequence=0):
        if not self.lock.acquire(False):
            return None
        try:
            sequence, h, w, length = self.header[:]
            if sequence == after_sequence or not h:
                return None
            descriptor = json.loads(bytes(self.metadata[:length]))
            if descriptor["protocol_version"] != PROTOCOL_VERSION:
                raise ValueError("Unsupported renderer protocol")
            frame = (
                np.frombuffer(self.pixels, np.uint8, h * w * 3).reshape(h, w, 3).copy()
            )
            return sequence, frame, descriptor
        finally:
            self.lock.release()


def encode_people(people):
    # Segmentation transport is deliberately deferred until the ghost port.
    return [
        dict(
            id=p.id,
            confidence=p.confidence,
            bounding_box=p.bounding_box,
            landmarks={
                name: [point.x, point.y, point.confidence]
                for name, point in p.landmarks.items()
            },
        )
        for p in people
    ]


def decode_people(data):
    from app.tracking.models import Point, PersonTrackingData

    return [
        PersonTrackingData(
            p["id"],
            {name: Point(*point) for name, point in p["landmarks"].items()},
            tuple(p["bounding_box"]),
            p["confidence"],
        )
        for p in data
    ]


def gpu_worker(mailbox, commands, events, settings):
    import moderngl
    import pygame

    from app.cues.animations import create_cues
    from app.effects.pumpkin_head import PumpkinHead
    from app.effects.witch import Witch
    from app.effects.frankenstein import Frankenstein
    from app.effects.vampire import Vampire
    from app.effects.mummy import Mummy
    from app.renderer.compositor import standby_frame
    from app.renderer.gpu import GpuRenderer

    def emit(message):
        try:
            events.put_nowait(dict(protocol_version=PROTOCOL_VERSION, **message))
        except queue.Full:
            pass

    renderer = context = None
    fullscreen = settings["fullscreen"]
    metrics = StageMetrics()
    try:
        pygame.display.init()
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MAJOR_VERSION, 3)
        pygame.display.gl_set_attribute(pygame.GL_CONTEXT_MINOR_VERSION, 3)
        pygame.display.gl_set_attribute(
            pygame.GL_CONTEXT_PROFILE_MASK, pygame.GL_CONTEXT_PROFILE_CORE
        )
        if settings["monitor"] >= pygame.display.get_num_displays():
            raise RuntimeError("Requested monitor is unavailable")
        flags = pygame.OPENGL | pygame.DOUBLEBUF
        if fullscreen:
            flags |= pygame.FULLSCREEN
        pygame.display.set_mode(
            (settings["width"], settings["height"]),
            flags,
            display=settings["monitor"],
            vsync=0,
        )
        pygame.display.set_caption("Afterdark — experimental GPU rehearsal")
        context = moderngl.create_context(require=330)
        renderer = GpuRenderer(context, settings["width"], settings["height"])
        effects = {
            effect.name: effect
            for effect in (PumpkinHead(), Witch(), Frankenstein(), Vampire(), Mummy())
        }
        cues = create_cues()
        standby = standby_frame(settings["width"], settings["height"])
        current = standby
        descriptor = {}
        sequence = 0
        previous = last_health = time.monotonic()
        running = True
        clock = pygame.time.Clock()
        emit(
            {
                "type": "ready",
                "running": True,
                "hardware": renderer.hardware,
                "backend": renderer.info,
                "fullscreen": fullscreen,
                "monitor": settings["monitor"],
            }
        )

        def set_fullscreen(value):
            nonlocal fullscreen
            if bool(value) != fullscreen:
                if pygame.display.toggle_fullscreen() == -1:
                    raise RuntimeError("SDL could not change fullscreen mode")
                fullscreen = bool(value)
            emit(
                {
                    "type": "window",
                    "fullscreen": fullscreen,
                    "monitor": settings["monitor"],
                }
            )

        while running:
            now = time.monotonic()
            dt = min(0.2, max(0.001, now - previous))
            previous = now
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                    set_fullscreen(not fullscreen)
            while True:
                try:
                    command = commands.get_nowait()
                except queue.Empty:
                    break
                error = None
                kind = command.get("type")
                if command.get("protocol_version") != PROTOCOL_VERSION:
                    error = "Unsupported protocol version"
                elif kind == "stop":
                    running = False
                elif kind == "cue" and command.get("name") in cues:
                    cues[command["name"]].trigger()
                elif kind == "cancel_cues":
                    for cue in cues.values():
                        cue.reset()
                elif kind == "fullscreen":
                    set_fullscreen(command.get("value", False))
                else:
                    error = "Unsupported command in this migration stage"
                emit(
                    {
                        "type": "ack",
                        "command_id": command.get("command_id"),
                        "error": error,
                    }
                )
            started = time.perf_counter()
            packet = mailbox.latest(sequence)
            if packet:
                sequence, current, descriptor = packet
            metrics.record("input_copy", time.perf_counter() - started)
            fresh = now - descriptor.get("timestamp", 0) < 1
            people = decode_people(descriptor.get("people", [])) if fresh else []
            started = time.perf_counter()
            canvas = renderer.begin(current if fresh else standby)
            assignments = descriptor.get("person_effects", {})
            active = descriptor.get("active_effects", [])
            unsupported = sorted(
                (set(active) | {e for es in assignments.values() for e in es})
                - set(HEADS)
            )
            if unsupported:
                raise RuntimeError(
                    "Unported effects requested: " + ", ".join(unsupported)
                )
            for name, effect in effects.items():
                effect.settings = descriptor.get("effect_settings", {})
                selected = [
                    p for p in people if name in assignments.get(str(p.id), active)
                ]
                effect.update(canvas, selected, dt)
                effect.render(canvas)
            for cue in cues.values():
                cue.settings = descriptor.get("effect_settings", {})
                if cue.alive:
                    cue.update(canvas, [], dt)
                    cue.render(canvas)
            renderer.present(pygame.display.get_window_size())
            metrics.record("composition_submit", time.perf_counter() - started)
            started = time.perf_counter()
            pygame.display.flip()
            metrics.record("presentation", time.perf_counter() - started)
            if now - last_health >= 1:
                emit(
                    {
                        "type": "health",
                        "running": True,
                        "sequence": sequence,
                        "input_age_ms": round((now - descriptor["timestamp"]) * 1000, 1)
                        if descriptor
                        else None,
                        "stale_input": not fresh,
                        "timings": metrics.snapshot(),
                        "active_cues": [
                            name for name, cue in cues.items() if cue.alive
                        ],
                    }
                )
                last_health = now
            clock.tick(settings["fps"])
    except Exception as exc:
        emit({"type": "error", "running": False, "error": str(exc)})
    finally:
        if renderer:
            renderer.close()
        if context:
            context.release()
        pygame.quit()
        emit({"type": "stopped", "running": False})


class GpuProjector:
    def __init__(self, config):
        self.config = config
        self.context = mp.get_context("spawn")
        self.mailbox = RenderMailbox(
            self.context, config.camera_width, config.camera_height
        )
        self.process = None
        self.commands = self.events = None
        self.command_id = 0

    def start(self):
        if self.process:
            raise RuntimeError("Stop the current renderer before restarting")
        self.commands = self.context.Queue(32)
        self.events = self.context.Queue(32)
        self.process = self.context.Process(
            target=gpu_worker,
            args=(
                self.mailbox,
                self.commands,
                self.events,
                dict(
                    width=self.config.output_width,
                    height=self.config.output_height,
                    fps=self.config.target_fps,
                    monitor=self.config.projector_monitor,
                    fullscreen=self.config.fullscreen,
                ),
            ),
            name="afterdark-gpu",
        )
        self.process.start()

    def send(self, kind, **values):
        self.command_id += 1
        self.commands.put_nowait(
            dict(
                protocol_version=PROTOCOL_VERSION,
                command_id=self.command_id,
                type=kind,
                **values,
            )
        )
        return self.command_id

    def poll(self):
        result = []
        while self.events:
            try:
                result.append(self.events.get_nowait())
            except queue.Empty:
                break
        return result

    def stop(self):
        if self.process:
            try:
                self.send("stop")
            except queue.Full:
                pass
            self.process.join(3)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(2)
            self.process.close()
            self.process = None
        for channel in (self.commands, self.events):
            if channel:
                channel.close()
                channel.cancel_join_thread()
        self.commands = self.events = None
