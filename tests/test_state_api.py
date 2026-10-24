from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.config import Config
from app.main import create_app
from app.state.app_state import AppState, SettingsPatch, EFFECTS


def test_state_copies_and_thread_safety():
    state = AppState(Config())

    def work(i):
        state.settings(SettingsPatch(effect_intensity=(i % 10) / 10))
        state.set_effect("bats", bool(i % 2))

    with ThreadPoolExecutor(4) as pool:
        list(pool.map(work, range(100)))
    snap = state.snapshot()
    snap["active_effects"].append("fake")
    snap["effect_settings"]["effect_intensity"] = 7
    assert "fake" not in state.snapshot()["active_effects"]
    assert 0 <= state.snapshot()["effect_settings"]["effect_intensity"] <= 1


def test_http_scenes_toggles_settings_and_invalid_commands():
    app = create_app(Config(auto_start_camera=False), start_runtime=False)
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert "Afterdark" in client.get("/").text
        for scene in (
            "normal_camera",
            "pumpkin_dance",
            "skeleton_dance",
            "ghost_mode",
            "magic_mode",
        ):
            r = client.post("/api/scene/" + scene)
            assert r.status_code == 200
            assert r.json()["active_scene"] == scene
        for name in EFFECTS:
            assert (
                name
                in client.post(f"/api/effects/{name}/enable").json()["active_effects"]
            )
            assert (
                name
                not in client.post(f"/api/effects/{name}/disable").json()[
                    "active_effects"
                ]
            )
        assert (
            client.post(
                "/api/settings", json={"fullscreen": False, "tracking_smoothing": 0.3}
            ).json()["fullscreen"]
            is False
        )
        assert client.post("/api/settings", json={"max_people": 0}).status_code == 422
        assert (
            client.post("/api/settings", json={"effect_intensity": 2}).status_code
            == 422
        )
        assert client.post("/api/settings", json={"unknown": True}).status_code == 422
        assert client.post("/api/scene/nope").status_code == 400
        assert client.post("/api/effects/nope/enable").status_code == 400
        assert client.post("/api/trigger/nope").status_code == 400
        assert client.post("/api/camera/start").json()["camera_requested"]
        assert not client.post("/api/camera/stop").json()["camera_requested"]
        assert client.post("/api/projector/start").json()["projector_requested"]
        assert not client.post("/api/projector/stop").json()["projector_requested"]
        assert (
            client.post("/api/trigger/reset_scene").json()["active_scene"]
            == "normal_camera"
        )
        assert (
            client.post("/api/trigger/reset_tracking").json()["tracking_revision"] == 1
        )


def test_websocket_commands_and_errors():
    with TestClient(create_app(Config(), start_runtime=False)) as client:
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "status"
            ws.send_json(
                {"action": "scene", "value": "pumpkin_dance", "request_id": "a"}
            )
            while (message := ws.receive_json())["type"] == "status":
                pass
            assert message["type"] == "ack" and message["request_id"] == "a"
            assert message["data"]["active_scene"] == "pumpkin_dance"
            ws.send_json({"action": "settings", "settings": {"particle_amount": 5}})
            while (message := ws.receive_json())["type"] == "status":
                pass
            assert message["type"] == "error"
            ws.send_text("not-json")
            while (message := ws.receive_json())["type"] == "status":
                pass
            assert message["type"] == "error"


def test_person_override_and_cross_origin():
    app = create_app(Config(), start_runtime=False)
    app.state.show.update(people=[{"id": 2, "confidence": 0.9}])
    with TestClient(app) as client:
        assert client.post(
            "/api/people/2/effects", json={"effects": ["pumpkin_head"]}
        ).json()["person_effects"] == {"2": ["pumpkin_head"]}
        assert (
            client.post("/api/people/2/effects", json={"effects": None}).json()[
                "person_effects"
            ]
            == {}
        )
        assert (
            client.post("/api/people/7/effects", json={"effects": []}).status_code
            == 400
        )
        assert (
            client.post(
                "/api/scene/ghost_mode", headers={"Origin": "https://unrelated.example"}
            ).status_code
            == 403
        )
