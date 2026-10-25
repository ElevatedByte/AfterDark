"""Single inference/composition worker. API threads only communicate through state."""

import logging
import queue
import threading
import time
import cv2
from app.camera.camera_manager import CameraManager
from app.cues.automation import RandomShow
from app.renderer.compositor import (
    standby_frame,
    draw_debug,
    camera_viewport,
    letterbox_output,
)
from app.renderer.projector import Projector
from app.renderer.metrics import StageMetrics
from app.renderer.preview import PreviewEncoder
from app.tracking.pose_tracker import MediaPipePoseTracker
from app.tracking.person_tracker import PersonTracker
from app.tracking.gesture_detector import GestureDetector
from app.effects.manager import EffectManager

log = logging.getLogger(__name__)


class Runtime:
    def __init__(self, config, state):
        self.config, self.state = config, state
        self.camera = CameraManager(config)
        if config.demo_mode:
            from app.camera.demo import DemoCamera

            self.camera = DemoCamera(config)
        self.identities = PersonTracker(config.tracking_smoothing, config.track_timeout)
        self.gestures = GestureDetector(config)
        self.effects = EffectManager()
        self.random_show = RandomShow()
        self._tracking_revision = 0
        self.projector = Projector(config)
        self._stop = threading.Event()
        self._thread = None
        self.metrics = StageMetrics()
        self.encoder = PreviewEncoder(self.metrics)
        self.tracker = None
        self._tracker_retry = 0
        self._tracker_max = config.max_people
        self._last_fullscreen = config.fullscreen
        self._last_monitor = config.projector_monitor

    def start(self):
        self.encoder.start()
        self._thread = threading.Thread(
            target=self._run, name="show-processing", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(6)
        self.encoder.stop()

    def preview(self):
        return self.encoder.read()

    def output_snapshot(self):
        """Encode a full-size still on demand, without slowing the live preview loop."""
        frame = self.projector.shared.read()
        if frame is None:
            return None
        ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 94])
        return jpeg.tobytes() if ok else None

    def _projector_control(self, snapshot):
        requested = snapshot["projector_requested"]
        if requested:
            if self.projector.process is None:
                self._last_fullscreen = snapshot["fullscreen"]
                self._last_monitor = snapshot["projector_monitor_index"]
                self.projector.start(self._last_fullscreen, self._last_monitor)
            elif snapshot["projector_monitor_index"] != self._last_monitor:
                self.projector.stop()
                self.state.update(projector_running=False)
                return
            elif snapshot["fullscreen"] != self._last_fullscreen:
                self._last_fullscreen = snapshot["fullscreen"]
                self.projector.send(
                    {"type": "fullscreen", "value": self._last_fullscreen}
                )
        elif self.projector.process:
            self.projector.stop()
            self.state.update(projector_running=False)
        for event in self.projector.poll():
            if event.get("type") == "timing":
                self.metrics.record("presentation", event["seconds"])
                continue
            values = {"projector_running": event["running"]}
            if event.get("error"):
                values["projector_error"] = event["error"]
            if "fullscreen" in event:
                values["projector_fullscreen"] = event["fullscreen"]
                values["projector_monitor_actual"] = event["monitor"]
                if event.get("source") == "keyboard":
                    self._last_fullscreen = event["fullscreen"]
                    values["fullscreen"] = event["fullscreen"]
            if "driver" in event:
                values["projector_driver"] = event["driver"]
            if not event["running"]:
                values["projector_requested"] = False
            self.state.update(**values)
        process = self.projector.process
        if process and (
            not process.is_alive()
            or (
                not self.state.snapshot()["projector_running"]
                and time.monotonic() - self.projector.started > 10
            )
        ):
            previous = self.state.snapshot()
            self.state.update(
                projector_running=False,
                projector_requested=False,
                projector_error=previous["projector_error"]
                or "Projector closed or failed to initialize",
            )
            self.projector.stop()

    def _detect(self, frame, now, snapshot):
        if self.config.demo_mode:
            self.state.update(tracking_status="simulated", tracking_error=None)
            return self.camera.people[: snapshot["max_people"]]
        if self.tracker and self._tracker_max != snapshot["max_people"]:
            self.tracker.close()
            self.tracker = None
            self._tracker_retry = 0
        if self.tracker is None and now >= self._tracker_retry:
            try:
                self.tracker = MediaPipePoseTracker(self.config, snapshot["max_people"])
                self._tracker_max = snapshot["max_people"]
                self.state.update(tracking_status="ready", tracking_error=None)
            except Exception as exc:
                self._tracker_retry = now + 10
                self.state.update(
                    tracking_status="unavailable", tracking_error=str(exc)
                )
        if self.tracker:
            try:
                return self.tracker.detect(frame, int(now * 1000))
            except Exception as exc:
                log.exception("Tracking failed; camera display continues")
                self.tracker.close()
                self.tracker = None
                self._tracker_retry = now + 5
                self.state.update(
                    tracking_status="unavailable", tracking_error=str(exc)
                )
        return []

    def _run(self):
        cv2.setNumThreads(2)
        last_seq = -1
        last_time = time.monotonic()
        last_stats = last_idle = 0.0
        frames = 0
        fps = 0.0
        slow_since = None
        camera_active = False
        try:
            while not self._stop.is_set():
                tick = time.monotonic()
                snapshot = self.state.snapshot()
                self._projector_control(snapshot)
                if snapshot["camera_requested"] and not camera_active:
                    self.camera.start()
                    camera_active = True
                elif not snapshot["camera_requested"] and camera_active:
                    self.camera.stop()
                    camera_active = False
                    last_seq = -1
                    self.identities.reset()
                    self.gestures.reset()
                    self.effects.reset()
                    self.state.update(tracking_status="idle", person_effects={})
                started = time.perf_counter()
                packet = self.camera.latest() if camera_active else None
                self.metrics.record("capture_poll", time.perf_counter() - started)
                fresh = (
                    packet is not None
                    and packet.sequence != last_seq
                    and tick - packet.timestamp < 1
                )
                self.state.update(
                    camera_running=camera_active,
                    camera_connected=bool(
                        not self.config.demo_mode
                        and self.camera.connected
                        and packet
                        and tick - packet.timestamp < 1
                    ),
                    camera_error=self.camera.error,
                )
                if fresh:
                    started = time.perf_counter()
                    frame = packet.color.copy()
                    last_seq = packet.sequence
                    self.metrics.record("capture_age", tick - packet.timestamp)
                    if packet.capture_ms:
                        self.metrics.record(
                            "capture_read_and_prepare", packet.capture_ms / 1000
                        )
                    self.metrics.record("frame_copy", time.perf_counter() - started)
                    started = time.perf_counter()
                    people = self._detect(frame, packet.timestamp, snapshot)
                    self.metrics.record("inference", time.perf_counter() - started)
                    frames += 1
                elif tick - last_idle >= (
                    1 / self.config.target_fps if self.effects.active_cues else 0.1
                ) and (packet is None or tick - packet.timestamp >= 1):
                    frame = standby_frame(
                        self.config.output_width,
                        self.config.output_height,
                        "CAMERA RECONNECTING"
                        if camera_active
                        else "The Dance Floor Awaits",
                    )
                    people = []
                    last_idle = tick
                else:
                    self._stop.wait(0.005)
                    continue
                dt = min(0.2, max(0.001, tick - last_time))
                last_time = tick
                started = time.perf_counter()
                frame, people = self.process_frame(
                    frame, people, dt, tick, snapshot, fresh
                )
                self.metrics.record(
                    "composition_and_control", time.perf_counter() - started
                )
                started = time.perf_counter()
                self.projector.shared.publish(frame)
                self.metrics.record("shared_publish", time.perf_counter() - started)
                self.encoder.submit(frame)
                self.metrics.record("processing", time.monotonic() - tick)
                self.state.update(
                    tracked_people_count=len(people),
                    people=[
                        {"id": p.id, "confidence": round(p.confidence, 2)}
                        for p in people
                    ],
                    frame_latency_ms=round(
                        (time.monotonic() - packet.timestamp) * 1000, 1
                    )
                    if fresh
                    else 0,
                    camera_resolution=[self.camera.width, self.camera.height],
                )
                if tick - last_stats >= 1:
                    fps = frames / (tick - last_stats) if last_stats else 0
                    frames = 0
                    last_stats = tick
                    self.state.update(fps=round(fps, 1))
                    self.state.update(
                        renderer_timings=self.metrics.snapshot(),
                        preview_dropped=self.encoder.dropped,
                        preview_error=self.encoder.error,
                    )
                    if (
                        fresh
                        and 0 < fps < self.config.low_fps_threshold
                        and snapshot["adaptive_resolution"]
                    ):
                        slow_since = slow_since or tick
                        if (
                            tick - slow_since > 5
                            and self.camera.width * self.camera.height > 640 * 480
                        ):
                            self.camera.set_resolution(640, 480)
                            self.state.update(resolution_reduced=True)
                    else:
                        slow_since = None
                self._stop.wait(
                    max(0, 1 / self.config.target_fps - (time.monotonic() - tick))
                )
        except Exception as exc:
            log.exception("Processing stopped")
            self.state.update(runtime_error=str(exc))
        finally:
            self.camera.stop()
            self.projector.stop()
            if self.tracker:
                self.tracker.close()
            self.state.update(
                camera_running=False,
                camera_connected=False,
                projector_running=False,
                tracked_people_count=0,
                people=[],
                fps=0,
                active_cues=[],
            )

    def process_frame(self, frame, people, dt, now, snapshot, fresh):
        if snapshot["tracking_revision"] != self._tracking_revision:
            self.identities.reset()
            self.gestures.reset()
            self.effects.reset()
            if self.tracker:
                self.tracker.close()
                self.tracker = None
            self._tracker_retry = 0
            self._tracking_revision = snapshot["tracking_revision"]
        self.identities.smoothing = snapshot["effect_settings"]["tracking_smoothing"]
        previous_ids = set(self.identities.tracks)
        people = self.identities.update(people, now)
        new_ids = {person.id for person in people} - previous_ids
        if (
            snapshot["active_scene"] == "normal_camera"
            and self.effects.scene_revision != snapshot["scene_revision"]
        ):
            # Returning to Normal Camera assigns random effects to existing tracks too.
            new_ids = set(self.identities.tracks)
        snapshot["person_effects"] = self.state.sync_person_effects(
            new_ids, set(self.identities.tracks)
        )
        self.effects.sync(snapshot)
        for event in self.gestures.update(people, now):
            person = [p for p in people if p.id == event.person_id]
            if self.effects.trigger(event.trigger, person):
                self.state.update(
                    last_gesture=f"Person {event.person_id}: {event.name.replace('_', ' ')}"
                )
                if event.trigger == "lightning":
                    self.projector.send({"type": "sound", "name": "lightning"})
        automatic = self.random_show.tick(
            now, snapshot["random_show"], self.effects.active_cues
        )
        if automatic:
            try:
                self.state.trigger(automatic)
            except ValueError:
                pass  # A busy manual queue takes priority over automation.
            else:
                self.state.update(last_auto_trigger=automatic)
        while True:
            try:
                trigger = self.state.commands.get_nowait()
            except queue.Empty:
                break
            self.effects.trigger(trigger, people, manual=True)
            if trigger in ("scream", "lightning", "ghost_appearance"):
                self.projector.send(
                    {
                        "type": "sound",
                        "name": "ghost" if trigger == "ghost_appearance" else trigger,
                    }
                )
        width, height = self.config.output_width, self.config.output_height
        view, offset = camera_viewport(frame, width, height)
        # Normalized landmarks/masks stay in camera coordinates. The matching
        # high-resolution viewport preserves alignment without another inference.
        view = self.effects.render(view, people, dt)
        if snapshot["debug_skeleton"]:
            draw_debug(view, people)
        output = letterbox_output(view, width, height, offset)
        if self.effects.active_cues != snapshot["active_cues"]:
            self.state.update(active_cues=self.effects.active_cues)
        return output, people
