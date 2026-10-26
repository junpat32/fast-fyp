"""Bed plants, tiers 1-2 (T-22 batch 2; spec §5, D-61, D-69, D-73, D-74, D-84).

One plant per bed cell, drawn standing on the cell's centre. Names and stages follow the game
rules: shared/game.json "plants" (tier 1 serai, pandan, chilli; tier 2 bunga raya, bougainvillea,
ixora) and engine.game.plant_stage (seedling -> young after 7 growing days -> full after 21).
Every stage has a droop version for really bad months: leaves and blades hang lower and darker,
flowers stay (never dead, never gone, never a lower stage; D-73). Plus a free seedling for empty
bed cells (D-69). Heights (spec §2): seedling ~6 px, young ~12 px, full 18-24 px.

Drawn as pixel shapes, like the chicken and the money plant: blades are curved lines, leaves the
money plant's shaded heart, flowers small templates. Grass-like blades are only 1-2 px wide, so the
garden outline (outline_soft, spec §1) is drawn just OUTSIDE the plant instead of replacing its
edge pixels (which would turn a thin blade solid dark); never under the plant, where it meets the soil.
"""
from __future__ import annotations

import numpy as np

from .furniture import LEAF, SPROUT
from .geometry import STRUCT_ORIGIN
from .palette import IDX, TRANSPARENT
from .pieces import Piece

C = IDX
OL = C["outline_soft"]
BASE = (STRUCT_ORIGIN[0] + 32, STRUCT_ORIGIN[1] + 16)      # the cell centre on the ground (a = b = 8)
STAGES = ("seedling", "young", "full")
TIER_1_2 = ("serai", "pandan", "chilli", "bunga_raya", "bougainvillea", "ixora")
GREENS = {"L": "green_light", "M": "green_mid", "D": "green_dark"}
DROOP = {"green_light": "green_mid", "green_mid": "green_dark", "green_dark": "green_dark"}


def _canvas():
    return np.full((152, 80), TRANSPARENT, np.int16)


def _put(canvas, x, y, colour):
    if 0 <= y < canvas.shape[0] and 0 <= x < canvas.shape[1]:
        canvas[y, x] = C[colour]


def _blade(canvas, angle, height, bend, colours, droop=False, width=1, x0=0):
    """A curved blade from the base: leans by `angle` (px of sideways lean at the top), arches by
    `bend` (the tip curls further out and down). Lit colour on the left, shade on the right."""
    lit, shade = colours
    if droop:
        bend, height = bend + height * 0.18, height * 0.88         # tips bow over; it never lies flat
        lit, shade = DROOP.get(lit, lit), DROOP.get(shade, shade)
    bx, by = BASE[0] + x0, BASE[1]
    steps = max(int(height * 1.5), 4)
    for k in range(steps + 1):
        t = k / steps
        x = bx + angle * t + np.sign(angle or 1) * bend * t ** 2
        y = by - height * t + bend * 0.8 * t ** 3                  # the tip arches back down
        for w in range(width):
            _put(canvas, round(x) + w, round(y), lit if w == 0 and t > 0.25 else shade)


def _leaf(canvas, x, y, droop=False, small=False):
    rows = SPROUT if small else LEAF
    if droop:
        rows = rows[::-1]
    w, h = len(rows[0]), len(rows)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                colour = GREENS[ch] if ch in GREENS else "green_mid"
                _put(canvas, BASE[0] + x - w // 2 + i, BASE[1] - y - h + 1 + j, DROOP[colour] if droop else colour)


def _stamp(canvas, x, y, rows, key):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                _put(canvas, BASE[0] + x + i, BASE[1] - y + j, key[ch])


HIBISCUS = [".rr.", "rRyr", "rRRr", ".rr."]                          # bunga raya: red, yellow stamen
HIBISCUS_KEY = {"r": "accent_red", "R": "red_dark", "y": "coin_light"}
BRACTS = [".p.", "pPp", ".P."]                                        # bougainvillea bract cluster
BRACTS_KEY = {"p": "pink_light", "P": "pink_mid"}
IXORA = [".oo.", "oOOo", ".oo."]                                      # ixora: a round cluster of small flowers
IXORA_KEY = {"o": "orange", "O": "accent_red"}
CHILLI = ["r", "r", "R"]                                              # a hanging red chilli
CHILLI_KEY = {"r": "accent_red", "R": "red_dark"}
GREEN_CHILLI_KEY = {"r": "green_light", "R": "green_mid"}


def _outer_outline(canvas):
    """1-px outline around the plant, outside its pixels; never directly under it (soil contact)."""
    sil = canvas >= 0
    pad = np.pad(sil, 1)
    up, down, left, right = pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]
    ring = ~sil & (up | down | left | right)
    under = ~sil & up & ~down & ~left & ~right
    ring &= ~(under & (np.arange(canvas.shape[0])[:, None] >= BASE[1]))
    canvas[ring] = OL
    return canvas


# ---------------------------------------------------------------- the plants
def serai(stage, droop=False):
    """Lemongrass: a clump of pale, upright, arching blades with a sandy base."""
    c = _canvas()
    n, h = {"seedling": (3, 6), "young": (6, 12), "full": (9, 20)}[stage]
    for k in range(n):
        lean = (k - (n - 1) / 2) * (2.2 if stage == "full" else 1.6)
        _blade(c, lean, h * (0.75 + 0.25 * ((k * 7) % 5) / 4), abs(lean) * 0.4, ("green_light", "green_mid"),
               droop, x0=round(lean / 3))
    for dx in (-1, 0, 1):                                              # the pale bulb at the base
        _put(c, BASE[0] + dx, BASE[1] - 1, "sand_light")
    return _outer_outline(c)


def pandan(stage, droop=False):
    """Pandan: a rosette of long, glossy, dark-green strap leaves arching outwards."""
    c = _canvas()
    n, h = {"seedling": (3, 6), "young": (6, 12), "full": (9, 19)}[stage]
    for k in range(n):
        lean = (k - (n - 1) / 2) * (1.5 if stage == "full" else 1.2)
        _blade(c, lean, h * (0.75 + 0.25 * ((k * 3) % 4) / 3), abs(lean) * 0.6 + 1, ("green_mid", "green_dark"),
               droop, width=2, x0=0)
    return _outer_outline(c)


def _bush(c, leaves, droop):
    for x, y in sorted(leaves, key=lambda p: -p[1]):
        _leaf(c, x, y, droop)


def _rows(rows, step=3):
    """Leaves in rows: (height, half-width) -> a filled shape, rows offset so leaves interlock."""
    return [(x + (y // 3) % 2, y) for y, half in rows for x in range(-half, half + 1, step)]


# each shrub has its own silhouette: chilli a low round bush, ixora a compact dome, bunga raya a
# tall oval on short stems, bougainvillea a V that widens and spills at the top
CHILLI_BUSH = {"young": _rows(((2, 3), (5, 3), (8, 1))),
               "full": _rows(((2, 6), (5, 7), (8, 6), (11, 3)))}
IXORA_DOME = {"young": _rows(((2, 4), (5, 4), (8, 2))),
              "full": _rows(((2, 6), (5, 7), (8, 7), (11, 6), (14, 3)))}
HIBISCUS_OVAL = {"young": _rows(((4, 3), (7, 3), (10, 1))),
                 "full": _rows(((5, 4), (8, 6), (11, 7), (14, 7), (17, 5), (19, 2)))}
BOUGAIN_V = {"young": _rows(((3, 2), (6, 4), (9, 4))),
             "full": _rows(((3, 2), (6, 4), (9, 6), (12, 8), (15, 9), (18, 7), (21, 3)))}


def chilli(stage, droop=False):
    """Chilli: a small leafy bush; when full, red and green chillies hang from it."""
    c = _canvas()
    if stage == "seedling":
        _leaf(c, -1, 1, droop, small=True)
        _leaf(c, 2, 2, droop, small=True)
        return _outer_outline(c)
    _bush(c, CHILLI_BUSH[stage], droop)
    if stage == "full":
        sag = 1 if droop else 0
        for k, (x, y) in enumerate(((-5, 6), (-1, 5), (3, 7), (5, 4), (1, 11))):
            _stamp(c, x, y - sag, CHILLI, CHILLI_KEY if k % 3 != 2 else GREEN_CHILLI_KEY)
    return _outer_outline(c)


def _flowering(c, stage, droop, leaves, flower, key, spots, stems=False):
    """A shrub (a leaf layout per stage) with flowers at `spots`; stems=True shows two short woody
    stems under the leaves. Drooping: leaves hang and darken, flowers hang 1 px lower but stay."""
    if stage == "seedling":
        _leaf(c, -1, 1, droop, small=True)
        _leaf(c, 2, 2, droop, small=True)
        return
    if stems:
        low = min(y for _, y in leaves[stage])
        for dx, colour in ((-1, "wood_mid"), (1, "wood_dark")):
            for y in range(1, low):
                _put(c, BASE[0] + dx, BASE[1] - y, colour)
    _bush(c, leaves[stage], droop)
    for x, y in spots[stage]:
        _stamp(c, x, y - (1 if droop else 0), flower, key)


def bunga_raya(stage, droop=False):
    """Bunga raya (hibiscus, the national flower): a tall oval shrub with big red flowers."""
    c = _canvas()
    _flowering(c, stage, droop, HIBISCUS_OVAL, HIBISCUS, HIBISCUS_KEY,
               {"young": [(-1, 11)], "full": [(-7, 13), (3, 16), (-2, 19), (2, 9)]}, stems=True)
    return _outer_outline(c)


def bougainvillea(stage, droop=False):
    """Bougainvillea: a V-shaped shrub that widens and spills at the top, covered in magenta bracts."""
    c = _canvas()
    _flowering(c, stage, droop, BOUGAIN_V, BRACTS, BRACTS_KEY,
               {"young": [(-4, 8), (2, 10)],
                "full": [(-9, 14), (7, 13), (-4, 17), (3, 19), (-7, 19), (6, 17), (-1, 22), (0, 12)]}, stems=True)
    return _outer_outline(c)


def ixora(stage, droop=False):
    """Ixora (jejarum): a compact dome with round clusters of small red-orange flowers."""
    c = _canvas()
    _flowering(c, stage, droop, IXORA_DOME, IXORA, IXORA_KEY,
               {"young": [(-1, 9)], "full": [(-6, 9), (3, 11), (-2, 16), (5, 5), (-8, 4)]})
    return _outer_outline(c)


# ---------------------------------------------------------------- tiers 3-4 (D-86)
ORCHID = [".ppp.", "ppYpp", "pPYPp", ".P.P."]                         # a moth orchid flower, yellow lip
ORCHID_KEY = {"p": "purple_light", "P": "purple_mid", "Y": "coin_light"}
BUD = ["g", "G"]
BUD_KEY = {"g": "green_light", "G": "green_mid"}
FRANGI = [".w.", "wyw", ".w."]                                        # kemboja: white, yellow centre
FRANGI_KEY = {"w": "wall_cream", "y": "coin_light"}
TORCH = ["..p..", ".pPp.", ".PpP.", "pPPPp", ".pPp.", "..R.."]       # bunga kantan: a pink torch
TORCH_KEY = {"p": "pink_light", "P": "pink_mid", "R": "red_dark"}
JADE = [".g.", "jJj", "jJ.", ".Jj", "jJ.", ".J.", ".j."]              # a hanging claw-flower cluster
JADE_KEY = {"j": "jade_light", "J": "jade_mid", "g": "green_dark"}
BAMBOO = ("sand_light", "sand_mid", "sand_dark")


def _line_px(c, x0, y0, x1, y1, colour, width=1, shade=None):
    """A line in canvas pixels (relative to BASE), `width` px wide; the right column in `shade`."""
    n = max(abs(x1 - x0), abs(y1 - y0), 1)
    for t in range(n + 1):
        x, y = round(x0 + (x1 - x0) * t / n), round(y0 + (y1 - y0) * t / n)
        for w in range(width):
            _put(c, BASE[0] + x + w, BASE[1] - y, shade if (shade and w == width - 1 and width > 1) else colour)


def orchid(stage, droop=False):
    """Orchids (anggerik): a low rosette of broad, fleshy leaves and arching spikes of round purple
    moth-orchid flowers."""
    c = _canvas()
    rosette = {"seedling": [(-1, 1), (2, 1)], "young": [(-3, 1), (3, 1), (0, 3)],
               "full": [(-4, 1), (4, 1), (-1, 3), (2, 2)]}[stage]
    spikes = {"seedling": [], "young": [(0, 15, 3)], "full": [(-1, 22, -7), (1, 19, 7)]}[stage]
    for x0, top, lean in spikes:                                       # spikes behind the leaves
        bend = 2 if droop else 0
        pts = [(x0 + round(lean * (t / 6) ** 2), round(3 + (top - 3) * t / 6) - (bend * t // 6)) for t in range(7)]
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            _line_px(c, xa, ya, xb, yb, "green_dark")
        if stage == "young":
            _stamp(c, pts[-1][0], pts[-1][1] + 1, BUD, BUD_KEY)
            _stamp(c, pts[-2][0] + 1, pts[-2][1] + 1, BUD, BUD_KEY)
        else:                                                          # three flowers along the arch
            for xf, yf in (pts[3], pts[5], pts[6]):
                _stamp(c, xf - 2, yf + 2, ORCHID, ORCHID_KEY)
    for x, y in rosette:
        _leaf(c, x, y, droop, small=stage == "seedling")
    return _outer_outline(c)


def frangipani(stage, droop=False):
    """Frangipani (kemboja): a small tree with thick grey forked branches, fans of long leaves at the
    tips and white-and-yellow flowers. Up to ~52 px when full (spec §2)."""
    c = _canvas()
    if stage == "seedling":                                            # a rooted cutting with a few leaves
        _line_px(c, 0, 0, 0, 3, "stone_soft", 2, "stone_mid")
        for x, y in ((-2, 3), (2, 3), (0, 5)):
            _leaf(c, x, y, droop)
        return _outer_outline(c)
    scale = 0.55 if stage == "young" else 1.0
    trunk_top = round(16 * scale)
    _line_px(c, 0, 0, 0, trunk_top, "stone_soft", 3, "stone_mid")
    tips = [(-14, 34), (-6, 42), (5, 44), (14, 36)] if stage == "full" else [(-6, 20), (5, 22)]
    for tx, ty in tips:                                                # forked branches
        mx, my = round(tx * 0.45), round(trunk_top + (ty - trunk_top) * 0.45)
        _line_px(c, 0, trunk_top, mx, my, "stone_soft", 2, "stone_mid")
        _line_px(c, mx, my, tx, ty - 3, "stone_soft", 2, "stone_mid")
    for tx, ty in tips:                                                # leaf fans at the tips
        for dx, dy in ((-4, 0), (4, 0), (-2, 3), (2, 3), (0, 5), (-5, -3), (5, -3)):
            _leaf(c, tx + dx, ty + dy - 2, droop)
    for k, (tx, ty) in enumerate(tips):                                # flower clusters
        if stage == "young" and k:
            continue
        for dx, dy in ((0, 6), (-3, 4), (3, 5)) if stage == "full" else ((0, 5),):
            _stamp(c, tx + dx - 1, ty + dy + 1 - (1 if droop else 0), FRANGI, FRANGI_KEY)
    return _outer_outline(c)


def torch_ginger(stage, droop=False):
    """Torch ginger (bunga kantan): tall leafy stems and, when full, a pink torch flower on its own
    short stalk. Up to ~54 px when full (spec §2)."""
    c = _canvas()
    # stems as (base x, lean at the top, height): they fan out a little, the middle one tallest
    stems = {"seedling": [(0, 1, 7)], "young": [(-1, -2, 21), (1, 2, 25)],
             "full": [(-2, -5, 44), (0, 0, 52), (2, 5, 47)]}[stage]
    longest = {"seedling": 3, "young": 7, "full": 11}[stage]
    step = {"seedling": 3, "young": 5, "full": 6}[stage]

    def stem_x(x0, lean, h, y):
        return x0 + lean * (y / h) ** 1.5

    leaves = []
    for k, (x0, lean, h) in enumerate(stems):
        side = -1 if lean < 0 else 1                                   # the first leaf points outwards
        for j, y in enumerate(range(step, h - 3, step)):
            s = side if j % 2 == 0 else -side                          # alternately each side, up the stem
            inner = (lean != 0) and (s != np.sign(lean))
            length = longest * (0.55 + 0.45 * np.sin(np.pi * y / h)) * (0.6 if inner else 1.0)
            leaves.append((stem_x(x0, lean, h, y), y, s, length))
    for x0, lean, h in stems:                                          # the leafy stems (pseudo-stems)
        for y in range(h + 1):
            x = round(stem_x(x0, lean, h, y))
            _put(c, BASE[0] + x, BASE[1] - y, "green_mid")
            _put(c, BASE[0] + x + 1, BASE[1] - y, "green_dark")
        tx = round(stem_x(x0, lean, h, h))                             # a new leaf still rolled up at the top
        for d in (1, 2, 3):
            _put(c, BASE[0] + tx, BASE[1] - h - d, "green_light")
    widest = {"seedling": 1.5, "young": 2.5, "full": 3.5}[stage]
    for x, y, s, length in sorted(leaves, key=lambda leaf: -leaf[1]):  # higher leaves behind the lower ones
        droop_by = 3 if droop else 0
        steps = max(int(length * 3), 6)
        for t in range(steps + 1):                                     # a broad lance: up and out, the tip
            u = t / steps                                              # arching over, widest in the middle
            lx = x + (1 if s > 0 else 0) + s * length * u
            ly = y + length * 0.75 * u - (length * 0.6 + droop_by) * u ** 3
            half = widest * np.sin(np.pi * u) ** 0.8 / 2
            for r in range(int(np.floor(ly - half)), int(np.ceil(ly + half)) + 1):
                colour = "green_light" if r > ly + 0.3 else "green_dark" if r < ly - half + 0.6 else "green_mid"
                _put(c, BASE[0] + round(lx), BASE[1] - r, colour)
    if stage == "full":
        _line_px(c, -10, 0, -10, 12, "green_dark")                     # the flower's own short stalk
        _stamp(c, -12, 18 - (1 if droop else 0), TORCH, TORCH_KEY)
    return _outer_outline(c)


def jade_vine(stage, droop=False):
    """Jade vine: a climber on its own small trellis in the bed cell (the garden arch is a separate
    decoration), with hanging clusters of jade-turquoise claw flowers when full. ~32 px."""
    from .geometry import Box
    from .pieces import boxes, solid, tone
    bamboo = tone(*BAMBOO)                                             # a bamboo trellis, tied at the joints
    if stage == "seedling":
        c = solid(boxes(Box(7.5, 8.5, 7.5, 8.5, 0, 9, **bamboo)), line=None)          # a little bamboo stake
        _leaf(c, -2, 2, droop, small=True)
        _leaf(c, 2, 4, droop, small=True)
        return _outer_outline(c)
    c = solid(boxes(*[Box(7.5, 8.5, b, b + 1, 0, 26, **bamboo) for b in (3.5, 11.5)],      # centred on the cell
                    *[Box(7.6, 8.4, 4.5, 11.5, h, h + 1, **bamboo) for h in (9, 17, 24.5)]), line=None)
    # the vine (x, height above the base, in px): up the front post, along the middle bar to the back
    # post; when full, also up the back post and along the top bar (the bars rise towards the back)
    vines = [[(-6, 0), (-7, 7), (-6, 14), (0, 17), (6, 20)]]
    if stage == "full":
        vines += [[(8, 5), (9, 14), (8, 23), (1, 25), (-6, 22)], [(6, 20), (7, 26), (3, 29)]]
    k = 0
    for poly in vines:
        s = 0.0
        for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
            seg = float(np.hypot(x1 - x0, y1 - y0))
            nx, ny = -(y1 - y0) / seg, (x1 - x0) / seg
            for i in range(int(seg * 2)):
                t = i / (seg * 2)
                wob = np.sin((s + t * seg) * 0.9)                      # it twines
                x, y = x0 + (x1 - x0) * t + nx * wob, y0 + (y1 - y0) * t + ny * wob
                _put(c, BASE[0] + round(x), BASE[1] - round(y), "green_dark")
            s += seg
        for x, y in poly[1:]:                                          # leaves along it, alternately each side
            _leaf(c, round(x) + (2 if k % 2 else -2), round(y) - 1, droop)
            k += 1
        for (x0, y0), (x1, y1) in zip(poly, poly[1:]):                 # and between the bends
            _leaf(c, round((x0 + x1) / 2) + (2 if k % 2 else -2), round((y0 + y1) / 2) - 1, droop)
            k += 1
    if stage == "full":
        for x, y in ((-5, 21), (-1, 23), (3, 25), (7, 26)):            # claw flowers hang from the top bar
            _stamp(c, x, y - (1 if droop else 0), JADE, JADE_KEY)
    return _outer_outline(c)


def free_seedling(droop=False):
    """The free seedling that sprouts in an empty bed cell (D-69); a choice replaces it."""
    c = _canvas()
    _leaf(c, -1, 0, droop, small=True)
    _leaf(c, 1, 1, droop, small=True)
    return _outer_outline(c)


DRAW = {"serai": serai, "pandan": pandan, "chilli": chilli, "bunga_raya": bunga_raya,
        "bougainvillea": bougainvillea, "ixora": ixora, "orchid": orchid, "frangipani": frangipani,
        "torch_ginger": torch_ginger, "jade_vine": jade_vine}
TIER = {"serai": 1, "pandan": 1, "chilli": 1, "bunga_raya": 2, "bougainvillea": 2, "ixora": 2,
        "orchid": 3, "frangipani": 3, "torch_ginger": 4, "jade_vine": 4}          # = shared/game.json
TIER_3_4 = ("orchid", "frangipani", "torch_ginger", "jade_vine")
PLANT_PIECES = [Piece(f"plant_{name}_{stage}{'_droop' if d else ''}", "garden/plants", "struct",
                      (lambda name=name, stage=stage, d=d: DRAW[name](stage, d)),
                      f"bed plant, tier {TIER[name]}, {stage}{'; really bad month (droops, D-73)' if d else ''}")
                for name in TIER_1_2 for stage in STAGES for d in (False, True)]
PLANT_PIECES += [Piece(f"plant_free_seedling{'_droop' if d else ''}", "garden/plants", "struct",
                       (lambda d=d: free_seedling(d)), "free seedling in an empty bed cell (D-69)"
                       + ("; droops" if d else ""))
                 for d in (False, True)]
# tiers 3-4 come after the free seedling so the earlier pieces keep their order in the manifest
PLANT_PIECES += [Piece(f"plant_{name}_{stage}{'_droop' if d else ''}", "garden/plants", "struct",
                       (lambda name=name, stage=stage, d=d: DRAW[name](stage, d)),
                       f"bed plant, tier {TIER[name]}, {stage}{'; really bad month (droops, D-73)' if d else ''}")
                 for name in TIER_3_4 for stage in STAGES for d in (False, True)]
