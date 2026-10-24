from app.cues.animations import create_cues
from app.effects.pumpkin_head import PumpkinHead
from app.effects.witch import Witch
from app.effects.frankenstein import Frankenstein
from app.effects.vampire import Vampire
from app.effects.mummy import Mummy
from app.effects.skeleton import Skeleton
from app.effects.bats import Bats
from app.effects.ghost import Ghost
from app.effects.magic import Magic
from app.effects.lightning import Lightning


class EffectManager:
    def __init__(self):
        self.effects = {
            effect.name: effect
            for effect in [
                Ghost(),
                Skeleton(),
                PumpkinHead(),
                Witch(),
                Frankenstein(),
                Vampire(),
                Mummy(),
                Bats(),
                Magic(),
                Lightning(),
            ]
        }
        self.cues = create_cues()
        self.scene_revision = -1
        self.active = set()
        self.assignments = {}

    def reset(self):
        for effect in (*self.effects.values(), *self.cues.values()):
            effect.reset()

    @property
    def active_cues(self):
        return [name for name, cue in self.cues.items() if cue.alive]

    def sync(self, snapshot):
        if self.scene_revision != snapshot["scene_revision"]:
            self.reset()
            self.scene_revision = snapshot["scene_revision"]
        self.active = set(snapshot["active_effects"])
        self.assignments = snapshot["person_effects"]
        for cue in self.cues.values():
            cue.settings = snapshot["effect_settings"]
        needed = self.active | {e for es in self.assignments.values() for e in es}
        for name, effect in self.effects.items():
            effect.settings = snapshot["effect_settings"]
            if name in needed:
                effect.enable()
            elif effect.enabled:
                effect.disable()

    def applies(self, name, person):
        return name in self.assignments.get(str(person.id), self.active)

    def trigger(self, name, people, manual=False):
        if name == "stop_animations":
            for cue in self.cues.values():
                cue.reset()
            return True
        if name in self.cues:
            self.cues[name].trigger()
            return True
        target = {
            "spawn_bats": "bats",
            "ghost_appearance": "ghost",
            "spell_burst": "magic",
            "lightning": "lightning",
        }.get(name)
        if not target:
            return False
        selected = people if manual else [p for p in people if self.applies(target, p)]
        if not manual and not selected:
            return False
        self.effects[target].trigger(selected)
        return True

    def render(self, frame, people, dt):
        for name, effect in self.effects.items():
            selected = [p for p in people if self.applies(name, p)]
            if effect.enabled or effect.alive:
                effect.update(frame, selected, dt)
                frame = effect.render(frame)
        for cue in self.cues.values():
            if cue.alive:
                cue.update(frame, [], dt)
                frame = cue.render(frame)
        return frame
