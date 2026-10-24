"""Shader correctness checks may use software EGL; never hardware acceptance."""

import multiprocessing as mp

import numpy as np
import pytest

from app.renderer.gpu_process import RenderMailbox, encode_people, decode_people
from app.tracking.models import Point, PersonTrackingData


@pytest.fixture
def renderer():
    moderngl = pytest.importorskip("moderngl")
    from app.renderer.gpu import GpuRenderer

    try:
        context = moderngl.create_standalone_context(require=330, backend="egl")
    except Exception as exc:
        pytest.skip(f"EGL context unavailable: {exc}")
    target = GpuRenderer(context, 320, 180, allow_software=True)
    yield target
    target.close()
    context.release()


def test_mailbox_atomic_sequence_latest_and_capacity():
    mailbox = RenderMailbox(mp.get_context("spawn"), 8, 6)
    for number in range(1, 8):
        assert mailbox.publish(np.full((6, 8, 3), number, np.uint8), {"number": number})
    sequence, frame, metadata = mailbox.latest()
    assert sequence == 7 and metadata["number"] == 7
    assert np.all(frame == 7)
    assert metadata["stride"] == 24 and metadata["pixel_format"] == "BGR8"
    assert mailbox.latest(sequence) is None
    with mailbox.lock:
        assert not mailbox.publish(frame, {})
        assert mailbox.latest() is None
    assert mailbox.dropped == 1
    with pytest.raises(ValueError):
        mailbox.publish(np.zeros((7, 8, 3), np.uint8), {})
    with pytest.raises(ValueError):
        mailbox.publish(frame, {"oversized": "a" * 65536})


def test_pose_wire_round_trip():
    person = PersonTrackingData(9, {"head": Point(0.25, 0.4, 0.8)}, (0, 0, 1, 1), 0.9)
    restored = decode_people(encode_people([person]))[0]
    assert restored == person


def test_bgr_orientation_letterbox_alpha_and_clipping(renderer):
    source = np.full((120, 160, 3), (10, 20, 30), np.uint8)
    source[:60] = (40, 50, 60)
    canvas = renderer.begin(source)
    assert canvas.shape == (180, 240, 3) and canvas.offset == (40, 0)
    sprite = np.full((8, 8, 4), (200, 100, 50, 255), np.uint8)
    canvas.sprite(sprite, 120, 90, 40, 40, alpha=0.5)
    # A sprite crossing the viewport must not paint the letterbox.
    canvas.sprite(sprite, 0, 90, 80, 80)
    output = renderer.read()
    assert np.allclose(output[10, 50], (40, 50, 60), atol=1)
    assert np.allclose(output[170, 50], (10, 20, 30), atol=1)
    assert np.allclose(output[95, 160], (105, 60, 40), atol=2)
    assert np.all(output[:, :40] == (15, 10, 20))
    assert np.all(output[:, 280:] == (15, 10, 20))


def test_all_cues_and_heads_draw_on_shader_canvas(renderer):
    from app.cues.animations import create_cues
    from app.effects.pumpkin_head import PumpkinHead
    from app.effects.witch import Witch
    from app.effects.frankenstein import Frankenstein
    from app.effects.vampire import Vampire
    from app.effects.mummy import Mummy

    person = PersonTrackingData(
        1,
        {
            "head": Point(0.5, 0.4),
            "left_shoulder": Point(0.3, 0.6),
            "right_shoulder": Point(0.7, 0.55),
        },
        (0.2, 0.2, 0.8, 0.9),
        1,
    )
    source = np.zeros((120, 160, 3), np.uint8)
    for effect in (PumpkinHead(), Witch(), Frankenstein(), Vampire(), Mummy()):
        canvas = renderer.begin(source)
        effect.update(canvas, [person], 1 / 30)
        effect.render(canvas)
        assert renderer.read()[:, 40:280].max() > 40, effect.name
    for cue in create_cues().values():
        canvas = renderer.begin(source)
        cue.trigger()
        cue.elapsed = cue.duration * 0.5
        cue.update(canvas, [], 1 / 30)
        cue.render(canvas)
        assert renderer.read()[:, 40:280].max() > 40, cue.name


def test_software_backend_rejected_by_default():
    from types import SimpleNamespace
    from app.renderer.gpu import GpuRenderer

    fake_context = SimpleNamespace(
        info={
            "GL_VENDOR": "Mesa",
            "GL_RENDERER": "llvmpipe (LLVM 21.1.8)",
            "GL_VERSION": "4.5",
        }
    )
    with pytest.raises(RuntimeError, match="Software OpenGL renderer rejected"):
        GpuRenderer(fake_context, 320, 180)
