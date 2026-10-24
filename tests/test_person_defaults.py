import numpy as np
import pytest
from app.config import Config
from app.runtime import Runtime
from app.state.app_state import AppState, RANDOM_PERSON_EFFECTS, SCENES


def test_new_people_get_one_effect_and_keep_it_through_dropout(
    make_person, monkeypatch
):
    choices = iter(["pumpkin_head", "skeleton", "magic"])
    picked = []

    def choose(pool):
        assert pool == RANDOM_PERSON_EFFECTS
        result = next(choices)
        picked.append(result)
        return result

    monkeypatch.setattr("app.state.app_state.random.choice", choose)
    state = AppState(Config())
    runtime = Runtime(Config(), state)
    frame = np.zeros((240, 320, 3), np.uint8)

    def step(detections, now):
        return runtime.process_frame(
            frame.copy(), detections, 0.033, now, state.snapshot(), True
        )[1]

    people = step([make_person(x=0.25), make_person(x=0.75)], 0)
    first, second = [p.id for p in people]
    expected = {str(first): ["pumpkin_head"], str(second): ["skeleton"]}
    assert state.snapshot()["person_effects"] == expected
    assert [p.id for p in runtime.effects.effects["pumpkin_head"].people] == [first]
    assert [p.id for p in runtime.effects.effects["skeleton"].people] == [second]
    step([make_person(x=0.74), make_person(x=0.26)], 0.1)
    step([], 0.2)
    step([make_person(x=0.25), make_person(x=0.75)], 0.4)
    assert state.snapshot()["person_effects"] == expected
    assert len(picked) == 2
    step([], 2)
    assert state.snapshot()["person_effects"] == {}
    newcomer = step([make_person(x=0.25)], 2.1)[0]
    assert newcomer.id not in (first, second)
    assert state.snapshot()["person_effects"] == {str(newcomer.id): ["magic"]}


def test_operator_choices_and_scene_reset_are_not_randomized_again(
    make_person, monkeypatch
):
    monkeypatch.setattr(
        "app.state.app_state.random.choice", lambda pool: "pumpkin_head"
    )
    state = AppState(Config())
    runtime = Runtime(Config(), state)
    frame = np.zeros((240, 320, 3), np.uint8)

    def step(now, snapshot=None):
        people = runtime.process_frame(
            frame.copy(),
            [make_person()],
            0.033,
            now,
            snapshot or state.snapshot(),
            True,
        )[1]
        state.update(people=[{"id": people[0].id, "confidence": 0.9}])
        return people[0].id

    identity = step(0)
    for effects in (None, [], ["skeleton"]):
        stale_snapshot = state.snapshot()
        state.assign_person(identity, effects)
        step(0.1, stale_snapshot)
        assigned = state.snapshot()["person_effects"]
        assert assigned == ({} if effects is None else {str(identity): effects})

    state.set_scene("ghost_mode")
    step(0.2)
    assert state.snapshot()["person_effects"] == {}
    assert runtime.effects.applies("ghost", runtime.identities.tracks[identity].person)
    state.trigger("reset_tracking")
    new_identity = step(0.3)
    assert new_identity != identity
    assert state.snapshot()["person_effects"] == {}
    assert runtime.effects.applies(
        "ghost", runtime.identities.tracks[new_identity].person
    )
    state.set_scene("normal_camera")
    step(0.4)
    assert state.snapshot()["person_effects"] == {str(new_identity): ["pumpkin_head"]}


@pytest.mark.parametrize("scene", [name for name in SCENES if name != "normal_camera"])
def test_themed_scenes_apply_to_existing_and_new_people(
    make_person, monkeypatch, scene
):
    monkeypatch.setattr(
        "app.state.app_state.random.choice", lambda pool: "pumpkin_head"
    )
    state = AppState(Config())
    runtime = Runtime(Config(), state)
    frame = np.zeros((240, 320, 3), np.uint8)

    def step(people, now):
        tracked = runtime.process_frame(
            frame.copy(), people, 0.033, now, state.snapshot(), True
        )[1]
        state.update(people=[{"id": p.id, "confidence": 0.9} for p in tracked])
        return tracked

    existing = step([make_person(x=0.25)], 0)[0]
    assert state.snapshot()["person_effects"] == {str(existing.id): ["pumpkin_head"]}
    state.set_scene(scene)

    def no_random_in_themed_mode(pool):
        pytest.fail("A themed scene must not generate random assignments")

    monkeypatch.setattr("app.state.app_state.random.choice", no_random_in_themed_mode)
    people = step([make_person(x=0.25), make_person(x=0.75)], 0.1)
    assert state.snapshot()["person_effects"] == {}
    for person in people:
        applied = {
            name
            for name in runtime.effects.effects
            if runtime.effects.applies(name, person)
        }
        assert applied == set(SCENES[scene])
    # The scene supplies the starting effect; operator choices stay editable.
    state.assign_person(existing.id, ["magic"])
    step([make_person(x=0.25), make_person(x=0.75)], 0.15)
    assert state.snapshot()["person_effects"] == {str(existing.id): ["magic"]}
    assert runtime.effects.applies(
        "magic", runtime.identities.tracks[existing.id].person
    )
    assert {
        name
        for name in runtime.effects.effects
        if runtime.effects.applies(name, people[1])
    } == set(SCENES[scene])
    step([], 0.2)
    step([make_person(x=0.25)], 0.3)
    assert state.snapshot()["person_effects"] == {str(existing.id): ["magic"]}
    state.assign_person(existing.id, [])
    step([make_person(x=0.25)], 0.32)
    assert not any(
        runtime.effects.applies(name, runtime.identities.tracks[existing.id].person)
        for name in runtime.effects.effects
    )
    state.assign_person(existing.id, None)
    step([make_person(x=0.25)], 0.35)
    assert state.snapshot()["person_effects"] == {}
    assert {
        name
        for name in runtime.effects.effects
        if runtime.effects.applies(name, runtime.identities.tracks[existing.id].person)
    } == set(SCENES[scene])
    state.trigger("reset_tracking")
    step([make_person(x=0.25)], 0.4)
    assert state.snapshot()["person_effects"] == {}

    monkeypatch.setattr("app.state.app_state.random.choice", lambda pool: "skeleton")
    state.set_scene("normal_camera")
    people = step([make_person(x=0.25)], 0.5)
    assert state.snapshot()["person_effects"] == {str(people[0].id): ["skeleton"]}
    step([make_person(x=0.25)], 0.6)
    assert state.snapshot()["person_effects"] == {str(people[0].id): ["skeleton"]}
