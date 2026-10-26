"""T-22 / T-16: the app icon, splash and badge icons (tools/asset_generation/app_icons.py)."""
import numpy as np
import pytest
from PIL import Image

from engine.game import load_game
from tools.asset_generation import app_icons as ai
from tools.asset_generation.palette import IDX, palettes

OUTPUTS = ai.outputs()
AFTERNOON = {tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in palettes()["afternoon"].values()}


def test_the_files_expo_needs():
    assert {"icon.png", "adaptive-icon.png", "splash.png", "favicon.png"} <= set(OUTPUTS)
    for name in ("icon.png", "adaptive-icon.png", "splash.png"):
        assert OUTPUTS[name][0].shape == (1024, 1024)
    assert (OUTPUTS["icon.png"][0] >= 0).all()                                    # the store icon is opaque
    assert (OUTPUTS["splash.png"][0] < 0).any() and (OUTPUTS["splash.png"][0] >= 0).any()


def test_adaptive_icon_stays_inside_androids_safe_circle():
    """Android masks the 108 dp layer to many shapes; only the middle 66 dp circle is always shown."""
    fg = OUTPUTS["adaptive-icon.png"][0]
    ys, xs = np.nonzero(fg >= 0)
    assert len(ys) and (np.hypot(xs + 0.5 - 512, ys + 0.5 - 512) <= 1024 * 66 / 108 / 2).all()
    assert (fg < 0).any()                                                         # the background is app.json's colour


def test_badges_are_the_games_three_earned_and_locked():
    names = {k for k in load_game()["badges"] if not k.startswith("_")}
    expected = {"cushion_builder", "steady_saver", "honest_tracker"}
    assert set(ai.BADGE_COLOURS) == expected and all(any(n.startswith(b.split("_")[0]) for n in names) for b in expected)
    for name in expected:
        for suffix in ("", "_locked"):
            for scale in (1, 4, 8):
                arr, s = OUTPUTS[f"badges/{name}{suffix}@{scale}x.png"]
                assert arr.shape == (24, 24) and s == scale
        locked = ai.badge(name, earned=False)
        allowed = {IDX[c] for c in ai.LOCKED} | {IDX["outline_soft"], -1}
        assert set(np.unique(locked)) <= allowed                                  # grey: not earned yet
        assert not (ai.badge(name) == locked).all()


@pytest.mark.parametrize("rel", sorted(OUTPUTS))
def test_on_disk_palette_only_hard_alpha_and_up_to_date(rel):
    arr, scale = OUTPUTS[rel]
    img = np.asarray(Image.open(ai.OUT / rel).convert("RGBA"))
    assert img.shape[:2] == (arr.shape[0] * scale, arr.shape[1] * scale), "stale: run python -m tools.asset_generation.app_icons"
    assert set(np.unique(img[..., 3])) <= {0, 255}
    colours = {tuple(px) for px in img[img[..., 3] == 255][:, :3].reshape(-1, 3)}
    assert colours <= AFTERNOON
    expect = np.kron(arr, np.ones((scale, scale), dtype=np.int16)) if scale > 1 else arr
    assert ((img[..., 3] == 255) == (expect >= 0)).all()
