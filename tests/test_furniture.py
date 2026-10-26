"""T-22 batch 2 (D-84): room furniture and interactive objects (docs/assets/FAST_ASSET_SPEC_BATCH2.md)."""
from functools import cache

import numpy as np
import pytest

from tools.asset_generation.furniture import FURNITURE, JAR_FILLS, PLANT_STAGES
from tools.asset_generation.palette import IDX
from tools.asset_generation.scenes import (KITCHEN, ROOM, ROOM_KEEP_CLEAR, ROOM_LAYOUT, ROOM_LEVEL_NAMES,
                                           home_scene, room_furniture)

NAMES = {p.name for p in FURNITURE}


@cache
def img(name):
    return next(p for p in FURNITURE if p.name == name).render()


def footprint(cell, size):
    return {(cell[0] + i, cell[1] + j) for i in range(size[0]) for j in range(size[1])}


WALL_ITEMS = ("budget_board", "curtains", "wall_shelf", "wall_art", "window_view")   # on a wall: share a cell
ON_TOP = ("coin_jar", "desk_lamp")                                                    # stand on the table or desk
FLOOR = ("rug",)                                                                      # floor overlay under furniture


@pytest.mark.parametrize("level", sorted(ROOM_LEVEL_NAMES))
def test_room_layout_fits_and_keeps_walkways_clear(level):
    """Every piece is inside the 7 x 7 room; floor pieces never overlap; the walkways from the
    entrance door and to the garden door stay clear (spec §3)."""
    taken = set()
    for cell, name, size in room_furniture(level):
        fp = footprint(cell, size)
        assert all(0 <= gx < ROOM and 0 <= gy < ROOM for gx, gy in fp), name
        if name.startswith(WALL_ITEMS + ON_TOP + FLOOR):
            continue
        assert not (fp & taken), (name, fp & taken)
        assert not (fp & ROOM_KEEP_CLEAR), name
        taken |= fp


def test_room_levels_only_add_or_replace():
    """Levels never go down (D-11): a higher room level keeps every piece or puts its replacement
    in the same place."""
    for lv in range(1, max(ROOM_LEVEL_NAMES)):
        lower = {(c, s) for c, _, s in room_furniture(lv)}
        higher = {(c, s) for c, _, s in room_furniture(lv + 1)}
        assert lower <= higher, lv


def test_starter_room_has_the_spec_pieces_and_worn_floor():
    names = {n for _, n, _ in room_furniture(1)}
    for piece in ("mattress", "folding_table", "kitchen_counter_sink", "shoe_rack", "crate_shelf",
                  "budget_board_right", "coin_jar_table_0", "savings_plant_0"):
        assert piece in names
    ground = home_scene(0, room_state={"level": 1})["ground"]
    assert {ground[(gx, gy)] for gx in range(ROOM) for gy in range(ROOM) if (gx, gy) not in KITCHEN} \
        == {"floor_light_wood_worn"}
    assert set(ROOM_LAYOUT) <= set(ROOM_LEVEL_NAMES)


def test_room_scene_draws_back_to_front():
    from tools.asset_generation.kit import PIECES
    cells = {p.name: p.cells for p in PIECES}
    sc = home_scene(0, room_state={"level": 1, "jar": 3, "plant": 4, "droop": True})
    _behind_first(sc, cells)
    names = [n for _, n in sc["structs"]]
    assert "coin_jar_table_3" in names and "savings_plant_4_droop" in names
    assert names.index("coin_jar_table_3") > names.index("folding_table")     # the jar stands on the table


def coin_pixels(name):
    return int(np.isin(img(name), [IDX["coin_light"], IDX["coin_mid"], IDX["coin_dark"]]).sum())


@pytest.mark.parametrize("on", ["table", "desk"])
def test_coin_jar_fills_with_the_cushion(on):
    """5 fills for a current game cushion of 0, 0.5, 1, 2, 3+ months (spec §4): empty, then more
    coins at every step."""
    counts = [coin_pixels(f"coin_jar_{on}_{k}") for k in range(len(JAR_FILLS))]
    assert counts[0] == 0 and all(a < b for a, b in zip(counts, counts[1:])), counts


def test_savings_plant_grows_and_never_loses_a_leaf():
    """Stage 0-4 = engine savings_plant_stage; each stage keeps every leaf of the one before (it
    never shrinks, spec §4), and the plant is bigger at every stage."""
    for lo, hi in zip(PLANT_STAGES[1:], PLANT_STAGES[2:]):
        assert set(lo) <= set(hi)
    sizes = [int((img(f"savings_plant_{k}") >= 0).sum()) for k in range(len(PLANT_STAGES))]
    assert all(a < b for a, b in zip(sizes, sizes[1:])), sizes


@pytest.mark.parametrize("stage", range(len(PLANT_STAGES)))
def test_drooping_plant_stays_green_and_present(stage):
    """D-73: in a really bad month the plant droops (hangs lower) but keeps its stage and stays
    green: never dead, never gone."""
    normal, droop = img(f"savings_plant_{stage}"), img(f"savings_plant_{stage}_droop")
    greens = [IDX["green_mid"], IDX["green_dark"], IDX["green_light"]]
    assert np.isin(droop, greens).sum() >= 0.6 * np.isin(normal, greens).sum()
    top = lambda a: np.flatnonzero(np.isin(a, greens).any(axis=1)).min()      # noqa: E731
    assert top(droop) >= top(normal)                                          # hangs, never taller


from tools.asset_generation.palette import NIGHT_OVERRIDES   # noqa: E402

GLOWS = [IDX[n] for n in NIGHT_OVERRIDES]                   # colours lit at night: windows, lamps, glint
LAMPS = ("desk_lamp", "floor_lamp")


@pytest.mark.parametrize("piece", FURNITURE, ids=lambda p: p.name)
def test_only_lamps_glow_at_night(piece):
    """Only windows and lamps glow at night (spec §1, E3): a lamp's shade uses the colours whose night
    palette is lit; no other furniture uses any of them."""
    lit = np.isin(img(piece.name), GLOWS)
    if piece.name in LAMPS:
        assert np.isin(img(piece.name), [IDX["lamp_shade"], IDX["lamp_shade_dark"]]).any()
    else:
        assert not lit.any()


@pytest.mark.parametrize("piece", FURNITURE, ids=lambda p: p.name)
def test_room_outline_and_nothing_below_the_footprint(piece):
    from tools.asset_generation.geometry import struct_canvas
    a = img(piece.name)
    _, _, (_, fy) = struct_canvas(piece.cells)
    assert not (a[fy + 16 * sum(piece.cells):] >= 0).any()
    assert not (a == IDX["outline_soft"]).any()                                   # room objects: room outline
    if not piece.name.startswith("window_view"):                                  # the window's frame shows through
        assert (a == IDX["outline"]).any()


@pytest.mark.parametrize("level, pieces", [
    (2, ("single_bed", "desk", "office_chair", "desk_lamp", "coin_jar_desk_0")),
    (3, ("wardrobe", "rug", "wall_shelf_left", "potted_plant")),
    (4, ("sofa", "coffee_table", "bookshelf", "compact_fridge", "stove", "curtains_left", "curtains_right")),
    (5, ("wall_art_left", "floor_lamp", "big_plant", "window_view_left", "window_view_right")),
])
def test_each_room_level_adds_the_spec_furniture(level, pieces):
    """Spec §3: what each room level unlocks; replaced pieces are gone (mattress, folding table,
    crate shelf, the coin jar on the table)."""
    names = {n for _, n, _ in room_furniture(level)}
    assert set(pieces) <= names
    gone = {2: ("mattress", "coin_jar_table_0"), 4: ("folding_table", "crate_shelf")}
    for lv, old in gone.items():
        if level >= lv:
            assert not names & set(old)
    floor = home_scene(0, room_state={"level": level})["ground"][(1, 2)]
    assert floor == ("floor_light_wood" if level >= 3 else "floor_light_wood_worn")


def test_layers_within_a_cell():
    """Within a cell: wall, window view, wall items, furniture, things standing on furniture; rugs
    are floor overlays drawn before any structure."""
    sc = home_scene(0, room_state={"level": 5, "jar": 4})
    names = [n for _, n in sc["structs"]]
    pos = {(c, n): k for k, (c, n) in enumerate(sc["structs"])}
    desk_cell = (2, 0)
    assert pos[(desk_cell, "wall_window_right")] < pos[(desk_cell, "window_view_right")] \
        < pos[(desk_cell, "curtains_right")] < pos[(desk_cell, "desk")] < pos[(desk_cell, "desk_lamp")]
    assert pos[(desk_cell, "desk")] < pos[(desk_cell, "coin_jar_desk_4")]
    assert "rug" not in names and sc["decals"] == [((2, 3), "rug")]


def _behind_first(sc, sizes):
    """Every pair whose screen columns overlap: a piece wholly behind the other along gx or gy is drawn first."""
    from tools.asset_generation.scenes import order_violations
    bad = order_violations(sc["structs"], lambda s: sizes.get(s[1].partition("|")[0], (1, 1)))
    assert not bad, bad[:3]


@pytest.mark.parametrize("level", sorted(ROOM_LEVEL_NAMES))
def test_nothing_floats_in_front_of_what_is_in_front_of_it(level):
    """D-88: the sofa was drawn over the coffee table in front of it (same front-cell number), and
    plants in the front row over the low front walls. Pieces wholly behind others come first, and
    the front cut-away walls come after the furniture in their cell."""
    from tools.asset_generation.kit import PIECES
    sizes = {p.name: p.cells for p in PIECES}
    sc = home_scene(0, room_state={"level": level, "jar": 2, "plant": 2, "decor": ALL_DECOR})
    _behind_first(sc, sizes)
    names = [n for _, n in sc["structs"]]
    if level >= 4:
        assert names.index("sofa") < names.index("coffee_table")
    pos = {(c, n): k for k, (c, n) in enumerate(sc["structs"])}
    if level >= 3:
        assert pos[((6, 3), "potted_plant")] < pos[((6, 3), "wall_cutaway_front_right")]


# ---------------------------------------------------------------- decorations (D-86)
from engine.game import load_game                                              # noqa: E402
from tools.asset_generation.scenes import ROOM_DECOR, room_json                  # noqa: E402

ROOM_DECOR_NAMES = load_game()["decorations"]["room"]
ALL_DECOR = list(ROOM_DECOR_NAMES)


def test_every_room_decoration_has_pieces_and_a_place():
    """shared/game.json's room decorations (1 choice per 200 points, D-69) each have their pieces
    and a place at every room level; room.json gives the app the same data."""
    assert set(ROOM_DECOR) == set(ROOM_DECOR_NAMES)
    for name in ROOM_DECOR_NAMES:
        for lv in ROOM_LEVEL_NAMES:
            items = room_furniture(lv, decor=[name])
            assert all(n in NAMES for _, n, _ in items), name
    assert set(room_json()["decorations"]) == set(ROOM_DECOR_NAMES)


@pytest.mark.parametrize("level", sorted(ROOM_LEVEL_NAMES))
def test_decorations_fit_with_the_furniture_at_every_level(level):
    """With every decoration chosen, floor pieces still never overlap and the walkways stay clear."""
    taken = set()
    for cell, name, size in room_furniture(level, decor=ALL_DECOR):
        fp = footprint(cell, size)
        assert all(0 <= gx < ROOM and 0 <= gy < ROOM for gx, gy in fp), name
        if name.startswith(WALL_ITEMS + ON_TOP + FLOOR + ("desk_plant",)):
            continue
        assert not (fp & taken), (level, name, fp & taken)
        assert not (fp & ROOM_KEEP_CLEAR), name
        taken |= fp


def test_curtain_and_rug_colours_replace_the_level_ones():
    """A chosen curtain or rug colour replaces the level's (or appears before that level arrives);
    the last one chosen shows."""
    names = [n for _, n, _ in room_furniture(5, decor=["curtains_sage", "rug_green", "curtains_blue"])]
    curtains = [n for n in names if n.startswith("curtains")]
    assert curtains == ["curtains_blue_left", "curtains_blue_right", "curtains_blue_right"]
    assert [n for n in names if n.startswith("rug")] == ["rug_green"]
    assert [n for n in (n for _, n, _ in room_furniture(1, decor=["curtains_peach"])) if n.startswith("curtains")] \
        == ["curtains_peach_left", "curtains_peach_right", "curtains_peach_right"]
    sc = home_scene(0, room_state={"level": 3, "decor": ["rug_blue"]})
    assert sc["decals"] == [((2, 3), "rug_blue")]                             # still a floor overlay


def test_desk_plant_stands_on_the_table_then_the_desk():
    on1 = [(c, n) for c, n, _ in room_furniture(1, decor=["desk_plant"]) if n.startswith("desk_plant")]
    on2 = [(c, n) for c, n, _ in room_furniture(2, decor=["desk_plant"]) if n.startswith("desk_plant")]
    assert on1 == [((3, 3), "desk_plant_table")] and on2 == [((2, 0), "desk_plant")]
    sc = home_scene(0, room_state={"level": 2, "decor": ["desk_plant"]})
    names = [n for _, n in sc["structs"]]
    assert names.index("desk_plant") > names.index("desk")


@pytest.mark.parametrize("variant", ["curtains_sage_left", "rug_terracotta", "wall_art_kampung_right"])
def test_colour_variants_differ_from_the_level_piece(variant):
    base = {"curtains_sage_left": "curtains_left", "rug_terracotta": "rug", "wall_art_kampung_right": "wall_art_right"}
    assert img(variant).shape == img(base[variant]).shape
    assert (img(variant) != img(base[variant])).any()
