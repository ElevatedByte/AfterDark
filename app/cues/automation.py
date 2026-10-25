"""Server-owned random show timing, independent of connected controllers."""

import random
from app.cues.catalog import LIVE_CUES

AUTO_TRIGGERS = (
    *LIVE_CUES,
    "lightning",
    "spawn_bats",
    "ghost_appearance",
    "spell_burst",
)
AUTO_CATALOG = {
    **{
        name: {"label": cue["label"], "group": "Visitors"}
        for name, cue in LIVE_CUES.items()
    },
    **{
        name: {"label": label, "group": "Effects"}
        for name, label in (
            ("lightning", "Lightning"),
            ("spawn_bats", "Bats"),
            ("ghost_appearance", "Ghost appearance"),
            ("spell_burst", "Magic burst"),
        )
    },
}


class RandomShow:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self.deadline = None
        self.previous = None
        self.options = None

    def tick(
        self,
        now,
        enabled,
        active_cues=(),
        minimum=3,
        maximum=10,
        included=AUTO_TRIGGERS,
    ):
        options = (minimum, maximum, tuple(included))
        if options != self.options:
            self.deadline = None
            self.options = options
        if not enabled or not included:
            self.deadline = None
            return None
        if self.deadline is None:
            self.deadline = now + self.rng.uniform(minimum, maximum)
        if now < self.deadline:
            return None
        # Schedule from now: delayed frames never generate a catch-up burst.
        self.deadline = now + self.rng.uniform(minimum, maximum)
        available = [name for name in included if name not in active_cues]
        choices = [name for name in available if name != self.previous] or available
        if not choices:
            return None
        self.previous = self.rng.choice(choices)
        return self.previous
