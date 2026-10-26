"""The garden tree (T-22 batch 2; spec §2 and §5, D-74, D-86): 7 stages, bought with a choice at G4,
growing one stage per ~14 growing days (shared/game.json "growth").

A pink trumpet tree (tecoma, Tabebuia rosea, the "Malaysian sakura" of town gardens and roadsides):
mound, sprout, sapling, young, medium, mature, and flowering mature, from a 4 px mound to ~100 px
(compressed from real size, as isometric games do, spec §2). Every stage is drawn on the same 2 x 2
canvas, standing on the centre of its 2 x 2 spot (scenes.TREE_SPOT), so the tree never moves as it grows.
Each stage has a droop version for really bad months (D-73): the canopy sags and darkens, the
blossoms stay; never bare, never smaller.

The canopy is a cluster of round clumps, each shaded from the upper left (light, mid, dark) with a
leafy speckle, drawn back to front and outlined once, the usual way trees are drawn in pixel art.
"""
from __future__ import annotations

import numpy as np

from .geometry import struct_canvas
from .palette import IDX, TRANSPARENT
from .pieces import Piece, hash01

C = IDX
OL = C["outline_soft"]
CELLS = (2, 2)
W, H, (OX, OY) = struct_canvas(CELLS)
BASE = (OX + 32 + 2 * 16 - 2 * 16, OY + 16 + 16)          # the centre of the 2 x 2 spot on the ground
STAGES = ("mound", "sprout", "sapling", "young", "medium", "mature", "flowering")
YS, XS = np.mgrid[0:H, 0:W] + 0.5
LEAVES = ("green_light", "green_mid", "green_dark")
DROOP_LEAVES = ("green_mid", "green_dark", "green_dark")

# per stage: trunk height, trunk half-width, canopy clumps as (dx, height of the centre, radius)
CANOPY = {
    "young": (16, 1, [(0, 26, 8), (-6, 22, 6), (6, 23, 6), (0, 33, 6)]),
    "medium": (22, 1.5, [(0, 38, 12), (-11, 32, 9), (11, 33, 9), (-6, 47, 9), (7, 46, 9), (0, 28, 9)]),
    "mature": (34, 2, [(0, 64, 15), (-17, 56, 12), (17, 57, 12), (-9, 76, 12), (10, 75, 12), (-24, 48, 9),
                       (24, 49, 9), (0, 50, 13), (-12, 46, 10), (13, 47, 10), (0, 84, 9)]),
}
CANOPY["flowering"] = CANOPY["mature"]


def _canvas():
    return np.full((H, W), TRANSPARENT, np.int16)


def _put(c, x, y, colour):
    if 0 <= y < H and 0 <= x < W:
        c[y, x] = C[colour]


def _mound(c):
    """A small planted mound of soil, 4 px high."""
    bx, by = BASE
    m = (((XS - bx) / 7) ** 2 + ((YS - by + 1.5) / 3.2) ** 2 <= 1) & (YS < by + 1)
    c[m] = C["soil_mid"]
    c[m & (XS - bx + (YS - by) * 2 < -3)] = C["soil_light"]
    c[m & (XS - bx + (YS - by) * 2 > 4)] = C["soil_dark"]


def _trunk(c, height, half, droop):
    """A tapering trunk with two branches up into the canopy; lit on the left."""
    bx, by = BASE
    for y in range(height + 1):
        w = half * (1.0 - 0.4 * y / max(height, 1))
        for x in range(round(bx - w - 0.5), round(bx + w + 0.5)):
            _put(c, x, by - 1 - y, "wood_mid" if x < bx else "wood_dark")
    for side in (-1, 1):                                               # branches
        x, y = bx, by - height
        for k in range(round(height * 0.5)):
            x += side * 0.9
            y -= 1
            _put(c, round(x), round(y), "wood_mid" if side < 0 else "wood_dark")
            _put(c, round(x) + 1, round(y), "wood_dark")


def _canopy(c, clumps, droop, blossoms=False, seed=0):
    """Round clumps, back (high) ones first; each shaded light at the upper left, dark at the lower
    right, with a leafy speckle. Droop: darker, and every clump sags lower and flatter."""
    bx, by = BASE
    lit, mid, dark = DROOP_LEAVES if droop else LEAVES
    sil = np.zeros(c.shape, bool)
    for k, (dx, h, r) in enumerate(sorted(clumps, key=lambda q: -q[1])):
        sag = (2 + r * 0.25) if droop else 0
        cx, cy = bx + dx * 2, by - h + sag
        rx, ry = r * 1.25, r * (0.85 if droop else 1.0)
        d = np.hypot((XS - cx) / rx, (YS - cy) / ry)
        m = d <= 1
        u = (XS - cx) / rx + (YS - cy) / ry                             # towards the lower right
        speck = hash01(np.floor(XS / 2), np.floor(YS / 2), seed + k) < 0.3
        c[m] = C[mid]
        c[m & (u < -0.45)] = C[lit]
        c[m & (u < -0.45) & speck] = C[mid]
        c[m & (u > 0.55)] = C[dark]
        c[m & (u > -0.2) & (u <= 0.55) & speck] = C[dark]
        c[m & (d > 0.86) & (u > 0.2)] = C[dark]                          # rim where it meets the clump behind
        sil |= m
    if blossoms:                                                        # pink trumpet flowers all over
        rng = np.random.default_rng(seed + 11)
        pts = np.argwhere(sil)
        for y, x in pts[rng.random(len(pts)) < 0.08]:
            _put(c, x, y, "pink_light")
            _put(c, x + 1, y, "pink_mid")
            _put(c, x, y + 1, "pink_mid")
    return sil


def _outline(c):
    """The soft garden outline just outside the tree, as for the bed plants (a thin stem or stake
    stays visible); never along the ground under it."""
    sil = c >= 0
    pad = np.pad(sil, 1)
    up, down, left, right = pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]
    ring = ~sil & (up | down | left | right)
    under = ~sil & up & ~down & ~left & ~right
    ring &= ~(under & (YS >= BASE[1] - 1))
    c[ring] = OL


def tree(stage: str, droop: bool = False) -> np.ndarray:
    c = _canvas()
    bx, by = BASE
    _mound(c)
    if stage == "mound":
        _outline(c)
        return c
    if stage in ("sprout", "sapling"):
        if stage == "sapling":                                          # a slim stem tied to a stake
            for y in range(1, 22):
                _put(c, bx + 3, by - y, "wood_light")
            for y in range(1, 17):
                _put(c, bx, by - y, "wood_mid")
            for y in (8, 14):
                _put(c, bx + 1, by - y, "sand_light")
                _put(c, bx + 2, by - y, "sand_light")
            leaves = [(-3, 9), (3, 11), (-3, 14), (2, 16), (0, 19)]
        else:
            for y in range(1, 5):
                _put(c, bx, by - y, "green_mid")
            leaves = [(-2, 5), (2, 6)]
        lit, mid, dark = DROOP_LEAVES if droop else LEAVES
        for x, y in leaves:                                             # small oval leaves
            y -= 1 if droop else 0
            for i in range(-1, 2):
                _put(c, bx + x + i, by - y, mid)
            _put(c, bx + x - 1, by - y - 1, lit)
            _put(c, bx + x, by - y - 1, lit)
            _put(c, bx + x + 1, by - y + 1, dark)
        _outline(c)
        return c
    height, half, clumps = CANOPY[stage]
    _trunk(c, height, half, droop)
    _canopy(c, clumps, droop, blossoms=stage == "flowering", seed=STAGES.index(stage))
    _outline(c)
    if stage == "flowering":                                            # a few fallen petals round the base
        for dx, dy in ((-14, 2), (-9, 4), (10, 3), (15, 1), (4, 5), (-3, 6), (20, 4), (-19, 3)):
            _put(c, bx + dx, by + dy - 3, "pink_light")
    return c


TREE_PIECES = [Piece(f"tree_{k}_{s}{'_droop' if d else ''}", "garden/tree", "struct",
                     (lambda s=s, d=d: tree(s, d)),
                     f"the garden tree, stage {k + 1} of 7 ({s}); 2 x 2 spot"
                     f"{'; really bad month (droops, D-73)' if d else ''}", CELLS)
               for k, s in enumerate(STAGES) for d in (False, True)]
