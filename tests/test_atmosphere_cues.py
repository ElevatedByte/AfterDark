import numpy as np
import pytest

from app.cues.animations import create_cues
from app.cues import atmosphere_art
from app.renderer import sprites


@pytest.mark.parametrize("name", ["creeping_fog", "haunted_eyes", "ghost_portal"])
def test_dynamic_animation_keeps_sprite_cache_bounded(name):
    cue = create_cues()[name]
    frame = np.full((180, 320, 3), 35, np.uint8)
    cue.trigger()
    for _ in range(180):
        cue.update(frame, [], cue.duration / 180)
        cue.render(frame.copy())
        assert len(cue._scaled) <= 4
    cue.update(frame, [], 0.1)
    assert not cue.alive
    assert np.array_equal(cue.render(frame.copy()), frame)


def test_new_art_has_alpha_and_portal_center_is_open():
    for name in ("fog_bank", "haunted_eyes", "portal_ring"):
        image = sprites.load_sprite(name)
        assert image is not None
        assert image.shape[2] == 4 and image.dtype == np.uint8
        alpha = image[:, :, 3]
        assert np.any(alpha == 0) and np.any(alpha > 128)
        assert not image.flags.writeable
    portal = sprites.load_sprite("portal_ring")
    h, w = portal.shape[:2]
    assert portal[h // 2, w // 2, 3] == 0
    eyes = sprites.load_sprite("haunted_eyes")
    middle = eyes.shape[1] // 2
    assert np.any(eyes[:, :middle, 3] > 128)
    assert np.any(eyes[:, middle:, 3] > 128)


def test_missing_new_assets_still_produce_transparent_fallbacks(tmp_path, monkeypatch):
    sprites.load_sprite.cache_clear()
    with monkeypatch.context() as patch:
        patch.setattr(sprites, "ASSET_DIR", tmp_path)
        for factory in (
            atmosphere_art.fog_bank,
            atmosphere_art.haunted_eyes,
            atmosphere_art.portal_ring,
        ):
            image = factory()
            assert image.shape[2] == 4
            assert np.any(image[:, :, 3] == 0)
            assert np.any(image[:, :, 3] > 32)  # Fog is intentionally translucent.
    sprites.load_sprite.cache_clear()
