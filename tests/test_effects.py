import numpy as np
from app.config import Config
from app.state.app_state import AppState
from app.effects.manager import EffectManager


def test_effect_lifecycle_and_visible_output(make_person):
    state = AppState(Config())
    manager = EffectManager()
    frame = np.full((240, 320, 3), 50, np.uint8)
    people = [make_person()]
    for name, effect in manager.effects.items():
        state.set_scene("normal_camera")
        state.set_effect(name, True)
        manager.sync(state.snapshot())
        assert effect.enabled
        if name in ("lightning", "ghost", "bats", "magic"):
            effect.trigger(people)
        result = manager.render(frame.copy(), people, 0.016)
        assert result.shape == frame.shape and result.dtype == np.uint8
        assert np.any(result != frame), name
        state.set_effect(name, False)
        manager.sync(state.snapshot())
        assert not effect.enabled and not effect.alive


def test_manual_cues_work_without_active_effect_or_people():
    manager = EffectManager()
    manager.sync(AppState(Config()).snapshot())
    for cue in ("lightning", "spawn_bats", "ghost_appearance", "spell_burst"):
        assert manager.trigger(cue, [], manual=True)
    result = manager.render(np.zeros((240, 320, 3), np.uint8), [], 0.016)
    assert result.max() > 0
    for _ in range(150):
        manager.render(np.zeros((240, 320, 3), np.uint8), [], 0.05)
    assert not any(e.alive for e in manager.effects.values())


def test_assignments_filter_people_and_scene_reset(make_person):
    state = AppState(Config())
    state.set_effect("pumpkin_head", True)
    state.set_effect("bats", True)
    state.update(person_effects={"2": ["skeleton"]})
    manager = EffectManager()
    manager.sync(state.snapshot())
    manager.render(
        np.zeros((240, 320, 3), np.uint8), [make_person(1), make_person(2)], 0.016
    )
    assert [p.id for p in manager.effects["pumpkin_head"].people] == [1]
    assert [p.id for p in manager.effects["skeleton"].people] == [2]
    assert not manager.trigger("lightning", [make_person(1)])
    state.set_scene("normal_camera")
    manager.sync(state.snapshot())
    assert not any(e.enabled or e.alive for e in manager.effects.values())


def test_ghost_history_segmentation_decay_and_shape_change(make_person):
    manager = EffectManager()
    state = AppState(Config())
    state.set_scene("ghost_mode")
    manager.sync(state.snapshot())
    person = make_person()
    person.segmentation_mask = np.ones((240, 320), np.float32)
    for _ in range(20):
        manager.render(np.full((240, 320, 3), 80, np.uint8), [person], 0.1)
    ghost = manager.effects["ghost"]
    assert len(ghost.history) <= 8
    person.segmentation_mask = None
    for _ in range(30):
        manager.render(np.zeros((240, 320, 3), np.uint8), [], 0.1)
    assert not ghost.history
    manager.render(np.zeros((120, 160, 3), np.uint8), [], 0.1)


def test_particles_are_bounded_and_zero_intensity_preserves_frame(make_person):
    manager = EffectManager()
    state = AppState(Config())
    state.set_scene("magic_mode")
    state.settings(
        __import__("app.state.app_state", fromlist=["SettingsPatch"]).SettingsPatch(
            effect_intensity=0
        )
    )
    manager.sync(state.snapshot())
    effect = manager.effects["magic"]
    for _ in range(100):
        effect.trigger([make_person()])
    assert len(effect.particles) <= effect.cap
    frame = np.full((240, 320, 3), 50, np.uint8)
    assert np.array_equal(manager.render(frame.copy(), [make_person()], 0.01), frame)


def test_zero_intensity_hides_every_effect(make_person):
    from app.state.app_state import SettingsPatch

    manager = EffectManager()
    state = AppState(Config())
    state.settings(SettingsPatch(effect_intensity=0))
    frame = np.full((240, 320, 3), 50, np.uint8)
    people = [make_person()]
    for name, effect in manager.effects.items():
        state.set_scene("normal_camera")
        state.set_effect(name, True)
        manager.sync(state.snapshot())
        effect.trigger(people)
        result = manager.render(frame.copy(), people, 0.016)
        assert np.array_equal(frame, result), name
