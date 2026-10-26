"""D-122: the tab icons (tools/asset_generation/tab_icons.py) are what the code draws, inside Material's
keylines, square pixels at every scale, and plain enough for the tab bar to tint (template mode)."""
import numpy as np
import pytest
from PIL import Image

from tools.asset_generation import tab_icons as t


@pytest.mark.parametrize("name", list(t.ICONS))
def test_each_icon_on_disk_is_the_drawing_at_every_scale(name):
    g = t.ICONS[name]()
    assert g.shape == (t.SIZE, t.SIZE) and g.any()
    for suffix, k in t.SCALES.items():
        img = np.asarray(Image.open(t.OUT / f"{name}{suffix}.png").convert("RGBA"))
        assert img.shape == (t.SIZE * k, t.SIZE * k, 4), "stale: run python -m tools.asset_generation.tab_icons"
        assert (img[..., 3] > 0).tolist() == np.repeat(np.repeat(g, k, 0), k, 1).tolist(), f"stale: {name}{suffix}"
        assert set(np.unique(img[..., 3])) <= {0, 255} and not img[..., :3].any()   # black, opaque or clear


@pytest.mark.parametrize("name", list(t.ICONS))
def test_the_shape_stays_inside_the_keylines(name):
    g = t.ICONS[name]()
    rows, cols = np.flatnonzero(g.any(axis=1)), np.flatnonzero(g.any(axis=0))
    lo, hi = t.KEYLINE, t.SIZE - 1 - t.KEYLINE
    assert rows.min() >= lo and rows.max() <= hi and cols.min() >= lo and cols.max() <= hi
    assert (cols.min() + cols.max()) / 2 == pytest.approx(t.MID, abs=1)            # centred across


def test_four_different_icons_left_right_symmetric_where_the_shape_is():
    grids = {n: f() for n, f in t.ICONS.items()}
    assert len({g.tobytes() for g in grids.values()}) == 4
    for name in ("home", "add", "future"):
        assert (grids[name] == grids[name][:, ::-1]).all(), name
