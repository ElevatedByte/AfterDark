from dataclasses import dataclass
import math
import random
from app.effects.base import Effect
from app.tracking.models import Point


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    age: float = 0.0
    phase: float = 0.0


class ParticleEffect(Effect):
    cap = 600

    def initialize(self):
        self.particles = []
        self.hands = {}
        self.rng = random.Random()
        self.spawn_credit = {}

    def reset(self):
        super().reset()
        self.particles = []
        self.hands = {}
        self.spawn_credit = {}

    @property
    def alive(self):
        return bool(self.particles)

    def emit(self, point, count, speed=0.25):
        for _ in range(min(count, self.cap - len(self.particles))):
            angle = self.rng.uniform(0, math.tau)
            self.particles.append(
                Particle(
                    point.x,
                    point.y,
                    math.cos(angle) * speed,
                    self.rng.uniform(-speed, -0.02),
                    self.rng.uniform(0.8, 2.2),
                    phase=angle,
                )
            )

    def trigger(self, people=None):
        hands = [
            p.point(side)
            for p in (people or [])
            for side in ("left_hand", "right_hand")
            if p.point(side)
        ]
        count = round(40 * self.settings.get("particle_amount", 0.55))
        for point in hands or [Point(0.5, 0.5)]:
            self.emit(point, count, 0.4)

    def update(self, frame, tracking_data, delta_time):
        super().update(frame, tracking_data, delta_time)
        current = {}
        for p in tracking_data:
            for side in ("left_hand", "right_hand"):
                hand = p.point(side)
                if not hand:
                    continue
                key = p.id, side
                speed = (
                    hand.distance(self.hands[key]) / delta_time
                    if key in self.hands
                    else 0
                )
                current[key] = hand
                self.on_hand(hand, min(5, speed), delta_time, key)
        self.hands = current
        self.spawn_credit = {k: v for k, v in self.spawn_credit.items() if k in current}
        alive = []
        for part in self.particles:
            part.age += delta_time
            part.x += part.vx * delta_time
            part.y += part.vy * delta_time
            if part.age < part.life and -0.2 < part.x < 1.2 and -0.3 < part.y < 1.2:
                alive.append(part)
        self.particles = alive

    def on_hand(self, hand, speed, dt, key):
        pass

    def emit_rate(self, hand, rate, dt, key, speed):
        count = self.spawn_credit.get(key, 0) + rate * dt
        self.emit(hand, int(count), speed)
        self.spawn_credit[key] = count - int(count)
