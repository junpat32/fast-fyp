"""T-22 isometric kit: geometry (D-57), footprints, palette, determinism, run joins, files on disk."""
import json
from functools import cache
from pathlib import Path

import numpy as np
import pytest

from tools.asset_generation.geometry import (STRUCT_ORIGIN, Face, cell_screen, diamond_mask, draw_faces,
                                             ground_ab, pixel_grid, struct_canvas)
from tools.asset_generation.palette import IDX, NAMES, TIMES, to_rgba
from tools.asset_generation.kit import PIECES

KIT = Path(__file__).resolve().parents[1] / "assets" / "isometric"


@cache
def rendered():
    return {p.name: p.render() for p in PIECES}


def d57_rows():
    """The D-57 diamond written out row by row, independently of geometry.py."""
    m = np.zeros((32, 64), bool)
    for y in range(32):
        j = min(y, 31 - y)
        m[y, 31 - 2 * j:32 + 2 * j + 1] = True
    return m


def compose(cells):
    """Draw struct pieces at grid cells, back to front (gx + gy), as the app will."""
    out = np.full((420, 640), -1, np.int16)
    for (gx, gy), name in sorted(cells, key=lambda c: c[0][0] + c[0][1]):
        piece = rendered()[name]
        sx, sy = cell_screen(gx, gy)
        x0, y0 = 300 + sx - STRUCT_ORIGIN[0], 150 + sy - STRUCT_ORIGIN[1]
        view = out[y0:y0 + piece.shape[0], x0:x0 + piece.shape[1]]
        np.copyto(view, piece, where=piece >= 0)
    return out


# ---- geometry
def test_diamond_is_d57():
    assert (diamond_mask() == d57_rows()).all()
    assert diamond_mask().sum() == 1024          # 64 x 32 / 2


def test_diamond_tiles_with_no_gaps_or_overlaps():
    cover = np.zeros((32 * 10, 64 * 10), int)
    for gx in range(8):
        for gy in range(8):
            x, y = (gx - gy) * 32 + 288, (gx + gy) * 16 + 16
            cover[y:y + 32, x:x + 64] += d57_rows()
    inner = cover[96:160, 256:384]               # well inside the 8 x 8 patch
    assert inner.min() == 1 and inner.max() == 1


@pytest.mark.parametrize("a, b, h", [(0.5, 0.5, 0), (3.25, 12.75, 0), (15.5, 0.5, 40), (7, 9, 96)])
def test_projection_round_trip(a, b, h):
    x, y = 32 + 2 * a - 2 * b, a + b - h
    assert np.allclose(ground_ab(x, y, h), (a, b))


def test_face_renderer_matches_the_diamond():
    """The depth-buffered face renderer (roofs, wheels; D-59) samples exactly like the tiles: a
    flat quad over one cell covers the D-57 diamond pixel for pixel, at any height."""
    for h in (0, 37):
        canvas = np.full((32 + 64, 64), -1, np.int16)
        X, Y = pixel_grid(64, 32 + 64, (0, 64))
        draw_faces(canvas, X, Y, [Face((0, 0, h), (16, 0, 0), (0, 16, 0), 1)])
        assert ((canvas[64 - h:96 - h] >= 0) == d57_rows()).all()
        assert (canvas >= 0).sum() == 1024


def test_nearer_face_wins():
    """Two overlapping flat quads: the higher one (nearer the viewer) is drawn, whatever the order."""
    for order in (1, -1):
        canvas = np.full((96, 64), -1, np.int16)
        X, Y = pixel_grid(64, 96, (0, 64))
        faces = [Face((0, 0, 0), (16, 0, 0), (0, 16, 0), 1), Face((0, 0, 8), (16, 0, 0), (0, 16, 0), 2)][::order]
        draw_faces(canvas, X, Y, faces)
        assert (canvas == 2).sum() == 1024


# ---- every piece
def test_names_are_unique_snake_case():
    from tools.asset_generation.kit import BATCH1
    names = [p.name for p in PIECES]
    assert len(names) == len(set(names)) and BATCH1 == 48
    assert all(n.replace("_", "").isalnum() and n == n.lower() for n in names)


@pytest.mark.parametrize("piece", PIECES, ids=lambda p: p.name)
def test_piece_size_and_palette(piece):
    img = rendered()[piece.name]
    w, h, _ = struct_canvas(piece.cells)
    assert img.shape == ((32, 64) if piece.kind == "tile" else (h, w))
    assert img.min() >= -1 and img.max() < len(NAMES)        # palette index or transparent only


@pytest.mark.parametrize("piece", [p for p in PIECES if p.kind == "tile"], ids=lambda p: p.name)
def test_ground_tile_footprint_is_exactly_the_diamond(piece):
    assert ((rendered()[piece.name] >= 0) == d57_rows()).all()


@pytest.mark.parametrize("piece", PIECES, ids=lambda p: p.name)
def test_render_is_deterministic(piece):
    assert (piece.render() == rendered()[piece.name]).all()


# ---- runs join cleanly: one outline pixel per column, no tick at the joins
RUNS = {
    "left wall run": ([((0, 1), "wall_left"), ((0, 2), "wall_left"), ((0, 3), "wall_left")], "outline"),
    "right wall run": ([((1, 0), "wall_right"), ((2, 0), "wall_right"), ((3, 0), "wall_right")], "outline"),
    "corner + both walls": ([((0, 0), "wall_inside_corner"), ((0, 1), "wall_left"), ((0, 2), "wall_left"),
                             ((1, 0), "wall_right"), ((2, 0), "wall_right")], "outline"),
    "walls with features": ([((0, 1), "wall_window_left"), ((0, 2), "wall_door_closed_left"),
                             ((0, 3), "wall_doorway_open_left")], "outline"),
    "front-left stub run": ([((0, 6), "wall_cutaway_front_left"), ((1, 6), "wall_cutaway_front_left"),
                             ((2, 6), "wall_cutaway_front_left")], "outline"),
    "front-right stub run": ([((6, 0), "wall_cutaway_front_right"), ((6, 1), "wall_cutaway_front_right"),
                              ((6, 2), "wall_cutaway_front_right")], "outline"),
    "stubs meet at the front": ([((4, 6), "wall_cutaway_front_left"), ((5, 6), "wall_cutaway_doorstep_front_left"),
                                 ((6, 6), "wall_cutaway_front_corner"), ((6, 5), "wall_cutaway_front_right"),
                                 ((6, 4), "wall_cutaway_doorstep_front_right")], "outline"),
    "border corner + runs": ([((0, 0), "garden_border_corner_inner"), ((0, 1), "garden_border_straight_left"),
                              ((1, 0), "garden_border_straight_right"),
                              ((2, 0), "garden_border_straight_right")], "outline_soft"),
}


@pytest.mark.parametrize("name", RUNS)
def test_run_has_one_continuous_top_outline(name):
    """No column has two outline pixels (a tick at a join). The line may stop only within the
    4-px cap end of a run that has no corner piece before it (that end is drawn as 'joined');
    a run that starts at the inside corner is outlined in every column."""
    cells, line = RUNS[name]
    img = compose(cells)
    per_column = (img == IDX[line]).sum(axis=0)[(img >= 0).any(axis=0)]
    assert per_column.max() == 1, f"tick at columns {np.flatnonzero(per_column > 1)}"
    if "corner" in name:
        assert per_column.min() == 1
    else:
        assert (per_column[4:-4] == 1).all(), "gap in the outline inside the run"


def _post_groups(img, min_height=26):
    """Runs of adjacent columns whose opaque span is post-tall (rails alone are much shorter)."""
    rows = [np.flatnonzero(img[:, x] >= 0) for x in range(img.shape[1])]
    tall = [len(r) > 0 and r.max() - r.min() + 1 >= min_height for r in rows]
    groups, start = [], None
    for x, t in enumerate(tall + [False]):
        if t and start is None:
            start = x
        elif not t and start is not None:
            groups.append(x - start)
            start = None
    return groups


@pytest.mark.parametrize("cells, posts", [
    ([((0, 0), "fence_left"), ((0, 1), "fence_left")], 5),
    ([((0, 0), "fence_right"), ((1, 0), "fence_right")], 5),
    ([((0, 0), "fence_gate_left"), ((0, 1), "fence_left")], 4),         # a gate has no middle post
], ids=["left", "right", "gate"])
def test_fence_joins_share_one_post(cells, posts):
    """The join post is shared, so 3 + 3 posts show as 5 (gate: 2 + 3 as 4), each a single 6 px
    post; the old kit drew two posts side by side at every join (D-58)."""
    groups = _post_groups(compose(cells))
    assert len(groups) == posts and max(groups) <= 7, groups


# ---- home scene layout (D-58)
@pytest.mark.parametrize("level", range(5))
def test_scene_uses_kit_pieces_in_draw_order(level):
    from tools.asset_generation.scenes import home_scene
    sc = home_scene(level)
    names = {p.name for p in PIECES}
    used = {sc["default"]} | set(sc["ground"].values()) | {n for _, n in sc["structs"] + sc["background"]}
    assert used <= names, used - names
    cells = {p.name: p.cells for p in PIECES}
    from tools.asset_generation.scenes import order_violations                 # wholly-behind pieces first (D-88)
    assert not order_violations(sc["structs"], lambda s: cells[s[1]])


def test_chicken_coop_only_with_chickens_and_clear_of_the_garden():
    """D-67: the coop appears only if the user chose chickens; it never sits on the bed, the path
    loop, the planters or the room, at any level or growth step, and stays inside the fence."""
    from tools.asset_generation.scenes import (ANIMAL_HOMES, BACK, MAX_BED_STEPS, PLANTERS, RADIUS, ROOM,
                                               bed_cells, bed_loop, home_scene)
    home = ANIMAL_HOMES["chickens"]
    coop = _footprint(home["cell"], home["size"])
    assert "prop_chicken_coop" not in {n for _, n in home_scene(3, animals=())["structs"]}
    assert "prop_chicken_coop" in {n for _, n in home_scene(3, animals=("chickens",))["structs"]}
    room = {(gx, gy) for gx in range(ROOM) for gy in range(ROOM)}
    for level, steps in [(2, 0), (3, 0)] + [(4, k) for k in range(MAX_BED_STEPS + 1)]:
        busy = bed_cells(level, steps) | bed_loop(level, steps) | set(PLANTERS[min(level, 3)]) | room
        assert not (coop & busy), (level, steps)
        hi = ROOM - 1 + RADIUS[level]
        assert all(-BACK <= c <= hi for cell in coop | {home["sleep"]} for c in cell)
    assert home["sleep"] not in coop | room


def _footprint(cell, cells):
    return {(cell[0] + i, cell[1] + j) for i in range(cells[0]) for j in range(cells[1])}


def test_neighbourhood_never_overlaps_and_stays_off_the_home_plot():
    """Houses and props never share a cell, and none stands on the home plot at any level, even
    at G4 when the plot runs past the screen (D-59)."""
    from tools.asset_generation.scenes import BACK, NEIGHBOUR_PROPS, NEIGHBOURS, RADIUS, ROOM
    taken = set()
    for cell, _, size in NEIGHBOURS + NEIGHBOUR_PROPS:
        fp = _footprint(cell, size)
        assert not (fp & taken), cell
        taken |= fp
    hi = ROOM - 1 + max(RADIUS.values())
    assert not {c for c in taken if -BACK <= c[0] <= hi and -BACK <= c[1] <= hi}


def test_neighbourhood_is_fixed():
    """Neighbours never change with the player's level: same houses, props and porches (D-59)."""
    from tools.asset_generation.scenes import home_scene
    scenes = [home_scene(lv) for lv in range(5)]
    assert all(s["background"] == scenes[0]["background"] for s in scenes)
    porch = {c: n for c, n in scenes[0]["ground"].items() if min(c) < -1 or max(c) < 0}
    for s in scenes:
        assert {c: s["ground"][c] for c in porch} == porch


def test_bed_runs_along_the_path_grows_and_stays_in_view():
    """D-61, D-63, D-68: a rectangle alongside the straight path (every bed row touches a path cell,
    so the path gives access to the plants); bigger at every garden level (2 x 2 dug starter bed at
    G1), then one row per qualifying month after G4, never losing a cell, until complete; it stays
    in the default view."""
    from tools.asset_generation.scenes import MAX_BED_STEPS, _path, bed_cells, bed_size, home_scene
    path = {c for c, _ in zip((c for c, _ in _path()), range(60))}
    assert len({gx for gx, _ in path}) == 1                              # straight
    assert bed_size(1) == (2, 2) and bed_size(4, MAX_BED_STEPS) == (5, 6)
    prev = bed_cells(1)
    for cur in [bed_cells(2), bed_cells(3), bed_cells(4)] + [bed_cells(4, k) for k in range(1, MAX_BED_STEPS + 1)]:
        assert prev < cur                                                 # only ever grows
        rows = {gy for _, gy in cur}
        assert all(((min(gx for gx, _ in cur) - 1, gy) in path) for gy in rows)   # path along its side
        assert not (cur & path)
        prev = cur
    assert bed_cells(4, MAX_BED_STEPS + 12) == prev                      # complete: capped
    # in the default 540 x 1200 view: room top vertex at (270, 330); cell (gx, gy) spans
    # x = 270 + (gx - gy) * 32 +- 32
    assert all(0 <= 270 + (gx - gy) * 32 - 32 and 270 + (gx - gy) * 32 + 32 <= 540 for gx, gy in prev)
    assert home_scene(1)["ground"][min(bed_cells(1))] == "garden_soil_bare"           # freshly dug
    assert all(home_scene(4, MAX_BED_STEPS)["ground"][c] == "garden_soil_improved" for c in prev)


def test_path_goes_all_round_the_bed():
    """D-64: at every level and growth step each bed cell's neighbours are bed or path, so the
    character can reach every side; the loop stays inside the fence and joins the main path."""
    from tools.asset_generation.scenes import MAX_BED_STEPS, PATH, bed_cells, home_scene
    for level, steps in [(1, 0), (2, 0), (3, 0)] + [(4, k) for k in range(MAX_BED_STEPS + 1)]:
        ground = home_scene(level, steps)["ground"]
        bed = bed_cells(level, steps)
        for gx, gy in bed:
            for n in ((gx - 1, gy), (gx + 1, gy), (gx, gy - 1), (gx, gy + 1)):
                assert n in bed or ground[n] == PATH[level], (level, steps, n)


def test_unlocked_garden_keeps_wild_grass_inside_the_fence():
    """D-63: at the unlock the yard is claimed, not dug up: no ring of bare soil round the house."""
    from tools.asset_generation.scenes import bed_cells, home_scene
    g1 = home_scene(1)["ground"]
    assert {c for c, n in g1.items() if n == "garden_soil_bare"} == bed_cells(1)


def test_garden_grows_and_door_opens_with_level():
    from tools.asset_generation.scenes import ROOM, home_scene

    def tended(lv):          # home-plot ground that is not the room
        return sum(1 for (gx, gy), n in home_scene(lv)["ground"].items()
                   if min(gx, gy) >= -1 and not (gx < ROOM and gy < ROOM and min(gx, gy) >= 0))
    tended = [tended(lv) for lv in range(5)]
    assert tended[0] == 0 and tended == sorted(tended) and len(set(tended)) == 5
    for lv in range(5):
        structs = [n for _, n in home_scene(lv)["structs"]]
        assert ("wall_cutaway_doorstep_front_left" in structs) == (lv >= 1)
        assert any(n.startswith("fence_gate") for n in structs) == (lv >= 1)        # fence kept at G4 (D-65)


# ---- the PNGs on disk are what the code produces now (catches a forgotten rebuild)
@pytest.mark.skipif(not (KIT / "manifest.json").exists(), reason="kit not built")
def test_files_on_disk_match_the_code():
    from PIL import Image
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    assert [e["name"] for e in manifest["pieces"]] == [p.name for p in PIECES]
    for e in manifest["pieces"]:
        assert set(e["files"]) == set(TIMES)
        for t, rel in e["files"].items():
            on_disk = np.asarray(Image.open(KIT / rel).convert("RGBA"))
            assert (on_disk == to_rgba(rendered()[e["name"]], t)).all(), f"stale: {rel} (rebuild the kit)"


@pytest.mark.skipif(not (KIT / "manifest.json").exists(), reason="kit not built")
def test_exported_scenes_match_the_layout():
    """assets/isometric/scenes/home_g*.json (what the app loads) equal scenes.py (what the
    previews draw), and every piece they name is in the manifest."""
    from tools.asset_generation.scenes import LEVEL_NAMES, scene_json
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    names = {e["name"] for e in manifest["pieces"]}
    for level in LEVEL_NAMES:
        on_disk = json.loads((KIT / manifest["scenes"][str(level)]).read_text(encoding="utf-8"))
        assert on_disk == scene_json(level), f"stale: home_g{level}.json (rebuild the kit)"
        used = {on_disk["default_ground"]} | {n for key in ("ground", "background", "structures")
                                              for *_, n in on_disk[key]}
        assert used <= names


@pytest.mark.skipif(not (KIT / "manifest.json").exists(), reason="kit not built")
def test_exported_room_matches_the_layout():
    """assets/isometric/scenes/room.json (the room's furniture per room level, for the app) equals
    scenes.room_json(); every piece it names exists for every coin-jar fill and plant stage."""
    from tools.asset_generation.scenes import room_json
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    on_disk = json.loads((KIT / manifest["scenes"]["room"]).read_text(encoding="utf-8"))
    assert on_disk == json.loads(json.dumps(room_json())), "stale: room.json (rebuild the kit)"
    names = {e["name"] for e in manifest["pieces"]}
    for level in on_disk["levels"].values():
        for _, _, piece, *_ in level["furniture"]:
            for jar in range(5):
                for plant in [f"{k}{d}" for k in range(5) for d in ("", "_droop")]:
                    assert piece.format(jar=jar, plant=plant) in names
    from tools.asset_generation.kit import APPROVED
    assert all(e["approved"] == (e["batch"] == 1 or e["name"] in APPROVED) for e in manifest["pieces"])
    assert {"single_bed", "plant_ixora_full_droop", "avatar_01_mood_calm"} <= APPROVED          # D-86
    assert not {"avatar_01_sit_0", "avatar_02_front_idle_0", "dining_table", "tree_0_mound", "plant_orchid_full",
                "chicken_walk_0", "bench"} & APPROVED


@pytest.mark.skipif(not (KIT / "manifest.json").exists(), reason="kit not built")
def test_validator_passes_on_disk():
    from tools.asset_generation.validate import check
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    fails = [r for r in check(manifest) if not r[2]]
    assert not fails, fails[:5]
