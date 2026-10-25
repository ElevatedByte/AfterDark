"""Launch an isolated rehearsal server, exercise HTTP/WS/renderer, then stop it."""

import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--real-display", action="store_true", help="Use monitor 0 instead of SDL dummy"
    )
    args = parser.parse_args()
    from app.state.app_state import CHARACTER_EFFECTS, EFFECTS, RANDOM_PERSON_EFFECTS
    from app.cues.catalog import LIVE_CUES

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env.pop("SETTINGS_PATH", None)  # Never read or overwrite the live show preferences.
    env.update(
        PORT=str(port),
        DEMO_MODE="true",
        RANDOM_SHOW="false",
        CAMERA_WIDTH="640",
        CAMERA_HEIGHT="480",
        OUTPUT_WIDTH="960",
        OUTPUT_HEIGHT="540",
        PROJECTOR_MONITOR="0",
        AUTO_START_CAMERA="true",
    )
    if not args.real_display:
        env["SDL_VIDEODRIVER"] = "dummy"
    base = f"http://127.0.0.1:{port}"
    report = {"display": "real" if args.real_display else "dummy", "checks": []}

    def request(path, payload=None, post=False):
        req = urllib.request.Request(
            base + path,
            data=json.dumps(payload or {}).encode() if post else None,
            headers={"Content-Type": "application/json"},
            method="POST" if post else "GET",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read()

    def post(path, payload=None):
        return json.loads(request(path, payload, True))

    def status():
        return json.loads(request("/api/status"))

    def wait_for(predicate, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            s = status()
            if s["runtime_error"]:
                raise AssertionError(s["runtime_error"])
            if predicate(s):
                return s
            time.sleep(0.1)
        raise AssertionError(f"Timed out; status={status()}")

    (ROOT / "artifacts").mkdir(exist_ok=True)
    with (ROOT / "artifacts/smoke-server.log").open("w") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError("Server exited; see artifacts/smoke-server.log")
                try:
                    status()
                    break
                except (OSError, urllib.error.URLError):
                    time.sleep(0.1)
            else:
                raise RuntimeError("Server never started")
            assert b"Afterdark" in request("/")
            report["checks"].append("dashboard_html")
            initial = wait_for(lambda s: s["tracked_people_count"] == 2)
            pool = set(RANDOM_PERSON_EFFECTS)
            assigned = initial["person_effects"]
            assert len(assigned) == 2
            assert all(
                len(effects) == 1 and effects[0] in pool
                for effects in assigned.values()
            )
            time.sleep(0.3)
            assert status()["person_effects"] == assigned
            identity = initial["people"][0]["id"]
            post(f"/api/people/{identity}/effects", {"effects": None})
            time.sleep(0.3)
            assert str(identity) not in status()["person_effects"]
            assert any(key != str(identity) for key in status()["person_effects"])
            report["checks"].append(
                "random_new_person_effects_and_follow_scene_override"
            )
            jpeg = request("/api/preview.jpg")
            assert jpeg.startswith(b"\xff\xd8")
            report["checks"].append("composite_jpeg_and_two_synthetic_people")
            import cv2
            import numpy as np

            native = cv2.imdecode(
                np.frombuffer(request("/api/output.jpg"), np.uint8), cv2.IMREAD_COLOR
            )
            assert native.shape == (540, 960, 3)
            assert status()["camera_resolution"] == [640, 480]
            report["checks"].append("native_output_resolution_independent_of_camera")
            for scene in (
                "normal_camera",
                "pumpkin_dance",
                "skeleton_dance",
                "ghost_mode",
                "magic_mode",
            ):
                assert post("/api/scene/" + scene)["active_scene"] == scene
                previous_ids = {p["id"] for p in status()["people"]}
                post("/api/trigger/reset_tracking")
                updated = wait_for(
                    lambda s: s["tracked_people_count"] == 2
                    and not previous_ids.intersection(p["id"] for p in s["people"])
                )
                if scene == "normal_camera":
                    assert len(updated["person_effects"]) == 2
                else:
                    assert updated["person_effects"] == {}
                    identity = updated["people"][0]["id"]
                    assert post(
                        f"/api/people/{identity}/effects", {"effects": ["magic"]}
                    )["person_effects"][str(identity)] == ["magic"]
                    time.sleep(0.15)
                    assert status()["person_effects"][str(identity)] == ["magic"]
                    assert (
                        post(f"/api/people/{identity}/effects", {"effects": None})[
                            "person_effects"
                        ]
                        == {}
                    )
                time.sleep(0.12)
                assert request("/api/preview.jpg").startswith(b"\xff\xd8")
            report["checks"].append("all_five_scenes_and_mode_specific_person_effects")
            for effect in EFFECTS:
                assert effect in post(f"/api/effects/{effect}/enable")["active_effects"]
                assert (
                    effect
                    not in post(f"/api/effects/{effect}/disable")["active_effects"]
                )
            report["checks"].append("all_effect_toggles")
            identity = status()["people"][0]["id"]
            for effect in CHARACTER_EFFECTS:
                assert post(f"/api/people/{identity}/effects", {"effects": [effect]})[
                    "person_effects"
                ][str(identity)] == [effect]
                time.sleep(0.15)
                assert status()["person_effects"][str(identity)] == [effect]
                assert request("/api/preview.jpg").startswith(b"\xff\xd8")
            report["checks"].append("four_character_overrides_and_live_previews")
            for trigger in (
                "lightning",
                "spawn_bats",
                "ghost_appearance",
                "scream",
                "spell_burst",
            ):
                post("/api/trigger/" + trigger)
            report["checks"].append("all_manual_cues_without_sound_assets")
            assert status()["cue_catalog"] == LIVE_CUES
            for cue in LIVE_CUES:
                post("/api/trigger/" + cue)
                wait_for(lambda s: cue in s["active_cues"])
            wait_for(lambda s: set(s["active_cues"]) == set(LIVE_CUES))
            assert request("/api/preview.jpg").startswith(b"\xff\xd8")
            wait_for(lambda s: not s["active_cues"], timeout=12)
            post("/api/trigger/witch_flyby")
            wait_for(lambda s: "witch_flyby" in s["active_cues"])
            post("/api/trigger/stop_animations")
            wait_for(lambda s: not s["active_cues"])
            report["checks"].append("all_live_cues_overlap_expire_and_cancel")
            post("/api/scene/normal_camera")
            wait_for(lambda s: len(s["person_effects"]) == 2)
            identity = status()["people"][0]["id"]
            assert post(
                f"/api/people/{identity}/effects", {"effects": ["pumpkin_head"]}
            )["person_effects"][str(identity)] == ["pumpkin_head"]
            post("/api/settings", {"max_people": 1})
            wait_for(lambda s: s["tracked_people_count"] == 1)
            post("/api/settings", {"max_people": 4})
            wait_for(lambda s: s["tracked_people_count"] == 2)
            report["checks"].append("person_assignments_and_max_people")
            from websockets.sync.client import connect

            with connect(f"ws://127.0.0.1:{port}/ws", proxy=None, open_timeout=5) as ws:
                assert json.loads(ws.recv(timeout=3))["type"] == "status"
                ws.send(
                    json.dumps(
                        {
                            "action": "scene",
                            "value": "pumpkin_dance",
                            "request_id": "smoke",
                        }
                    )
                )
                while (data := json.loads(ws.recv(timeout=3)))["type"] == "status":
                    pass
                assert (
                    data["type"] == "ack"
                    and data["data"]["active_scene"] == "pumpkin_dance"
                )
            report["checks"].append("websocket_live_command_and_status")
            post("/api/projector/start")
            s = wait_for(lambda s: s["projector_running"], 20)
            assert s["projector_fullscreen"]
            report["projector_driver"] = s["projector_driver"]
            # No browser connection is required to keep capture/output alive.
            time.sleep(0.6)
            assert status()["projector_running"]
            with connect(f"ws://127.0.0.1:{port}/ws", proxy=None, open_timeout=5) as ws:
                restored = json.loads(ws.recv(timeout=3))
                assert restored["type"] == "status"
                assert restored["data"]["projector_running"]
                assert restored["data"]["active_scene"] == "pumpkin_dance"
            time.sleep(0.4)
            assert status()["projector_running"]
            report["checks"].append(
                "controller_disconnect_reconnect_preserves_running_show"
            )
            post("/api/settings", {"fullscreen": False})
            wait_for(lambda s: s["projector_running"] and not s["projector_fullscreen"])
            time.sleep(0.4)
            post("/api/settings", {"fullscreen": True})
            wait_for(lambda s: s["projector_running"] and s["projector_fullscreen"])
            time.sleep(0.4)
            post("/api/projector/stop")
            wait_for(lambda s: not s["projector_running"])
            report["checks"].append("projector_process_fullscreen_toggle_and_stop")
            post("/api/projector/start")
            wait_for(lambda s: s["projector_running"], 20)
            post("/api/projector/stop")
            wait_for(lambda s: not s["projector_running"])
            report["checks"].append("projector_restart")
            post("/api/camera/stop")
            wait_for(
                lambda s: not s["camera_running"] and s["tracked_people_count"] == 0
            )
            post("/api/trigger/spider_drop")
            wait_for(lambda s: "spider_drop" in s["active_cues"])
            assert request("/api/preview.jpg").startswith(b"\xff\xd8")
            post("/api/trigger/stop_animations")
            wait_for(lambda s: not s["active_cues"])
            report["checks"].append("live_animation_with_camera_stopped")
            post("/api/camera/start")
            wait_for(lambda s: s["camera_running"] and s["tracked_people_count"] == 2)
            post("/api/trigger/reset_tracking")
            post("/api/trigger/reset_scene")
            wait_for(
                lambda s: s["tracked_people_count"] == 2
                and s["active_scene"] == "normal_camera"
            )
            report["checks"].append("camera_restart_tracking_reset_scene_reset")
            post("/api/show/start")
            wait_for(
                lambda s: s["camera_running"]
                and s["projector_running"]
                and s["random_show"]
            )
            post("/api/trigger/witch_flyby")
            wait_for(lambda s: "witch_flyby" in s["active_cues"])
            post("/api/show/stop")
            wait_for(
                lambda s: not s["camera_running"]
                and not s["projector_running"]
                and not s["random_show"]
                and not s["active_cues"]
            )
            # Stop also clears visitors when the camera was already stopped.
            post("/api/trigger/spider_drop")
            wait_for(lambda s: "spider_drop" in s["active_cues"])
            post("/api/show/stop")
            wait_for(lambda s: not s["active_cues"])
            post("/api/show/start")
            wait_for(
                lambda s: s["camera_running"]
                and s["projector_running"]
                and s["random_show"]
            )
            report["checks"].append("start_stop_show_and_clear_pending_animation")
            time.sleep(1.2)
            report["fps"] = status()["fps"]
            # Keep a preview connected: shutdown must not wait forever for MJPEG.
            stream = urllib.request.urlopen(base + "/api/preview.mjpg", timeout=5)
            assert b"--frame" in stream.read(64)
            shutdown_started = time.monotonic()
            process.terminate()
            process.wait(8)
            stream.close()
            report["shutdown_seconds"] = round(time.monotonic() - shutdown_started, 2)
            report["checks"].append("shutdown_with_connected_preview")
            report["passed"] = True
        finally:
            process.terminate()
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            (ROOT / "artifacts/smoke-test.json").write_text(
                json.dumps(report, indent=2)
            )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
