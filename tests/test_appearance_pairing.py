import numpy as np

from app.config import Config
from app.effects.manager import EffectManager
from app.state.app_state import AppState, EFFECTS, RANDOM_PERSON_EFFECTS, SettingsPatch


def test_mixed_people_get_exactly_one_head_and_matching_layers(make_person):
    names = [
        "witch",
        "vampire",
        "mummy",
        "skeleton",
        "pumpkin_head",
        "frankenstein",
        "ghost",
    ]
    people = [make_person(i + 1) for i in range(len(names))]
    state = AppState(Config())
    state.update(
        active_effects=list(EFFECTS),
        person_effects={str(p.id): [name] for p, name in zip(people, names)},
    )
    manager = EffectManager()
    manager.sync(state.snapshot())
    manager.render(np.zeros((240, 320, 3), np.uint8), people, 0.033)
    for p, name in zip(people, names):
        assert [e for e in RANDOM_PERSON_EFFECTS if manager.applies(e, p)] == [name]
    assert [p.id for p in manager.effects["magic"].people] == [1, 2]
    assert [p.id for p in manager.mummy_body.people] == [3]
    assert [p.id for p in manager.effects["mummy"].people] == [3]
    assert [p.id for p in manager.effects["skeleton"].people] == [4]
    assert set(manager.effects["skeleton"].poses) == {4}
    state.settings(SettingsPatch(disabled_effects=["magic"]))
    manager.sync(state.snapshot())
    assert not any(manager.applies("magic", p) for p in people)
    assert manager.applies("witch", people[0])
    assert manager.applies("vampire", people[1])


def test_legacy_stacked_scene_and_overrides_are_normalized(make_person):
    state = AppState(Config())
    state.update(
        active_effects=list(EFFECTS),
        person_effects={"1": ["witch", "mummy", "skeleton", "magic"]},
    )
    assigned = state.sync_person_effects({2, 3}, {1, 2, 3})
    assert assigned["1"] == ["magic", "witch"]
    assert all(
        len(set(effects) & set(RANDOM_PERSON_EFFECTS)) == 1
        for effects in assigned.values()
    )
    assert state.sync_person_effects(set(), {1, 2, 3}) == assigned
    # Even a stale/un-normalized snapshot cannot draw multiple appearances.
    state.update(person_effects={"1": list(EFFECTS)})
    manager = EffectManager()
    manager.sync(state.snapshot())
    assert (
        sum(manager.applies(name, make_person(1)) for name in RANDOM_PERSON_EFFECTS)
        == 1
    )


def test_manual_magic_burst_only_targets_matching_people(make_person, monkeypatch):
    state = AppState(Config())
    state.update(person_effects={"1": ["mummy"], "2": ["witch"]})
    manager = EffectManager()
    manager.sync(state.snapshot())
    recipients = []
    monkeypatch.setattr(
        manager.effects["magic"],
        "trigger",
        lambda people: recipients.extend(p.id for p in people),
    )
    assert manager.trigger("spell_burst", [make_person(1), make_person(2)], manual=True)
    assert recipients == [2]
    assert not manager.trigger("spell_burst", [make_person(1)], manual=True)
