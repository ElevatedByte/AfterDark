from types import SimpleNamespace
from app.tracking.models import map_landmarks, LANDMARK_INDEX, Point
from app.tracking.person_tracker import PersonTracker


def test_normalized_mapping_all_required_joints():
    lms = [
        SimpleNamespace(x=i / 40, y=0.4, visibility=0.9, presence=0.8)
        for i in range(33)
    ]
    person = map_landmarks(lms)
    assert len(person.landmarks) == len(LANDMARK_INDEX)
    assert person.left_hand.x == 15 / 40
    assert person.right_hand.x == 16 / 40
    assert person.shoulders[0].x == 11 / 40
    assert person.feet[1].x == 32 / 40
    assert person.confidence == 0.8 or abs(person.confidence - 0.8) < 1e-8


def test_missing_and_invalid_landmarks_do_not_escape_bounds():
    lms = [
        SimpleNamespace(x=-0.3, y=1.4, visibility=0.8, presence=1) for _ in range(33)
    ]
    assert map_landmarks(lms) is None
    lms[0] = SimpleNamespace(x=0.4, y=0.3, visibility=0.8, presence=1)
    lms[11] = SimpleNamespace(x=float("nan"), y=0.3, visibility=0.8, presence=1)
    p = map_landmarks(lms)
    assert p.head.x == 0.4 and p.left_hand is None
    assert all(0 <= v.x <= 1 and 0 <= v.y <= 1 for v in p.landmarks.values())
    assert "left_shoulder" not in p.landmarks


def test_ids_survive_order_changes_and_brief_occlusion(make_person):
    tracker = PersonTracker(smoothing=0)
    p = tracker.update([make_person(x=0.25), make_person(x=0.75)], 0)
    left, right = [person.id for person in p]
    swapped = tracker.update([make_person(x=0.74), make_person(x=0.26)], 0.1)
    assert [person.id for person in swapped] == [right, left]
    assert tracker.update([], 0.2) == []
    assert tracker.update([make_person(x=0.27)], 0.5)[0].id == left
    assert tracker.update([make_person(x=0.27)], 2)[0].id != left


def test_smoothing_and_low_confidence(make_person):
    tracker = PersonTracker(smoothing=0.65)
    initial = tracker.update([make_person(x=0.3)], 0)[0]
    moved = make_person(x=0.4)
    moved.landmarks["left_hand"] = Point(0.4, 0.3, 0.1)
    next_person = tracker.update([moved], 1 / 30)[0]
    assert initial.head.x < next_person.head.x < 0.4
    assert next_person.left_hand is None
    tracker.reset()
    assert tracker.update([make_person(x=0.4)], 0.1)[0].id > initial.id
