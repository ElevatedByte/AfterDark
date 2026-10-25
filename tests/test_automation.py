import random

from app.config import Config
from app.cues.automation import AUTO_TRIGGERS, RandomShow
from app.state.app_state import AppState, SettingsPatch


def test_random_show_intervals_exclusions_and_no_catchup():
    show = RandomShow(random.Random(42))
    now = 100.0
    assert show.tick(now, True) is None
    previous = None
    for _ in range(100):
        assert 3 <= show.deadline - now <= 10
        assert show.tick(show.deadline - 0.001, True) is None
        now = show.deadline
        trigger = show.tick(now, True, active_cues=("witch_flyby",))
        assert trigger in AUTO_TRIGGERS
        assert trigger != "witch_flyby"
        assert trigger != previous
        previous = trigger
    now += 1000
    assert show.tick(now, True) in AUTO_TRIGGERS
    assert show.tick(now, True) is None
    assert 3 <= show.deadline - now <= 10


def test_pause_and_resume_starts_a_fresh_delay():
    show = RandomShow(random.Random(1))
    show.tick(0, True)
    assert show.tick(100, False) is None
    assert show.deadline is None
    assert show.tick(200, True) is None
    assert 203 <= show.deadline <= 210


def test_operator_can_pause_and_stop_animations_disables_automation():
    state = AppState(Config(random_show=True))
    assert state.snapshot()["random_show"]
    state.settings(SettingsPatch(random_show=False))
    assert not state.snapshot()["random_show"]
    state.settings(SettingsPatch(random_show=True))
    state.trigger("stop_animations")
    assert not state.snapshot()["random_show"]
    assert state.commands.get_nowait() == "stop_animations"
    assert not set(AUTO_TRIGGERS) & {"reset_scene", "reset_tracking", "stop_animations", "scream"}
