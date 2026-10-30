from collections import Counter

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.main import create_app
from app.renderer.scenery import Scenery, layout
from app.state.app_state import AppState, SettingsPatch


def test_layout_counts_clear_center_ground_and_seed_repeatability():
    state = AppState(Config()).snapshot()
    state.update(
        scenery_houses=2, scenery_graves=12, scenery_pumpkins=16, scenery_trees=4
    )
    for seed in range(100):
        state["scenery_seed"] = seed
        items = layout(state)
        assert items == layout(state)
        assert Counter(i["kind"] for i in items) == {
            "scenery_house": 2,
            "scenery_tree": 4,
            "gravestone": 12,
            "scenery_pumpkin": 16,
        }
        for i, item in enumerate(items):
            x, y, w, h = (item[k] for k in ("x", "y", "w", "h"))
            assert 0 <= x < x + w <= 1 and 0 <= y < y + h <= 1
            assert x + w <= 0.285 or x >= 0.715
            assert 0.71 <= y + h <= 0.982
        houses = [item for item in items if item["kind"] == "scenery_house"]
        assert all(item["w"] >= 0.24 and item["h"] >= 0.47 for item in houses)
        props = [item for item in items if item["kind"] != "scenery_house"]
        assert max(item["w"] for item in props) > min(item["w"] for item in props) * 1.5
        grounds = [item["y"] + item["h"] for item in items]
        assert grounds == sorted(grounds)
        assert len(set(round(g, 4) for g in grounds)) > 20
    original = layout(state)
    state["scenery_seed"] += 1
    assert layout(state) != original


@pytest.mark.parametrize("size", [(1920, 1080), (640, 480), (480, 640)])
def test_render_preserves_center_cache_and_hide(size):
    state = AppState(Config()).snapshot()
    state.update(scenery_enabled=True, scenery_trees=2)
    w, h = size
    frame = np.full((h, w, 3), 25, np.uint8)
    scenery = Scenery()
    result = scenery.render(frame.copy(), state)
    assert len(scenery.sprites) == 18
    assert not np.array_equal(result, frame)
    assert np.array_equal(
        result[:, round(w * 0.30) : round(w * 0.70)],
        frame[:, round(w * 0.30) : round(w * 0.70)],
    )
    sprites = scenery.sprites
    assert np.array_equal(result, scenery.render(frame.copy(), state))
    assert scenery.sprites is sprites
    state["scenery_seed"] += 1
    scenery.render(frame.copy(), state)
    assert scenery.sprites is not sprites and len(scenery.sprites) == 18
    state["scenery_enabled"] = False
    assert np.array_equal(scenery.render(frame.copy(), state), frame)


def test_generate_save_restore_hide_and_validation(tmp_path):
    config = Config(settings_path=tmp_path / "show.json")
    with TestClient(create_app(config, start_runtime=False)) as client:
        counts = dict(
            scenery_houses=1, scenery_graves=4, scenery_pumpkins=9, scenery_trees=3
        )
        first = client.post("/api/scenery/generate", json=counts).json()
        assert first["scenery_enabled"]
        assert all(first[k] == v for k, v in counts.items())
        assert layout(AppState(config).snapshot()) == layout(first)
        second = client.post("/api/scenery/generate", json=counts).json()
        assert second["scenery_seed"] != first["scenery_seed"]
        for invalid in (
            {"scenery_houses": 3},
            {"scenery_trees": 5},
            {"scenery_trees": -1},
            {"scenery_graves": -1},
            {"scenery_pumpkins": 17},
            {"scenery_graves": 2.5},
            {"scenery_graves": True},
            {"random_show": True},
        ):
            assert client.post("/api/scenery/generate", json=invalid).status_code in (
                400,
                422,
            )
            assert (
                client.get("/api/status").json()["scenery_seed"]
                == second["scenery_seed"]
            )
        hidden = client.post("/api/settings", json={"scenery_enabled": False}).json()
        assert not hidden["scenery_enabled"]
        assert layout(hidden) == layout(second)
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json(
                {
                    "action": "scenery_generate",
                    "settings": counts,
                    "request_id": "scenery-test",
                }
            )
            while True:
                response = ws.receive_json()
                if response.get("request_id") == "scenery-test":
                    assert response["type"] == "ack"
                    assert response["data"]["scenery_seed"] != second["scenery_seed"]
                    break
    assert AppState(config).snapshot()["scenery_enabled"]


def test_zero_counts_and_scene_changes_keep_layout():
    state = AppState(Config())
    state.generate_scenery(
        SettingsPatch(scenery_houses=0, scenery_graves=0, scenery_pumpkins=0)
    )
    assert layout(state.snapshot()) == []
    seed = state.snapshot()["scenery_seed"]
    state.set_scene("ghost_mode")
    state.set_show(False)
    assert state.snapshot()["scenery_seed"] == seed


def test_adding_trees_preserves_other_objects_and_old_settings_default():
    snapshot = AppState(Config()).snapshot()
    assert snapshot["scenery_trees"] == 0
    previous = layout(snapshot)
    snapshot["scenery_trees"] = 4
    assert [
        item for item in layout(snapshot) if item["kind"] != "scenery_tree"
    ] == previous


@pytest.mark.parametrize("size", [(1920, 1080), (640, 480), (480, 640)])
def test_corner_web_modes_keep_floor_clear_and_mirror(size):
    snapshot = AppState(Config()).snapshot()
    snapshot.update(
        scenery_enabled=True,
        scenery_houses=0,
        scenery_graves=0,
        scenery_pumpkins=0,
        scenery_trees=0,
    )
    w, h = size
    blank = np.full((h, w, 3), 25, np.uint8)
    renderer = Scenery()
    results = {}
    for mode, count in [("none", 0), ("left", 1), ("right", 1), ("both", 2)]:
        snapshot["scenery_webs"] = mode
        results[mode] = renderer.render(blank.copy(), snapshot)
        assert len(renderer.webs) == count
        assert np.array_equal(
            results[mode][:, round(w * 0.30) : round(w * 0.70)],
            blank[:, round(w * 0.30) : round(w * 0.70)],
        )
        assert np.array_equal(
            results[mode][round(h * 0.41) :], blank[round(h * 0.41) :]
        )
        assert len(renderer.sprites) == 0
    assert np.array_equal(results["none"], blank)
    assert not np.array_equal(results["left"], blank)
    assert np.array_equal(results["left"][:, ::-1], results["right"])
    assert np.array_equal(results["both"][:, : w // 2], results["left"][:, : w // 2])
    assert np.array_equal(results["both"][:, w // 2 :], results["right"][:, w // 2 :])
    snapshot["scenery_enabled"] = False
    assert np.array_equal(renderer.render(blank.copy(), snapshot), blank)


def test_web_selection_saves_without_rerolling(tmp_path):
    config = Config(settings_path=tmp_path / "webs.json")
    with TestClient(create_app(config, start_runtime=False)) as client:
        initial = client.get("/api/status").json()
        assert initial["scenery_webs"] == "none"
        for mode in ("both", "left", "right", "none"):
            response = client.post("/api/settings", json={"scenery_webs": mode})
            assert response.status_code == 200
            current = response.json()
            assert current["scenery_seed"] == initial["scenery_seed"]
            assert layout(current) == layout(initial)
            assert AppState(config).snapshot()["scenery_webs"] == mode
        assert (
            client.post("/api/settings", json={"scenery_webs": "bottom"}).status_code
            == 422
        )
        generated = client.post(
            "/api/scenery/generate", json={"scenery_webs": "both"}
        ).json()
        assert generated["scenery_webs"] == "both" and generated["scenery_enabled"]
        assert AppState(config).snapshot()["scenery_webs"] == "both"
