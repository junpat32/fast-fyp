"""Exact isometric geometry (style guide §3-4, D-57).

Ground point (a, b) at height h projects to screen x = 32 + 2a - 2b, y = a + b - h, relative to
the top-left of a cell's 64x32 box. One cell is a, b in [0, 16). Sampling at pixel centres
reproduces the D-57 diamond exactly (rows x = 31-2j .. 32+2j) and never lands on a boundary,
so there are no rounding ties.

Canvases
  ground tiles (floors, terrain, paths): 64 x 32, cell box at (0, 0)
  structures (walls, trims, borders, planters, fences): 80 x 152, cell box at STRUCT_ORIGIN
Placement (manifest): draw an asset at  cell_screen_position - footprint_origin,  where
  cell_screen_position = map_origin + ((gx - gy) * 32, (gx + gy) * 16).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Union

import numpy as np

CELL_W, CELL_H = 64, 32
STRUCT_W, STRUCT_H = 80, 152
STRUCT_ORIGIN = (8, 112)

Color = Union[int, Callable, None]   # palette index, fn(u, v) -> index array (-1 = leave as is), or None


def diamond_mask() -> np.ndarray:
    """The D-57 diamond as a 32 x 64 boolean mask (defined row by row, independent of the projection)."""
    m = np.zeros((CELL_H, CELL_W), bool)
    for y in range(CELL_H):
        j = y if y < 16 else 31 - y
        m[y, 31 - 2 * j:33 + 2 * j] = True
    return m


def pixel_grid(w: int, h: int, origin: tuple[int, int]):
    """Pixel-centre coordinates relative to the cell box origin."""
    ys, xs = np.mgrid[0:h, 0:w]
    return xs + 0.5 - origin[0], ys + 0.5 - origin[1]


def ground_ab(X, Y, h=0.0):
    d = (X - 32) / 2
    return (d + Y + h) / 2, (Y + h - d) / 2


@dataclass
class Box:
    """An axis-aligned box in iso space: a in [a0, a1), b in [b0, b1), height h in [h0, h1).
    Visible faces: top (h = h1), left (b = b1, faces down-left: lit), right (a = a1, faces
    down-right: shaded). Face colour fns get (along-face coordinate, height) for the sides and
    (a, b) for the top."""
    a0: float
    a1: float
    b0: float
    b1: float
    h0: float
    h1: float
    top: Color = None
    left: Color = None
    right: Color = None


def _apply(canvas, mask, color, u, v):
    if color is None or not mask.any():
        return
    vals = color(u[mask], v[mask]) if callable(color) else np.full(int(mask.sum()), color)
    sub = canvas[mask]
    keep = vals >= 0
    sub[keep] = vals[keep]
    canvas[mask] = sub


def draw_box(canvas: np.ndarray, X, Y, box: Box) -> None:
    """Draw one box over the canvas (painter's order: call back-to-front)."""
    d = (X - 32) / 2
    b_r = box.a1 - d
    h_r = box.a1 + b_r - Y
    m_r = (b_r >= box.b0) & (b_r < box.b1) & (h_r >= box.h0) & (h_r < box.h1)
    a_l = box.b1 + d
    h_l = a_l + box.b1 - Y
    m_l = (a_l >= box.a0) & (a_l < box.a1) & (h_l >= box.h0) & (h_l < box.h1)
    a_t, b_t = ground_ab(X, Y, box.h1)
    m_t = (a_t >= box.a0) & (a_t < box.a1) & (b_t >= box.b0) & (b_t < box.b1)
    _apply(canvas, m_r, box.right, b_r, h_r)
    _apply(canvas, m_l, box.left, a_l, h_l)
    _apply(canvas, m_t, box.top, a_t, b_t)        # top wins at shared edges


@dataclass
class Face:
    """A flat quad in iso space: points O + u*U + v*V with u, v in [0, 1); tri=True keeps only
    u + v < 1 (a triangle). Vectors are (a, b, h). The colour fn gets the distances along U and V
    (in a/b/h units). Used for shapes boxes can't make: sloped roofs, wheels (D-59)."""
    O: tuple
    U: tuple
    V: tuple
    color: Color
    tri: bool = False
    bias: float = 0.0          # depth tie-break where faces share an edge (tops win)


def box_faces(bx: Box) -> list[Face]:
    """A Box as its three visible faces, colour fns called with the same arguments as draw_box."""
    def wrap(fn, f):
        return (lambda u, v: fn(*f(u, v))) if callable(fn) else fn
    w, d, h = bx.a1 - bx.a0, bx.b1 - bx.b0, bx.h1 - bx.h0
    out = []
    if bx.right is not None:
        out.append(Face((bx.a1, bx.b0, bx.h0), (0, d, 0), (0, 0, h), wrap(bx.right, lambda u, v: (bx.b0 + u, bx.h0 + v))))
    if bx.left is not None:
        out.append(Face((bx.a0, bx.b1, bx.h0), (w, 0, 0), (0, 0, h), wrap(bx.left, lambda u, v: (bx.a0 + u, bx.h0 + v))))
    if bx.top is not None:
        out.append(Face((bx.a0, bx.b0, bx.h1), (w, 0, 0), (0, d, 0), wrap(bx.top, lambda u, v: (bx.a0 + u, bx.b0 + v)),
                        bias=1e-6))
    return out


def draw_faces(canvas: np.ndarray, X, Y, faces: list[Face]) -> None:
    """Depth-buffered drawing: each pixel shows the nearest face along its line of sight.

    The pixel at (X, Y) sees the points a - b = d, a + b - h = Y; with t = a + b (larger = nearer
    the viewer) they are a = (t + d) / 2, b = (t - d) / 2, h = t - Y. Setting that equal to
    O + uU + vV gives a 3 x 3 linear system whose matrix is constant per face, so (u, v, t) for
    every pixel is one matrix-vector product."""
    d = (X - 32) / 2
    zbuf = np.full(canvas.shape, -np.inf)
    for f in faces:
        M = np.array([[f.U[0], f.V[0], -0.5], [f.U[1], f.V[1], -0.5], [f.U[2], f.V[2], -1.0]])
        if abs(np.linalg.det(M)) < 1e-9:
            continue                                  # seen exactly edge-on
        Mi = np.linalg.inv(M)
        r = (d / 2 - f.O[0], -d / 2 - f.O[1], -Y - f.O[2])
        u, v, t = (Mi[k, 0] * r[0] + Mi[k, 1] * r[1] + Mi[k, 2] * r[2] for k in range(3))
        inside = (u >= 0) & (v >= 0) & ((u + v < 1) if f.tri else (u < 1) & (v < 1))
        m = inside & (t + f.bias > zbuf)
        if not m.any():
            continue
        lu, lv = np.linalg.norm(f.U), np.linalg.norm(f.V)
        vals = np.asarray(f.color(u[m] * lu, v[m] * lv) if callable(f.color) else np.full(int(m.sum()), f.color))
        ok = vals >= 0                                # -1 = a hole in the face: leave what is behind
        idx = np.flatnonzero(m)[ok]
        canvas.flat[idx] = vals[ok]
        zbuf.flat[idx] = (t + f.bias).flat[idx]


def struct_canvas(cells: tuple[int, int]) -> tuple[int, int, tuple[int, int]]:
    """Canvas (w, h) and footprint origin for a struct covering cells (W along gx, D along gy).
    1 x 1 gives the standard 80 x 152 canvas with origin (8, 112)."""
    W, D = cells
    return 32 * (W + D) + 16, STRUCT_ORIGIN[1] + 16 * (W + D) + 8, (32 * (D - 1) + 8, STRUCT_ORIGIN[1])


def outline(canvas: np.ndarray, color: int, mode: str = "full", context: np.ndarray | None = None) -> None:
    """1-px outline on the silhouette, never where the piece stands on the ground.
    mode "full": top and sides (standalone objects: posts, planters, corners)
    mode "top":  top edge only (pieces that join neighbours in a run: walls, borders), so a
                 continuous wall shows no seam where two pieces meet
    context: extra silhouette (e.g. the neighbouring piece in a run) that counts as 'something
             there' when testing neighbours, but is not drawn"""
    sil = canvas >= 0
    pad = np.pad(sil if context is None else sil | context, 1)
    up, down = pad[:-2, 1:-1], pad[2:, 1:-1]
    left, right = pad[1:-1, :-2], pad[1:-1, 2:]
    if mode == "top":
        edge = sil & ~up
    else:
        edge = sil & (~up | ~left | ~right)
        edge &= ~(sil & ~down & up & left & right)     # bottom-only edges stay unoutlined (ground contact)
    canvas[edge] = color


def cell_screen(gx: int, gy: int) -> tuple[int, int]:
    return (gx - gy) * 32, (gx + gy) * 16
