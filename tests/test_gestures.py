from app.config import Config
from app.tracking.gesture_detector import GestureDetector
from app.tracking.models import Point


def detector():
    return GestureDetector(Config(hands_above_duration=0.3, gesture_cooldown=0.4))


def test_hands_above_are_held_then_latched(make_person):
    d = detector()
    p = make_person(left=(0.3, 0.1), right=(0.7, 0.1))
    events = []
    for i in range(20):
        events += d.update([p], i * 0.1)
    assert [e.name for e in events].count("hands_above_head") == 1
    d.update([make_person()], 2)
    events = []
    for i in range(6):
        events += d.update([p], 2.1 + i * 0.1)
    assert any(e.name == "hands_above_head" for e in events)


def test_hands_together_hysteresis_and_cooldown(make_person):
    d = detector()
    p = make_person(left=(0.48, 0.4), right=(0.52, 0.4))
    assert d.update([p], 0)[0].name == "hands_together"
    assert not d.update([p], 1)
    d.update([make_person()], 1.1)
    assert d.update([p], 1.2)[0].name == "hands_together"


def test_jump_once_until_landing(make_person):
    d = detector()
    events = []
    for i, y in enumerate(
        [0.60, 0.60, 0.58, 0.54, 0.50, 0.49, 0.50, 0.49, 0.50, 0.54, 0.60]
    ):
        events += d.update([make_person(y=y)], i * 0.1)
    assert [e.name for e in events].count("jump") == 1
    events = []
    for i, y in enumerate([0.60, 0.58, 0.54, 0.50]):
        events += d.update([make_person(y=y)], 1.2 + i * 0.1)
    assert any(e.name == "jump" for e in events)


def test_wave_requires_multiple_direction_changes(make_person):
    d = detector()
    events = []
    for i, x in enumerate([0.2, 0.32, 0.2, 0.32, 0.2]):
        events += d.update([make_person(left=(x, 0.22))], i * 0.15)
    assert any(e.name == "wave" for e in events)


def test_no_gestures_on_low_confidence_or_tracking_gap(make_person):
    d = detector()
    p = make_person(left=(0.3, 0.1), right=(0.7, 0.1))
    p.landmarks["left_hand"] = Point(0.3, 0.1, 0.05)
    assert not d.update([p], 0)
    assert not d.update([p], 1)
    p = make_person(left=(0.3, 0.1), right=(0.7, 0.1))
    d.update([p], 2)
    assert not d.update([p], 3)
    d.reset()
    assert not d.people
