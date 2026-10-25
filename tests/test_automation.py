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
    assert not set(AUTO_TRIGGERS) & {
        "reset_scene",
        "reset_tracking",
        "stop_animations",
        "scream",
    }


def test_custom_timing_and_changed_options_reset_pending_delay():
    show = RandomShow(random.Random(5))
    assert show.tick(0, True, minimum=30, maximum=40, included=["lightning"]) is None
    assert 30 <= show.deadline <= 40
    assert (
        show.tick(2, True, minimum=1.5, maximum=1.5, included=["spell_burst"]) is None
    )
    assert show.deadline == 3.5
    assert (
        show.tick(3.5, True, minimum=1.5, maximum=1.5, included=["spell_burst"])
        == "spell_burst"
    )
    assert (
        show.tick(5, True, minimum=1.5, maximum=1.5, included=["spell_burst"])
        == "spell_burst"
    )


def test_empty_selection_pauses_and_single_visitor_waits_until_finished():
    show = RandomShow(random.Random(1))
    assert show.tick(0, True, included=[]) is None
    assert show.deadline is None
    options = dict(minimum=1, maximum=1, included=["witch_flyby"])
    assert show.tick(10, True, **options) is None
    assert show.tick(11, True, **options) == "witch_flyby"
    assert show.tick(12, True, active_cues=["witch_flyby"], **options) is None
    assert show.tick(13, True, **options) == "witch_flyby"
    assert show.tick(14, True, included=[]) is None
    assert show.deadline is None


def test_removed_choice_cannot_be_enqueued_by_a_stale_processing_frame():
    state = AppState(Config(random_show=True))
    state.settings(SettingsPatch(random_triggers=["spell_burst"]))
    state.trigger_automatic("lightning")
    assert state.commands.empty()
    state.trigger_automatic("spell_burst")
    assert state.commands.get_nowait() == "spell_burst"
    state.settings(SettingsPatch(random_triggers=[]))
    state.set_show(True)
    assert state.snapshot()["random_triggers"] == []
    state.trigger_automatic("spell_burst")
    assert state.commands.empty()
