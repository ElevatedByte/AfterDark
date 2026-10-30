from app.cues.automation import TRIGGER_EFFECTS, trigger_allowed
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
from app.state.app_state import RANDOM_PERSON_EFFECTS


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
        self.mummy_body = Skeleton()
        self.cues = create_cues()
        self.scene_revision = -1
        self.active = set()
        self.disabled = set()
        self.assignments = {}

    def reset(self):
        for effect in (*self.effects.values(), self.mummy_body, *self.cues.values()):
            effect.reset()

    @property
    def active_cues(self):
        return [name for name, cue in self.cues.items() if cue.alive]

    def sync(self, snapshot):
        if self.scene_revision != snapshot["scene_revision"]:
            self.reset()
            self.scene_revision = snapshot["scene_revision"]
        self.disabled = set(snapshot.get("disabled_effects", []))
        self.active = set(snapshot["active_effects"]) - self.disabled
        self.assignments = snapshot["person_effects"]
        for name, cue in self.cues.items():
            if name in self.disabled:
                cue.reset()
            cue.settings = snapshot["effect_settings"]
        needed = self.active | {e for es in self.assignments.values() for e in es}
        if needed & {"witch", "vampire"}:
            needed.add("magic")
        else:
            needed.discard("magic")
        self.mummy_body.settings = snapshot["effect_settings"]
        for name, effect in self.effects.items():
            effect.settings = snapshot["effect_settings"]
            if name in self.disabled:
                effect.disable()
            elif name in needed:
                effect.enable()
            elif effect.enabled:
                effect.disable()

    def appearance(self, person):
        selected = self.assignments.get(str(person.id), self.active)
        return next(
            (
                name
                for name in RANDOM_PERSON_EFFECTS
                if name in selected and name not in self.disabled
            ),
            None,
        )

    def applies(self, name, person):
        if name in self.disabled:
            return False
        appearance = self.appearance(person)
        if name == "magic":
            return appearance in ("witch", "vampire")
        if name in RANDOM_PERSON_EFFECTS:
            return name == appearance
        return name in self.assignments.get(str(person.id), self.active)

    def trigger(self, name, people, manual=False):
        if name == "stop_animations":
            for cue in self.cues.values():
                cue.reset()
            return True
        if not trigger_allowed(name, self.disabled):
            return False
        if name in self.cues:
            self.cues[name].trigger()
            return True
        target = TRIGGER_EFFECTS.get(name)
        if not target:
            return False
        selected = (
            people
            if manual and target != "magic"
            else [p for p in people if self.applies(target, p)]
        )
        if target == "magic" and people and not selected:
            return False
        if not manual and not selected:
            return False
        self.effects[target].trigger(selected)
        return True

    def render(self, frame, people, dt):
        mummies = [p for p in people if self.appearance(p) == "mummy"]
        self.mummy_body.update(frame, mummies, dt)
        frame = self.mummy_body.render_body(frame)
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
