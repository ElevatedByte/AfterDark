"""A child process owns SDL on its main thread. Frames use one shared memory slot."""

import multiprocessing as mp
import os
import queue
import time
import numpy as np


class SharedFrame:
    def __init__(self, context, width, height):
        self.capacity = max(width * height, 640 * 480) * 3
        self.buffer = context.RawArray("B", self.capacity)
        self.shape = context.Array("i", [0, 0], lock=False)
        self.lock = context.Lock()

    def publish(self, frame):
        if frame.size > self.capacity:
            raise ValueError("Frame exceeds shared memory capacity")
        if not self.lock.acquire(False):
            return
        try:
            np.frombuffer(self.buffer, np.uint8, count=frame.size)[:] = frame.reshape(
                -1
            )
            self.shape[:] = frame.shape[:2]
        finally:
            self.lock.release()

    def read(self):
        with self.lock:
            h, w = self.shape[:]
            if not h:
                return None
            return (
                np.frombuffer(self.buffer, np.uint8, count=h * w * 3)
                .reshape(h, w, 3)
                .copy()
            )


def projector_worker(shared, commands, events, config):
    os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    import pygame
    from app.audio.sound_manager import SoundManager

    sound = SoundManager()
    try:
        pygame.display.init()
        desktops = pygame.display.get_desktop_sizes()
        monitor = config["monitor"]
        if monitor >= len(desktops):
            raise RuntimeError(
                f"Monitor {monitor} unavailable; SDL sees {len(desktops)} display(s). Select monitor 0 for a single display."
            )
        fullscreen = config["fullscreen"]
        size = config["width"], config["height"]

        def open_window(source="request"):
            flags = pygame.FULLSCREEN if fullscreen else pygame.RESIZABLE
            screen = pygame.display.set_mode(size, flags, display=monitor)
            pygame.display.set_caption(
                "Halloween Dance — Projector (F: fullscreen / Esc: close)"
            )
            pygame.mouse.set_visible(not fullscreen)
            events.put(
                {
                    "running": True,
                    "fullscreen": fullscreen,
                    "monitor": monitor,
                    "displays": desktops,
                    "driver": pygame.display.get_driver(),
                    "source": source,
                }
            )
            return screen

        screen = open_window()
        clock = pygame.time.Clock()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
                ):
                    running = False
                if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                    fullscreen = not fullscreen
                    screen = open_window("keyboard")
            while True:
                try:
                    cmd = commands.get_nowait()
                except queue.Empty:
                    break
                if cmd["type"] == "stop":
                    running = False
                elif cmd["type"] == "fullscreen":
                    fullscreen = cmd["value"]
                    screen = open_window()
                elif cmd["type"] == "sound":
                    sound.play(cmd["name"])
            frame = shared.read()
            screen.fill((15, 10, 20))
            if frame is not None:
                rgb = np.ascontiguousarray(frame[:, :, ::-1])
                surface = pygame.image.frombuffer(
                    rgb.tobytes(), (frame.shape[1], frame.shape[0]), "RGB"
                )
                sw, sh = screen.get_size()
                ratio = min(sw / surface.get_width(), sh / surface.get_height())
                fit = (
                    max(1, round(surface.get_width() * ratio)),
                    max(1, round(surface.get_height() * ratio)),
                )
                if fit != surface.get_size():
                    surface = pygame.transform.smoothscale(surface, fit)
                screen.blit(surface, ((sw - fit[0]) // 2, (sh - fit[1]) // 2))
            pygame.display.flip()
            clock.tick(config["fps"])
    except Exception as exc:
        events.put({"running": False, "error": str(exc)})
    finally:
        sound.close()
        pygame.quit()
        events.put({"running": False})


class Projector:
    def __init__(self, config):
        self.config = config
        self.ctx = mp.get_context("spawn")
        self.shared = SharedFrame(self.ctx, config.output_width, config.output_height)
        self.process = None
        self.commands = None
        self.events = None
        self.started = 0

    def start(self, fullscreen, monitor):
        if self.process and self.process.is_alive():
            return
        self.commands, self.events = self.ctx.Queue(32), self.ctx.Queue()
        self.process = self.ctx.Process(
            target=projector_worker,
            args=(
                self.shared,
                self.commands,
                self.events,
                {
                    "monitor": monitor,
                    "fullscreen": fullscreen,
                    "width": self.config.output_width,
                    "height": self.config.output_height,
                    "fps": self.config.target_fps,
                },
            ),
            daemon=True,
            name="projector",
        )
        self.started = time.monotonic()
        self.process.start()

    def send(self, command):
        if self.commands:
            try:
                self.commands.put_nowait(command)
            except queue.Full:
                pass

    def poll(self):
        result = []
        if self.events:
            while True:
                try:
                    result.append(self.events.get_nowait())
                except queue.Empty:
                    break
        return result

    def stop(self):
        if self.process:
            self.send({"type": "stop"})
            self.process.join(2)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(1)
            self.process.close()
            self.process = None
        for channel in (self.commands, self.events):
            if channel:
                channel.close()
                channel.cancel_join_thread()
        self.commands = self.events = None
