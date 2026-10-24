"""Small, dependency-free global matching with velocity prediction and EMA smoothing."""

from dataclasses import dataclass, replace
from functools import lru_cache
from math import hypot
from app.tracking.models import Point


@dataclass
class Track:
    person: object
    seen: float
    vx: float = 0.0
    vy: float = 0.0


class PersonTracker:
    def __init__(self, smoothing=0.65, timeout=1.2):
        self.smoothing = smoothing
        self.timeout = timeout
        self.tracks = {}
        self.next_id = 1

    def reset(self):
        self.tracks.clear()  # Never reuse an ID during this session.

    def update(self, detections, now):
        self.tracks = {
            i: t for i, t in self.tracks.items() if now - t.seen <= self.timeout
        }
        # At most 8 observations and 16 retained tracks: bounded assignment search.
        ids = list(self.tracks)
        costs = []
        for person in detections:
            row = []
            for i in ids:
                track = self.tracks[i]
                elapsed = min(0.5, now - track.seen)
                center = track.person.center
                distance = hypot(
                    person.center.x - center.x - track.vx * elapsed,
                    person.center.y - center.y - track.vy * elapsed,
                )
                old = track.person.bounding_box
                new = person.bounding_box
                size_error = abs((old[2] - old[0]) - (new[2] - new[0])) + abs(
                    (old[3] - old[1]) - (new[3] - new[1])
                )
                row.append(distance + 0.12 * size_error if distance < 0.23 else 10.0)
            costs.append(row)

        @lru_cache(None)
        def assign(index, used):
            if index == len(detections):
                return 0.0, ()
            cost, tail = assign(index + 1, used)
            best = cost + 0.28, (-1,) + tail
            for j in range(len(ids)):
                if used & (1 << j) or costs[index][j] >= 0.28:
                    continue
                tail_cost, tail = assign(index + 1, used | (1 << j))
                option = costs[index][j] + tail_cost, (j,) + tail
                if option[0] < best[0]:
                    best = option
            return best

        matching = assign(0, 0)[1]
        current = []
        for person, match in zip(detections, matching):
            if match < 0:
                identity = self.next_id
                self.next_id += 1
                person = replace(person, id=identity)
                self.tracks[identity] = Track(person, now)
            else:
                identity = ids[match]
                track = self.tracks[identity]
                elapsed = max(0.001, now - track.seen)
                retention = self.smoothing ** (elapsed * 30)
                landmarks = {}
                for key, new in person.landmarks.items():
                    old = track.person.landmarks.get(key)
                    if old and old.confidence >= 0.35 and new.confidence >= 0.35:
                        landmarks[key] = Point(
                            old.x * retention + new.x * (1 - retention),
                            old.y * retention + new.y * (1 - retention),
                            new.confidence,
                            new.depth_m,
                        )
                    else:
                        landmarks[key] = new
                raw_center = person.center
                old_center = track.person.center
                vx = max(-1, min(1, (raw_center.x - old_center.x) / elapsed))
                vy = max(-1, min(1, (raw_center.y - old_center.y) / elapsed))
                person = replace(person, id=identity, landmarks=landmarks)
                self.tracks[identity] = Track(
                    person, now, 0.5 * track.vx + 0.5 * vx, 0.5 * track.vy + 0.5 * vy
                )
            current.append(person)
        # Retain brief occlusions for matching, never render stale bodies or masks.
        if len(self.tracks) > 16:
            current_ids = {p.id for p in current}
            ordered = sorted(
                self.tracks,
                key=lambda i: (i in current_ids, self.tracks[i].seen),
                reverse=True,
            )[:16]
            self.tracks = {i: self.tracks[i] for i in ordered}
        return current
