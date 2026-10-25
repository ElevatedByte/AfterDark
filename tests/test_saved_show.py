import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app
from app.state.app_state import AppState, SettingsPatch
from app.state import storage


def test_saved_preferences_restore_but_runtime_and_person_ids_do_not(tmp_path):
    config = Config(settings_path=tmp_path / "show.json", auto_start_camera=False)
    state = AppState(config)
    state.set_scene("magic_mode")
    state.set_effect("lightning", False)
    state.set_effect("witch", True)
    state.settings(
        SettingsPatch(
            random_show=True,
            fullscreen=False,
            projector_monitor_index=2,
            max_people=6,
            effect_intensity=0.33,
            ghost_trail_strength=0.4,
            particle_amount=0.8,
            tracking_smoothing=0.2,
            adaptive_resolution=False,
            debug_skeleton=True,
        )
    )
    state.update(
        camera_requested=True,
        projector_requested=True,
        people=[{"id": 9, "confidence": 0.9}],
        active_cues=["witch_flyby"],
    )
    state.assign_person(9, ["vampire"])
    restored = AppState(config).snapshot()
    for key in (
        "active_scene",
        "active_effects",
        "effect_settings",
        "random_show",
        "fullscreen",
        "projector_monitor_index",
        "max_people",
        "adaptive_resolution",
        "debug_skeleton",
    ):
        assert restored[key] == state.snapshot()[key]
    assert not restored["camera_requested"]
    assert not restored["projector_requested"]
    assert restored["person_effects"] == {}
    assert restored["active_cues"] == []
    assert restored["settings_save_error"] is None


@pytest.mark.parametrize(
    "contents",
    [
        "{broken",
        json.dumps({"version": 2}),
        json.dumps(
            {
                "version": 1,
                "active_scene": "magic_mode",
                "active_effects": [],
                "settings": {"max_people": 999},
            }
        ),
        json.dumps(
            {"version": 1, "active_scene": "bad", "active_effects": [], "settings": {}}
        ),
    ],
)
def test_invalid_saved_file_uses_defaults_without_overwriting_evidence(
    tmp_path, contents
):
    path = tmp_path / "show.json"
    path.write_text(contents)
    state = AppState(Config(settings_path=path))
    assert state.snapshot()["active_scene"] == "normal_camera"
    assert state.snapshot()["settings_save_error"]
    assert path.read_text() == contents


def test_failed_atomic_save_keeps_last_good_file_and_reports_recovery(
    tmp_path, monkeypatch
):
    config = Config(settings_path=tmp_path / "show.json")
    state = AppState(config)
    original = config.settings_path.read_text()
    with monkeypatch.context() as patch:

        def fail(*args):
            raise OSError("Disk unavailable")

        patch.setattr(storage.os, "replace", fail)
        state.set_scene("ghost_mode")
        assert state.snapshot()["active_scene"] == "ghost_mode"
        assert state.snapshot()["settings_save_error"]
        assert config.settings_path.read_text() == original
        assert list(tmp_path.iterdir()) == [config.settings_path]
    state.settings(SettingsPatch(fullscreen=False))
    assert state.snapshot()["settings_save_error"] is None
    assert AppState(config).snapshot()["active_scene"] == "ghost_mode"


def test_multiple_controllers_save_latest_state(tmp_path):
    config = Config(settings_path=tmp_path / "show.json")
    state = AppState(config)
    with ThreadPoolExecutor(4) as pool:
        list(
            pool.map(lambda n: state.settings(SettingsPatch(max_people=n)), range(1, 9))
        )
    assert AppState(config).snapshot()["max_people"] == state.snapshot()["max_people"]


def test_show_commands_http_websocket_and_full_queue(tmp_path):
    config = Config(settings_path=tmp_path / "show.json", auto_start_camera=False)
    app = create_app(config, start_runtime=False)
    state = app.state.show
    state.set_scene("pumpkin_dance")
    with TestClient(app) as client:
        started = client.post("/api/show/start").json()
        assert all(
            started[k]
            for k in ("camera_requested", "projector_requested", "random_show")
        )
        assert started["active_scene"] == "pumpkin_dance"
        for _ in range(64):
            state.trigger("witch_flyby")
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"action": "show_stop", "request_id": "stop"})
            while (reply := ws.receive_json())["type"] == "status":
                pass
            assert reply["type"] == "ack"
            assert reply["request_id"] == "stop"
            assert not any(
                reply["data"][k]
                for k in ("camera_requested", "projector_requested", "random_show")
            )
        assert state.commands.empty()
        state.trigger_automatic(
            "lightning"
        )  # A frame begun before Stop cannot refill the queue.
        assert state.commands.empty()
        restored = AppState(config).snapshot()
        assert restored["active_scene"] == "pumpkin_dance"
        assert restored["active_effects"] == ["pumpkin_head", "bats"]
        assert not restored["random_show"]
        assert client.post("/api/show/invalid").status_code == 404
        assert (
            client.post(
                "/api/show/start", headers={"Origin": "https://other.example"}
            ).status_code
            == 403
        )


def test_automation_options_validate_combined_patch_and_restore(tmp_path):
    config = Config(settings_path=tmp_path / "show.json", auto_start_camera=False)
    app = create_app(config, start_runtime=False)
    with TestClient(app) as client:
        for payload in (
            {"random_min_seconds": 0},
            {"random_max_seconds": 301},
            {"random_triggers": ["reset_scene"]},
            {"random_min_seconds": "nan"},
        ):
            assert client.post("/api/settings", json=payload).status_code == 422
        before = config.settings_path.read_text()
        assert (
            client.post("/api/settings", json={"random_min_seconds": 11}).status_code
            == 400
        )
        assert config.settings_path.read_text() == before
        result = client.post(
            "/api/settings",
            json={
                "random_min_seconds": 20,
                "random_max_seconds": 30,
                "random_triggers": ["spell_burst", "witch_flyby", "witch_flyby"],
            },
        )
        assert result.status_code == 200
        assert result.json()["random_triggers"] == ["witch_flyby", "spell_burst"]
        assert (
            client.post("/api/settings", json={"random_max_seconds": 19}).status_code
            == 400
        )
        client.post("/api/settings", json={"effect_intensity": 0.4})
        restored = AppState(config).snapshot()
        assert restored["random_min_seconds"] == 20
        assert restored["random_max_seconds"] == 30
        assert restored["random_triggers"] == ["witch_flyby", "spell_burst"]
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"action": "settings", "settings": {"random_triggers": []}})
            while (reply := ws.receive_json())["type"] == "status":
                pass
            assert reply["type"] == "ack"
        assert AppState(config).snapshot()["random_triggers"] == []


def test_older_saved_file_gets_default_automation_options(tmp_path):
    from app.cues.automation import AUTO_TRIGGERS

    path = tmp_path / "show.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "active_scene": "ghost_mode",
                "active_effects": ["ghost"],
                "settings": {"random_show": False, "fullscreen": False},
            }
        )
    )
    state = AppState(Config(settings_path=path))
    s = state.snapshot()
    assert s["active_scene"] == "ghost_mode"
    assert not s["random_show"]
    assert (s["random_min_seconds"], s["random_max_seconds"]) == (3, 10)
    assert s["random_triggers"] == list(AUTO_TRIGGERS)
    state.settings(SettingsPatch(random_min_seconds=2))
    assert AppState(Config(settings_path=path)).snapshot()["random_min_seconds"] == 2


def test_reversed_saved_timing_is_rejected_before_any_setting_is_applied(tmp_path):
    path = tmp_path / "show.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "active_scene": "ghost_mode",
                "active_effects": ["ghost"],
                "settings": {"random_min_seconds": 20, "random_max_seconds": 10},
            }
        )
    )
    s = AppState(Config(settings_path=path)).snapshot()
    assert s["settings_save_error"]
    assert s["active_scene"] == "normal_camera"
    assert (s["random_min_seconds"], s["random_max_seconds"]) == (3, 10)
