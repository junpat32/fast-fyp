"""Batch-2 room furniture and interactive objects (T-22; docs/assets/FAST_ASSET_SPEC_BATCH2.md, D-72, D-84).

Same method as batch 1 (pieces.py): boxes and faces in iso space, drawn as palette indices, lit
from the upper left (tops lightest, faces pointing down-left lit, faces pointing down-right
shaded), a 1-px room outline (spec §1), three times of day by palette swap. Organic parts (the
savings plant) are small pixel templates stamped on top, like the chicken (creatures.py).

Scale (spec §2): 1 cell = 1 m = 16 ground units; 39 px of height per metre.
Coordinates inside a piece: a along gx, b along gy, both 0..16 per cell; h in px.
Placement: by the piece's back cell (scenes.ROOM_LAYOUT). Wall items stand on the wall's room
face: the left wall is the cell's a = 0 edge, the right wall its b = 0 edge (as in batch 1).

Room level 1 (Starter, spec §3): mattress, folding table, kitchen counter with sink, shoe rack,
crate shelf (opens the AI assistant), budget board (left- and right-wall versions), coin jar
(5 fills, on the folding table; on the desk from level 2) and the savings plant (5 stages, each
with a droop version for really bad months, D-73).
"""
from __future__ import annotations

import numpy as np

from .geometry import STRUCT_ORIGIN, Box, outline
from .palette import IDX
from .pieces import Piece, boxes, hash01, solid, tone

C = IDX
OL = C["outline"]                  # room objects use the room outline (spec §1)


def _col(fn_or_name):
    return fn_or_name if callable(fn_or_name) else C[fn_or_name]


# ---------------------------------------------------------------- level 1: Starter
def mattress():
    """A single mattress on the floor, 1 x 2 cells along gy, head at the back (b = 0). 0.9 x 1.9 m,
    8 px high with the blanket (0.2 m)."""
    def side(colour):
        def fn(u, h):
            out = np.full(u.shape, C[colour], np.int16)
            out[(h >= 3) & (h < 4)] = C["stone_soft"]                       # piping round the mattress
            return out
        return fn

    def sheet(a, b):
        return np.full(a.shape, C["wall_cream"], np.int16)

    def blanket(a, b):
        out = np.full(a.shape, C["accent_blue"], np.int16)
        out[b < 17] = C["wall_cream"]                                         # sheet turned down over it
        out[(b >= 17) & (((b - 17) % 5) < 0.6)] = C["accent_blue_dark"]       # quilting
        return out

    parts = boxes(Box(1, 15, 1, 31, 0, 7, top=sheet, left=side("wall_beige"), right=side("wall_shadow")),
                  Box(1, 15, 15, 31, 7, 8, top=blanket, left=C["accent_blue_dark"], right=C["accent_blue_dark"]),
                  Box(3, 13, 2.5, 7.5, 7, 9, **tone("tile_light", "tile_shade", "tile_shade")))    # pillow
    return solid(parts, cells=(1, 2), line=OL)


def folding_table():
    """A low folding table (floor sitting), 0.6 x 0.6 m top, 18 px high, on thin metal legs."""
    legs = tone("stone_mid", "stone_mid", "stone_dark")
    parts = boxes(*[Box(a, a + 1, b, b + 1, 0, 16, **legs) for a in (4, 11) for b in (4, 11)],
                  Box(4, 12, 11, 12, 6, 7, **legs),                              # folding brace
                  Box(3, 13, 3, 13, 16, 18, **tone("wood_light", "wood_warm", "wood_mid")))
    return solid(parts, line=OL)


def kitchen_counter_sink():
    """Base cabinet with a stone top, sink and tap, against the back-right wall (b = 0); 35 px
    (0.9 m) to the worktop, 0.65 m deep."""
    def doors(lit):
        base, line = ("wood_warm", "wood_mid") if lit else ("wood_mid", "wood_dark")

        def fn(u, h):
            out = np.full(u.shape, C[base], np.int16)
            out[h < 3] = C["recess"]                                              # toe kick
            if lit:
                out[(h >= 3) & (np.abs(u - 8) < 0.4)] = C[line]                  # two doors
                out[(h >= 29.5) & (h < 30.5)] = C[line]                           # drawer line
                out[(h >= 23) & (h < 27) & ((np.abs(u - 6.6) < 0.35) | (np.abs(u - 9.4) < 0.35))] = C["stone_mid"]
            return out
        return fn

    def worktop(a, b):
        out = np.full(a.shape, C["stone_light"], np.int16)
        basin = (a >= 3.5) & (a < 12.5) & (b >= 1.5) & (b < 8.5)
        inner = (a >= 4.25) & (a < 11.75) & (b >= 2.25) & (b < 7.75)
        out[basin] = C["stone_soft"]
        out[inner] = C["stone_mid"]
        out[inner & ((a < 5.5) | (b < 3.5))] = C["stone_dark"]                   # inner back walls in shadow
        out[(np.abs(a - 8) < 0.6) & (np.abs(b - 5.5) < 0.6)] = C["stone_dark"]   # drain
        return out

    metal = tone("stone_soft", "stone_light", "stone_mid")
    parts = boxes(Box(0.5, 15.5, 0, 10, 0, 32, top=C["wood_light"], left=doors(True), right=doors(False)),
                  Box(0, 16, 0, 11, 32, 35, top=worktop, left=C["stone_soft"], right=C["stone_mid"]),
                  Box(7.25, 8.75, 0.25, 1.5, 35, 42, **metal),                     # tap
                  Box(7.5, 8.5, 1.5, 4, 40, 42, **metal))                          # spout
    return solid(parts, line=OL)


def shoe_rack():
    """An open two-shelf shoe rack by the entrance door, against the left wall (a = 0); 23 px
    (0.6 m) high, open towards the room (+a)."""
    wood = tone("wood_light", "wood_warm", "wood_mid")
    frame = [Box(0, 6, 2, 3, 0, 23, **wood), Box(0, 6, 13, 14, 0, 23, **wood),     # sides
             Box(0, 6, 3, 13, 2, 3.5, **wood), Box(0, 6, 3, 13, 11, 12.5, **wood),  # shelves
             Box(0, 6, 2, 14, 21.5, 23, **wood)]                                     # top board
    shoes = []
    for h0, pairs in ((3.5, [(4, "wall_cream", "tile_shade", 3), (8.5, "stone_dark", "recess", 3)]),
                      (12.5, [(4, "roof_mid", "roof_dark", 2), (8.5, "accent_red", "roof_dark", 2.5)])):
        for b0, lit, dark, tall in pairs:
            for k in (0, 1.6):                                                       # a pair: two shoes
                shoes.append(Box(1, 5.5, b0 + k, b0 + k + 1.2, h0, h0 + tall, **tone(lit, lit, dark)))
    return solid(boxes(*frame, *shoes), line=OL)


BOOKS = ("accent_blue", "accent_red", "green_mid", "sand_light", "roof_mid", "wall_cream", "accent_blue_dark")


def _crate_front(a0, a1, h0, h1, books, seed):
    """The open front of a crate lying on its side (faces +b): plank rim, dark inside, books."""
    widths = [1.0 + hash01(k, 3, seed) * 0.6 for k in range(12)]

    def fn(u, h):
        out = np.full(u.shape, C["recess"], np.int16)
        x = a0 + 0.9
        for k in range(books):
            w = widths[k]
            top = h0 + 1 + 6 + hash01(k, 7, seed) * 3
            m = (u >= x) & (u < x + w) & (h < top)
            out[m] = C[BOOKS[(k + seed) % len(BOOKS)]]
            x += w
        rim = (u < a0 + 0.75) | (u >= a1 - 0.75) | (h < h0 + 1) | (h >= h1 - 1)
        out[rim] = C["wood_light"]
        return out
    return fn


def _slats(colour, gap, every=3.6):
    def fn(u, h):
        out = np.full(u.shape, C[colour], np.int16)
        out[(h % every) < 0.7] = C[gap]
        return out
    return fn


def crate_shelf():
    """Starter shelf from wooden crates on their sides, against the back-right wall (b = 0):
    two crates below, one on top, books inside; 23 px (0.6 m). Opens the AI assistant (spec §4);
    it grows into the bookshelf at room level 4."""
    def crate(a0, a1, h0, h1, books, seed):
        return Box(a0, a1, 0, 7, h0, h1, top=C["wood_light"], left=_crate_front(a0, a1, h0, h1, books, seed),
                   right=_slats("wood_mid", "wood_dark"))
    parts = boxes(crate(1, 8, 0, 11, 4, 1), crate(8, 15, 0, 11, 5, 4), crate(1, 8, 11, 22, 3, 2),
                  Box(9, 14, 1, 6, 11, 12.5, **tone("accent_blue", "accent_blue", "accent_blue_dark")),  # books lying
                  Box(9.5, 13.5, 1.5, 5.5, 12.5, 14, **tone("sand_light", "sand_light", "sand_mid")))
    return solid(parts, line=OL)


def _board_face(shaded: bool, u0: float):
    """A cork budget board: wooden frame, pinned notes (a list, a bar chart, a sticky note)."""
    frame, cork, cork2 = ("wood_dark", "sand_dark", "soil_light") if shaded else ("wood_mid", "sand_mid", "sand_dark")
    paper, paper2, sticky = ("wall_beige", "tile_shade", "green_mid") if shaded else ("wall_cream", "tile_light", "green_light")

    def fn(u, h):
        x = u - u0                                                     # 0..10 across the board
        out = np.where(hash01(np.floor(x * 2), np.floor(h), 61) < 0.25, C[cork2], C[cork]).astype(np.int16)
        list_note = (x >= 1.2) & (x < 4.6) & (h >= 59) & (h < 70)
        out[list_note] = C[paper]
        out[list_note & ((h % 2.5) < 0.7) & (h < 68) & (x < 4.1)] = C["stone_mid"]      # budget lines
        chart = (x >= 5.6) & (x < 8.9) & (h >= 60) & (h < 71)
        out[chart] = C[paper2]
        for k, (bx, top) in enumerate(((6.1, 65), (7.0, 68), (7.9, 63))):              # a small bar chart
            out[chart & (x >= bx) & (x < bx + 0.6) & (h >= 61) & (h < top)] = C["accent_blue" if k != 1 else "green_mid"]
        note = (x >= 1.6) & (x < 4.9) & (h >= 47) & (h < 56)
        out[note] = C[sticky]
        out[note & ((h % 2.5) < 0.7) & (h < 54) & (x < 4.4)] = C["green_dark"]
        receipt = (x >= 6.1) & (x < 8.4) & (h >= 46) & (h < 57)
        out[receipt] = C[paper]
        out[receipt & ((h % 2) < 0.6)] = C["stone_soft"]
        for px, ph, pin in ((2.9, 69, "accent_red"), (7.2, 70, "accent_blue"), (3.2, 55, "accent_red"),
                            (7.2, 56, "accent_blue")):
            out[(np.abs(x - px) < 0.35) & (h >= ph) & (h < ph + 1)] = C[pin]
        rim = (x < 0.6) | (x >= 9.4) | (h < 45) | (h >= 73)
        out[rim] = C[frame]
        return out
    return fn


def budget_board(wall: str):
    """The budget board (spec §4, opens Budgets): 10 units wide and 30 px tall (0.6 x 0.75 m),
    hanging 44-74 px up the wall (1.1-1.9 m). wall = 'right' (b = 0 edge, lit room face) or
    'left' (a = 0 edge, shaded room face)."""
    if wall == "right":
        bx = Box(3, 13, 0, 0.6, 44, 74, top=C["wood_light"], left=_board_face(False, 3), right=C["wood_mid"])
    else:
        bx = Box(0, 0.6, 3, 13, 44, 74, top=C["wood_light"], right=_board_face(True, 3), left=C["wood_warm"])
    return solid(boxes(bx), line=OL)


# ---- coin jar (spec §4): 5 fills = the CURRENT game cushion 0, 0.5, 1, 2, 3+ months
JAR_FILLS = (0.0, 0.22, 0.45, 0.7, 0.95)
JAR_ON = {"table": (6.0, 6.0, 18), "desk": (11.0, 2.0, 29)}     # (a0, b0, top height) of what it stands on


def coin_jar(fill: int, on: str):
    a0, b0, h0 = JAR_ON[on]
    H = 11                                                         # 0.28 m
    coins_to = h0 + 1 + JAR_FILLS[fill] * (H - 2)

    def side(glass, coin):
        def fn(u, h):
            out = np.full(u.shape, C[glass], np.int16)
            c = h < coins_to
            speck = hash01(np.floor(u * 2), np.floor(h), 51) < 0.35
            out[c] = np.where(speck, C["coin_light"], C[coin])[c]
            out[(h < h0 + 1)] = C[glass]                               # the jar's glass base
            return out
        return fn

    def lit_side(u, h):
        out = side("jar_light", "coin_mid")(u, h)
        out[(np.abs(u - (a0 + 1)) < 0.3) & (h >= coins_to) & (h < h0 + H - 1)] = C["tile_light"]   # glass shine
        return out

    def lid(a, b):
        out = np.full(a.shape, C["stone_light"], np.int16)
        out[(np.abs(a - (a0 + 2)) < 1.1) & (np.abs(b - (b0 + 2)) < 0.3)] = C["stone_dark"]         # coin slot
        return out

    parts = boxes(Box(a0, a0 + 4, b0, b0 + 4, h0, h0 + H, top=C["jar_light"], left=lit_side,
                      right=side("jar_mid", "coin_dark")),
                  Box(a0 - 0.25, a0 + 4.25, b0 - 0.25, b0 + 4.25, h0 + H, h0 + H + 1.5, top=lid,
                      left=C["stone_soft"], right=C["stone_mid"]))
    return solid(parts, line=OL)


# ---- savings plant (spec §4): a pokok duit (money plant, pothos) in a terracotta pot by the
# window. Stage = savings_plant_stage in engine/game.py: 0 sprout, then 1, 2, 3, 6 months saved
# (>= 5% of income). It never shrinks; in a really bad month it droops (D-73) but keeps its leaves.
# A leaf is a rounded heart, lit from the upper left (light top-left, darker bottom-right), its stalk
# at the bottom centre. Leaves overlap into one mass that is outlined once, so the plant reads as a
# bush, not as separate twigs. Drooping: the same leaf hanging (flipped), in darker greens.
LEAF = [".LLM.",
        "LLMMM",
        "LMMMD",
        ".MMD.",
        "..D.."]
LEAF_Y = [".LLM.",                                 # variegated (pothos leaves have cream streaks)
          "LYMMM",
          "LMYMD",
          ".MMD.",
          "..D.."]
SPROUT = [".L.",
          "LLM",
          ".M."]
PLANT_KEY = {"L": "green_light", "M": "green_mid", "D": "green_dark", "Y": "sand_light"}
DROOP_KEY = {"L": "green_mid", "M": "green_mid", "D": "green_dark", "Y": "sand_light"}
# leaves per stage as (x, height of the stalk above the soil, variegated); higher stages keep every
# lower leaf (the plant never loses one) and add more; negative heights trail over the pot's rim
_S1 = [(-2, 1, 0), (2, 2, 0), (0, 4, 0)]
_S2 = _S1 + [(-4, 3, 1), (3, 5, 0), (-1, 7, 0), (2, 8, 1)]
_S3 = _S2 + [(-4, 8, 0), (4, 10, 1), (-2, 11, 1), (1, 13, 0), (-6, -2, 0)]
_S4 = _S3 + [(-3, 15, 0), (2, 17, 1), (0, 20, 0), (5, 14, 0), (-5, 13, 1), (6, -1, 1), (-7, -5, 1), (7, -5, 0)]
PLANT_STAGES = ([(-1, 0, 0), (1, 1, 0)], _S1, _S2, _S3, _S4)
POT = (2, 8, 5, 11)                                # a0, a1, b0, b1 of the pot by the left wall
POT_H = 9


def _line(canvas, x0, y0, x1, y1, colour):
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for t in range(n + 1):
        x, y = round(x0 + (x1 - x0) * t / n), round(y0 + (y1 - y0) * t / n)
        if 0 <= y < canvas.shape[0] and 0 <= x < canvas.shape[1]:
            canvas[y, x] = colour


def _soil_point(a0, a1, b0, b1, h):
    """Canvas pixel of the centre of a pot's soil (a1-a0 x b1-b0 pot, h px tall)."""
    ox, oy = STRUCT_ORIGIN
    ca, cb = (a0 + a1) / 2, (b0 + b1) / 2
    return round(ox + 32 + 2 * ca - 2 * cb), round(oy + ca + cb - h)


def _pot_boxes(a0, a1, b0, b1, h, top, lit, shaded, side_lit=None, side_shaded=None):
    """A pot: a slightly narrower body under a 2 px rim, dark soil inside the rim."""
    def soil(a, b):
        out = np.full(a.shape, C[top], np.int16)
        inner = (a >= a0 + 0.75) & (a < a1 - 0.75) & (b >= b0 + 0.75) & (b < b1 - 0.75)
        out[inner] = C["soil_dark"]
        return out
    return boxes(Box(a0 + 0.5, a1 - 0.5, b0 + 0.5, b1 - 0.5, 0, h - 2, top=C[top],
                     left=side_lit or C[lit], right=side_shaded or C[shaded]),
                 Box(a0, a1, b0, b1, h - 2, h, top=soil, left=C[lit], right=C[shaded]))


def _stamp_leaves(canvas, sx, sy, leaves, droop=False, small=False):
    """Leaves as (x, stalk height above the soil, variegated), back (high) leaves first."""
    key = DROOP_KEY if droop else PLANT_KEY
    top = max(y for _, y, _ in leaves)
    for x, y, var in sorted(leaves, key=lambda leaf: -leaf[1]):
        rows = SPROUT if small else (LEAF_Y if var else LEAF)
        sag = 0
        if droop:
            rows = rows[::-1]                                       # hanging, stalk at the top
            sag = 1 + round(2 * max(y, 0) / max(top, 1))            # a little lower; never into the soil
        w, hh = len(rows[0]), len(rows)
        x0 = sx + x - w // 2 + (int(np.sign(x)) if droop else 0)    # drooping leaves also splay outwards
        y0 = sy - y - hh + 1 + sag
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                yy, xx = y0 + j, x0 + i
                if ch != "." and 0 <= yy < canvas.shape[0] and 0 <= xx < canvas.shape[1]:
                    canvas[yy, xx] = C[key[ch]]


def savings_plant(stage: int, droop: bool = False):
    """Pot (terracotta, 9 px) with the money plant above it. droop: same leaves, tips hanging down,
    darker; never fewer leaves and never a lower stage (D-73)."""
    a0, a1, b0, b1 = POT
    canvas = solid(_pot_boxes(a0, a1, b0, b1, POT_H, "roof_light", "roof_light", "roof_mid"), line=None)
    sx, sy = _soil_point(a0, a1, b0, b1, POT_H)
    if stage >= 3:                                                  # a moss stake to climb, behind the leaves
        _line(canvas, sx, sy - 1, sx, sy - (21 if stage == 4 else 15), C["wood_mid"])
    _stamp_leaves(canvas, sx, sy, PLANT_STAGES[stage], droop, small=stage == 0)
    outline(canvas, OL, "full")
    return canvas


# ---------------------------------------------------------------- level 2: Settling in (0.5 month)
WOOD = tone("wood_light", "wood_warm", "wood_mid")
METAL = tone("stone_soft", "stone_mid", "stone_dark")
SHADE = tone("lamp_shade", "lamp_shade", "lamp_shade_dark")


def _piped(colour):
    def fn(u, h, low=0):
        out = np.full(u.shape, C[colour], np.int16)
        out[(h >= 12.5) & (h < 13.5)] = C["stone_soft"]                 # piping round the mattress
        return out
    return fn


def _bed_sheet(a, b):
    return np.full(a.shape, C["wall_cream"], np.int16)


def _bed_blanket(a, b):
    out = np.full(a.shape, C["accent_blue"], np.int16)
    out[b < 16.5] = C["wall_cream"]                                       # sheet turned down over it
    out[(b >= 16.5) & (((b - 16.5) % 5) < 0.6)] = C["accent_blue_dark"]   # quilting
    return out


def single_bed():
    """A single bed with simple bedding (replaces the mattress), 1 x 2 along gy, head at the back;
    18 px to the top of the bedding, headboard 31 px."""
    def headboard(u, h):
        out = np.full(u.shape, C["wood_warm"], np.int16)
        panel = (u >= 3) & (u < 13) & (h >= 14) & (h < 28)
        out[panel] = C["wood_light"]
        out[panel & ((u < 3.6) | (u >= 12.4) | (h < 14.8) | (h >= 27.2))] = C["wood_mid"]
        return out
    parts = boxes(*[Box(a, a + 1.5, b, b + 1.5, 0, 5, **WOOD) for a in (1, 13.5) for b in (1, 29.5)],
                  Box(1, 15, 1, 31, 5, 10, **WOOD),                                         # frame
                  Box(1.5, 14.5, 1.5, 30.5, 10, 16, top=_bed_sheet, left=_piped("wall_beige"),
                      right=_piped("wall_shadow")),
                  Box(1.25, 14.75, 14, 30.75, 16, 17.5, top=_bed_blanket, left=C["accent_blue_dark"],
                      right=C["accent_blue_dark"]),
                  Box(3, 13, 2.5, 7, 16, 18, **tone("tile_light", "tile_shade", "tile_shade")),  # pillow
                  Box(1, 15, 0, 1.5, 0, 31, top=C["wood_light"], left=headboard, right=C["wood_mid"]))
    return solid(parts, cells=(1, 2), line=OL)


def desk():
    """A compact study/work desk against the back-right wall (b = 0), 29 px: a drawer unit on the
    right (the coin jar stands there from level 2), the lamp on the left."""
    def drawers(u, h):
        out = np.full(u.shape, C["wood_warm"], np.int16)
        out[((h % 9) < 0.8) & (h > 1)] = C["wood_mid"]                    # three drawers
        out[(np.abs(u - 12.5) < 0.5) & ((np.abs(h - 5) < 0.6) | (np.abs(h - 14) < 0.6)
                                        | (np.abs(h - 23) < 0.6))] = C["stone_mid"]
        return out
    parts = boxes(Box(1, 2, 0.5, 8.5, 0, 27, **WOOD),                                     # left panel
                  Box(2, 10, 0, 1, 10, 27, **tone("wood_mid", "wood_mid", "wood_dark")),  # modesty panel
                  Box(10, 15, 0.5, 8.5, 0, 27, top=C["wood_light"], left=drawers, right=C["wood_mid"]),
                  Box(0.5, 15.5, 0, 9, 27, 29, **WOOD))                                     # desktop
    return solid(parts, line=OL)


def office_chair():
    """An office chair at the desk, facing it (towards -b), so the viewer sees its back; seat 18 px,
    backrest 35 px."""
    fabric = tone("stone_mid", "stone_dark", "recess")
    caster = tone("recess", "recess", "recess")
    parts = boxes(Box(4, 12, 7.5, 8.5, 1, 2.5, **METAL), Box(7.5, 8.5, 4, 12, 1, 2.5, **METAL),   # star base
                  *[Box(a, a + 1, b, b + 1, 0, 1, **caster) for a, b in ((3.5, 7.5), (11.5, 7.5), (7.5, 3.5),
                                                                          (7.5, 11.5))],
                  Box(7.5, 8.5, 7.5, 8.5, 2.5, 15, **METAL),                                # gas lift
                  Box(4, 12, 4, 12, 15, 18, **fabric),                                      # seat
                  Box(3.5, 4.5, 5, 10, 18, 23, **METAL), Box(11.5, 12.5, 5, 10, 18, 23, **METAL),  # armrests
                  Box(4.5, 11.5, 11, 12.5, 18, 35, **fabric))                               # backrest
    return solid(parts, line=OL)


def desk_lamp():
    """A desk lamp on the desk's left side, 18 px above the desktop; its shade glows at night."""
    parts = boxes(Box(2.5, 5, 1.5, 4, 29, 30.5, **METAL),                                 # base
                  Box(3.5, 4, 2.5, 3, 30.5, 41, **METAL),                                  # stem
                  Box(2, 5.5, 1, 4.5, 41, 47, **SHADE))                                    # shade
    return solid(parts, line=OL)


# ---------------------------------------------------------------- level 3: Home (1 month)
def wardrobe():
    """A two-door wardrobe against the left wall (a = 0), 74 px (1.9 m); the doors face the room (+a)."""
    def doors(u, h):
        out = np.full(u.shape, C["wood_mid"], np.int16)
        out[h < 4] = C["wood_dark"]                                                       # plinth
        inset = (h >= 8) & (h < 68) & (((u >= 2.5) & (u < 7)) | ((u >= 9) & (u < 13.5)))
        edge = inset & ((h < 8.8) | (h >= 67.2) | (np.abs(u - 2.8) < 0.3) | (np.abs(u - 6.7) < 0.3)
                        | (np.abs(u - 9.3) < 0.3) | (np.abs(u - 13.2) < 0.3))
        out[edge] = C["wood_dark"]
        out[(np.abs(u - 8) < 0.35) & (h >= 4)] = C["wood_dark"]                             # door split
        out[((np.abs(u - 7.3) < 0.3) | (np.abs(u - 8.7) < 0.3)) & (h >= 36) & (h < 42)] = C["stone_soft"]
        return out

    def side(u, h):
        out = np.full(u.shape, C["wood_warm"], np.int16)
        out[h < 4] = C["wood_mid"]
        return out
    parts = boxes(Box(0.5, 8, 1, 15, 0, 72, top=C["wood_light"], left=side, right=doors),
                  Box(0, 8.5, 0.5, 15.5, 72, 74.5, **WOOD))                                 # crown
    return solid(parts, line=OL)


def rug(colours=("roof_mid", "roof_light", "sand_light")):
    """A 2 x 2 rug (1.9 m square), a floor overlay 1 px thick: border, field, a diamond motif.
    Drawn before the furniture (scenes: 'decals'), so it never covers a leg."""
    border, motif, field = colours

    def pattern(a, b):
        out = np.full(a.shape, C[field], np.int16)
        edge = np.minimum(np.minimum(a - 1, 31 - a), np.minimum(b - 1, 31 - b))
        out[edge < 2.5] = C[border]
        out[(edge >= 3.5) & (edge < 4.2)] = C[border]                                    # inner line
        d = np.abs(a - 16) + np.abs(b - 16)
        out[((d >= 5.6) & (d < 7)) | (d < 2.5)] = C[motif]
        return out
    return solid(boxes(Box(1, 31, 1, 31, 0, 1, top=pattern, left=C[border], right=C[border])), cells=(2, 2),
                 line=OL)


def _on_wall(wall):
    """Box maker in wall coordinates (depth d out from the wall, s along it): the left wall is the
    cell's a = 0 edge, the right wall its b = 0 edge."""
    def box(d0, d1, s0, s1, h0, h1, **c):
        return Box(d0, d1, s0, s1, h0, h1, **c) if wall == "left" else Box(s0, s1, d0, d1, h0, h1, **c)
    return box


def wall_shelf(wall):
    """A short wall shelf 50 px up (1.3 m) with a cactus, books and a photo; wall = 'left' or 'right'."""
    box = _on_wall(wall)
    parts = [box(0, 4, 2, 14, 50, 51.5, **WOOD),                                              # board
             box(0, 4, 3.5, 4.3, 47, 50, **WOOD), box(0, 4, 11.7, 12.5, 47, 50, **WOOD),       # brackets, flush
             box(1, 3, 3, 5, 51.5, 55, **tone("roof_light", "roof_light", "roof_mid")),        # cactus pot
             box(1.4, 2.6, 3.4, 4.6, 55, 60, **tone("green_light", "green_mid", "green_dark")),
             box(0.5, 1.5, 10.5, 13, 51.5, 57, **tone("wood_dark", "wood_mid", "wood_dark"))]  # photo frame
    for k, (s0, top, col) in enumerate(((6.8, 58, "accent_red"), (7.7, 59, "accent_blue"), (8.6, 57.5, "green_mid"))):
        parts.append(box(0.5, 3.5, s0, s0 + 0.9, 51.5, top, **tone(col, col, col)))
    return solid(boxes(*parts), line=OL)


POTTED = [(-3, 1, 0), (3, 1, 0), (0, 2, 0), (-5, 4, 0), (5, 4, 0), (-2, 5, 0), (2, 6, 0), (-4, 8, 0),
          (4, 8, 0), (0, 8, 0), (-2, 10, 0), (2, 11, 0), (0, 12, 0)]


def potted_plant():
    """A leafy house plant in a stone-grey pot, 27 px."""
    a0, a1, b0, b1, h = 4.5, 11.5, 4.5, 11.5, 10
    canvas = solid(_pot_boxes(a0, a1, b0, b1, h, "stone_light", "stone_soft", "stone_mid"), line=None)
    sx, sy = _soil_point(a0, a1, b0, b1, h)
    _stamp_leaves(canvas, sx, sy, POTTED)
    outline(canvas, OL, "full")
    return canvas


# ---------------------------------------------------------------- level 4: Comfortable (2 months)
def sofa():
    """A two-seat sofa, 1 x 2 along gy, its back towards -a and facing the coffee table (+a), so the
    viewer sees its front; 31 px to the top of the back."""
    fabric = tone("blue_light", "accent_blue", "accent_blue_dark")
    legs = tone("wood_mid", "wood_mid", "wood_dark")
    parts = boxes(*[Box(a, a + 1, b, b + 1, 0, 3, **legs) for a in (2, 13) for b in (2, 29)],
                  Box(1.5, 14, 1.5, 30.5, 3, 11, **fabric),                                    # base
                  Box(5, 13.5, 4.5, 15.6, 11, 15, **fabric), Box(5, 13.5, 16.4, 27.5, 11, 15, **fabric),   # cushions
                  Box(1.5, 5, 1.5, 30.5, 11, 31, **fabric),                                    # back
                  Box(5, 14, 1.5, 4.5, 11, 20, **fabric), Box(5, 14, 27.5, 30.5, 11, 20, **fabric))   # arms
    return solid(parts, cells=(1, 2), line=OL)


def coffee_table():
    """A coffee table (replaces the folding table), 18 px, darker wood, a lower shelf with a magazine."""
    dark = tone("wood_warm", "wood_mid", "wood_dark")
    parts = boxes(*[Box(a, a + 1, b, b + 1, 0, 15, **dark) for a in (3, 12) for b in (4, 11)],
                  Box(3, 13, 4, 12, 4, 5, **dark),                                              # lower shelf
                  Box(5, 10, 6, 10, 5, 6, **tone("wall_cream", "tile_shade", "tile_shade")),    # magazine
                  Box(2.5, 13.5, 3.5, 12.5, 15, 18, **dark))
    return solid(parts, line=OL)


def bookshelf():
    """A tall bookshelf (the crate shelf grown up; still opens the AI assistant) against the back-right
    wall (b = 0), 70 px (1.8 m), four shelves of books."""
    shelves = (1, 18, 35, 52)

    def front(u, h):
        out = np.full(u.shape, C["recess"], np.int16)
        for k, s in enumerate(shelves):
            x, j = 2.0, 0
            while x < 14:
                w = 0.9 + hash01(j, k, 71) * 0.7
                top = s + 8 + hash01(j, k, 72) * 6
                out[(u >= x) & (u < min(x + w, 14)) & (h >= s) & (h < top)] = C[BOOKS[(j + 3 * k) % len(BOOKS)]]
                x += w + (0.6 if hash01(j, k, 73) < 0.15 else 0)
                j += 1
        for s in shelves:
            out[(h >= s - 1.2) & (h < s)] = C["wood_light"]
        out[(u < 2) | (u >= 14) | (h >= 67)] = C["wood_warm"]                                # sides, top rail
        return out
    parts = boxes(Box(1, 15, 0, 6, 0, 68, top=C["wood_light"], left=front, right=C["wood_mid"]),
                  Box(0.5, 15.5, 0, 6.5, 68, 70, **WOOD))
    return solid(parts, line=OL)


def compact_fridge():
    """A compact fridge in the kitchen corner (b = 0 wall), 55 px (1.4 m), freezer door on top."""
    def door(u, h):
        out = np.full(u.shape, C["tile_shade"], np.int16)
        out[(h >= 37) & (h < 38)] = C["stone_soft"]                                           # freezer split
        out[(np.abs(u - 12.6) < 0.4) & (((h >= 40) & (h < 49)) | ((h >= 22) & (h < 33)))] = C["stone_mid"]
        out[h < 2] = C["stone_mid"]                                                            # grille
        return out
    return solid(boxes(Box(2, 14, 0, 11, 0, 55, top=C["tile_light"], left=door, right=C["stone_soft"])), line=OL)


def _cabinet(lit):
    base, line = ("wood_warm", "wood_mid") if lit else ("wood_mid", "wood_dark")

    def fn(u, h):
        out = np.full(u.shape, C[base], np.int16)
        out[h < 3] = C["recess"]                                                               # toe kick
        if lit:
            out[(h >= 3) & (np.abs(u - 8) < 0.4)] = C[line]
            out[(h >= 23) & (h < 27) & ((np.abs(u - 6.6) < 0.35) | (np.abs(u - 9.4) < 0.35))] = C["stone_mid"]
        return out
    return fn


def stove():
    """A base cabinet with a two-burner gas hob (common in Malaysian kitchens) beside the sink, 35 px."""
    def hob(a, b):
        out = np.full(a.shape, C["stone_light"], np.int16)
        plate = (a >= 2) & (a < 14) & (b >= 1.5) & (b < 9)
        out[plate] = C["stone_dark"]
        for ca in (5, 11):
            r = np.hypot(a - ca, b - 5)
            out[plate & (r < 2.6) & (r >= 1.7)] = C["stone_mid"]                               # burner rings
            out[plate & (r < 0.9)] = C["recess"]
        return out

    def front(u, h):
        out = _cabinet(True)(u, h)
        out[(h >= 33) & (h < 35) & ((np.abs(u - 5) < 0.6) | (np.abs(u - 11) < 0.6))] = C["recess"]   # knobs
        return out
    parts = boxes(Box(0.5, 15.5, 0, 10, 0, 32, top=C["wood_light"], left=_cabinet(True), right=_cabinet(False)),
                  Box(0, 16, 0, 11, 32, 35, top=hob, left=front, right=C["stone_mid"]))
    return solid(parts, line=OL)


def curtains(wall, colours=("sand_light", "sand_mid", "sand_dark")):
    """Curtains drawn open each side of a window, on a rod at 84 px; wall = 'left' or 'right'."""
    light, mid, dark = colours
    box = _on_wall(wall)
    lit = wall == "right"                                       # the right wall's room face is the lit one

    def folds(u, h):
        a, b = (light, mid) if lit else (mid, dark)
        out = np.where((u % 1.0) < 0.5, C[a], C[b]).astype(np.int16)
        out[h < 45.2] = C[b]                                                                   # hem
        return out
    face = {"left": folds, "right": C[mid]} if lit else {"right": folds, "left": C[mid]}
    parts = [box(0.2, 1.2, s0, s1, 44, 83, top=C[light], **face) for s0, s1 in ((0.3, 3.2), (12.8, 15.7))]
    parts.append(box(0.4, 0.9, 0, 16, 83, 85, **WOOD))                                         # rod
    return solid(boxes(*parts), line=OL)


# ---------------------------------------------------------------- level 5: Cosy (3 months)
def _hills(x, h):
    """Room level 5's painting: a kampung house in green hills under a blue sky (x 0..8 across)."""
    out = np.full(x.shape, C["sky"], np.int16)
    out[h >= 66] = C["sky_light"]
    out[h < 58 + 2 * np.sin(x * 0.9)] = C["green_mid"]                                         # hills
    out[h < 54 - 1.5 * np.cos(x * 0.7)] = C["green_dark"]
    out[(x >= 4.6) & (x < 6.4) & (h >= 55) & (h < 59)] = C["wall_cream"]                       # house
    out[(x >= 4.2) & (x < 6.8) & (h >= 59) & (h < 61.5)] = C["roof_mid"]
    out[(np.abs(x - 2) < 0.7) & (np.abs(h - 67.5) < 1)] = C["coin_light"]                      # sun
    return out


def _kampung_sunset(x, h):
    """Decoration: a rumah kampung on stilts beside a coconut palm, against a sunset."""
    out = np.full(x.shape, C["coin_light"], np.int16)
    out[h >= 63] = C["sand_light"]
    out[h >= 68] = C["pink_light"]
    out[(np.hypot((x - 2.2) * 2, h - 58) < 3.2)] = C["wall_cream"]                             # the setting sun
    out[h < 55.5] = C["orange"]                                                                # glow on the water
    out[(h < 55.5) & ((h % 2) < 0.6) & ((x + h) % 3 < 1.6)] = C["coin_light"]
    out[h < 53.5] = C["green_dark"]                                                            # the bank
    house = (x >= 3.6) & (x < 6.6)
    out[house & (h >= 56) & (h < 60)] = C["wood_mid"]
    out[house & (h >= 57) & (h < 59) & (np.abs(x - 5.1) < 0.4)] = C["recess"]                  # window
    roof = (h >= 60) & (h < 64) & (np.abs(x - 5.1) < 2.0 - (h - 60) * 0.45)
    out[roof] = C["roof_dark"]
    out[(h >= 53.5) & (h < 56) & ((np.abs(x - 3.9) < 0.3) | (np.abs(x - 6.3) < 0.3))] = C["wood_dark"]  # stilts
    trunk = (np.abs(x - (1.0 + (h - 52) * 0.06)) < 0.3) & (h >= 53.5) & (h < 66)
    out[trunk] = C["wood_dark"]
    for dx, dh in ((-0.9, -1), (0.9, -1), (-0.6, 0.6), (0.7, 0.6), (0, 1)):                    # palm fronds
        out[(np.abs(x - 1.8 - dx) < 0.55) & (np.abs(h - 66 - dh) < 0.6)] = C["green_dark"]
    return out


def _flowers(x, h):
    """Decoration: bunga raya and leaves in a blue vase on a cream wall."""
    out = np.full(x.shape, C["wall_cream"], np.int16)
    out[h < 54] = C["wall_beige"]                                                              # the table
    vase = (np.abs(x - 4) < 1.3 - np.maximum(0, h - 58) * 0.2) & (h >= 53) & (h < 60)
    out[vase] = C["accent_blue"]
    out[vase & (x < 3.5)] = C["blue_light"]
    for cx, ch in ((2.3, 63.5), (5.6, 62.5), (3.4, 67), (5.0, 66.5)):                          # leaves
        out[(np.abs(x - cx) < 0.8) & (np.abs(h - ch) < 1.2)] = C["green_mid"]
    out[(np.abs(x - 4) < 0.25) & (h >= 60) & (h < 66)] = C["green_dark"]                       # stems
    for cx, ch in ((2.7, 65.5), (5.4, 64.5), (4.1, 68.5)):                                     # three flowers
        petals = np.hypot((x - cx) * 2.2, h - ch) < 2.0
        out[petals] = C["accent_red"]
        out[petals & (np.hypot((x - cx) * 2.2, h - ch) < 0.8)] = C["coin_light"]
    return out


PICTURES = {"hills": (_hills, "wood_dark", "wood_mid"), "kampung": (_kampung_sunset, "wood_dark", "wood_mid"),
            "flowers": (_flowers, "wood_light", "wood_warm")}


def wall_art(wall, design="hills"):
    """A framed painting, 50-72 px up the wall: room level 5's hills, or a decoration (kampung at
    sunset, flowers)."""
    box = _on_wall(wall)
    draw, frame, side = PICTURES[design]

    def picture(u, h):
        x = u - 4                                                                              # 0..8 across
        out = draw(x, h)
        out[(x < 0.6) | (x >= 7.4) | (h < 50.8) | (h >= 71.2)] = C[frame]                       # frame
        return out
    face = {"left": picture, "right": C[frame]} if wall == "right" else {"right": picture, "left": C[side]}
    return solid(boxes(box(0, 0.6, 4, 12, 50, 72, top=C[side], **face)), line=OL)


def floor_lamp():
    """A floor lamp by the sofa, 62 px (1.6 m); its shade glows at night."""
    parts = boxes(Box(5.5, 10.5, 5.5, 10.5, 0, 1.5, **tone("stone_mid", "stone_dark", "recess")),
                  Box(7.6, 8.4, 7.6, 8.4, 1.5, 50, **METAL),
                  Box(4.5, 11.5, 4.5, 11.5, 50, 62, **SHADE))
    return solid(parts, line=OL)


# a dense oval canopy: rows of overlapping leaves, widest in the middle (half-widths in px)
BIG_PLANT = [(x + (y // 4) % 2, y, 0)
             for y, half in ((10, 5), (14, 8), (18, 10), (22, 11), (26, 11), (30, 10), (34, 8), (38, 5), (41, 2))
             for x in range(-half, half + 1, 3)]


def big_plant():
    """A tall rubber plant (pokok getah hiasan) in a woven basket, 59 px."""
    a0, a1, b0, b1, h = 3.5, 12.5, 3.5, 12.5, 14

    def weave(dark):
        def fn(u, hh):
            woven = ((np.floor(u) + np.floor(hh / 2)) % 2) == 0
            return np.where(woven, C["sand_dark" if dark else "sand_mid"], C["sand_mid" if dark else "sand_light"]
                            ).astype(np.int16)
        return fn
    canvas = solid(_pot_boxes(a0, a1, b0, b1, h, "sand_light", "sand_mid", "sand_dark", side_lit=weave(False),
                              side_shaded=weave(True)), line=None)
    sx, sy = _soil_point(a0, a1, b0, b1, h)
    _stamp_leaves(canvas, sx, sy, BIG_PLANT)
    outline(canvas, OL, "full")
    for dx, colour in ((0, "wood_mid"), (1, "wood_dark")):                                     # the trunk
        _line(canvas, sx + dx, sy - 1, sx + dx, sy - 9, C[colour])
    return canvas


def window_view(wall):
    """The view through a window (sky, cloud, trees), over the glass only, so the window's frame and
    bars show through. It darkens at night like the outside; it never glows."""
    from .pieces import WIN_HI, WIN_LO
    mid = (WIN_LO + WIN_HI) // 2 - 1

    def view(u, h):
        out = np.full(u.shape, C["sky"], np.int16)
        out[h >= 70] = C["sky_light"]
        out[(np.abs(u - 10.5) < 1.8) & (np.abs(h - 74) < 1.4)] = C["wall_cream"]              # cloud
        out[h < 57 + 3 * np.sin(u * 1.3) + 2 * np.cos(u * 0.7)] = C["green_mid"]              # trees
        out[h < 53 + 2 * np.sin(u * 2.1)] = C["green_dark"]
        win = (u >= 2) & (u < 14) & (h >= WIN_LO) & (h < WIN_HI)
        frame = win & ((u < 2.5) | (u >= 13.5) | (h < WIN_LO + 1) | (h >= WIN_HI - 1)
                       | ((u >= 7.75) & (u < 8.25)) | ((h >= mid) & (h < mid + 1)))
        out[~win | frame] = -1                                                                 # the frame shows through
        return out
    # on the wall plane itself (a = 0 / b = 0), so it lines up with the window pixel for pixel
    bx = Box(-0.3, 0, 0, 16, WIN_LO, WIN_HI, right=view) if wall == "left" else \
        Box(0, 16, -0.3, 0, WIN_LO, WIN_HI, left=view)
    return solid(boxes(bx), line=None)


# ---------------------------------------------------------------- decorations (shared/game.json, D-69)
# One choice per 200 points. Colour variants of the level pieces, two paintings, a desk plant, a
# dining set and a storage cabinet. Where each one goes: scenes.ROOM_DECOR.
CURTAIN_COLOURS = {"sage": ("house_sage", "house_sage_shade", "green_mid"),
                   "peach": ("house_peach", "house_peach_shade", "sand_dark"),
                   "blue": ("blue_light", "accent_blue", "accent_blue_dark")}
RUG_COLOURS = {"green": ("green_dark", "sand_light", "green_mid"),          # (border, motif, field)
               "terracotta": ("roof_dark", "sand_light", "roof_light"),
               "blue": ("accent_blue_dark", "wall_cream", "blue_light")}


def dining_table():
    """A small square dining table for two, 29 px (0.75 m), with a cup of teh on it."""
    parts = boxes(*[Box(a, a + 1.2, b, b + 1.2, 0, 27, **WOOD) for a in (3, 11.8) for b in (3, 11.8)],
                  Box(2.5, 13.5, 2.5, 13.5, 27, 29, **WOOD),
                  Box(9, 11, 5.5, 7.5, 29, 32, **tone("roof_light", "wall_cream", "tile_shade")))   # teh in a cup
    return solid(parts, line=OL)


def dining_chair():
    """A wooden dining chair facing the table (+a), so the viewer sees the seat; seat 18 px, back 35 px."""
    parts = boxes(*[Box(a, a + 1, b, b + 1, 0, 16, **WOOD) for a in (3.5, 11) for b in (4, 11)],
                  Box(3, 12.5, 3.5, 12.5, 16, 18, **WOOD),                                    # seat
                  Box(3, 4.5, 4, 5.2, 18, 35, **WOOD), Box(3, 4.5, 10.8, 12, 18, 35, **WOOD),  # back posts
                  Box(3, 4.5, 5.2, 10.8, 27, 33, **tone("wood_light", "wood_warm", "wood_mid")))  # back rail
    return solid(parts, line=OL)


def storage_cabinet():
    """A low storage cabinet against the left wall (a = 0), doors facing the room (+a), 35 px, a woven
    basket on top."""
    def doors(u, h):
        out = np.full(u.shape, C["wood_mid"], np.int16)
        out[h < 3] = C["recess"]                                                            # toe kick
        out[(h >= 3) & (np.abs(u - 8) < 0.35)] = C["wood_dark"]                               # door split
        out[(h >= 23) & (h < 23.8)] = C["wood_dark"]                                           # drawer line
        out[(h >= 27) & (h < 29) & (np.abs(u - 8) < 1.2)] = C["stone_soft"]                    # drawer pull
        out[(h >= 14) & (h < 19) & ((np.abs(u - 6.9) < 0.3) | (np.abs(u - 9.1) < 0.3))] = C["stone_soft"]
        return out

    def weave(lit):
        a, b = ("sand_light", "sand_mid") if lit else ("sand_mid", "sand_dark")

        def fn(u, h):
            out = np.where(((np.floor(u) + np.floor(h / 1.5)) % 2) == 0, C[a], C[b]).astype(np.int16)
            out[h >= 40] = C["sand_dark"]                                                      # the basket's rim
            return out
        return fn

    def opening(a, b):                                                                        # looking into it
        out = np.full(a.shape, C["recess"], np.int16)
        out[(a < 2.6) | (a >= 6.4) | (b < 3.6) | (b >= 8.4)] = C["sand_light"]
        return out
    parts = boxes(Box(0.5, 8, 1, 15, 0, 33, top=C["wood_light"], left=C["wood_warm"], right=doors),
                  Box(0, 8.5, 0.5, 15.5, 33, 35, **WOOD),
                  Box(2, 7, 3, 9, 35, 41, top=opening, left=weave(True), right=weave(False)),
                  Box(3, 6, 4.5, 7.5, 39, 42.5, **tone("blue_light", "accent_blue", "accent_blue_dark")))  # a towel
    return solid(parts, line=OL)


def _outline_outside(canvas, mask, colour, keep):
    """1-px outline just outside `mask` (thin leaves stay green instead of turning into outline),
    never over the pixels in `keep` (the pot the leaves grow out of)."""
    pad = np.pad(mask, 1)
    ring = ~mask & (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:])
    canvas[ring & ~keep] = colour


SNAKE_LEAVES = [(-3, 7, -1), (-1, 10, 0), (1, 9, 0), (3, 6, 1)]      # (x, height, lean) of each blade


def desk_plant(on="desk"):
    """A snake plant (lidah jin) in a small white pot, on the desk (room level 2+) or, before there is a
    desk, on the folding table beside the coin jar."""
    a0, b0, h0 = {"desk": (6.5, 1.5, 29), "table": (9.5, 3.5, 18)}[on]
    a1, b1, H = a0 + 3, b0 + 3, 5
    pot = boxes(Box(a0 + 0.25, a1 - 0.25, b0 + 0.25, b1 - 0.25, h0, h0 + H - 1, **tone("wall_cream", "wall_cream",
                                                                                       "tile_shade")),
                Box(a0, a1, b0, b1, h0 + H - 1, h0 + H, top=C["soil_dark"], left=C["tile_light"], right=C["tile_shade"]))
    canvas = solid(pot, line=OL)
    sx, sy = _soil_point(a0, a1, b0, b1, h0 + H)
    pot_px = canvas >= 0
    leaves = np.zeros(canvas.shape, bool)
    for x, hgt, lean in SNAKE_LEAVES:
        for k in range(hgt):
            xx = sx + x + round(lean * k / hgt)
            for dx, colour in ((0, "green_mid"), (1, "green_dark")):
                if k == hgt - 1 and dx == 1:
                    continue                                                                 # pointed tip
                canvas[sy - 1 - k, xx + dx] = C["green_light" if k % 3 == 1 and dx == 0 else colour]   # bands
                leaves[sy - 1 - k, xx + dx] = True
    _outline_outside(canvas, leaves, OL, keep=pot_px & ~leaves)
    return canvas


# ---------------------------------------------------------------- registry
def _f(name, fn, note="", cells=(1, 1), folder="apartment/furniture"):
    return Piece(name, folder, "struct", fn, note, cells)


FURNITURE = [
    _f("mattress", mattress, "room level 1: on the floor, 1 x 2 along gy, head at the back", cells=(1, 2)),
    _f("folding_table", folding_table, "room level 1: low table; the coin jar stands on it"),
    _f("kitchen_counter_sink", kitchen_counter_sink, "room level 1: against the back-right wall (b = 0)"),
    _f("shoe_rack", shoe_rack, "room level 1: by the entrance door, against the left wall (a = 0)"),
    _f("crate_shelf", crate_shelf, "room level 1: opens the AI assistant; becomes the bookshelf at level 4",
       folder="apartment/interactive"),
    _f("budget_board_right", lambda: budget_board("right"), "opens Budgets; on the right wall (b = 0)",
       folder="apartment/interactive"),
    _f("budget_board_left", lambda: budget_board("left"), "opens Budgets; on the left wall (a = 0)",
       folder="apartment/interactive"),
]
FURNITURE += [_f(f"coin_jar_{on}_{k}", (lambda k=k, on=on: coin_jar(k, on)),
                 f"opens Savings; current game cushion {('0', '0.5', '1', '2', '3+')[k]} months; on the {on}",
                 folder="apartment/interactive")
              for on in JAR_ON for k in range(len(JAR_FILLS))]
FURNITURE += [_f(f"savings_plant_{k}{'_droop' if d else ''}", (lambda k=k, d=d: savings_plant(k, d)),
                 f"opens Savings history; stage {k} ({('sprout', '1 month', '2 months', '3 months', '6 months')[k]} "
                 f"saved){', really bad month (droops, D-73)' if d else ''}", folder="apartment/interactive")
              for k in range(len(PLANT_STAGES)) for d in (False, True)]
APPROVED = {p.name for p in FURNITURE}          # step 1 (room level 1), approved by Patrick 2026-10-14
FURNITURE += [
    _f("single_bed", single_bed, "room level 2: replaces the mattress; 1 x 2 along gy", cells=(1, 2)),
    _f("desk", desk, "room level 2: against the back-right wall (b = 0); the coin jar moves onto it"),
    _f("office_chair", office_chair, "room level 2: at the desk, facing it (-b)"),
    _f("desk_lamp", desk_lamp, "room level 2: stands on the desk; glows at night"),
    _f("wardrobe", wardrobe, "room level 3: against the left wall (a = 0)"),
    _f("rug", rug, "room level 3: 2 x 2 floor overlay, drawn before the furniture", cells=(2, 2)),
    _f("wall_shelf_left", lambda: wall_shelf("left"), "room level 3: on the left wall", folder="apartment/wall_items"),
    _f("wall_shelf_right", lambda: wall_shelf("right"), "room level 3: on the right wall", folder="apartment/wall_items"),
    _f("potted_plant", potted_plant, "room level 3"),
    _f("sofa", sofa, "room level 4: 1 x 2 along gy, facing +a", cells=(1, 2)),
    _f("coffee_table", coffee_table, "room level 4: replaces the folding table"),
    _f("bookshelf", bookshelf, "room level 4: replaces the crate shelf; opens the AI assistant",
       folder="apartment/interactive"),
    _f("compact_fridge", compact_fridge, "room level 4: kitchen corner"),
    _f("stove", stove, "room level 4: beside the sink"),
    _f("curtains_left", lambda: curtains("left"), "room level 4: on a left-wall window", folder="apartment/wall_items"),
    _f("curtains_right", lambda: curtains("right"), "room level 4: on a right-wall window", folder="apartment/wall_items"),
    _f("wall_art_left", lambda: wall_art("left"), "room level 5: on the left wall", folder="apartment/wall_items"),
    _f("wall_art_right", lambda: wall_art("right"), "room level 5: on the right wall", folder="apartment/wall_items"),
    _f("floor_lamp", floor_lamp, "room level 5: glows at night"),
    _f("big_plant", big_plant, "room level 5"),
    _f("window_view_left", lambda: window_view("left"), "room level 5: over a left-wall window's glass",
       folder="apartment/wall_items"),
    _f("window_view_right", lambda: window_view("right"), "room level 5: over a right-wall window's glass",
       folder="apartment/wall_items"),
]
DECOR = "apartment/decorations"
DECORATIONS = [
    _f("dining_table", dining_table, "decoration 'dining_set' (with the dining chair)", folder=DECOR),
    _f("dining_chair", dining_chair, "decoration 'dining_set': faces the table (+a)", folder=DECOR),
    _f("storage_cabinet", storage_cabinet, "decoration: against the left wall (a = 0)", folder=DECOR),
    _f("desk_plant", desk_plant, "decoration: a snake plant on the desk (room level 2+)", folder=DECOR),
    _f("desk_plant_table", lambda: desk_plant("table"), "decoration 'desk_plant' at room level 1, on the "
       "folding table", folder=DECOR),
]
DECORATIONS += [_f(f"curtains_{name}_{wall}", (lambda name=name, wall=wall: curtains(wall, CURTAIN_COLOURS[name])),
                   f"decoration 'curtains_{name}': replaces the curtains on a {wall}-wall window", folder=DECOR)
                for name in CURTAIN_COLOURS for wall in ("left", "right")]
DECORATIONS += [_f(f"rug_{name}", (lambda name=name: rug(RUG_COLOURS[name])),
                   f"decoration 'rug_{name}': replaces the rug; 2 x 2 floor overlay", cells=(2, 2), folder=DECOR)
                for name in RUG_COLOURS]
DECORATIONS += [_f(f"wall_art_{design}_{wall}", (lambda design=design, wall=wall: wall_art(wall, design)),
                   f"decoration 'wall_art_{design}' on the {wall} wall", folder=DECOR)
                for design in ("kampung", "flowers") for wall in ("left", "right")]
FURNITURE += DECORATIONS
