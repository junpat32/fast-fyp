"""The app's four tab icons (T-22, D-122), drawn in code in the kit's pixel style (D-55; no image
generation, D-83):

    .venv\\Scripts\\python -m tools.asset_generation.tab_icons   # -> app/assets/images/tabIcons/, previews/tab_icons.png

Home is a house, Money two rising stacks of coins, Add a plus cut out of a disc (the main action, so
the boldest shape), Future an hourglass ("later on"). Each is a 24 x 24 grid, the size of an Android
bottom-navigation icon in dp, with the shape inside the middle 20 x 20 (Material's keylines), saved
at 1x, 2x and 3x by whole-number nearest-neighbour scaling, so pixels stay square. Pixels are black
and either opaque or clear: the app shows them in "template" mode, so the tab bar tints them (grey,
or dark when selected) in light and dark mode alike.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "app" / "assets" / "images" / "tabIcons"
PREVIEWS = Path(__file__).resolve().parent / "previews"
SIZE, KEYLINE = 24, 2                           # the grid, and the clear margin round the shape
SCALES = {"": 1, "@2x": 2, "@3x": 3}
MID = (SIZE - 1) / 2


def _grid() -> np.ndarray:
    return np.zeros((SIZE, SIZE), dtype=bool)


def home() -> np.ndarray:
    """A house: a roof wider than the walls, and a door."""
    g = _grid()
    for k in range(10):                         # the roof, two pixels wider each row
        g[2 + k, 11 - k:13 + k] = True
    g[12:21, 5:19] = True                       # the walls
    g[15:21, 10:14] = False                     # the door
    return g


def money() -> np.ndarray:
    """Two stacks of coins, the right one taller: money, and money growing."""
    g = _grid()
    for x0, coins in ((3, 3), (13, 5)):
        for i in range(coins):
            bottom = 20 - 4 * i                 # each coin three rows high, a clear row between
            g[bottom - 2, x0 + 1:x0 + 7] = True
            g[bottom - 1, x0:x0 + 8] = True
            g[bottom, x0 + 1:x0 + 7] = True
    return g


def add() -> np.ndarray:
    """A disc with a plus cut out of it."""
    y, x = np.mgrid[0:SIZE, 0:SIZE]
    g = (x - MID) ** 2 + (y - MID) ** 2 <= 10 ** 2
    g[6:18, 11:13] = False
    g[11:13, 6:18] = False
    return g


HOURGLASS_EDGE = [5, 5, 6, 7, 8, 9, 9, 10]      # the glass's left edge on rows 4-11 (2 px thick); neck 11-12
SAND = {8: (10, 14), 9: (11, 13), 10: (11, 13),             # a little sand left at the top,
        13: (11, 13), 14: (11, 13), 15: (11, 13),           # a thin stream through the neck,
        16: (11, 13), 17: (10, 14), 18: (8, 16), 19: (7, 17)}   # and the mound it has made


def future() -> np.ndarray:
    """An hourglass: caps top and bottom, a glass narrowing to the neck, sand running down."""
    g = _grid()
    g[2:4, 4:20] = True                         # the caps
    g[20:22, 4:20] = True
    for y, xl in zip(range(4, 12), HOURGLASS_EDGE):
        for yy in (y, SIZE - 1 - y):            # the bottom half mirrors the top
            g[yy, xl:xl + 2] = True
            g[yy, SIZE - 2 - xl:SIZE - xl] = True     # the right edge mirrors the left
    for y, (x0, x1) in SAND.items():
        g[y, x0:x1] = True
    return g


ICONS = {"home": home, "money": money, "add": add, "future": future}


def rgba(g: np.ndarray, k: int) -> Image.Image:
    a = np.repeat(np.repeat(g, k, axis=0), k, axis=1)
    out = np.zeros((*a.shape, 4), dtype=np.uint8)
    out[..., 3] = np.where(a, 255, 0)           # black, opaque or clear: tinted by the tab bar
    return Image.fromarray(out, "RGBA")


def build(out: Path = OUT) -> dict[str, np.ndarray]:
    out.mkdir(parents=True, exist_ok=True)
    grids = {name: draw() for name, draw in ICONS.items()}
    for name, g in grids.items():
        for suffix, k in SCALES.items():
            rgba(g, k).save(out / f"{name}{suffix}.png")
    return grids


def preview(grids: dict[str, np.ndarray], path: Path = PREVIEWS / "tab_icons.png") -> Path:
    """The four icons as the tab bar shows them (3x, light and dark, grey and selected), and enlarged."""
    bars =[((255, 255, 255), (96, 100, 108), (0, 0, 0)), ((21, 19, 26), (183, 176, 194), (243, 239, 231))]
    k, big, pad = 3, 8, 24
    w = len(grids) * (SIZE * big + pad) + pad
    h = pad + SIZE * big + pad + 2 * (SIZE * k + 2 * pad)
    sheet = Image.new("RGB", (w, h), (232, 223, 201))
    for i, g in enumerate(grids.values()):
        x = pad + i * (SIZE * big + pad)
        ink = Image.new("RGB", (SIZE * big, SIZE * big), (40, 36, 48))
        sheet.paste(ink, (x, pad), rgba(g, big))
        for j, (bg, grey, selected) in enumerate(bars):
            y = pad + SIZE * big + pad + j * (SIZE * k + 2 * pad)
            sheet.paste(Image.new("RGB", (SIZE * big, SIZE * k + 2 * pad), bg), (x, y))
            colour = selected if i == j else grey          # one selected per bar, the others grey
            sheet.paste(Image.new("RGB", (SIZE * k, SIZE * k), colour), (x + (SIZE * big - SIZE * k) // 2, y + pad),
                        rgba(g, k))
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


def ascii_art(g: np.ndarray) -> str:
    return "\n".join("".join("#" if v else "." for v in row) for row in g)


if __name__ == "__main__":
    drawn = build()
    for name, g in drawn.items():
        print(f"{name}\n{ascii_art(g)}\n")
    print(f"-> {OUT}\n-> {preview(drawn)}")
