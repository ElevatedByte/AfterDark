"""Optional local WAV/OGG cues; missing assets/devices are harmless."""

import logging
from app.config import ROOT


class SoundManager:
    def __init__(self):
        self.sounds = {}
        self.failed = False

    def play(self, name):
        if self.failed or name not in ("scream", "lightning", "ghost"):
            return
        path = next(
            (
                ROOT / "app/assets/sounds" / f"{name}.{ext}"
                for ext in ("wav", "ogg")
                if (ROOT / "app/assets/sounds" / f"{name}.{ext}").is_file()
            ),
            None,
        )
        if not path:
            return
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init()
            if name not in self.sounds:
                self.sounds[name] = pygame.mixer.Sound(str(path))
            self.sounds[name].play()
        except Exception as exc:
            logging.warning("Sound unavailable: %s", exc)
            self.failed = True

    def close(self):
        import pygame

        if pygame.mixer.get_init():
            pygame.mixer.quit()
