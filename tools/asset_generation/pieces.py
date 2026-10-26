"""The 41 batch-1 pieces (docs/assets/FAST_CODE_ASSET_SPEC.md; D-53, D-57, D-58).

Ground tiles are textures on the diamond; textures depend only on (a, b) in [0, 16) or on the
pixel position inside the tile, so a tile repeats once per cell and neighbours join seamlessly.
Structures are boxes (geometry.Box) lit by the style-guide rule:
top lightest, left-facing (down-left) lighter, right-facing (down-right) darker.

Naming: spec names are kept; pieces the spec lists once but that an isometric room needs on
both back walls get a _left / _right suffix (left = the cell's top-left edge, D-53 C2).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

import numpy as np

from .geometry import (CELL_H, CELL_W, STRUCT_H, STRUCT_ORIGIN, STRUCT_W, Box, Face, box_faces, diamond_mask,
                       draw_box, draw_faces, ground_ab, outline, pixel_grid, struct_canvas)
from .palette import IDX, TRANSPARENT

C = IDX   # short alias: C["wood_light"] -> palette index


def hash01(ix, iy, seed: int):
    """Deterministic per-integer-coordinate noise in [0, 1)."""
    ix = np.asarray(ix, np.int64)
    iy = np.asarray(iy, np.int64)
    h = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / 16777216.0


# ---------------------------------------------------------------- ground tiles
def tile(texture: Callable) -> np.ndarray:
    X, Y = pixel_grid(CELL_W, CELL_H, (0, 0))
    a, b = ground_ab(X, Y, 0)
    ys, xs = np.mgrid[0:CELL_H, 0:CELL_W]
    out = np.full((CELL_H, CELL_W), TRANSPARENT, np.int16)
    m = diamond_mask()
    out[m] = texture(a[m], b[m], xs[m], ys[m])
    return out


def wood(base, alt, seam, grain, seed, worn=False):
    def tex(a, b, x, y):
        plank = np.floor(b / 4).astype(int)                       # 4 boards per cell, running along a
        col = np.where(hash01(plank, 1, seed) < 0.5, C[base], C[alt])
        n = hash01(x, y, seed + 1)
        col = np.where(n < 0.07, C[grain], col)                   # grain flecks
        if worn:
            centre = (np.abs(a - 8) < 5) & (np.abs(b - 8) < 5)
            col = np.where(centre & (n > 0.86), C["wood_high"], col)    # scuffed, lighter centre
            col = np.where(hash01(x, y, seed + 2) < 0.015, C["wood_mid"], col)   # nicks
        joint = ((a - (plank * 7 + 3) % 16) % 16) < 0.5           # staggered board ends
        return np.where(((b % 4) < 0.5) | joint, C[seam], col)
    return tex


def kitchen_tile(a, b, x, y):
    checker = ((np.floor(a / 8) + np.floor(b / 8)) % 2) == 1      # 2 x 2 ceramic tiles per cell
    col = np.where(checker, C["tile_shade"], C["tile_light"])
    n = hash01(x, y, 41)
    col = np.where(n < 0.04, np.where(checker, C["tile_light"], C["tile_shade"]), col)
    return np.where(((a % 8) < 0.5) | ((b % 8) < 0.5), C["grout"], col)


def soil_bare(a, b, x, y):
    n, p = hash01(x, y, 11), hash01(x, y, 12)
    col = np.where(n < 0.15, C["soil_light"], np.where(n < 0.30, C["soil_dark"], C["soil_mid"]))
    return np.where(p < 0.025, C["stone_light"], col)                # pebbles


def soil_improved(a, b, x, y):
    n, p = hash01(x, y, 13), hash01(x, y, 14)
    col = np.where(n < 0.25, C["soil_mid"], C["soil_dark"])
    return np.where(p < 0.04, C["green_mid"], np.where(p < 0.05, C["green_light"], col))   # sprouts


def grass_healthy(a, b, x, y):
    n = hash01(x, y, 15)
    return np.select([n < 0.22, n < 0.30, n < 0.33], [C["green_mid"], C["green_light"], C["green_dark"]],
                     C["green_grass"])


# Ground that covers large areas uses pixel-scale noise only: any feature bigger than a pixel
# repeats every 64 x 32 tile and shows as a lattice across a full screen (D-58). The levels
# differ by colour: wild is dull olive with straw, basic shows soil, healthy is bright, lush is
# the richest. "Blades" are 1 x 2 px (hash of x and y // 2): taller grass than a mown lawn.
def grass_basic(a, b, x, y):
    n = hash01(x, y, 17)
    return np.select([n < 0.13, n < 0.20, n < 0.30, n < 0.40], [C["soil_mid"], C["soil_light"], C["green_mid"],
                     C["green_light"]], C["green_grass"])               # new lawn, soil showing through


def grass_lush_tex():
    def tex(a, b, x, y):
        n = hash01(x, np.floor(y / 2), 18)
        return np.select([n < 0.10, n < 0.26, n < 0.70], [C["green_dark"], C["green_mid"], C["green_grass"]],
                         C["green_light"])                              # dense, with light tips
    return tex


def grass_wild(a, b, x, y):
    """Untended ground outside the tended garden (D-58): dull olive with straw-coloured blades.
    Rougher than any lawn and calmer than bare soil, so tending the garden reads as progress."""
    n = hash01(x, np.floor(y / 2), 31)
    return np.select([n < 0.24, n < 0.78, n < 0.84, n < 0.93], [C["green_dark"], C["green_mid"], C["green_grass"],
                     C["sand_mid"]], C["sand_dark"])


def trodden_earth(a, b, x, y):
    n = hash01(x, y, 33)
    return np.where(n < 0.20, C["soil_light"], np.where(n < 0.26, C["soil_dark"], C["soil_mid"]))


def stepping_stone(a, b, x, y):
    col = trodden_earth(a, b, x, y)              # on earth, so it suits bare soil (G1) and basic grass (G2)
    for ca, cb, r in ((4.5, 4.5, 2.6), (8.0, 10.5, 2.4), (12.0, 5.0, 2.2)):   # stones kept inside the cell
        d = np.hypot(a - ca, b - cb)
        stone = d < r
        rim = stone & (d > r - 0.9) & ((a - ca) + (b - cb) > 0)               # front rim reads as thickness
        speck = stone & (hash01(x, y, 19) < 0.12)
        col = np.where(stone, C["stone_light"], col)
        col = np.where(speck, C["stone_soft"], col)
        col = np.where(rim, C["stone_mid"], col)
    return col


def paved(a, b, x, y):
    tone = hash01(np.floor(a / 4), np.floor(b / 4), 20) < 0.4            # 4 x 4 pavers per cell
    col = np.where(tone, C["stone_soft"], C["stone_light"])
    col = np.where(hash01(x, y, 21) < 0.04, C["stone_mid"], col)
    return np.where(((a % 4) < 0.5) | ((b % 4) < 0.5), C["stone_mid"], col)


def nice_paved(a, b, x, y):
    row = np.floor(b / 2)
    shift = np.where(row % 2 == 1, 2, 0)                                  # running bond
    brick = np.floor((a + shift) / 4)
    col = np.where(hash01(brick, row, 22) < 0.45, C["sand_mid"], C["sand_light"])
    joint = ((b % 2) < 0.5) | (((a + shift) % 4) < 0.5)
    return np.where(joint, C["sand_dark"], col)


# ---------------------------------------------------------------- structures
def struct(boxes: list[Box], line: int | None = C["outline"], mode: str = "full",
           context: list[Box] = ()) -> np.ndarray:
    canvas = np.full((STRUCT_H, STRUCT_W), TRANSPARENT, np.int16)
    X, Y = pixel_grid(STRUCT_W, STRUCT_H, STRUCT_ORIGIN)
    for bx in boxes:
        draw_box(canvas, X, Y, bx)
    ctx = None
    if context:
        scratch = np.full_like(canvas, TRANSPARENT)
        for bx in context:
            draw_box(scratch, X, Y, replace(bx, top=0, left=0, right=0))
        ctx = scratch >= 0
    if line is not None:
        outline(canvas, line, mode, ctx)
    return canvas


def _previous(bx: Box) -> Box:
    """The same box one cell back along its run (towards the room corner / run start)."""
    if (bx.b1 - bx.b0) > (bx.a1 - bx.a0):
        return replace(bx, b0=bx.b0 - 16, b1=bx.b1 - 16)
    return replace(bx, a0=bx.a0 - 16, a1=bx.a1 - 16)


def run(boxes: list[Box], line: int = C["outline"], joined: bool = True,
        context: list[Box] | None = None) -> np.ndarray:
    """Pieces that join neighbours in a continuous run (walls, borders): top outline only.
    The back end of a cap lies on the piece's upper outline. In a run the previous piece
    continues the cap there and this piece is drawn over it, so outlining that end would leave a
    tick mid-cap at every join: the outline is computed as if the previous piece were present.
    joined=False for corner pieces, whose back ends meet each other, not a previous piece.
    context: the previous piece's boxes, when they are not simply these boxes one cell back."""
    if context is None:
        context = [_previous(b) for b in boxes] if joined else []
    return struct(boxes, line, mode="top", context=context)


def face(colour: str, base: str | None = None, base_top: str | None = None, feature=None):
    """A wall face: plain colour, optional baseboard (h < 5), optional feature (door/window)."""
    def fn(u, h):
        out = np.full(u.shape, C[colour], np.int16)
        if base:
            out[h < 4] = C[base]
            out[(h >= 4) & (h < 5)] = C[base_top]
        return feature(u, h, out) if feature else out
    return fn


DOOR_H = 80                     # 2.05 m at 39 px/m (D-60; was 64 = 1.64 m)
WIN_LO, WIN_HI = 48, 80         # window 1.23-2.05 m: its top lines up with the door top


def door(closed: bool, leaf: str, frame: str):
    def f(u, h, out):
        inside = (u >= 4) & (u < 12) & (h < DOOR_H)                       # 16 px wide
        fr = inside & ((u < 4.5) | (u >= 11.5) | (h >= DOOR_H - 1))
        inner = inside & ~fr
        out[fr] = C[frame]
        if closed:
            out[inner] = C[leaf]
            rails = inner & (((h >= 8) & (h < 9)) | ((h >= 42) & (h < 43)) | ((h >= 72) & (h < 73))) \
                & (u >= 5.5) & (u < 10.5)
            stiles = inner & (h >= 8) & (h < 73) & (((u >= 5.5) & (u < 6)) | ((u >= 10) & (u < 10.5)))
            out[rails | stiles] = C["wood_dark"]
            out[inner & (u >= 9.5) & (u < 10) & (h >= 37) & (h < 40)] = C["brass"]   # handle at ~1 m
        else:
            out[inner] = C["recess"]
            out[inner & (u < 5.5)] = C["wood_dark"]                       # visible inner jamb
        return out
    return f


def window(frame: str, sill: str):
    def f(u, h, out):
        win = (u >= 2) & (u < 14) & (h >= WIN_LO) & (h < WIN_HI)          # 24 px wide, 32 px tall
        mid = (WIN_LO + WIN_HI) // 2 - 1
        fr = win & ((u < 2.5) | (u >= 13.5) | (h < WIN_LO + 1) | (h >= WIN_HI - 1) | ((u >= 7.75) & (u < 8.25))
                    | ((h >= mid) & (h < mid + 1)))
        glass = win & ~fr
        out[glass] = C["glass"]
        out[glass & ((((u * 2) + (h - WIN_LO) * 0.75) % 7) < 1.2)] = C["glass_light"]
        out[fr] = C[frame]
        out[(u >= 1.5) & (u < 14.5) & (h >= WIN_LO - 2) & (h < WIN_LO)] = C[sill]
        return out
    return f


T = 2          # wall thickness in a/b units = 4 px wall cap (D-53 C3)
H_WALL = 96
H_STUB = 12    # front walls are cut away to a low stub so the room stays visible (D-58)


def wall_left_box(h=H_WALL, feature=None, b0=0):
    """Wall on the cell's top-left edge (a = 0); its room face points down-right (shaded)."""
    return Box(-T, 0, b0, 16, 0, h, top=C["wall_cream"], left=C["wall_beige"],
               right=face("wall_shadow", "wood_mid", "wood_warm", feature))


def wall_right_box(h=H_WALL, feature=None):
    """Wall on the cell's top-right edge (b = 0); its room face points down-left (lit)."""
    return Box(0, 16, -T, 0, 0, h, top=C["wall_cream"], right=C["wall_shadow"],
               left=face("wall_beige", "wood_warm", "wood_light", feature))


def stub_front_left_box(a0=0.0, a1=16.0):
    """Cut-away wall on the cell's bottom-left edge (b = 16), inside the cell; outer face points
    down-left (lit), with a stone plinth like the outside corner."""
    return Box(a0, a1, 16 - T, 16, 0, H_STUB, top=C["wall_cream"],
               left=face("wall_beige", "stone_mid", "stone_soft"), right=C["wall_shadow"])


def stub_front_right_box(b0=0.0, b1=16.0):
    """Cut-away wall on the cell's bottom-right edge (a = 16); outer face points down-right (shaded)."""
    return Box(16 - T, 16, b0, b1, 0, H_STUB, top=C["wall_cream"], left=C["wall_beige"],
               right=face("wall_shadow", "stone_dark", "stone_mid"))


def step(a0, a1, b0, b1):
    return Box(a0, a1, b0, b1, 0, 2, top=C["stone_light"], left=C["stone_soft"], right=C["stone_mid"])


def stone_side(colour):
    def fn(u, h):
        out = np.full(u.shape, C[colour], np.int16)
        out[(u % 4) < 0.5] = C["stone_dark"]                              # block joints
        return out
    return fn


def border(a0, a1, b0, b1):
    return Box(a0, a1, b0, b1, 0, 6, top=C["stone_light"], left=stone_side("stone_soft"),
               right=stone_side("stone_mid"))


# Borders and fences sit centred ON the cell edge (D-58): neighbouring pieces then share the
# corner (borders overlap by half a unit, fences share the post), so runs show no double posts
# and a bed's rectangle closes at every corner without special pieces.
E = 0.5        # half a border's width


def border_left():      # on the top-left edge (a = 0)
    return border(-E, E, -E, 16 + E)


def border_right():     # on the top-right edge (b = 0)
    return border(-E, 16 + E, -E, E)


def planter(soil: bool):
    def top(a, b):
        rim = (a < 3) | (a >= 13) | (b < 3) | (b >= 13)
        if soil:
            n = hash01(np.floor(a * 2), np.floor(b * 2), 23)
            inner = np.select([n < 0.2, n < 0.35], [C["soil_light"], C["soil_mid"]], C["soil_dark"])
        else:
            back = (a < 4.5) | (b < 4.5)                                   # inner back walls in shadow
            inner = np.where(back, C["recess"], C["wood_dark"])
        return np.where(rim, C["wood_light"], inner)

    def side(colour):
        def fn(u, h):
            out = np.full(u.shape, C[colour], np.int16)
            out[(h % 5) < 1] = C["wood_dark"]                              # board lines
            return out
        return fn
    return Box(2, 14, 2, 14, 0, 14, top=top, left=side("wood_warm"), right=side("wood_mid"))


WOOD = dict(top=C["wood_light"], left=C["wood_warm"], right=C["wood_mid"])
H_FENCE = 28


P = 0.75       # half a post


def post(a, b, h=H_FENCE):
    """A post centred on (a, b). Posts at cell corners are shared: the end post of one piece is
    exactly the start post of the next, so a run never shows two posts side by side."""
    return Box(a - P, a + P, b - P, b + P, 0, h, **WOOD)


def rails_left():   # on the top-left edge (a = 0), between the corner posts
    return [Box(-0.25, 0.25, P, 16 - P, h0, h0 + 3, **WOOD) for h0 in (8, 19)]


def rails_right():  # on the top-right edge (b = 0)
    return [Box(P, 16 - P, -0.25, 0.25, h0, h0 + 3, **WOOD) for h0 in (8, 19)]


def gate_face(u, h):
    u0, u1 = P + 1, 16 - P - 1                                           # inner edges of the frame
    frame = (h < 6) | (h >= 22) | (u < u0) | (u >= u1)
    brace = np.abs((h - 6) - (u - u0) * 16 / (u1 - u0)) < 1.3
    slat = (u % 2) < 0.5
    return np.where(frame | brace | slat, C["wood_mid"], TRANSPARENT).astype(np.int16)


def gate_face_lit(u, h):
    out = gate_face(u, h)
    return np.where(out >= 0, C["wood_warm"], out).astype(np.int16)


# ---------------------------------------------------------------- neighbourhood (D-59)
# Neighbours' houses and props are fixed scenery: they never change with anyone's progress.
# Drawn with depth-buffered faces (geometry.Face), which handles sloped roofs and wheels.
def solid(faces: list[Face], cells=(1, 1), line: int | None = C["outline"]) -> np.ndarray:
    w, h, origin = struct_canvas(cells)
    canvas = np.full((h, w), TRANSPARENT, np.int16)
    X, Y = pixel_grid(w, h, origin)
    draw_faces(canvas, X, Y, faces)
    if line is not None:
        outline(canvas, line, "full")
    return canvas


def shifted(feature, u0):
    """Place a one-cell wall feature (door/window, u in [0, 16)) at u0 along a longer face."""
    return lambda u, h, out: feature(u - u0, h, out)


def features(*fs):
    def f(u, h, out):
        for g in fs:
            out = g(u, h, out)
        return out
    return f


def roof_tiles(base, line):
    """Clay tiles: a course every 5 units down the slope, staggered joints every 4 along it."""
    def fn(u, v):
        course = np.floor(v / 5)
        joint = (((u + np.where(course % 2 == 1, 2, 0)) % 4) < 0.5) & ((v % 5) > 1.5)
        return np.where(((v % 5) < 1.0) | joint, C[line], C[base])
    return fn


H_HOUSE, RISE, EAVE = 96, 34, 3


def house(W, D, ridge, roof, door_on, door_cell, win_left, win_right, walls=("wall_beige", "wall_shadow")):
    """A neighbour's single-storey terrace house: W x D cells, 96 px walls (same as the room), a
    gable roof with its ridge along `ridge` ('a' or 'b'). roof = (lit, shaded, line) colour names;
    walls = (lit, shaded) paint. Doors and windows reuse the room's wall features, one per cell
    index along each front face."""
    paint_lit, paint_shaded = walls
    A, B, H, R, ov = 16 * W, 16 * D, H_HOUSE, RISE, EAVE

    def wall(colour, base, base_top, door_here, wins, leaf, frame, w_frame, w_sill):
        fs = [shifted(window(w_frame, w_sill), 16 * k) for k in wins]
        if door_here is not None:
            fs.append(shifted(door(True, leaf, frame), 16 * door_here))
        return face(colour, base, base_top, features(*fs))

    left = wall(paint_lit, "stone_mid", "stone_soft", door_cell if door_on == "left" else None, win_left,
                "wood_warm", "wood_light", "wood_light", "wood_warm")
    right = wall(paint_shaded, "stone_dark", "stone_mid", door_cell if door_on == "right" else None, win_right,
                 "wood_mid", "wood_warm", "wood_warm", "wood_mid")
    faces = [Face((0, B, 0), (A, 0, 0), (0, 0, H), left),            # front-left wall, faces +b (lit)
             Face((A, 0, 0), (0, B, 0), (0, 0, H), right)]           # front-right wall, faces +a (shaded)
    lit, shaded, line = roof
    if ridge == "a":
        m = B / 2
        drop = R + ov * R / m
        top = (-ov, m, H + R)
        along = (A + 2 * ov, 0, 0)
        faces += [Face(top, along, (0, m + ov, -drop), roof_tiles(lit, line), bias=2e-6),        # faces +b
                  Face(top, along, (0, -(m + ov), -drop), roof_tiles(shaded, line), bias=2e-6),  # faces -b
                  Face((A, 0, H), (0, B, 0), (0, m, R), C[paint_shaded], tri=True),           # gable end
                  Face((-ov, B + ov, H - ov * R / m - 2), along, (0, 0, 2), C[line], bias=3e-6),   # eave edge
                  Face((A + ov, m, H + R - 2), (0, m + ov, -drop), (0, 0, 2), C[line], bias=3e-6),  # verge
                  Face((A + ov, m, H + R - 2), (0, -(m + ov), -drop), (0, 0, 2), C[line], bias=3e-6)]
    else:
        m = A / 2
        drop = R + ov * R / m
        top = (m, -ov, H + R)
        along = (0, B + 2 * ov, 0)
        faces += [Face(top, along, (m + ov, 0, -drop), roof_tiles(shaded, line), bias=2e-6),     # faces +a
                  Face(top, along, (-(m + ov), 0, -drop), roof_tiles(lit, line), bias=2e-6),     # faces -a
                  Face((0, B, H), (A, 0, 0), (m, 0, R), C[paint_lit], tri=True),
                  Face((A + ov, -ov, H - ov * R / m - 2), along, (0, 0, 2), C[line], bias=3e-6),
                  Face((m, B + ov, H + R - 2), (m + ov, 0, -drop), (0, 0, 2), C[line], bias=3e-6),
                  Face((m, B + ov, H + R - 2), (-(m + ov), 0, -drop), (0, 0, 2), C[line], bias=3e-6)]
    return solid(faces, (W, D))


TERRACOTTA = ("roof_light", "roof_mid", "roof_dark")
SLATE = ("stone_soft", "stone_mid", "stone_dark")


def boxes(*bxs):
    return [f for b in bxs for f in box_faces(b)]


def tone(top, lit, shaded):
    return dict(top=C[top], left=C[lit], right=C[shaded])


def ac_unit():
    """Outdoor air-con unit (very Malaysian), fan grille on the lit face."""
    def front(a, h):
        r = np.hypot(a - 8.5, h - 9)
        out = np.full(a.shape, C["stone_light"], np.int16)
        out[(r < 6.5) & ((r % 2) < 0.9)] = C["stone_mid"]
        out[r < 1.2] = C["stone_dark"]
        return out
    body = Box(3, 14, 8, 12, 1, 18, top=C["stone_light"], left=front, right=C["stone_soft"])
    feet = [Box(a, a + 1, 8.5, 11.5, 0, 1, **tone("stone_dark", "stone_dark", "stone_dark")) for a in (4, 12)]
    return solid(boxes(*feet, body), line=OL_SOFT)


# World scale: 1 cell (16 ground units) = 1 m. A ground unit is ~2.24 px on screen but a height
# unit is 1 px, so an equal world length is 2.45 height px per ground unit: 1 m of height = 39 px
# (the 96 px walls are 2.45 m). Round things must use different radii along the ground and up.
M_H = 39            # px of height per metre
M_G = 16            # ground units per metre


def washing_line():
    """Ampaian: two T-posts 1.6 m high, two lines 1.8 m long with clothes, along the b axis (1 x 2)."""
    metal = tone("stone_light", "stone_soft", "stone_mid")
    top = 1.6 * M_H
    parts = []
    for b in (2, 30):
        parts += [Box(7.5, 8.5, b - 0.5, b + 0.5, 0, top, **metal), Box(4.5, 11.5, b - 0.4, b + 0.4, top - 2, top, **metal)]
    parts += [Box(a - 0.2, a + 0.2, 2.5, 29.5, top - 1.6, top - 1, **tone("stone_dark", "stone_dark", "stone_dark"))
              for a in (5.5, 10.5)]
    for a, items in ((10.5, [(4, 10, 0.75, "accent_blue", "accent_blue_dark"), (11, 15, 0.5, "wall_cream", "wall_beige"),
                             (16, 22, 0.8, "roof_light", "roof_mid"), (23, 27, 0.55, "sand_light", "sand_mid")]),
                     (5.5, [(5, 11, 0.6, "green_light", "green_mid"), (13, 19, 0.7, "wall_cream", "wall_beige"),
                            (21, 26, 0.5, "accent_blue", "accent_blue_dark")])):
        parts += [Box(a - 0.3, a + 0.3, b0, b1, top - 1.6 - drop * M_H, top - 1.6, **tone(lit, lit, dark))
                  for b0, b1, drop, lit, dark in items]
    return solid(boxes(*parts), cells=(1, 2), line=OL_SOFT)


def wheel(a_face, bc, r_m=0.22, hub=0.4, n=16):
    """A wheel (radius r_m metres) as a 16-sided disc in the plane a = a_face, the side facing the
    viewer; radii differ along the ground and up so it is round in the world."""
    rb, rh = r_m * M_G, r_m * M_H
    out = []
    for k_r, colour, bias in ((1.0, C["outline_soft"], 0.0), (hub, C["stone_light"], 1e-6)):
        for k in range(n):
            t0, t1 = 2 * np.pi * k / n, 2 * np.pi * (k + 1) / n
            out.append(Face((a_face, bc, rh), (0, k_r * rb * np.cos(t0), k_r * rh * np.sin(t0)),
                            (0, k_r * rb * np.cos(t1), k_r * rh * np.sin(t1)), colour, tri=True, bias=bias))
    return out


def motorbike():
    """A kapcai-style scooter, 1.8 m long, 1 x 2 cells, parked along the b axis (front towards +b).
    Heights in metres x M_H: deck 0.25, seat 0.8, handlebar 1.05."""
    paint = tone("accent_blue", "accent_blue", "accent_blue_dark")
    dark = tone("outline_soft", "recess", "recess")
    metal = tone("stone_mid", "stone_mid", "stone_dark")
    h = lambda m: m * M_H                                                         # noqa: E731
    parts = boxes(Box(6, 10, 9, 21, h(0.2), h(0.28), **tone("stone_dark", "accent_blue_dark", "accent_blue_dark")),
                  Box(5.5, 10.5, 2, 13, h(0.28), h(0.72), **paint),               # rear body
                  Box(6, 10, 3, 12, h(0.72), h(0.8), **dark),                     # seat
                  Box(7.5, 8.5, 23, 26, h(0.2), h(0.75), **metal),                # front fork
                  Box(5.5, 10.5, 20, 23, h(0.2), h(0.95), **paint),               # leg shield
                  Box(3, 13, 21, 22.5, h(1.0), h(1.05), **tone("stone_dark", "stone_dark", "stone_dark")),
                  Box(7, 9, 23, 24, h(0.82), h(0.92), **tone("brass", "brass", "brass")))   # headlight
    return solid(parts + wheel(9.2, 6) + wheel(9.2, 26), cells=(1, 2), line=OL_SOFT)


def zinc(base, line):
    """Corrugated zinc: ridges running down the slope every 2 units along it."""
    def fn(u, v):
        return np.where((u % 2) < 0.6, C[line], C[base])
    return fn


def chicken_coop():
    """Reban ayam (D-67): a kampung chicken coop on short stilts, plank walls, a corrugated zinc
    gable roof and a cleated ramp down to the ground. 2 x 2 cells: the coop stands on the back row
    (b 2..12), the ramp comes down towards +gy. Heights in px at 39 px/m: stilts 0.3 m, walls
    0.8 m, ridge 1.2 m."""
    def planks(lit):
        base, line = ("wood_warm", "wood_mid") if lit else ("wood_mid", "wood_dark")

        def fn(u, h):
            out = np.where(((h - 12) % 5) < 1, C[line], C[base]).astype(np.int16)
            if lit:                                                     # door opening and frame
                door = (u >= 12) & (u < 20) & (h >= 14) & (h < 34)
                out[door] = C["recess"]
                out[door & ((u < 12.6) | (u >= 19.4) | (h >= 33.4))] = C["wood_dark"]
            return out
        return fn

    post = tone("wood_mid", "wood_mid", "wood_dark")
    parts = boxes(*[Box(a, a + 1.5, b, b + 1.5, 0, 12, **post) for a in (3, 27.5) for b in (3, 10.5)],
                  Box(2, 30, 2, 12, 12, 44, top=C["wood_light"], left=planks(True), right=planks(False)))
    A0, A1, B0, B1, H0, R, ov = 2, 30, 2, 12, 44, 14, 2                # gable roof, ridge along a
    m = (B0 + B1) / 2
    drop = R + ov * R / (m - B0)
    top, along = (A0 - ov, m, H0 + R), (A1 - A0 + 2 * ov, 0, 0)
    roof = [Face(top, along, (0, m - B0 + ov, -drop), zinc("stone_light", "stone_soft"), bias=2e-6),   # faces +b
            Face(top, along, (0, -(m - B0 + ov), -drop), zinc("stone_soft", "stone_mid"), bias=2e-6),  # faces -b
            Face((A1, B0, H0), (0, B1 - B0, 0), (0, m - B0, R), C["wood_mid"], tri=True)]           # gable end

    def cleats(u, v):
        return np.where((v % 3) < 0.8, C["wood_mid"], C["wood_light"])
    ramp = [Face((13, 12, 14), (6, 0, 0), (0, 12, -14), cleats)]
    return solid(parts + roof + ramp, cells=(2, 2), line=OL_SOFT)


# ---------------------------------------------------------------- registry
@dataclass
class Piece:
    name: str
    folder: str
    kind: str                       # "tile" (64x32) or "struct" (80x152; bigger for multi-cell)
    render: Callable[[], np.ndarray]
    note: str = ""
    cells: tuple = (1, 1)           # footprint (W along gx, D along gy) for multi-cell structs


def _p(name, folder, kind, fn, note="", cells=(1, 1)):
    return Piece(name, folder, kind, fn, note, cells)


OL_SOFT = C["outline_soft"]

PIECES = [
    # ---- apartment floors
    _p("floor_light_wood", "apartment/floors", "tile",
       lambda: tile(wood("wood_light", "wood_warm", "wood_mid", "wood_high", 1))),
    _p("floor_light_wood_worn", "apartment/floors", "tile",
       lambda: tile(wood("wood_light", "wood_warm", "wood_mid", "wood_warm", 2, worn=True))),
    _p("floor_dark_wood", "apartment/floors", "tile",
       lambda: tile(wood("wood_mid", "wood_dark", "outline_soft", "wood_warm", 3))),
    _p("floor_kitchen_tile", "apartment/floors", "tile", lambda: tile(kitchen_tile)),
    # ---- apartment walls (back walls 96 px; front walls cut away to a 12 px stub, D-58)
    _p("wall_left", "apartment/walls", "struct", lambda: run([wall_left_box()])),
    _p("wall_right", "apartment/walls", "struct", lambda: run([wall_right_box()])),
    _p("wall_inside_corner", "apartment/walls", "struct",
       lambda: run([wall_left_box(b0=-T), wall_right_box()], joined=False), "back corner: both top edges"),
    _p("wall_outside_corner", "apartment/walls", "struct",
       lambda: struct([Box(0, 16, 16, 16 + T, 0, H_WALL, top=C["wall_cream"],
                           left=face("wall_beige", "stone_mid", "stone_soft"), right=C["wall_shadow"]),
                       Box(16, 16 + T, 0, 16 + T, 0, H_WALL, top=C["wall_cream"],
                           left=face("wall_beige", "stone_mid", "stone_soft"),
                           right=face("wall_shadow", "stone_dark", "stone_mid"))]),
       "exterior corner: both bottom edges, faces outward; its 4 px thickness extends past the cell"),
    _p("wall_cutaway_front_left", "apartment/walls", "struct", lambda: run([stub_front_left_box()]),
       "front-left edge of the room (b = 16), cut away; inside the cell"),
    _p("wall_cutaway_front_right", "apartment/walls", "struct", lambda: run([stub_front_right_box()]),
       "front-right edge of the room (a = 16), cut away; inside the cell"),
    _p("wall_cutaway_front_corner", "apartment/walls", "struct",
       lambda: run([stub_front_left_box(0, 16 - T), stub_front_right_box()],
                   context=[stub_front_left_box(-16, 0), stub_front_right_box(-16, 0)]),
       "front corner of the room"),
    _p("wall_cutaway_doorstep_front_left", "apartment/walls", "struct",
       lambda: run([stub_front_left_box(0, 3), step(3, 13, 16 - T, 17), stub_front_left_box(13, 16)],
                   context=[stub_front_left_box(-16, 0)]),
       "garden door: a gap in the front-left stub with a stone step (open once the garden opens)"),
    _p("wall_cutaway_doorstep_front_right", "apartment/walls", "struct",
       lambda: run([stub_front_right_box(0, 3), step(16 - T, 17, 3, 13), stub_front_right_box(13, 16)],
                   context=[stub_front_right_box(-16, 0)]),
       "garden door in the front-right stub"),
    _p("wall_doorway_open_left", "apartment/walls", "struct",
       lambda: run([wall_left_box(feature=door(False, "wood_mid", "wood_warm"))])),
    _p("wall_doorway_open_right", "apartment/walls", "struct",
       lambda: run([wall_right_box(feature=door(False, "wood_warm", "wood_light"))])),
    _p("wall_door_closed_left", "apartment/walls", "struct",
       lambda: run([wall_left_box(feature=door(True, "wood_mid", "wood_warm"))])),
    _p("wall_door_closed_right", "apartment/walls", "struct",
       lambda: run([wall_right_box(feature=door(True, "wood_warm", "wood_light"))])),
    _p("wall_window_left", "apartment/walls", "struct",
       lambda: run([wall_left_box(feature=window("wood_warm", "wood_mid"))])),
    _p("wall_window_right", "apartment/walls", "struct",
       lambda: run([wall_right_box(feature=window("wood_light", "wood_warm"))])),
    # ---- trims (stand in front of a wall face)
    _p("baseboard_left", "apartment/trims", "struct",
       lambda: struct([Box(0, 0.5, 0, 16, 0, 5, top=C["wood_light"], left=C["wood_warm"], right=C["wood_mid"])],
                      line=None)),
    _p("baseboard_right", "apartment/trims", "struct",
       lambda: struct([Box(0, 16, 0, 0.5, 0, 5, top=C["wood_light"], left=C["wood_warm"], right=C["wood_mid"])],
                      line=None)),
    # ---- garden terrain (wild outside the garden; bare -> lush inside)
    _p("garden_wild", "garden/terrain", "tile", lambda: tile(grass_wild),
       "untended ground outside the tended garden (D-58)"),
    _p("garden_soil_bare", "garden/terrain", "tile", lambda: tile(soil_bare)),
    _p("garden_soil_improved", "garden/terrain", "tile", lambda: tile(soil_improved)),
    _p("garden_grass_basic", "garden/terrain", "tile", lambda: tile(grass_basic)),
    _p("garden_grass_healthy", "garden/terrain", "tile", lambda: tile(grass_healthy)),
    _p("garden_grass_lush", "garden/terrain", "tile", lambda: tile(grass_lush_tex())),
    # ---- paths (seamless whole tiles, D-53)
    _p("path_stepping_stone", "garden/paths", "tile", lambda: tile(stepping_stone)),
    _p("path_paved", "garden/paths", "tile", lambda: tile(paved)),
    _p("path_nice_paved", "garden/paths", "tile", lambda: tile(nice_paved)),
    # ---- borders (6 px stone edging, centred on the cell edge, D-58)
    _p("garden_border_straight_left", "garden/borders", "struct", lambda: run([border_left()], OL_SOFT),
       "on the top-left edge; a bed's front edges use straights on the cells in front of it"),
    _p("garden_border_straight_right", "garden/borders", "struct", lambda: run([border_right()], OL_SOFT)),
    _p("garden_border_corner_inner", "garden/borders", "struct",
       lambda: run([border_left(), border_right()], OL_SOFT, joined=False), "back corner of a bed"),
    _p("garden_border_corner_outer", "garden/borders", "struct",
       lambda: run([border(16 - E, 16 + E, -E, 16 + E), border(-E, 16 + E, 16 - E, 16 + E)], OL_SOFT,
                   joined=False), "both bottom edges (a one-cell bed's front); reaches 1 px past the cell"),
    # ---- planters (14 px)
    _p("planter_bed_empty", "garden/planters", "struct", lambda: struct([planter(False)], OL_SOFT)),
    _p("planter_bed_soil", "garden/planters", "struct", lambda: struct([planter(True)], OL_SOFT)),
    # ---- fences (28 px, centred on the cell edge; corner posts shared with the neighbour, D-58)
    _p("fence_left", "garden/fences", "struct",
       lambda: struct([post(0, 0)] + rails_left() + [post(0, 8), post(0, 16)], OL_SOFT)),
    _p("fence_right", "garden/fences", "struct",
       lambda: struct([post(0, 0)] + rails_right() + [post(8, 0), post(16, 0)], OL_SOFT)),
    _p("fence_corner", "garden/fences", "struct",
       lambda: struct([post(0, 0)] + rails_left() + rails_right()
                      + [post(0, 8), post(8, 0), post(0, 16), post(16, 0)], OL_SOFT)),
    _p("fence_gate_left", "garden/fences", "struct",
       lambda: struct([post(0, 0), Box(-0.25, 0.25, P, 16 - P, 4, 24, top=C["wood_light"], right=gate_face),
                       post(0, 16)], OL_SOFT)),
    _p("fence_gate_right", "garden/fences", "struct",
       lambda: struct([post(0, 0), Box(P, 16 - P, -0.25, 0.25, 4, 24, top=C["wood_light"], left=gate_face_lit),
                       post(16, 0)], OL_SOFT)),
    # ---- neighbourhood: fixed scenery, never tied to anyone's progress (D-59)
    _p("neighbour_house_a", "neighbourhood/houses", "struct",
       lambda: house(5, 5, "a", TERRACOTTA, "right", 2, win_left=[1, 3], win_right=[0, 4],
                     walls=("house_peach", "house_peach_shade")),
       "5 x 5, peach walls, terracotta, ridge along gx, door on the front-right face", cells=(5, 5)),
    _p("neighbour_house_b", "neighbourhood/houses", "struct",
       lambda: house(5, 5, "b", TERRACOTTA, "left", 2, win_left=[0, 4], win_right=[1, 3],
                     walls=("house_sage", "house_sage_shade")),
       "5 x 5, sage walls, terracotta, ridge along gy, door on the front-left face", cells=(5, 5)),
    _p("neighbour_house_c", "neighbourhood/houses", "struct",
       lambda: house(5, 5, "a", SLATE, "left", 1, win_left=[3], win_right=[1, 3],
                     walls=("house_blue", "house_blue_shade")),
       "5 x 5, pale blue walls, slate roof, door on the front-left face", cells=(5, 5)),
    _p("prop_ac_unit", "neighbourhood/props", "struct", ac_unit),
    _p("prop_washing_line", "neighbourhood/props", "struct", washing_line, "1 x 2, along gy", cells=(1, 2)),
    _p("prop_motorbike", "neighbourhood/props", "struct", motorbike, "1 x 2, front towards +gy", cells=(1, 2)),
    # ---- animal homes (D-67): shown when the user has chosen that animal
    _p("prop_chicken_coop", "garden/animals", "struct", chicken_coop,
       "reban ayam, 2 x 2: coop on the back row, ramp towards +gy; chickens sleep in front at night", cells=(2, 2)),
]
