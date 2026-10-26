"""Home scene layout (D-58, D-59, D-61 to D-63): a 7 x 7 room on its own plot, neighbours' houses
behind and to both sides, and a garden that grows down the phone screen.

Levels: 0 = before the garden opens (the first 2 monthly check-ins; garden door closed), 1-4 =
G1-G4 of game_design.md §8 (the garden opens on the 3rd monthly check-in for everyone and grows with
qualifying months, D-75). The home plot is a square of cells [-BACK, 6 + RADIUS[level]]: it reaches one
cell behind the house (the neighbours start past that) and grows towards the bottom of the screen.
Inside it: wild grass at the unlock, then a lawn; one rectangular flower bed alongside a straight
path from the garden door (D-63); planters; and a fence with a gate. Outside it the ground is wild. Neighbours are FIXED scenery:
nothing about them depends on anyone's progress (D-59). Furniture, plants and the character come in
batch 2. This module is the single description of the layout: the previews draw it and the app
(T-16) will load the same data.

Cells: (gx, gy); the room is gx, gy in [0, 7). A piece is placed by its back cell; its screen
position is map_origin + ((gx - gy) * 32, (gx + gy) * 16).
"""
from __future__ import annotations

from itertools import count

from engine.game import bed_cells as game_bed_cells
from engine.game import bed_size as game_bed_size
from engine.game import load_game

ROOM = 7
BACK = 1
KITCHEN = {(gx, gy) for gx in (4, 5, 6) for gy in (0, 1)}
LEFT_WALL = {2: "wall_window_left", 4: "wall_door_closed_left"}     # gy -> feature on the back-left wall
RIGHT_WALL = {2: "wall_window_right", 5: "wall_window_right"}       # gx -> feature on the back-right wall
GARDEN_DOOR = (5, 6)                                                # in the front-left stub

# Garden geometry comes from shared/game.json through engine.game, so the art and the game rules
# can never disagree (T-14b). Fence: 4 / 6 / 9 / 14 cells out; at G4 its front corner sits just above
# the bottom bar (D-65). The one big bed (D-61, D-63): a RECTANGLE alongside the path, on its right
# (the side that stays on screen longer), so the path leads to the plants and the character can walk
# to them. Size is (cells across, along gx; cells along the path, along gy). The bed grows with TIME
# (qualifying months, D-68), never with points: bigger at every garden level (a 2 x 2 freshly dug
# starter bed at the unlock, then 2 x 3, 3 x 3, 3 x 4), then one row per qualifying month after G4,
# alternately along the path and across it, up to 5 x 6 (the largest that stays in the default view).
_GARDEN = load_game()["garden"]
RADIUS = {int(k): v for k, v in _GARDEN["plot_radius"].items()}
BED_BACK = tuple(_GARDEN["bed_back_cell"])
BED_SIZE = {int(k): tuple(v) for k, v in _GARDEN["bed_size"].items()}
BED_GROWTH = [tuple(s) for s in _GARDEN["bed_growth_after_g4"]]
LAWN = {1: "garden_wild", 2: "garden_grass_basic", 3: "garden_grass_healthy", 4: "garden_grass_lush"}
PATH = {1: "path_stepping_stone", 2: "path_stepping_stone", 3: "path_paved", 4: "path_nice_paved"}
PLANTERS = {2: [(2, 7), (7, 2)], 3: [(1, 7), (2, 7), (7, 1), (7, 2)]}   # level 3 list also used at G4
# Animal homes (D-66, D-67): shown only when the user has chosen that animal (slots from 2 qualifying
# months). Back cell, footprint, and where the animals sleep at night (in front of the ramp).
ANIMAL_HOMES = {"chickens": {"piece": "prop_chicken_coop", "cell": (8, 2), "size": (2, 2), "sleep": (8, 4)}}
PREVIEW_ANIMALS = ("chickens",)        # previews assume the user picked chickens at the first slot
LEVEL_NAMES = {0: "Before the garden (first 2 check-ins)", 1: "G1 - garden opens (3rd check-in)",
               2: "G2 - 2 qualifying months", 3: "G3 - 4 months", 4: "G4 - 6+ months"}

# Neighbours (D-59): (back cell, piece, footprint). Behind-left and behind-right of the house, and a
# row of three across the top of the screen. Each has a paved porch along its two front faces.
NEIGHBOURS = [((-7, 1), "neighbour_house_a", (5, 5)), ((1, -7), "neighbour_house_b", (5, 5)),
              ((-14, -5), "neighbour_house_b", (5, 5)), ((-9, -9), "neighbour_house_c", (5, 5)),
              ((-5, -14), "neighbour_house_a", (5, 5))]
# Small fixed touches on the porches (lit windows at night come from the palette).
# Placed where the screen shows them: the centre house's porches and the green strips between houses
# (the side houses' porches face the home plot and are hidden behind its back walls).
NEIGHBOUR_PROPS = [((-4, -9), "prop_motorbike", (1, 2)), ((-4, -6), "prop_ac_unit", (1, 1)),
                   ((-7, -4), "prop_ac_unit", (1, 1)), ((-8, -3), "prop_washing_line", (1, 2))]


# Room furniture by ROOM level (spec §3; room levels follow the cushion, independent of the garden
# level). Each level lists what it adds as (cell, piece, footprint, replaces): a piece that
# replaces another takes its place in the drawing order (e.g. the single bed replaces the
# mattress). Cells are planned for all five levels so nothing has to move later; walkways stay
# clear: entrance door (0, 4) -> (1, 4), garden door (5, 6) -> (5, 5).
# "{jar}" = coin jar fill 0-4 (current game cushion 0 / 0.5 / 1 / 2 / 3+ months); "{plant}" =
# savings plant stage 0-4, plus "_droop" in a really bad month (D-73).
ROOM_LAYOUT = {
    1: [((0, 0), "mattress", (1, 2), None), ((1, 0), "crate_shelf", (1, 1), None),
        ((3, 0), "budget_board_right", (1, 1), None), ((5, 0), "kitchen_counter_sink", (1, 1), None),
        ((0, 2), "savings_plant_{plant}", (1, 1), None), ((0, 5), "shoe_rack", (1, 1), None),
        ((3, 3), "folding_table", (1, 1), None), ((3, 3), "coin_jar_table_{jar}", (1, 1), None)],
    2: [((0, 0), "single_bed", (1, 2), "mattress"), ((2, 0), "desk", (1, 1), None),
        ((2, 1), "office_chair", (1, 1), None), ((2, 0), "desk_lamp", (1, 1), None),
        ((2, 0), "coin_jar_desk_{jar}", (1, 1), "coin_jar_table_{jar}")],
    3: [((0, 3), "wardrobe", (1, 1), None), ((2, 3), "rug", (2, 2), None),
        ((0, 5), "wall_shelf_left", (1, 1), None), ((6, 3), "potted_plant", (1, 1), None)],
    4: [((1, 0), "bookshelf", (1, 1), "crate_shelf"), ((3, 3), "coffee_table", (1, 1), "folding_table"),
        ((2, 3), "sofa", (1, 2), None), ((4, 0), "stove", (1, 1), None), ((6, 0), "compact_fridge", (1, 1), None),
        ((0, 2), "curtains_left", (1, 1), None), ((2, 0), "curtains_right", (1, 1), None),
        ((5, 0), "curtains_right", (1, 1), None)],
    5: [((0, 1), "wall_art_left", (1, 1), None), ((1, 3), "floor_lamp", (1, 1), None),
        ((6, 6), "big_plant", (1, 1), None), ((0, 2), "window_view_left", (1, 1), None),
        ((2, 0), "window_view_right", (1, 1), None), ((5, 0), "window_view_right", (1, 1), None)],
}
# Drawing order inside one cell (the front-cell sort ties): walls, then the view through a window,
# then things on the walls, then furniture, then things standing on furniture. Rugs are floor
# overlays, drawn after the ground and before every structure, so they never cover a leg.
FLOOR_OVERLAYS = ("rug",)
LAYERS = (("window_view", 0.1), ("budget_board", 0.2), ("curtains", 0.2), ("wall_shelf", 0.2), ("wall_art", 0.2),
          ("coin_jar", 0.4), ("desk_lamp", 0.4), ("desk_plant", 0.4))
# Room decorations (shared/game.json "decorations.room"; 1 choice per 200 points, D-69) and where each
# goes, by room level ({from level: [(cell, piece, footprint)]}): spots no level piece uses, so a
# decoration never moves furniture. Curtain and rug colours replace the level's curtains / rug (or
# appear before that level arrives); the last one chosen shows. The desk plant sits on the folding
# table until the desk arrives (room level 2).
CURTAIN_SPOTS = [((0, 2), "left"), ((2, 0), "right"), ((5, 0), "right")]      # the three windows
ROOM_DECOR = {
    "dining_set": {1: [((5, 2), "dining_table", (1, 1)), ((4, 2), "dining_chair", (1, 1))]},
    "storage_cabinet": {1: [((0, 6), "storage_cabinet", (1, 1))]},
    **{f"curtains_{c}": {1: [(cell, f"curtains_{c}_{wall}", (1, 1)) for cell, wall in CURTAIN_SPOTS]}
       for c in ("sage", "peach", "blue")},
    **{f"rug_{c}": {1: [((2, 3), f"rug_{c}", (2, 2))]} for c in ("green", "terracotta", "blue")},
    "wall_art_kampung": {1: [((0, 6), "wall_art_kampung_left", (1, 1))]},
    "wall_art_flowers": {1: [((0, 0), "wall_art_flowers_left", (1, 1))]},
    "desk_plant": {1: [((3, 3), "desk_plant_table", (1, 1))], 2: [((2, 0), "desk_plant", (1, 1))]},
}
DECOR_REPLACES = ("curtains", "rug")                 # a decoration of this kind replaces the level's one


def decor_items(name: str, room_level: int) -> list:
    """[(cell, piece, footprint)] for one room decoration at a room level."""
    spots = ROOM_DECOR[name]
    return spots[max(lv for lv in spots if lv <= room_level)]


FRONT_WALL_LAYER = 0.5      # the low cut-away walls stand on their cell's FRONT edge: drawn after its furniture (D-88)


def layer(name: str) -> float:
    """Fraction added to a room piece's front-cell sort key (furniture 0.3; walls and garden 0)."""
    return next((v for prefix, v in LAYERS if name.startswith(prefix)), 0.3)
ROOM_KEEP_CLEAR = {(1, 4), (5, 5)}
ROOM_LEVEL_NAMES = {1: "Room 1 - Starter", 2: "Room 2 - Settling in (0.5 month)", 3: "Room 3 - Home (1 month)",
                    4: "Room 4 - Comfortable (2 months)", 5: "Room 5 - Cosy (3 months)"}


def room_furniture(room_level: int, jar=0, plant=0, droop: bool = False, decor=()) -> list:
    """[(cell, piece, footprint)] at a room level, earlier levels' pieces included (levels never go
    down, D-11), with the coin jar fill and savings plant stage filled in (or left as "{jar}" /
    "{plant}" placeholders for the app), plus the chosen decorations in the order chosen."""
    out = []
    for lv in range(1, room_level + 1):
        for cell, name, size, replaces in ROOM_LAYOUT.get(lv, []):
            item = (cell, name, size)
            names = [n for _, n, _ in out]
            if replaces in names:
                out[names.index(replaces)] = item
            else:
                out.append(item)
    for d in decor:
        kind = next((k for k in DECOR_REPLACES if d.startswith(k)), None)
        if kind:
            out = [item for item in out if not item[1].startswith(kind)]
        out += decor_items(d, room_level)
    plant_name = f"{plant}{'_droop' if droop else ''}"
    return [(c, n.format(jar=jar, plant=plant_name), s) for c, n, s in out]


def room_floor(room_level: int) -> str:
    """Worn wood floor at the start; light wood from room level 3 (spec §3)."""
    return "floor_light_wood_worn" if room_level < 3 else "floor_light_wood"


def _path():
    """Straight from the garden door along gy (D-62): on screen it runs down-left and leaves the
    screen's left edge after about 6 cells, as a path out to the street."""
    gx, gy = GARDEN_DOOR
    for i in count(1):
        yield (gx, gy + i), "gy"


def _edging(region: set) -> list:
    """Stone edging on every edge between a region cell and a cell outside it. Edging is centred on
    the edge and overlaps at the ends, so any outline closes at every corner (D-58)."""
    out = set()
    for gx, gy in region:
        if (gx - 1, gy) not in region:
            out.add(((gx, gy), "garden_border_straight_left"))
        if (gx, gy - 1) not in region:
            out.add(((gx, gy), "garden_border_straight_right"))
        if (gx + 1, gy) not in region:
            out.add(((gx + 1, gy), "garden_border_straight_left"))
        if (gx, gy + 1) not in region:
            out.add(((gx, gy + 1), "garden_border_straight_right"))
    return sorted(out)


MAX_BED_STEPS = len(BED_GROWTH)                 # 4 monthly steps: complete at 6 + 4 = 10 qualifying months


def bed_size(level: int, steps: int = 0) -> tuple[int, int]:
    """(across, along the path) at a garden level; `steps` (G4 only) = qualifying months after G4."""
    return game_bed_size(level, steps)


def bed_cells(level: int, steps: int = 0) -> set:
    """The bed at a garden level, capped once complete (the same cells the game rules use)."""
    return game_bed_cells(level, steps)


def bed_loop(level: int, steps: int = 0) -> set:
    """The path loop round the bed (D-64): one cell wide on all four sides, so the character can
    walk to every plant. Its left side is the main path (BED_BACK is one cell right of it); it
    moves outward as the bed grows, and the cells it leaves become bed."""
    bed = bed_cells(level, steps)
    if not bed:
        return set()
    x0, x1 = min(c[0] for c in bed) - 1, max(c[0] for c in bed) + 1
    y0, y1 = min(c[1] for c in bed) - 1, max(c[1] for c in bed) + 1
    return {(gx, gy) for gx in range(x0, x1 + 1) for gy in range(y0, y1 + 1)} - bed


BED_STEPS = [sorted(bed_cells(4, k) - bed_cells(4, k - 1)) for k in range(1, MAX_BED_STEPS + 1)]

# The tree (D-74, D-86): one fixed 2 x 2 spot on the lawn right of the bed, from G4
# (shared/game.json "tree_from_garden_level"); every stage is drawn on that spot, so it never moves.
TREE_FROM_LEVEL = _GARDEN["tree_from_garden_level"]
TREE_SPOT = (12, 9)
TREE_CELLS = {(TREE_SPOT[0] + i, TREE_SPOT[1] + j) for i in (0, 1) for j in (0, 1)}
# The default view (D-60: fitted to the screen width at 2x): a cell is fully on screen when
# |gx - gy| <= 7 (its 64 px stay inside the 540 px width) and gx + gy <= 38 (above the bottom bar)
VIEW_HALF_WIDTH, VIEW_DEPTH = 7, 38


def garden_reserved() -> set:
    """Cells a garden decoration may never use, at any level, so that one placed early never blocks
    what comes later (spec §5: paths and the bed are never blocked): the house, the whole path, the
    complete bed and the path round it, the planters, the animal homes and their sleep cells, the
    tree's spot, and the row behind the house."""
    hi = ROOM - 1 + RADIUS[max(RADIUS)]
    out = {(gx, gy) for gx in range(ROOM) for gy in range(ROOM)}
    out |= {(GARDEN_DOOR[0], GARDEN_DOOR[1] + i) for i in range(1, hi + 2)}          # the path to the gate
    out |= bed_cells(4, MAX_BED_STEPS) | bed_loop(4, MAX_BED_STEPS)
    out |= {c for cells in PLANTERS.values() for c in cells}
    for home in ANIMAL_HOMES.values():            # with a ring round it: the sleep cell in front, and
        (gx, gy), (w, d) = home["cell"], home["size"]          # nothing hidden behind it or hiding it
        out |= {(gx + i, gy + j) for i in range(-1, w + 1) for j in range(-1, d + 1)}
    tx, ty = TREE_SPOT                            # the same for the tree's canopy
    out |= {(tx + i, ty + j) for i in range(-1, 3) for j in range(-1, 3)}
    out |= {(gx, -BACK) for gx in range(-BACK, hi + 1)} | {(-BACK, gy) for gy in range(-BACK, hi + 1)}
    return out


def decor_spots(level: int, size=(1, 1), used=()) -> list:
    """Back cells where a garden decoration of `size` (cells along gx, gy) fits on free lawn at a
    garden level, nearest the garden door first: the app highlights the first 2-3 (K2). `used`: cells
    other decorations already take."""
    if level < 1:
        return []
    lo, hi = -BACK, ROOM - 1 + RADIUS[level]
    free = {(gx, gy) for gx in range(lo, hi + 1) for gy in range(lo, hi + 1)
            if abs(gx - gy) <= VIEW_HALF_WIDTH and gx + gy <= VIEW_DEPTH}      # on screen in the default view
    free -= garden_reserved() | set(used)
    w, d = size
    fits = [(gx, gy) for gx, gy in free if all((gx + i, gy + j) in free for i in range(w) for j in range(d))]
    door = GARDEN_DOOR
    return sorted(fits, key=lambda c: ((c[0] - door[0]) ** 2 + (c[1] - door[1]) ** 2, c))


def _fence(lo, hi, gate):
    pieces = {(lo, lo): "fence_corner"}
    pieces.update({(lo, y): "fence_left" for y in range(lo + 1, hi + 1)})
    pieces.update({(x, lo): "fence_right" for x in range(lo + 1, hi + 1)})
    pieces.update({(hi + 1, y): "fence_left" for y in range(lo, hi + 1)})       # front-right boundary
    pieces.update({(x, hi + 1): "fence_right" for x in range(lo, hi + 1)})      # front-left boundary
    if gate:
        pieces[gate[0]] = gate[1]
    return list(pieces.items())


def _front_sum(item):
    (gx, gy), _, (w, d) = item
    return gx + w - 1 + gy + d - 1


def depth_sort(items: list, size_of) -> list:
    """Drawing order for structures (D-88). Sorting by front cell alone ties a 1 x 2 sofa at (2, 3)
    with the 1 x 1 coffee table at (3, 3) in front of it, and the sofa was drawn over the table.

    Rule (isometric separating axis): A must be drawn before B when A's footprint lies wholly behind
    B's along gx (A.gx_end <= B.gx) or along gy (A.gy_end <= B.gy). Only pairs whose screen columns
    overlap need an order (footprints apart on both axes never overlap on screen). Pairs sharing
    cells (a wall and the furniture against it, a jar on a table) keep the incoming order, which is
    by front cell and layer. A topological sort that prefers the incoming order keeps everything
    else exactly as it was.
    Invariant: for every overlapping pair, the one wholly behind comes first.
    Cost: O(n^2) pair checks (n ~ 300 for the largest garden), fine for a build step and the app."""
    n = len(items)
    boxes_ = []
    for (gx, gy), _ in items:
        w, d = size_of(items[len(boxes_)])
        boxes_.append((gx, gx + w, gy, gy + d))
    after = [[] for _ in range(n)]
    indeg = [0] * n
    for i in range(n):
        a0, a1, b0, b1 = boxes_[i]
        for j in range(i + 1, n):
            c0, c1, d0, d1 = boxes_[j]
            if a1 - b0 <= c0 - d1 or c1 - d0 <= a0 - b1:              # screen columns (gx - gy) don't overlap
                continue
            if a1 <= c0 or b1 <= d0:
                first, second = i, j
            elif c1 <= a0 or d1 <= b0:
                first, second = j, i
            else:
                first, second = i, j                                   # shared cells: incoming order
            after[first].append(second)
            indeg[second] += 1
    import heapq
    ready = [i for i in range(n) if indeg[i] == 0]
    heapq.heapify(ready)
    out, done = [], [False] * n
    while len(out) < n:
        if not ready:                                                  # a cycle (none in our layouts):
            ready = [min(i for i in range(n) if not done[i])]          # fall back to the incoming order
        i = heapq.heappop(ready)
        if done[i]:
            continue
        done[i] = True
        out.append(items[i])
        for j in after[i]:
            indeg[j] -= 1
            if indeg[j] == 0 and not done[j]:
                heapq.heappush(ready, j)
    return out


def order_violations(items: list, size_of) -> list:
    """Pairs (earlier, later) in a drawing order where the later piece lies wholly behind the earlier
    one and they overlap on screen: what depth_sort rules out (for tests and the app's own checks)."""
    out = []
    boxes_ = [(gx, gx + size_of(it)[0], gy, gy + size_of(it)[1]) for it in items for (gx, gy) in [it[0]]]
    for i in range(len(items)):
        a0, a1, b0, b1 = boxes_[i]
        for j in range(i + 1, len(items)):
            c0, c1, d0, d1 = boxes_[j]
            if a1 - b0 <= c0 - d1 or c1 - d0 <= a0 - b1:
                continue
            if c1 <= a0 or d1 <= b0:
                out.append((items[i], items[j]))
    return out


def home_scene(level: int, bed_steps: int = 0, animals=None, room_state: dict | None = None,
               plants: dict | None = None, extras=()) -> dict:
    """{'default': ground name, 'ground': {(gx, gy): name},
        'background': [((gx, gy), name)]  neighbourhood, drawn first, back to front,
        'structs': [((gx, gy), name)]}    home plot, drawn after, back to front by front cell.
    bed_steps: growth steps after G4 (= qualifying months past 6), capped at MAX_BED_STEPS.
    animals: chosen animals whose homes to show (default: PREVIEW_ANIMALS from G2, the first slot).
    room_state: furniture to show, e.g. {"level": 1, "jar": 0, "plant": 0, "droop": False} (room_furniture);
    None = the empty room of batch 1.
    plants: {bed cell: plant piece}, e.g. {(6, 8): "plant_serai_full"} (previews; the app places
    plants from /v1/game "plants").
    extras: [(cell, piece, footprint, layer)] more pieces for previews (the tree, garden decorations,
    the avatar or chickens), sorted by their front cell plus `layer`; a piece name ending in "|flip"
    is drawn mirrored (the facing not drawn, spec §1)."""
    if animals is None:
        animals = PREVIEW_ANIMALS if level >= 2 else ()
    ground, structs = {}, []
    # neighbourhood: porches along each house's two front faces
    for (gx0, gy0), _, (w, d) in NEIGHBOURS:
        gx1, gy1 = gx0 + w - 1, gy0 + d - 1
        for gy in range(gy0, gy1 + 2):
            ground[(gx1 + 1, gy)] = "path_paved"
        for gx in range(gx0, gx1 + 2):
            ground[(gx, gy1 + 1)] = "path_paved"
    background = [(c, n) for c, n, _ in sorted(NEIGHBOURS + NEIGHBOUR_PROPS, key=_front_sum)]
    # home plot
    gate = None
    if level >= 1:
        lo, hi = -BACK, ROOM - 1 + RADIUS[level]
        inside = lambda c: lo <= c[0] <= hi and lo <= c[1] <= hi    # noqa: E731
        for gx in range(lo, hi + 1):
            for gy in range(lo, hi + 1):
                ground[(gx, gy)] = LAWN[level]
        path = []
        for cell, step in _path():
            if not inside(cell):
                gate = (cell, "fence_gate_right" if step == "gy" else "fence_gate_left")
                break
            path.append(cell)
        bed = bed_cells(level, bed_steps)
        for c in bed:                      # freshly dug at the unlock, enriched from G2 (D-63)
            ground[c] = "garden_soil_bare" if level == 1 else "garden_soil_improved"
        path += sorted(c for c in bed_loop(level, bed_steps) if inside(c) and c not in path)
        if level >= 3:
            structs += _edging(bed)
        if level >= 2:
            structs += [(c, "planter_bed_soil") for c in PLANTERS[min(level, 3)]]
        for c in path:
            ground[c] = PATH[level]
        structs += _fence(lo, hi, gate)
    # room (drawn over the garden ground)
    floor = room_floor(room_state["level"]) if room_state else "floor_light_wood"
    for gx in range(ROOM):
        for gy in range(ROOM):
            ground[(gx, gy)] = "floor_kitchen_tile" if (gx, gy) in KITCHEN else floor
    room = [((0, 0), "wall_inside_corner")]
    room += [((0, gy), LEFT_WALL.get(gy, "wall_left")) for gy in range(1, ROOM)]
    room += [((gx, 0), RIGHT_WALL.get(gx, "wall_right")) for gx in range(1, ROOM)]
    for gx in range(ROOM - 1):
        door = (gx, ROOM - 1) == GARDEN_DOOR and level >= 1
        room.append(((gx, ROOM - 1), "wall_cutaway_doorstep_front_left" if door else "wall_cutaway_front_left"))
    room += [((ROOM - 1, gy), "wall_cutaway_front_right") for gy in range(ROOM - 1)]
    room.append(((ROOM - 1, ROOM - 1), "wall_cutaway_front_corner"))
    sizes = {}
    for animal in animals:
        home = ANIMAL_HOMES[animal]
        structs.append((home["cell"], home["piece"]))
        sizes[home["piece"]] = home["size"]
    decals, furnished = [], set()
    if room_state:
        for cell, name, size in room_furniture(room_state["level"], room_state.get("jar", 0),
                                               room_state.get("plant", 0), room_state.get("droop", False),
                                               room_state.get("decor", ())):
            if name.startswith(FLOOR_OVERLAYS):
                decals.append((cell, name))
                continue
            structs.append((cell, name))
            sizes[name] = size
            furnished.add(name)
    for cell, name in (plants or {}).items():
        structs.append((tuple(cell), name))
    extra_key = {}
    for cell, name, (w, d), lay in extras:
        structs.append((tuple(cell), name))
        extra_key[(tuple(cell), name)] = cell[0] + cell[1] + w + d - 2 + lay
    # back to front by the piece's FRONT cell (= its back cell for 1 x 1 pieces); room furniture
    # ties are broken by layer (wall < window view < wall items < furniture < things on furniture);
    # then pieces wholly behind another along gx or gy go first (depth_sort)
    key = lambda s: extra_key.get(s, s[0][0] + s[0][1] + sum(sizes.get(s[1], (1, 1))) - 2   # noqa: E731
                                  + (layer(s[1]) if s[1] in furnished else FRONT_WALL_LAYER
                                     if s[1].startswith("wall_cutaway") else 0))
    extra_size = {(tuple(c), n): tuple(sz) for c, n, sz, _ in extras}
    structs = depth_sort(sorted(room + structs, key=key),
                         lambda s: extra_size.get(s, sizes.get(s[1].partition("|")[0], (1, 1))))
    scene = {"default": "garden_wild", "ground": ground, "background": background, "structs": structs}
    if decals:
        scene["decals"] = decals
    return scene


INTERACTIVE = {"crate_shelf": "assistant", "bookshelf": "assistant", "budget_board_right": "budgets",
               "budget_board_left": "budgets", "coin_jar": "savings", "savings_plant": "savings_history"}


def room_json() -> dict:
    """The room's furniture per room level as plain data for the app (T-16). Pieces with "{jar}"
    or "{plant}" are filled in from the game state (/v1/game: look.coin_jar 0-4, look.savings_plant
    0-4, plus "_droop" when look.plants is "droop" or "rest")."""
    return {
        "floor": {str(lv): room_floor(lv) for lv in ROOM_LEVEL_NAMES},
        "kitchen_floor": {"piece": "floor_kitchen_tile", "cells": [list(c) for c in sorted(KITCHEN)]},
        "levels": {str(lv): {"label": ROOM_LEVEL_NAMES[lv],
                             "furniture": [[c[0], c[1], n, list(s),
                                            "floor" if n.startswith(FLOOR_OVERLAYS) else layer(n)]
                                           for c, n, s in room_furniture(lv, "{jar}", "{plant}")]}
                   for lv in ROOM_LEVEL_NAMES},
        "keep_clear": [list(c) for c in sorted(ROOM_KEEP_CLEAR)],
        "decorations": {name: {"replaces": next((k for k in DECOR_REPLACES if name.startswith(k)), None),
                               "from_room_level": {str(lv): [[c[0], c[1], n, list(s),
                                                              "floor" if n.startswith(FLOOR_OVERLAYS) else layer(n)]
                                                             for c, n, s in items]
                                                   for lv, items in spots.items()}}
                        for name, spots in ROOM_DECOR.items()},
        "interactive": INTERACTIVE,
        "draw": "each furniture entry is [gx, gy, piece, footprint, layer]. Layer 'floor' (rugs): draw right "
                "after the ground tiles, before any structure. Every other piece: add it to the structures and "
                "sort by front cell (gx + gy + w - 1 + d - 1) plus its layer (0.1 window view, 0.2 wall items, "
                "0.3 furniture, 0.4 things standing on furniture, 0.5 the front cut-away walls; back walls and "
                "garden pieces 0), then depth_sort (a piece wholly behind another along gx or gy first, D-88). "
                "Tapping a piece "
                "whose name starts with a key of 'interactive' opens that screen. Each chosen decoration "
                "(in the order chosen) adds the entries of the highest 'from_room_level' at or below the room "
                "level; if it 'replaces' a kind (curtains, rug), first remove the pieces whose names start with it",
    }


def scene_json(level: int) -> dict:
    """The layout as plain data for the app (T-16): lists of [gx, gy, piece], in drawing order.
    G4 also carries the bed's monthly growth (D-61, D-63, D-64): for step k (k qualifying months
    after G4), paint bed_growth[0..k-1].cells with garden_soil_improved, then paint
    bed_growth[k-1].loop with path_nice_paved (the path round the bed moves outward), replace every
    garden_border_* structure with bed_growth[k-1].edging, and sort structures by gx + gy."""
    sc = home_scene(level, animals=())
    out = {
        "level": level, "label": LEVEL_NAMES[level], "room": [0, 0, ROOM, ROOM],
        "animal_homes": {a: {"piece": h["piece"], "cell": list(h["cell"]), "size": list(h["size"]),
                             "sleep_cell": list(h["sleep"]), "frames": "chicken_<walk|peck|idle|sleep>_k"}
                         for a, h in ANIMAL_HOMES.items()},
        "tree": ({"cell": list(TREE_SPOT), "size": [2, 2], "pieces": "tree_<stage 0-6>_<name>[_droop]"}
                 if level >= TREE_FROM_LEVEL else None),
        "decor_free_cells": [list(c) for c in decor_spots(level)],
        "default_ground": sc["default"],
        "ground": [[gx, gy, n] for (gx, gy), n in sorted(sc["ground"].items())],
        "background": [[gx, gy, n] for (gx, gy), n in sc["background"]],
        "structures": [[gx, gy, n] for (gx, gy), n in sc["structs"]],
        "draw": "every visible cell: ground[cell] or default_ground; then background in order; then "
                "structures in order, adding the home of each animal the user has chosen (animal_homes) "
                "and sorting by front cell (gx + gy + w - 1 + d - 1) plus layer (front cut-away walls "
                "'wall_cutaway_*' 0.5, room furniture as room.json, everything else 0), then applying "
                "depth_sort: a piece wholly behind another along gx or gy is drawn first (scenes.depth_sort, "
                "D-88). Each piece at map_origin + "
                "((gx-gy)*32, (gx+gy)*16) - footprint_origin (manifest). View: fitted to the screen width "
                "at 2x, pinch to 3x and drag (D-60). Animals sleep at their home's sleep_cell at night. "
                "The tree (from G4) stands on its 2 x 2 spot at every stage. A garden decoration goes on "
                "decor_free_cells: its footprint (manifest 'cells') must lie on free cells not used by "
                "another decoration; offer the first 2-3 that fit (nearest the garden door, K2)",
    }
    if level == 4:
        out["bed_growth"] = [
            {"step": k, "months_at_3plus": 6 + k, "cells": [list(c) for c in BED_STEPS[k - 1]],
             "loop": [list(c) for c in sorted(bed_loop(4, k))],
             "edging": [[gx, gy, n] for (gx, gy), n in _edging(bed_cells(4, k))]}
            for k in range(1, MAX_BED_STEPS + 1)]
    return out
