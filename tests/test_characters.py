import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import Config
from app.effects.manager import EffectManager
from app.main import create_app
from app.state.app_state import (
    AppState,
    CHARACTER_EFFECTS,
    EFFECTS,
    RANDOM_PERSON_EFFECTS,
)
from app.tracking.models import Point


@pytest.mark.parametrize("name", ["pumpkin_head", *CHARACTER_EFFECTS])
def test_head_overlays_follow_smoothly_and_clear_missing_landmarks(name, make_person):
    effect = EffectManager().effects[name]
    frame = np.zeros((240, 320, 3), np.uint8)

    def center(person):
        effect.update(frame, [person], 1 / 60)
        output = effect.render(frame.copy())
        rows, columns = np.where(output.any(axis=2))
        return columns.mean()

    initial = center(make_person(x=0.3, head_y=0.5))
    moving = make_person(x=0.6, head_y=0.5)
    first_step = center(moving)
    for _ in range(30):
        settled = center(moving)
    assert initial < first_step < settled
    assert settled - initial == pytest.approx(0.3 * frame.shape[1], abs=2)

    # Low confidence must remove the stale face instead of leaving it floating.
    moving.landmarks["head"] = Point(0.6, 0.5, confidence=0.1)
    effect.update(frame, [moving], 1 / 30)
    assert np.array_equal(effect.render(frame.copy()), frame)
    moving.landmarks["head"] = Point(0.6, 0.5)
    del moving.landmarks["left_shoulder"]
    effect.update(frame, [moving], 1 / 30)
    assert np.array_equal(effect.render(frame.copy()), frame)
    effect.update(frame, [], 1 / 30)
    assert not effect.poses


@pytest.mark.parametrize("name", CHARACTER_EFFECTS)
def test_character_clipping_tilt_and_processing_resize(name, make_person):
    effect = EffectManager().effects[name]
    for h, w in ((480, 640), (240, 320)):
        for x, y in ((0.01, 0.01), (0.99, 0.01), (0.01, 0.99), (0.99, 0.99)):
            effect.reset()
            person = make_person(x=x, head_y=y)
            person.landmarks["left_shoulder"] = Point(0.4, 0.6)
            person.landmarks["right_shoulder"] = Point(0.6, 0.7)
            frame = np.full((h, w, 3), 50, np.uint8)
            effect.update(frame, [person], 1 / 30)
            result = effect.render(frame.copy())
            assert result.shape == frame.shape and result.dtype == np.uint8
            assert np.any(result != frame)


def test_characters_are_random_defaults_and_independently_overridable(
    make_person, monkeypatch
):
    state = AppState(Config())
    manager = EffectManager()
    assert set(manager.effects) == set(EFFECTS)
    assert set(CHARACTER_EFFECTS) <= set(RANDOM_PERSON_EFFECTS)
    people = [make_person(i + 1, x=(i + 0.5) / 4) for i in range(4)]
    choices = iter(CHARACTER_EFFECTS)
    monkeypatch.setattr("app.state.app_state.random.choice", lambda pool: next(choices))
    state.sync_person_effects({1, 2, 3, 4}, {1, 2, 3, 4})
    state.update(people=[{"id": p.id, "confidence": p.confidence} for p in people])
    manager.sync(state.snapshot())
    manager.render(np.zeros((480, 1280, 3), np.uint8), people, 1 / 30)
    for identity, name in enumerate(CHARACTER_EFFECTS, 1):
        assert [p.id for p in manager.effects[name].people] == [identity]
    state.set_scene("ghost_mode")
    state.assign_person(1, ["witch"])
    manager.sync(state.snapshot())
    manager.render(np.zeros((480, 1280, 3), np.uint8), people, 1 / 30)
    assert [p.id for p in manager.effects["witch"].people] == [1]
    assert [p.id for p in manager.effects["ghost"].people] == [2, 3, 4]


def test_character_assignments_and_expanded_combinations_over_http_and_websocket():
    app = create_app(Config(), start_runtime=False)
    app.state.show.update(people=[{"id": 1, "confidence": 0.9}])
    with TestClient(app) as client:
        # A mode default can always be changed by the operator.
        client.post("/api/scene/skeleton_dance")
        for assignment in ([name] for name in CHARACTER_EFFECTS):
            response = client.post(
                "/api/people/1/effects", json={"effects": assignment}
            )
            assert response.status_code == 200
            assert response.json()["person_effects"] == {"1": assignment}
        # The old six-item validation cap must not reject the expanded catalog.
        response = client.post("/api/people/1/effects", json={"effects": list(EFFECTS)})
        assert response.status_code == 200
        assert response.json()["person_effects"] == {"1": list(EFFECTS)}
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "status"
            for assignment in [[name] for name in CHARACTER_EFFECTS] + [
                list(EFFECTS),
                [],
                None,
            ]:
                ws.send_json(
                    {"action": "person_effects", "person_id": 1, "effects": assignment}
                )
                while (message := ws.receive_json())["type"] == "status":
                    pass
                assert message["type"] == "ack"
                assert message["data"]["person_effects"] == (
                    {} if assignment is None else {"1": assignment}
                )
