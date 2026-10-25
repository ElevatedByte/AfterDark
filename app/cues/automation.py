"""Server-owned random show timing, independent of connected controllers."""

import random
from app.cues.catalog import LIVE_CUES

AUTO_TRIGGERS = (*LIVE_CUES, "lightning", "spawn_bats", "ghost_appearance", "spell_burst")


class RandomShow:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.deadline = None
        self.previous = None

    def tick(self, now, enabled, active_cues=()):
        if not enabled:
            self.deadline = None
            return None
        if self.deadline is None:
            self.deadline = now + self.rng.uniform(3, 10)
        if now < self.deadline:
            return None
        # Schedule from now: delayed frames never generate a catch-up burst.
        self.deadline = now + self.rng.uniform(3, 10)
        choices = [
            name for name in AUTO_TRIGGERS
            if name != self.previous and name not in active_cues
        ]
        if not choices:
            return None
        self.previous = self.rng.choice(choices)
        return self.previous
