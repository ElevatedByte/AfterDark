import numpy as np
import pytest
from app.config import Config
from app.runtime import Runtime
from app.state.app_state import AppState, RANDOM_PERSON_EFFECTS, SCENES


def test_new_people_get_one_effect_and_keep_it_through_dropout(
    make_person, monkeypatch
):
    choices = iter(["pumpkin_head", "skeleton", "witch"])
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
    assert state.snapshot()["person_effects"] == {str(newcomer.id): ["witch"]}


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
        assert assigned == {str(identity): effects or ["pumpkin_head"]}

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


@pytest.mark.parametrize("scene", list(SCENES))
def test_every_scene_has_one_appearance_and_matched_magic(
    make_person, monkeypatch, scene
):
    monkeypatch.setattr("app.state.app_state.random.choice", lambda pool: pool[0])
    state = AppState(Config())
    state.set_scene(scene)
    runtime = Runtime(Config(), state)
    frame = np.zeros((240, 320, 3), np.uint8)

    def step(now):
        people = runtime.process_frame(
            frame.copy(),
            [make_person(x=0.3), make_person(x=0.7)],
            0.033,
            now,
            state.snapshot(),
            True,
        )[1]
        state.update(people=[{"id": p.id, "confidence": 0.9} for p in people])
        for person in people:
            assert runtime.effects.applies("magic", person) == (
                runtime.effects.appearance(person) in ("witch", "vampire")
            )
            assert any(
                runtime.effects.applies(name, person) for name in RANDOM_PERSON_EFFECTS
            )
        assert {p.id for p in runtime.effects.effects["magic"].people} == {
            p.id
            for p in people
            if runtime.effects.appearance(p) in ("witch", "vampire")
        }
        return people

    people = step(0)
    identity = people[0].id
    for effects in (["magic"], [], None, ["witch"]):
        state.assign_person(identity, effects)
        step(0.1)
        assigned = state.snapshot()["person_effects"].copy()
        step(0.2)
        assert state.snapshot()["person_effects"] == assigned
    assert runtime.effects.applies("witch", people[0])
    state.trigger("reset_tracking")
    fresh = step(2)
    assert fresh[0].id != identity


def test_disabled_appearance_replaced_but_global_off_respected(make_person):
    from app.state.app_state import SettingsPatch

    state = AppState(Config())
    state.update(person_effects={"1": ["magic"]})
    assignments = state.sync_person_effects(set(), {1})
    appearance = next(
        name for name in assignments["1"] if name in RANDOM_PERSON_EFFECTS
    )
    state.settings(SettingsPatch(disabled_effects=[appearance, "magic"]))
    state.sync_person_effects(set(), {1})
    from app.effects.manager import EffectManager

    manager = EffectManager()
    manager.sync(state.snapshot())
    person = make_person(1)
    assert not manager.applies("magic", person)
    assert not manager.applies(appearance, person)
    assert any(manager.applies(name, person) for name in RANDOM_PERSON_EFFECTS)
    state.settings(SettingsPatch(disabled_effects=list(RANDOM_PERSON_EFFECTS)))
    state.sync_person_effects(set(), {1})
    manager.sync(state.snapshot())
    assert not manager.applies("magic", person)
    assert not any(manager.applies(name, person) for name in RANDOM_PERSON_EFFECTS)
