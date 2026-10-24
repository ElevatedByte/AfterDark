import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.cues.catalog import LIVE_CUES
from app.effects.manager import EffectManager
from app.main import create_app
from app.runtime import Runtime
from app.state.app_state import AppState, EFFECTS, RANDOM_PERSON_EFFECTS, SettingsPatch


@pytest.mark.parametrize("name", LIVE_CUES)
def test_cue_moves_expires_restarts_and_respects_intensity(name):
    state = AppState(Config())
    manager = EffectManager()
    manager.sync(state.snapshot())
    frame = np.full((360, 640, 3), 45, np.uint8)
    assert set(manager.effects).isdisjoint(LIVE_CUES)
    assert set(RANDOM_PERSON_EFFECTS).isdisjoint(LIVE_CUES)
    assert manager.trigger(name, [], manual=True)
    cue = manager.cues[name]
    early = manager.render(frame.copy(), [], cue.duration * 0.30)
    middle = manager.render(frame.copy(), [], cue.duration * 0.20)
    assert early.dtype == frame.dtype and early.shape == frame.shape
    assert np.any(early != frame), name
    assert np.any(middle != early), name
    assert manager.active_cues == [name]
    ended = manager.render(frame.copy(), [], cue.duration)
    assert np.array_equal(ended, frame)
    assert not manager.active_cues

    # Repeated clicks reuse a single timeline and cached artwork.
    assets = cue.assets
    for _ in range(100):
        manager.trigger(name, [], manual=True)
    replay = manager.render(frame.copy(), [], cue.duration * 0.30)
    assert np.array_equal(early, replay)
    assert cue.assets is assets and manager.active_cues == [name]
    state.settings(SettingsPatch(effect_intensity=0))
    manager.sync(state.snapshot())
    assert np.array_equal(manager.render(frame.copy(), [], 0.1), frame)
    manager.render(frame.copy(), [], cue.duration)
    assert not manager.active_cues


def test_cues_overlap_resize_and_cancel_without_changing_person_effects():
    state = AppState(Config())
    state.set_scene("pumpkin_dance")
    state.update(people=[{"id": 1}], person_effects={"1": ["witch"]})
    manager = EffectManager()
    manager.sync(state.snapshot())
    for name in LIVE_CUES:
        assert manager.trigger(name, [], manual=True)
    assert set(manager.active_cues) == set(LIVE_CUES)
    for h, w in ((720, 1280), (480, 640), (240, 320), (480, 270)):
        frame = np.full((h, w, 3), 45, np.uint8)
        result = manager.render(frame.copy(), [], 0.25)
        assert result.shape == frame.shape and result.dtype == np.uint8
        assert np.any(result != frame)
    manager.trigger("stop_animations", [], manual=True)
    assert not manager.active_cues
    assert manager.active == {"pumpkin_head", "bats"}
    assert manager.assignments == {"1": ["witch"]}
    assert set(manager.effects) == set(EFFECTS)
    assert all(len(cue._scaled) <= 4 for cue in manager.cues.values())


def test_runtime_publishes_playback_and_clears_on_resets():
    state = AppState(Config())
    runtime = Runtime(Config(), state)
    frame = np.zeros((240, 320, 3), np.uint8)

    def step(dt=0.1):
        runtime.process_frame(frame.copy(), [], dt, 1, state.snapshot(), False)

    for reset in ("stop_animations", "reset_scene", "reset_tracking"):
        for name in LIVE_CUES:
            state.trigger(name)
        step()
        assert set(state.snapshot()["active_cues"]) == set(LIVE_CUES)
        assert state.snapshot()["person_effects"] == {}
        state.trigger(reset)
        step()
        assert state.snapshot()["active_cues"] == []
    state.trigger("skeleton_peek")
    step()
    state.set_scene("magic_mode")
    step()
    assert not state.snapshot()["active_cues"]
    state.trigger("black_cat")
    step()
    step(10)
    assert not state.snapshot()["active_cues"]


def test_cue_catalog_and_commands_over_http_and_websocket():
    app = create_app(Config(auto_start_camera=False), start_runtime=False)
    state = app.state.show
    with TestClient(app) as client:
        assert client.get("/api/status").json()["cue_catalog"] == LIVE_CUES
        assert client.get("/api/status").json()["active_cues"] == []
        for name in (*LIVE_CUES, "stop_animations"):
            response = client.post("/api/trigger/" + name)
            assert response.status_code == 200
            assert state.commands.get_nowait() == name
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "status"
            for name in (*LIVE_CUES, "stop_animations"):
                ws.send_json({"action": "trigger", "value": name, "request_id": name})
                while (message := ws.receive_json())["type"] == "status":
                    pass
                assert message["type"] == "ack" and message["request_id"] == name
                assert state.commands.get_nowait() == name
