"""Time-based gestures. No graphics or model dependencies; events are edge-triggered."""

from collections import deque
from dataclasses import dataclass, field


@dataclass(frozen=True)
class GestureEvent:
    person_id: int
    name: str
    trigger: str


@dataclass
class Memory:
    last_seen: float = 0.0
    raised_since: float | None = None
    raised_latched: bool = False
    together: bool = False
    airborne: bool = False
    ground: float | None = None
    hip_history: deque = field(default_factory=lambda: deque(maxlen=30))
    waves: dict = field(default_factory=dict)
    cooldowns: dict = field(default_factory=dict)


class GestureDetector:
    def __init__(self, config):
        self.config = config
        self.people = {}

    def reset(self):
        self.people.clear()

    def update(self, people, now):
        self.people = {
            i: m
            for i, m in self.people.items()
            if now - m.last_seen <= self.config.track_timeout
        }
        events = []
        for p in people:
            m = self.people.setdefault(p.id, Memory())
            # A gap is not continuous evidence for a held pose or a jump.
            if now - m.last_seen > 0.3:
                m.raised_since = None
                m.hip_history.clear()
                m.waves.clear()
                m.ground = None
                m.airborne = False
            m.last_seen = now

            def emit(name, trigger):
                if now >= m.cooldowns.get(name, 0):
                    events.append(GestureEvent(p.id, name, trigger))
                    m.cooldowns[name] = now + self.config.gesture_cooldown

            head, left, right = p.head, p.left_hand, p.right_hand
            raised = bool(
                head
                and left
                and right
                and left.y < head.y - 0.025
                and right.y < head.y - 0.025
            )
            if raised:
                if m.raised_since is None:
                    m.raised_since = now
                if (
                    now - m.raised_since >= self.config.hands_above_duration
                    and not m.raised_latched
                ):
                    emit("hands_above_head", "spawn_bats")
                    m.raised_latched = True
            else:
                m.raised_since = None
                m.raised_latched = False
            if left and right:
                distance = left.distance(right)
                if distance < self.config.hands_together_distance and not m.together:
                    emit("hands_together", "spell_burst")
                    m.together = True
                if distance > self.config.hands_together_distance * 1.4:
                    m.together = False
            else:
                m.together = False
            if all(p.hips):
                hip = p.center.y
                if m.ground is None:
                    m.ground = hip
                while m.hip_history and now - m.hip_history[0][0] > 0.6:
                    m.hip_history.popleft()
                m.hip_history.append((now, hip))
                if len(m.hip_history) >= 3:
                    t0, y0 = m.hip_history[0]
                    speed = (hip - y0) / max(0.001, now - t0)
                    if (
                        not m.airborne
                        and m.ground - hip > self.config.jump_threshold
                        and speed < -0.15
                    ):
                        emit("jump", "lightning")
                        m.airborne = True
                    elif (
                        m.airborne
                        and hip >= m.ground - self.config.jump_threshold * 0.35
                    ):
                        m.airborne = False
                        m.hip_history.clear()
                        m.hip_history.append((now, hip))
                    elif not m.airborne and abs(speed) < 0.1:
                        m.ground = 0.98 * m.ground + 0.02 * hip
            else:
                m.hip_history.clear()
                m.ground = None
                m.airborne = False
            for side, hand in [("left", left), ("right", right)]:
                if not hand or not head or hand.y > head.y + 0.2:
                    m.waves.pop(side, None)
                    continue
                wave = m.waves.setdefault(
                    side, {"anchor": hand.x, "direction": 0, "turns": deque()}
                )
                dx = hand.x - wave["anchor"]
                if abs(dx) > 0.045:
                    direction = 1 if dx > 0 else -1
                    if wave["direction"] and direction != wave["direction"]:
                        wave["turns"].append(now)
                    wave["direction"] = direction
                    wave["anchor"] = hand.x
                while wave["turns"] and now - wave["turns"][0] > 1.5:
                    wave["turns"].popleft()
                if len(wave["turns"]) >= 3:
                    emit("wave", "spawn_bats")
                    wave["turns"].clear()
        return events
