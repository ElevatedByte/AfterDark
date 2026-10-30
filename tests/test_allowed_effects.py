import pytest

from app.config import Config
from app.cues.automation import TRIGGER_EFFECTS
from app.cues.catalog import LIVE_CUES
from app.effects.manager import EffectManager
from app.state.app_state import AppState, EFFECTS, SettingsPatch


@pytest.mark.parametrize("name", EFFECTS)
def test_sidebar_exclusion_overrides_scene_and_person(name, make_person):
    state = AppState(Config())
    person = make_person()
    state.update(
        active_effects=list(EFFECTS),
        person_effects={str(person.id): ["witch" if name == "magic" else name]},
    )
    manager = EffectManager()
    manager.sync(state.snapshot())
    assert manager.applies(name, person)
    state.settings(SettingsPatch(disabled_effects=[name]))
    manager.sync(state.snapshot())
    assert not manager.applies(name, person)
    assert not manager.effects[name].enabled
    assert not manager.effects[name].alive
    state.settings(SettingsPatch(disabled_effects=[]))
    manager.sync(state.snapshot())
    assert manager.applies(name, person)


@pytest.mark.parametrize(
    "trigger,target", [*TRIGGER_EFFECTS.items(), *((n, n) for n in LIVE_CUES)]
)
def test_exclusion_stops_active_and_blocks_all_trigger_paths(trigger, target):
    state = AppState(Config(random_show=True))
    manager = EffectManager()
    manager.sync(state.snapshot())
    assert manager.trigger(trigger, [], manual=True)
    state.settings(SettingsPatch(disabled_effects=[target]))
    manager.sync(state.snapshot())
    effect = manager.cues.get(target) or manager.effects[target]
    assert not effect.alive
    assert not manager.trigger(trigger, [], manual=True)
    assert not manager.trigger(trigger, [], manual=False)
    with pytest.raises(ValueError, match="turned off"):
        state.trigger(trigger)
    state.trigger_automatic(trigger)
    assert state.commands.empty()


def test_normal_scene_random_pool_and_persistence(tmp_path):
    config = Config(settings_path=tmp_path / "show.json")
    state = AppState(config)
    disabled = [name for name in EFFECTS if name != "pumpkin_head"]
    state.settings(SettingsPatch(disabled_effects=disabled))
    assigned = state.sync_person_effects(set(range(1, 20)), set(range(1, 20)))
    assert all(value == ["pumpkin_head"] for value in assigned.values())
    state.set_scene("ghost_mode")
    restored = AppState(config)
    assert restored.snapshot()["disabled_effects"] == disabled
    manager = EffectManager()
    manager.sync(restored.snapshot())
    assert not manager.effects["ghost"].enabled
    restored.settings(SettingsPatch(disabled_effects=list(EFFECTS)))
    restored.set_scene("normal_camera")
    assert restored.sync_person_effects({1}, {1}) == {}


def test_invalid_exclusion_rejected():
    with pytest.raises(ValueError):
        SettingsPatch(disabled_effects=["unknown"])


def test_sidebar_settings_over_http_and_websocket(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import create_app

    config = Config(settings_path=tmp_path / "show.json")
    with TestClient(create_app(config, start_runtime=False)) as client:
        response = client.post("/api/settings", json={"disabled_effects": ["ghost"]})
        assert response.status_code == 200
        assert response.json()["disabled_effects"] == ["ghost"]
        assert client.post("/api/trigger/ghost_appearance").status_code == 400
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json(
                {
                    "action": "settings",
                    "settings": {"disabled_effects": ["ghost", "creeping_fog"]},
                }
            )
            while True:
                reply = ws.receive_json()
                if reply.get("data", {}).get("disabled_effects") == [
                    "ghost",
                    "creeping_fog",
                ]:
                    break
        assert client.post("/api/trigger/creeping_fog").status_code == 400
        assert client.post("/api/scene/ghost_mode").json()["disabled_effects"] == [
            "ghost",
            "creeping_fog",
        ]
    assert AppState(config).snapshot()["disabled_effects"] == ["ghost", "creeping_fog"]
