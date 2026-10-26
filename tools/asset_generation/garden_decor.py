"""Garden decorations (T-22 batch 2; spec §2 and §5, shared/game.json "decorations.garden", D-69, D-86).

Bought with choices (1 per 200 points) and placed on a free lawn spot the user taps (K2; the spots
come from scenes.decor_spots). Same method as batch 1: boxes and faces in iso space, palette indices,
lit from the upper left, the soft garden outline (spec §1). Round things (bird bath, fountain, table
top) are many-sided cylinders drawn with the depth-buffered faces, so they are round in the world.
Only the garden lamp and the lantern glow at night (lamp_shade, spec §1 E3); water uses the sky
colours, which darken at night instead of lighting up like the window glass.

Heights (spec §2, 39 px/m): bench 18 (back 31), lamp 47, lantern 20, bird bath 31, fountain 39,
arch 86, outdoor table 29, chair 35, mailbox 43, bicycle rack 31, stones 12. Footprints: 1 x 1, the
benches, arch and bicycle rack 1 x 2 along gy, the fountain 2 x 2.
"""
from __future__ import annotations

import numpy as np

from .geometry import Box, Face, struct_canvas
from .palette import IDX
from .pieces import M_H, Piece, boxes, solid, tone

C = IDX
OL = C["outline_soft"]
WOOD = tone("wood_light", "wood_warm", "wood_mid")
DARK_WOOD = tone("wood_warm", "wood_mid", "wood_dark")
IRON = tone("stone_mid", "stone_dark", "recess")
STONE = tone("stone_light", "stone_soft", "stone_mid")
PAINT = tone("wall_cream", "wall_beige", "wall_shadow")
GLOW = tone("lamp_shade", "lamp_shade", "lamp_shade_dark")


def cylinder(ca, cb, r, h0, h1, top, sides=("stone_soft", "stone_mid", "stone_dark"), n=20, bias=0.0):
    """An upright n-sided cylinder (radius r ground units, from h0 to h1 px). Side faces are coloured
    by where they point: towards +b (down-left on screen) lit, towards +a (down-right) shaded."""
    lit, mid, dark = (C[s] for s in sides)
    out = []
    for k in range(n):
        t0, t1 = 2 * np.pi * k / n, 2 * np.pi * (k + 1) / n
        p0 = (ca + r * np.cos(t0), cb + r * np.sin(t0))
        p1 = (ca + r * np.cos(t1), cb + r * np.sin(t1))
        if top is not None:
            out.append(Face((ca, cb, h1), (p0[0] - ca, p0[1] - cb, 0), (p1[0] - ca, p1[1] - cb, 0),
                            C[top] if isinstance(top, str) else top, tri=True, bias=bias + 1e-6))
        tm = (t0 + t1) / 2
        na, nb = np.cos(tm), np.sin(tm)
        if na + nb <= -0.2:
            continue                                                       # faces away from the viewer
        colour = lit if nb - na > 0.55 else dark if nb - na < -0.55 else mid
        out.append(Face((p0[0], p0[1], h0), (p1[0] - p0[0], p1[1] - p0[1], 0), (0, 0, h1 - h0), colour, bias=bias))
    return out


def rod(a, b0, h0, b1, h1, w=1.6, colour="stone_dark", bias=2e-6):
    """A thin flat bar in the plane a (a bicycle tube, a spoke) from (b0, h0) to (b1, h1), about w px
    thick on screen: thickness goes up for a flat bar and sideways (along b) for a steep one."""
    steep = abs(h1 - h0) > 2 * abs(b1 - b0)
    o, v = ((a, b0 - w / 4, h0), (0, w / 2, 0)) if steep else ((a, b0, h0 - w / 2), (0, 0, w))
    return Face(o, (0, b1 - b0, h1 - h0), v, C[colour], bias=bias)


def bike_wheel(a, bc, r_m, n=20):
    """A spoked bicycle wheel in the plane a: a dark tyre ring, a grey rim, spokes and a hub, open
    in between (unlike the motorbike's solid wheels)."""
    rb, rh = r_m * 16, r_m * M_H                                      # radius along b (units) and up (px)
    out = []
    for k_out, k_in, colour, bias in ((1.0, 0.84, "outline_soft", 1e-6), (0.84, 0.74, "stone_soft", 1.5e-6)):
        for k in range(n):
            t0, t1 = 2 * np.pi * k / n, 2 * np.pi * (k + 1) / n
            p = [(bc + kr * rb * np.cos(t), rh + kr * rh * np.sin(t)) for kr, t in
                 ((k_in, t0), (k_out, t0), (k_out, t1), (k_in, t1))]
            for q0, q1, q2 in ((p[0], p[1], p[2]), (p[0], p[2], p[3])):
                out.append(Face((a, q0[0], q0[1]), (0, q1[0] - q0[0], q1[1] - q0[1]), (0, q2[0] - q0[0], q2[1] - q0[1]),
                                C[colour], tri=True, bias=bias))
    for k in range(6):                                                 # spokes
        t = np.pi * k / 3 + 0.3
        out.append(rod(a, bc, rh, bc + 0.74 * rb * np.cos(t), rh + 0.74 * rh * np.sin(t), 0.8, "stone_light", 0.5e-6))
    return out


def _px(cells, a, b, h):
    """Canvas pixel of the ground point (a, b) at height h."""
    _, _, (ox, oy) = struct_canvas(cells)
    return round(ox + 32 + 2 * a - 2 * b), round(oy + a + b - h)


def _slats(base, gap, period=2.6, along="a"):
    def fn(a, b):
        v = a if along == "a" else b
        return np.where((v % period) < 0.5, C[gap], C[base]).astype(np.int16)
    return fn


# ---------------------------------------------------------------- benches (1 x 2 along gy, facing +a)
def bench():
    """A simple wooden garden bench: slatted seat 18 px, slatted back 31 px, facing +a."""
    parts = boxes(*[Box(a, a + 1.2, b, b + 1.2, 0, 16, **DARK_WOOD) for a in (4, 11) for b in (3, 28)],
                  *[Box(2.5, 3.7, b, b + 1.2, 0, 31, **DARK_WOOD) for b in (3, 28)],          # back legs
                  Box(3.5, 12.5, 2, 30, 16, 18, top=_slats("wood_light", "wood_mid"), left=C["wood_warm"],
                      right=C["wood_mid"]),
                  *[Box(2.6, 3.6, 2, 30, h, h + 2.5, **WOOD) for h in (21, 25.5, 29)])         # back slats
    return solid(parts, cells=(1, 2), line=OL)


def bench_improved():
    """A park bench: cast-iron ends with armrests, varnished slats, a cushion; facing +a."""
    parts = boxes(*[Box(3, 13, b, b + 1.5, 0, 2, **IRON) for b in (2, 28.5)],                  # iron feet
                  *[Box(a, a + 1.2, b + 0.2, b + 1.3, 2, 16, **IRON) for a in (4, 11.5) for b in (2, 28.5)],
                  *[Box(2.5, 3.8, b + 0.2, b + 1.3, 2, 33, **IRON) for b in (2, 28.5)],
                  *[Box(3.5, 13, b, b + 1.5, 21, 22.5, **IRON) for b in (2, 28.5)],             # armrests
                  Box(3.5, 12.5, 3.5, 28.5, 16, 18, top=_slats("wood_warm", "wood_dark"), left=C["wood_mid"],
                      right=C["wood_dark"]),
                  *[Box(2.7, 3.6, 3.5, 28.5, h, h + 2.5, **DARK_WOOD) for h in (21, 25, 29)],
                  Box(5, 11.5, 12, 20, 18, 20.5, **tone("roof_light", "roof_mid", "roof_dark")))   # cushion
    return solid(parts, cells=(1, 2), line=OL)


# ---------------------------------------------------------------- lights (they glow at night)
def garden_lamp():
    """A post lamp, 47 px (1.2 m): iron post, a lantern head whose panes glow at night."""
    def panes(u, h):
        out = np.full(u.shape, C["lamp_shade"], np.int16)
        out[(np.abs(u - 8) < 0.4) | (h < 36.8) | (h >= 42.6)] = C["stone_dark"]
        return out
    parts = boxes(Box(5.5, 10.5, 5.5, 10.5, 0, 3, **IRON),
                  Box(7.3, 8.7, 7.3, 8.7, 3, 35, **IRON),
                  Box(5.5, 10.5, 5.5, 10.5, 35, 36, **IRON),
                  Box(6, 10, 6, 10, 36, 43.5, top=C["stone_dark"], left=panes, right=panes),
                  Box(5, 11, 5, 11, 43.5, 45, **IRON), Box(7.5, 8.5, 7.5, 8.5, 45, 47, **IRON))
    return solid(parts, line=OL)


def lantern():
    """A small wooden garden lantern on the ground, 20 px; its paper panes glow at night."""
    def panes(u, h):
        out = np.full(u.shape, C["lamp_shade"], np.int16)
        out[(np.abs(u - 8) < 0.35) | (h < 3.8) | (h >= 13.4)] = C["wood_dark"]
        return out
    parts = boxes(Box(5, 11, 5, 11, 0, 2, **DARK_WOOD),
                  Box(5.5, 10.5, 5.5, 10.5, 2, 14, top=C["wood_mid"], left=panes, right=panes),
                  Box(4.5, 11.5, 4.5, 11.5, 14, 16, **DARK_WOOD), Box(6, 10, 6, 10, 16, 18, **DARK_WOOD),
                  Box(7.4, 8.6, 7.4, 8.6, 18, 20, **DARK_WOOD))
    return solid(parts, line=OL)


# ---------------------------------------------------------------- water
def bird_bath():
    """A stone bird bath, 31 px: a pedestal, a round bowl of water, a sparrow on the rim."""
    faces = (cylinder(8, 8, 4.5, 0, 3, "stone_light") + cylinder(8, 8, 2, 3, 23, None)
             + cylinder(8, 8, 3.5, 21, 25, "stone_light", bias=1e-5)
             + cylinder(8, 8, 6.5, 25, 29, "stone_light", bias=2e-5)
             + cylinder(8, 8, 5.2, 29, 29.01, "sky", bias=3e-5))                     # the water
    canvas = solid(faces, line=OL)
    x, y = _px((1, 1), 8, 8, 29)
    canvas[y, x - 3:x + 1] = C["sky_light"]                                          # a glint on the water
    bird = [".kh.", "hhHH", ".HHS"]                                                  # a sparrow on the rim
    key = {"h": "wood_light", "H": "wood_mid", "S": "wood_dark", "k": "recess"}
    bx, by = _px((1, 1), 13.5, 7, 31)
    for j, row in enumerate(bird):
        for i, ch in enumerate(row):
            if ch != ".":
                canvas[by + j, bx + i] = C[key[ch]]
    return canvas


def fountain():
    """A simple two-tier stone fountain, 2 x 2, 39 px: a round basin, a column, an upper bowl, water
    falling from the top."""
    faces = (cylinder(16, 16, 13, 0, 8, "stone_light")
             + cylinder(16, 16, 11.5, 8, 8.01, "sky", bias=1e-5)                     # basin water
             + cylinder(16, 16, 2.2, 8, 24, None, bias=2e-5)
             + cylinder(16, 16, 6, 24, 28, "stone_light", bias=3e-5)
             + cylinder(16, 16, 4.8, 28, 28.01, "sky", bias=4e-5)                    # upper bowl water
             + cylinder(16, 16, 1.2, 28, 34, "stone_light", bias=5e-5))
    canvas = solid(faces, cells=(2, 2), line=OL)
    x, y = _px((2, 2), 16, 16, 34)
    for dx, dy in ((0, -1), (0, -2), (0, -3), (-1, -4), (1, -4), (-2, -3), (2, -3)):  # the spout
        canvas[y + dy, x + dx] = C["wall_cream"]
    sheet = {}                                                                       # a sheet of water falling
    for t in np.arange(-0.75, 2.35, 0.03):                                           # over the bowl's front rim
        x0, y0 = _px((2, 2), 16 + 6.3 * np.cos(t), 16 + 6.3 * np.sin(t), 25)
        x1, y1 = _px((2, 2), 16 + 7.0 * np.cos(t), 16 + 7.0 * np.sin(t), 8.5)
        sheet[x0] = (min(y0, sheet.get(x0, (y0, y1))[0]), max(y1, sheet.get(x0, (y0, y1))[1]))
    for x, (y0, y1) in sheet.items():
        for y in range(y0 + 1, y1):
            canvas[y, x] = C["sky_light" if x % 3 else "sky"]                        # stripes of falling water
        canvas[y0 + 1, x] = C["wall_cream"]                                          # where it pours off the lip
        if x % 2 == 0:
            canvas[y1, x] = C["wall_cream"]                                          # splashes in the basin
    for a, b in ((22, 12), (10, 20), (24, 22), (12, 9), (25, 17)):                    # ripples in the basin
        px, py = _px((2, 2), a, b, 8)
        canvas[py, px:px + 3] = C["sky_light"]
    return canvas


# ---------------------------------------------------------------- structures
def garden_arch():
    """A white painted garden arch, 1 x 2 (you walk through it along gx), 86 px: two lattice sides
    joined by a rounded top."""
    parts = boxes(*[Box(a, a + 1.5, b, b + 1.5, 0, 72, **PAINT) for a in (3, 11.5) for b in (2, 28.5)])
    faces = list(parts)
    for b in (2.75, 29.25):                                                          # lattice sides
        for h in range(10, 70, 10):
            faces += boxes(Box(4.5, 11.5, b - 0.4, b + 0.4, h, h + 1, **PAINT))
    steps = 14
    for a in (3.75, 12.25):                                                          # the curved top
        for k in range(steps):
            t0, t1 = k / steps, (k + 1) / steps
            b0, b1 = 2 + 28 * t0, 2 + 28 * t1
            h0, h1 = 72 + 14 * np.sin(np.pi * t0), 72 + 14 * np.sin(np.pi * t1)
            faces.append(Face((a - 0.75, b0, h0 - 1.5), (0, b1 - b0, h1 - h0), (0, 0, 3), C["wall_cream"], bias=3e-6))
            faces.append(Face((a + 0.75, b0, h0 - 1.5), (0, b1 - b0, h1 - h0), (0, 0, 3), C["wall_beige"], bias=2e-6))
            faces.append(Face((a - 0.75, b0, h0 + 1.5), (1.5, 0, 0), (0, b1 - b0, h1 - h0), C["wall_cream"], bias=4e-6))
    for k in range(1, 7):                                                            # cross bars over the top
        t = k / 7
        b, h = 2 + 28 * t, 72 + 14 * np.sin(np.pi * t)
        faces += boxes(Box(3.75, 12.25, b - 0.5, b + 0.5, h + 0.5, h + 1.5, **PAINT))
    return solid(faces, cells=(1, 2), line=OL)


def outdoor_table():
    """A round wooden garden table on a central post, 29 px."""
    faces = (cylinder(8, 8, 3.5, 0, 2, "wood_mid", ("wood_warm", "wood_mid", "wood_dark"))
             + cylinder(8, 8, 1.2, 2, 27, None, ("wood_warm", "wood_mid", "wood_dark"))
             + cylinder(8, 8, 6.5, 27, 29, "wood_light", ("wood_warm", "wood_mid", "wood_dark"), bias=1e-5))
    canvas = solid(faces, line=OL)
    for k in (-4, 0, 4):                                                             # board joints on the top
        x, y = _px((1, 1), 8 + k * 0.5, 8 - k * 0.5, 29)
        for d in range(-4, 5):
            if canvas[y + d // 2, x + d] == C["wood_light"]:
                canvas[y + d // 2, x + d] = C["wood_warm"]
    return canvas


def outdoor_chair():
    """A slatted wooden garden chair with armrests, facing +a; seat 17 px, back 35 px."""
    parts = boxes(*[Box(a, a + 1.2, b, b + 1.2, 0, 16, **DARK_WOOD) for a in (4.5, 11) for b in (3.5, 11.3)],
                  *[Box(3, 4.3, b, b + 1.2, 0, 35, **DARK_WOOD) for b in (3.5, 11.3)],
                  Box(4, 12.5, 3.5, 12.5, 15, 17, top=_slats("wood_light", "wood_mid", along="b"), left=C["wood_warm"],
                      right=C["wood_mid"]),
                  *[Box(3.5, 12.5, b, b + 1.2, 22, 23.5, **WOOD) for b in (3.5, 11.3)],     # armrests
                  *[Box(3.2, 4.1, 4.7, 11.3, h, h + 2.5, **WOOD) for h in (20, 24.5, 29, 32.5)])
    return solid(parts, line=OL)


def mailbox():
    """A letterbox the Malaysian way, 43 px: a red metal box on top of a plastered gate pillar, with
    the house number on a tile."""
    def pillar_front(u, h):
        out = np.full(u.shape, C["wall_beige"], np.int16)
        out[h < 3] = C["stone_mid"]                                                  # plinth
        tile = (np.abs(u - 8) < 2) & (h >= 18) & (h < 23)
        out[tile] = C["accent_blue_dark"]                                            # house number tile
        out[tile & (np.abs(u - 8) < 1.2) & (h >= 19) & (h < 22) & ((np.floor(u * 2) % 2) == 0)] = C["wall_cream"]
        return out

    def box_front(u, h):
        out = np.full(u.shape, C["accent_red"], np.int16)
        out[(h >= 37) & (h < 38) & (np.abs(u - 8) < 2.5)] = C["recess"]              # letter slot
        out[(np.abs(u - 4.9) < 0.3) | (np.abs(u - 11.1) < 0.3) | ((h >= 31.4) & (h < 32))] = C["red_dark"]
        out[(h >= 33.5) & (h < 35) & (np.abs(u - 10.2) < 0.4)] = C["stone_soft"]       # little lock
        return out
    parts = boxes(Box(4.5, 11.5, 4.5, 11.5, 0, 30, top=C["wall_cream"], left=pillar_front, right=C["wall_shadow"]),
                  Box(4, 12, 4, 12, 30, 31, **tone("wall_cream", "wall_beige", "wall_shadow")),   # pillar cap
                  Box(4.5, 11.5, 5, 11.5, 31, 40.5, top=C["accent_red"], left=box_front, right=C["red_dark"]),
                  Box(4, 12, 4.5, 12, 40.5, 42.5, **tone("accent_red", "red_dark", "red_dark")))  # lid
    return solid(parts, line=OL)


def bicycle_rack():
    """A metal bicycle rack, 1 x 2 along gy, with a bicycle parked in it (the saddle 31 px = 0.8 m)."""
    hoop = tone("stone_light", "stone_soft", "stone_mid")
    rack = boxes(*[Box(a, a + 1, 2, 30, 0, 1.5, **IRON) for a in (3, 12)],                 # base rails
                 *[Box(a, a + 1, b, b + 1, 1.5, 12, **hoop) for a in (3.5, 11.5) for b in (4, 22, 27)],
                 *[Box(3.5, 12.5, b, b + 1, 12, 13.5, **hoop) for b in (4, 22, 27)])    # hoops across
    a = 8.0
    r = 0.33                                                                         # 26-inch-ish wheels
    hub = r * M_H
    rear, front = 7.5, 24.5
    bb = (15.0, hub - 1)                                                             # bottom bracket
    paint = "accent_blue"
    frame = [rod(a, rear, hub, *bb, colour=paint),                                   # chain stay
             rod(a, *bb, 13.5, 26, 2.0, paint),                                      # seat tube
             rod(a, rear, hub, 13.5, 26, colour=paint),                              # seat stay
             rod(a, 13.5, 26, 22.5, 27, colour=paint),                               # top tube
             rod(a, *bb, 22.5, 27, 2.0, paint),                                      # down tube
             rod(a, 22.5, 27, front, hub, 1.4, "stone_mid"),                         # fork
             rod(a, 13.5, 26, 13, 30, 1.2, "stone_mid"),                             # seat post
             Face((a - 1.2, 11.2, 30.5), (2.4, 0, 0), (0, 3.6, 0.5), C["recess"], bias=3e-6),   # saddle
             rod(a, 22.5, 27, 22, 31, 1.2, "stone_mid"),                             # stem
             Face((a - 4, 21.5, 31), (8, 0, 0), (0, 1.0, 0), C["stone_dark"], bias=3e-6)]     # handlebar
    canvas = solid(rack + bike_wheel(a, rear, r) + bike_wheel(a, front, r) + frame, cells=(1, 2), line=None)
    # Thin tubes and hoops would turn solid dark under an outline on their own pixels, so the outline
    # goes just outside them (as for the bed plants), but not inside the wheels, which stay open.
    cw, ch, (ox, oy) = struct_canvas((1, 2))
    ys, xs = np.mgrid[0:ch, 0:cw] + 0.5
    b = (ox + 32 + 2 * a - xs) / 2
    h = oy + a + b - ys
    open_ = np.zeros(canvas.shape, bool)
    for bc in (rear, front):
        open_ |= ((b - bc) / (r * 16)) ** 2 + ((h - hub) / hub) ** 2 < 0.8 ** 2
    sil = canvas >= 0
    pad = np.pad(sil, 1)
    up, down, left, right = pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]
    ring = ~sil & (up | down | left | right) & ~open_
    ring &= ~(~sil & up & ~down & ~left & ~right & (ys > oy + 32))                     # not under it on the ground
    canvas[ring] = OL
    return canvas


def decorative_stones():
    """Three smooth river stones on a little bed of gravel, up to 12 px."""
    from .geometry import STRUCT_H, STRUCT_W
    canvas = np.full((STRUCT_H, STRUCT_W), -1, np.int16)
    ys, xs = np.mgrid[0:STRUCT_H, 0:STRUCT_W] + 0.5
    gravel = (((xs - 40) / 15) ** 2 + ((ys - 128) / 6.5) ** 2) <= 1
    rng = np.random.default_rng(7)
    speck = rng.random(canvas.shape)
    canvas[gravel & (speck < 0.55)] = C["stone_soft"]
    canvas[gravel & (speck >= 0.55)] = C["stone_light"]
    canvas[gravel & (speck < 0.12)] = C["stone_mid"]
    for gx, gy in ((27, 125), (52, 127), (38, 131)):                                 # grass tufts in the gravel
        for dx, h, colour in ((-1, 3, "green_mid"), (0, 4, "green_dark"), (1, 3, "green_mid"), (2, 2, "green_dark")):
            canvas[gy - h:gy, gx + dx] = C[colour]
    stones = np.zeros(canvas.shape, bool)
    for cx, cy, rx, ry, shades in ((44, 122, 8.5, 7.0, ("stone_light", "stone_soft", "stone_mid")),   # back first
                                   (32, 126, 6.0, 5.0, ("sand_light", "sand_mid", "sand_dark")),
                                   (46, 130, 5.0, 3.8, ("stone_soft", "stone_mid", "stone_dark"))):
        d = ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2
        m = (d <= 1) & (ys < cy + ry * 0.75)                                         # flat underside
        lit, mid, dark = (C[s] for s in shades)
        u = (xs - cx) / rx + (ys - cy) / ry
        canvas[m] = mid
        canvas[m & (u < -0.5)] = lit                                                 # light from the upper left
        canvas[m & (u > 0.6)] = dark
        canvas[m & (((xs - cx + rx * 0.35) / rx) ** 2 + ((ys - cy + ry * 0.45) / ry) ** 2 < 0.035)] = C["tile_light"]
        stones |= m
    pad = np.pad(stones, 1)
    edge = stones & ~(pad[:-2, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:] & pad[2:, 1:-1])
    canvas[edge] = OL
    return canvas


# ---------------------------------------------------------------- registry
DECOR = [("bench", bench, (1, 2), "a simple wooden bench, facing +a"),
         ("bench_improved", bench_improved, (1, 2), "a park bench with iron ends and a cushion, facing +a"),
         ("garden_lamp", garden_lamp, (1, 1), "a post lamp; glows at night"),
         ("lantern", lantern, (1, 1), "a small lantern on the ground; glows at night"),
         ("bird_bath", bird_bath, (1, 1), "a stone bird bath with a sparrow"),
         ("decorative_stones", decorative_stones, (1, 1), "three river stones on gravel"),
         ("garden_arch", garden_arch, (1, 2), "a white garden arch (walk through it along gx)"),
         ("outdoor_table", outdoor_table, (1, 1), "a round wooden garden table"),
         ("outdoor_chair", outdoor_chair, (1, 1), "a wooden garden chair, facing +a"),
         ("mailbox", mailbox, (1, 1), "a letterbox on a post"),
         ("bicycle_rack", bicycle_rack, (1, 2), "a bicycle rack with a bicycle"),
         ("fountain", fountain, (2, 2), "a two-tier stone fountain")]
GARDEN_DECOR_PIECES = [Piece(name, "garden/decorations", "struct", fn, f"decoration '{name}': {note}", cells)
                       for name, fn, cells, note in DECOR]
