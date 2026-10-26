"""T-22 batch 2 (D-86): tier 3-4 bed plants, the tree, garden decorations and where they go, and the
chickens in the kit (docs/assets/FAST_ASSET_SPEC_BATCH2.md §2, §5)."""
from functools import cache

import numpy as np
import pytest

from engine.game import load_game
from tools.asset_generation.creatures import ANIMAL_PIECES, KIT_FOOT
from tools.asset_generation.garden_decor import DECOR, GARDEN_DECOR_PIECES
from tools.asset_generation.garden_plants import BASE, PLANT_PIECES, STAGES, TIER_3_4
from tools.asset_generation.garden_tree import BASE as TREE_BASE
from tools.asset_generation.garden_tree import STAGES as TREE_STAGES
from tools.asset_generation.garden_tree import TREE_PIECES
from tools.asset_generation.geometry import struct_canvas
from tools.asset_generation.palette import IDX, NIGHT_OVERRIDES
from tools.asset_generation.scenes import (MAX_BED_STEPS, RADIUS, ROOM, TREE_CELLS, TREE_FROM_LEVEL, TREE_SPOT,
                                           VIEW_DEPTH, VIEW_HALF_WIDTH, bed_cells, bed_loop, decor_spots,
                                           garden_reserved, home_scene, scene_json)

GAME = load_game()
GREENS = [IDX["green_light"], IDX["green_mid"], IDX["green_dark"]]
GLOWS = [IDX[n] for n in NIGHT_OVERRIDES]
ALL = {p.name: p for p in PLANT_PIECES + TREE_PIECES + GARDEN_DECOR_PIECES + ANIMAL_PIECES}


@cache
def img(name):
    return ALL[name].render()


def height(a, base_y):
    return base_y - np.flatnonzero((a >= 0).any(axis=1)).min()


# ---------------------------------------------------------------- tier 3-4 plants
def test_tier_3_4_plants_follow_the_game_rules():
    tiers = GAME["garden"]["plants"]
    assert set(TIER_3_4) == {p for p, t in tiers.items() if t >= 3}
    for plant in TIER_3_4:
        for stage in STAGES:
            assert {f"plant_{plant}_{stage}", f"plant_{plant}_{stage}_droop"} <= set(ALL)


@pytest.mark.parametrize("plant", TIER_3_4)
def test_tier_3_4_heights(plant):
    """Spec §2: full 18-24 px, frangipani and torch ginger up to ~55; the jade vine climbs its own
    ~30 px trellis (D-86: not the garden arch)."""
    h = [height(img(f"plant_{plant}_{s}"), BASE[1]) for s in STAGES]
    assert h[0] < h[1] < h[2], h
    top = {"orchid": 27, "frangipani": 58, "torch_ginger": 58, "jade_vine": 40}[plant]
    assert h[0] <= 12 and h[2] <= top, h
    if plant in ("frangipani", "torch_ginger"):
        assert h[2] >= 45, h


@pytest.mark.parametrize("plant", TIER_3_4)
@pytest.mark.parametrize("stage", STAGES)
def test_tier_3_4_droop_stays_green_and_in_flower(plant, stage):
    normal, droop = img(f"plant_{plant}_{stage}"), img(f"plant_{plant}_{stage}_droop")
    assert np.isin(droop, GREENS).sum() >= 0.5 * np.isin(normal, GREENS).sum()
    assert height(droop, BASE[1]) <= height(normal, BASE[1])
    flowers = [IDX[c] for c in ("purple_light", "pink_mid", "jade_light", "wall_cream")]
    if np.isin(normal, flowers).any():
        assert np.isin(droop, flowers).any()


@pytest.mark.parametrize("plant, colour", [("orchid", "purple_light"), ("frangipani", "wall_cream"),
                                           ("torch_ginger", "pink_mid"), ("jade_vine", "jade_light")])
def test_tier_3_4_flower_when_full(plant, colour):
    assert np.isin(img(f"plant_{plant}_full"), [IDX[colour]]).any()
    assert not np.isin(img(f"plant_{plant}_seedling"), [IDX[colour]]).any()


# ---------------------------------------------------------------- the tree
def test_tree_has_seven_stages_each_with_a_droop():
    assert len(TREE_STAGES) == GAME["growth"]["tree_stages"] == 7
    assert {p.name for p in TREE_PIECES} == {f"tree_{k}_{s}{d}" for k, s in enumerate(TREE_STAGES)
                                             for d in ("", "_droop")}
    assert all(p.cells == (2, 2) for p in TREE_PIECES)


def test_tree_grows_from_a_mound_to_about_100_px():
    """Spec §2: from a 4 px mound to ~100 px; taller (or wider) at every stage, on one fixed spot."""
    hs = [height(img(f"tree_{k}_{s}"), TREE_BASE[1]) for k, s in enumerate(TREE_STAGES)]
    assert hs[0] <= 6 and 88 <= hs[-1] <= 105, hs
    assert all(a < b for a, b in zip(hs[:-2], hs[1:-1])), hs                     # flowering = mature + blossom
    sizes = [int((img(f"tree_{k}_{s}") >= 0).sum()) for k, s in enumerate(TREE_STAGES)]
    assert all(a < b for a, b in zip(sizes, sizes[1:])), sizes
    w, h, _ = struct_canvas((2, 2))
    assert all(img(p.name).shape == (h, w) for p in TREE_PIECES)


@pytest.mark.parametrize("k, stage", list(enumerate(TREE_STAGES)))
def test_tree_droop_is_darker_never_bare(k, stage):
    """D-73: in a really bad month the tree sags and darkens but keeps its stage, leaves and blossom."""
    normal, droop = img(f"tree_{k}_{stage}"), img(f"tree_{k}_{stage}_droop")
    assert np.isin(droop, GREENS).sum() >= 0.6 * np.isin(normal, GREENS).sum()
    assert height(droop, TREE_BASE[1]) <= height(normal, TREE_BASE[1])
    if k >= 1:
        light = IDX["green_light"]
        assert (droop == light).sum() < max((normal == light).sum(), 1)
    pink = [IDX["pink_light"], IDX["pink_mid"]]
    assert np.isin(normal, pink).any() == (stage == "flowering") == np.isin(droop, pink).any()


def test_tree_spot_is_free_visible_and_never_in_the_way():
    assert TREE_FROM_LEVEL == 4
    assert not TREE_CELLS & (bed_cells(4, MAX_BED_STEPS) | bed_loop(4, MAX_BED_STEPS))
    assert all(-1 < gx <= ROOM - 1 + RADIUS[4] and -1 < gy <= ROOM - 1 + RADIUS[4] for gx, gy in TREE_CELLS)
    assert all(abs(gx - gy) <= VIEW_HALF_WIDTH for gx, gy in TREE_CELLS)
    assert scene_json(4)["tree"]["cell"] == list(TREE_SPOT) and scene_json(3)["tree"] is None


# ---------------------------------------------------------------- garden decorations
def test_every_garden_decoration_is_a_piece():
    names = [n for n, *_ in DECOR]
    assert names == GAME["decorations"]["garden"]
    assert [p.name for p in GARDEN_DECOR_PIECES] == names


SPEC_HEIGHT = {"bench": 31, "bench_improved": 33, "garden_lamp": 47, "lantern": 20, "bird_bath": 31,
               "decorative_stones": 12, "garden_arch": 86, "outdoor_table": 29, "outdoor_chair": 35,
               "mailbox": 43, "bicycle_rack": 31, "fountain": 39}


@pytest.mark.parametrize("piece", GARDEN_DECOR_PIECES, ids=lambda p: p.name)
def test_garden_decoration_scale_outline_and_glow(piece):
    """Spec §2 heights, the soft garden outline, standing on its footprint, and only the lamp and the
    lantern glow at night (spec §1, E3). A point h px up shows at y = oy + a + b - h, so the top row
    of an object H px tall lies between the footprint's back corner (a = b = 0) and its middle."""
    a = img(piece.name)
    _, _, (ox, oy) = struct_canvas(piece.cells)
    w, d = piece.cells
    top, H = np.flatnonzero((a >= 0).any(axis=1)).min(), SPEC_HEIGHT[piece.name]
    assert oy - H - 3 <= top <= oy + 8 * (w + d) - H + 3, (piece.name, oy - top)
    assert (a == IDX["outline_soft"]).any() and not (a == IDX["outline"]).any()
    assert not (a[oy + 16 * (w + d):] >= 0).any()
    lit = np.isin(a, GLOWS).any()
    assert lit == (piece.name in ("garden_lamp", "lantern")), piece.name


@pytest.mark.parametrize("level", [1, 2, 3, 4])
def test_decoration_spots_never_block_and_stay_on_screen(level):
    """K2: the garden offers free lawn spots: inside the plot, on screen, never on the house, a path,
    the complete bed or its path, a planter, an animal home or the tree's spot, so nothing placed
    early ever blocks what grows later (spec §5)."""
    reserved = garden_reserved()
    assert bed_cells(4, MAX_BED_STEPS) <= reserved and bed_loop(4, MAX_BED_STEPS) <= reserved
    hi = ROOM - 1 + RADIUS[level]
    for size in ((1, 1), (1, 2), (2, 2)):
        spots = decor_spots(level, size)
        assert spots, (level, size)
        for gx, gy in spots:
            cells = {(gx + i, gy + j) for i in range(size[0]) for j in range(size[1])}
            assert not cells & reserved
            assert all(-1 < x <= hi and -1 < y <= hi for x, y in cells)
            assert all(abs(x - y) <= VIEW_HALF_WIDTH and x + y <= VIEW_DEPTH for x, y in cells)
    used = set(decor_spots(level)[:3])
    assert not set(decor_spots(level, used=used)) & used
    assert decor_spots(0) == []


def test_placed_decorations_draw_back_to_front():
    from tools.asset_generation.kit import PIECES
    cells = {p.name: p.cells for p in PIECES}
    extras = [(TREE_SPOT, "tree_6_flowering", (2, 2), 0), (decor_spots(4, (2, 2))[0], "fountain", (2, 2), 0),
              (decor_spots(4, (1, 2))[0], "bench", (1, 2), 0)]
    sc = home_scene(4, animals=(), extras=extras)
    from tools.asset_generation.scenes import order_violations
    assert not order_violations(sc["structs"], lambda s: cells[s[1]])
    assert {"tree_6_flowering", "fountain", "bench"} <= {n for _, n in sc["structs"]}


# ---------------------------------------------------------------- chickens in the kit
def test_chicken_frames_in_the_kit():
    """D-66: walk 4, peck 4, idle 2, asleep 8, on the 1 x 1 canvas with the feet at the cell centre and
    the small flat shadow (spec §1, E2); the beak no longer glints at night."""
    names = [p.name for p in ANIMAL_PIECES]
    assert names == ([f"chicken_walk_{k}" for k in range(4)] + [f"chicken_peck_{k}" for k in range(4)]
                     + [f"chicken_idle_{k}" for k in range(2)] + [f"chicken_sleep_{k}" for k in range(8)])
    for n in names:
        a = img(n)
        assert a.shape == (152, 80)
        body = (a >= 0) & (a != IDX["recess"])
        low = np.flatnonzero(body.any(axis=1)).max()
        assert low == KIT_FOOT[1] or ("sleep" in n and low == KIT_FOOT[1] - 1)    # asleep: breathing lifts it 1 px
        assert set(np.flatnonzero((a == IDX["recess"]).any(axis=1))) <= {KIT_FOOT[1], KIT_FOOT[1] + 1}
        assert not np.isin(a, GLOWS).any()
        assert 15 <= height(a, KIT_FOOT[1] + 1) <= 32                       # ~27 px standing (D-66), lower asleep
        assert (a == IDX["zed"]).any() == (n in {f"chicken_sleep_{k}" for k in range(2, 8)})   # the drifting z
