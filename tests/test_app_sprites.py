"""The app's sprites (tools/asset_generation/app_sprites.py, D-111): the savings plant, the bed plants,
the jar and the Home extras, cut from the kit's own drawing code and enlarged nearest-neighbour; the
portrait box the app paints faces through (D-125); and the face rules that matter once a face is
shown large."""
import json
import re
from pathlib import Path

import numpy as np
import pytest

from tools.asset_generation import app_sprites as s
from tools.asset_generation import characters as ch
from tools.asset_generation.palette import IDX, TIMES, TRANSPARENT, to_rgba

OUT = Path(__file__).resolve().parents[1] / "assets" / "app" / "sprites"


def test_enlarge_is_nearest_neighbour():
    a = np.array([[1, 2], [3, TRANSPARENT]])
    big = s.enlarge(a, 3)
    assert big.shape == (6, 6)
    assert (big[:3, :3] == 1).all() and (big[3:, 3:] == TRANSPARENT).all()   # whole blocks, no blending


def test_trim_cuts_to_the_opaque_pixels():
    a = np.full((10, 8), TRANSPARENT)
    a[2:5, 3:6] = 7
    assert s.trim(a).shape == (3, 3)


@pytest.fixture(scope="module")
def sprites():
    return s.sprites()


def test_five_plants_and_no_portraits(sprites):
    """D-127: portraits are painted by the app from the atlas (D-125), so no portrait files are made."""
    assert sorted(n for n in sprites if n.startswith("plant_")) == [f"plant_{k}" for k in range(5)]
    assert not [n for n in sprites if n.startswith("portrait_")]
    assert not list(OUT.glob("*/portrait_*.png")), "stale: run python -m tools.asset_generation.app_sprites"


def test_each_game_badge_earned_not_yet_and_small(sprites):
    """D-127: the Home points panel shows the game's three badges (shared/game.json "badges", the names
    engine/game.py awards), earned or not yet, x4; the pill shows earned ones at x2."""
    from engine.game import load_game

    from tools.asset_generation.app_icons import BADGE_COLOURS, badge
    rules = load_game()["badges"]
    assert sorted(BADGE_COLOURS) == sorted(k.split("_months")[0].split("_streak")[0] for k in rules)
    assert {n for n in sprites if n.startswith("badge_")} == {
        f"badge_{b}{v}" for b in BADGE_COLOURS for v in ("", "_locked", "_small")}
    for b in BADGE_COLOURS:
        assert (sprites[f"badge_{b}"] == s.enlarge(badge(b), s.BADGE_SCALE)).all()
        assert (sprites[f"badge_{b}_locked"] == s.enlarge(badge(b, earned=False), s.BADGE_SCALE)).all()
        assert sprites[f"badge_{b}_small"].shape == (24 * s.BADGE_SCALE // 2,) * 2


def test_the_app_paints_portraits_through_the_same_box():
    """app/src/lib/character.ts repeats PORTRAIT_BOX (a TypeScript file can't import Python)."""
    ts = (Path(__file__).resolve().parents[1] / "app" / "src" / "lib" / "character.ts").read_text(encoding="utf-8")
    m = re.search(r"export const PORTRAIT_BOX[^=]*=\s*\[([^\]]*)\]", ts)
    assert m and tuple(int(v) for v in m.group(1).split(",")) == s.PORTRAIT_BOX


def test_every_bed_plant_at_every_stage_and_every_jar_fill(sprites):
    """D-115: the Home cards show the plants and the jar as they grow and fill."""
    from engine.game import load_game
    plants = load_game()["garden"]["plants"]
    assert {n for n in sprites if n.startswith("crop_")} == {
        f"crop_{p}_{s}" for p in plants for s in ("seedling", "young", "full")}
    assert sorted(n for n in sprites if n.startswith("jar_")) == [f"jar_{k}" for k in range(5)]


def test_every_extra_has_a_crisp_tile_of_about_the_same_height(sprites):
    """D-120: the Home extras' picker shows each decoration, the tree's 7 stages and a chicken, each
    enlarged by a whole number (crisp) to about TILE_PX tall, whatever the piece's own size."""
    from engine.game import load_game
    decor = load_game()["decorations"]
    assert {n for n in sprites if n.startswith("decor_")} == {f"decor_{d}" for d in decor["room"] + decor["garden"]}
    assert sorted(n for n in sprites if n.startswith("tree_")) == [f"tree_{k}" for k in range(7)]
    for n in [n for n in sprites if n.startswith(("decor_", "tree_"))] + ["chicken"]:
        art = sprites[n]
        k = next(k for k in range(6, 0, -1) if art.shape[0] % k == 0 and art.shape[1] % k == 0
                 and (s.enlarge(art[::k, ::k], k) == art).all())               # its whole-number enlargement
        assert k == max(1, min(6, round(s.TILE_PX / (art.shape[0] // k)))), n
        assert art.shape[0] <= 2 * s.TILE_PX and (art.shape[0] >= s.TILE_PX / 2 or k == 6), n   # tiny: x6 at most


def test_the_portrait_box_holds_the_head_and_raised_arms(sprites):
    """Nothing opaque is cut off at the top or the sides, even with arms up (celebrating)."""
    x0, y0, x1, y1 = s.PORTRAIT_BOX
    for look in ch.AVATARS:
        for mood in ch.MOODS:
            f = ch.avatar(look, "front", face=mood, arms="up" if mood == "celebrating" else "down")
            above = f[:y1]                                               # the bust: everything above the cut
            ys, xs = np.nonzero(above != TRANSPARENT)
            assert ys.min() >= y0 and xs.min() >= x0 and xs.max() < x1, f"{look.name} {mood}"


def test_files_on_disk_match_the_code(sprites):
    from PIL import Image
    doc = json.loads((OUT / "sprites.json").read_text(encoding="utf-8"))
    assert sorted(doc["sprites"]) == sorted(sprites), "stale: run python -m tools.asset_generation.app_sprites"
    for name, entry in doc["sprites"].items():
        assert set(entry["files"]) == set(TIMES)
        for t, rel in entry["files"].items():
            on_disk = np.asarray(Image.open(OUT / rel).convert("RGBA"))
            assert (on_disk == to_rgba(sprites[name], t)).all(), f"stale: {rel}"


def test_the_atlas_holds_every_kit_piece_pixel_for_pixel():
    """D-114: the Home scene draws from these three pages and taps against their boxes; a kit change
    must regenerate them (python -m tools.asset_generation.app_sprites)."""
    from PIL import Image
    doc = json.loads((s.ATLAS / "atlas.json").read_text(encoding="utf-8"))
    layout, height = s.atlas_layout(s.piece_boxes())
    assert doc["pieces"] == layout and doc["size"] == [s.ATLAS_W, height], "stale atlas"
    manifest = json.loads((s.KIT / "manifest.json").read_text(encoding="utf-8"))
    pages = {t: np.asarray(Image.open(s.ATLAS / f"{t}.png").convert("RGBA")) for t in TIMES}
    for p in manifest["pieces"]:
        x, y, w, h, ox, oy = layout[p["name"]]
        cw, ch_ = p["canvas"]
        assert 0 <= ox and ox + w <= cw and 0 <= oy and oy + h <= ch_, p["name"]
        for t in TIMES:
            piece = np.asarray(Image.open(s.KIT / p["files"][t]).convert("RGBA"))
            assert (pages[t][y:y + h, x:x + w] == piece[oy:oy + h, ox:ox + w]).all(), f"{p['name']} {t}"
            outside = piece.copy()
            outside[oy:oy + h, ox:ox + w, 3] = 0
            assert not outside[..., 3].any(), f"{p['name']}: opaque pixels outside its box"
    boxes = [(x, y, x + w, y + h) for x, y, w, h, _, _ in layout.values() if w]
    for i, a in enumerate(boxes):                                     # no two pieces overlap on a page
        for b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
    assert layout["savings_plant_2"][3] < 152                         # far smaller than its canvas


def _face(face):
    c = np.full((ch.STRUCT_H, ch.STRUCT_W), TRANSPARENT, np.int16)
    ch._face(c, ch.CX, 89, face, blink=False)
    return c


def test_focused_reads_determined_not_angry():
    """Brows angled in read as cross on a large face (D-111): focused has level brows and a smile."""
    ys, _ = np.nonzero(_face("focused") == IDX["hair_dark"])
    assert len(set(ys)) == 1                                             # level brows
    ys, _ = np.nonzero(_face("focused") == IDX["red_dark"])
    assert len(set(ys)) == 2                                             # the mouth curves up at the ends


def test_celebrating_arms_stay_clear_of_the_head():
    """Raised arms hugging the head read as ears (D-111): at the hands' height every row shows three
    separate shapes (hand, head, hand), with background between them. (Lower down, wavy curls and
    the tudung are wider than a head, so the sleeves may touch them, as arms do.)"""
    hy = ch.FOOT[1] - ch.HEAD_Y
    for look in ch.AVATARS:
        up = ch.avatar(look, "front", face="celebrating", arms="up")
        for y in range(hy - 9, hy - 6):
            opaque = (up[y] != TRANSPARENT).astype(int)
            runs = int(opaque[0]) + int((np.diff(opaque) == 1).sum())
            assert runs >= 3, f"{look.name}: row {y - hy} has {runs} shapes"
