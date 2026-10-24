import pytest
from app.tracking.models import PersonTrackingData, Point


@pytest.fixture
def make_person():
    def make(identity=1, x=0.5, y=0.6, head_y=0.25, left=(0.3, 0.4), right=(0.7, 0.4)):
        points = {
            "head": Point(x, head_y),
            "left_shoulder": Point(x - 0.1, 0.35),
            "right_shoulder": Point(x + 0.1, 0.35),
            "left_elbow": Point(x - 0.15, 0.4),
            "right_elbow": Point(x + 0.15, 0.4),
            "left_hand": Point(*left),
            "right_hand": Point(*right),
            "left_hip": Point(x - 0.07, y),
            "right_hip": Point(x + 0.07, y),
            "left_knee": Point(x - 0.07, y + 0.15),
            "right_knee": Point(x + 0.07, y + 0.15),
            "left_ankle": Point(x - 0.07, 0.9),
            "right_ankle": Point(x + 0.07, 0.9),
            "left_foot": Point(x - 0.1, 0.92),
            "right_foot": Point(x + 0.1, 0.92),
        }
        return PersonTrackingData(
            identity, points, (x - 0.15, 0.2, x + 0.15, 0.95), 0.9
        )

    return make
