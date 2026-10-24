"""Guard against accidentally rendering graphics at the inference resolution again."""

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.config import Config
from app.main import create_app
from app.runtime import Runtime
from app.state.app_state import AppState
from app.renderer import sprites
from app.effects.ghost import Ghost


@pytest.mark.parametrize(
    "camera_size,output_size",
    [
        ((640, 480), (1920, 1080)),
        ((1280, 720), (1920, 1080)),
        ((640, 480), (3840, 2160)),
        ((640, 480), (480, 640)),
    ],
)
def test_effects_render_at_output_size_and_keep_normalized_alignment(
    camera_size, output_size, make_person, monkeypatch
):
    cw, ch = camera_size
    ow, oh = output_size
    config = Config(
        camera_width=cw, camera_height=ch, output_width=ow, output_height=oh
    )
    state = AppState(config)
    runtime = Runtime(config, state)
    person = make_person(x=0.4)
    person.segmentation_mask = np.ones((ch, cw), np.float32)
    original = np.full((ch, cw, 3), 40, np.uint8)
    observed = []

    def draw(frame, people, dt):
        observed.append(frame.shape)
        assert people[0].segmentation_mask.shape == (ch, cw)
        cv2.circle(frame, people[0].head.pixel(frame), 3, (0, 0, 255), -1)
        return frame

    monkeypatch.setattr(runtime.effects, "render", draw)
    output, _ = runtime.process_frame(
        original, [person], 1 / 30, 1, state.snapshot(), True
    )
    scale = min(ow / cw, oh / ch)
    vw, vh = round(cw * scale), round(ch * scale)
    assert observed == [(vh, vw, 3)]
    assert output.shape == (oh, ow, 3)
    left, top = (ow - vw) // 2, (oh - vh) // 2
    for bar in (
        output[:top],
        output[top + vh :],
        output[top : top + vh, :left],
        output[top : top + vh, left + vw :],
    ):
        assert np.all(bar == (15, 10, 20))
    assert np.all(original == 40)
    x, y = person.head.pixel(np.empty((vh, vw, 3), np.uint8))
    assert tuple(output[(oh - vh) // 2 + y, (ow - vw) // 2 + x]) == (0, 0, 255)
    runtime.projector.shared.publish(output)
    assert np.array_equal(runtime.projector.shared.read(), output)


def test_full_size_http_snapshot_is_not_the_small_preview():
    config = Config(output_width=960, output_height=540)
    app = create_app(config, start_runtime=False)
    app.state.runtime = Runtime(config, app.state.show)
    with TestClient(app) as client:
        assert client.get("/api/output.jpg").status_code == 204
        app.state.runtime.projector.shared.publish(np.full((540, 960, 3), 90, np.uint8))
        response = client.get("/api/output.jpg")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        image = cv2.imdecode(
            np.frombuffer(response.content, np.uint8), cv2.IMREAD_COLOR
        )
        assert image.shape == (540, 960, 3)
        assert np.all(image == 90)


def test_bundled_characters_have_transparency_and_survive_missing_packs(
    monkeypatch, tmp_path
):
    from app.effects.manager import EffectManager

    for name in sprites.REGIONS:
        asset = sprites.load_sprite(name)
        assert asset is not None, name
        assert asset.shape[2] == 4 and max(asset.shape[:2]) >= 350, name
        assert asset[:, :, 3].min() == 0 and asset[:, :, 3].max() > 240, name
        assert not asset.flags.writeable
    monkeypatch.setattr(sprites, "ASSET_DIR", tmp_path)
    sprites._atlas.cache_clear()
    sprites.load_sprite.cache_clear()
    try:
        manager = EffectManager()
        for effect in manager.effects.values():
            if hasattr(effect, "asset"):
                assert effect.asset.shape[2] == 4 and effect.asset[:, :, 3].max() > 0
        for cue in manager.cues.values():
            assert all(asset[:, :, 3].max() > 0 for asset in cue.assets.values())
    finally:
        sprites._atlas.cache_clear()
        sprites.load_sprite.cache_clear()


def test_ghost_history_stays_bounded_at_4k(make_person):
    ghost = Ghost()
    person = make_person()
    person.segmentation_mask = np.ones((480, 640), np.float32)
    frame = np.zeros((2160, 3840, 3), np.uint8)
    for _ in range(12):
        ghost.update(frame, [person], 0.1)
    assert len(ghost.history) == 8
    assert ghost.small.shape[1] <= 480 and ghost.small.shape[0] <= 270
    assert all(im.shape == ghost.small.shape for im, _, _ in ghost.history)
