"""App icon, splash and badge icons (T-22; for T-16), drawn in code in the kit's pixel style (D-55).

    .venv\\Scripts\\python -m tools.asset_generation.app_icons     # -> assets/app/, previews/app_icons.png

What Expo needs (app.json): `icon` (1024 x 1024, opaque), `android.adaptiveIcon.foregroundImage`
(1024 x 1024, transparent; Android crops it to a circle or squircle, so everything stays inside the
middle 66%) with `backgroundColor`, and a splash `image` (transparent) with `backgroundColor`.

The picture is the savings plant (the money plant, pokok duit: the room's savings object, already
approved) at its fullest stage with a gold coin: savings that grow. The badges are the game's three
(shared/game.json "badges"): cushion builder (a cushion with a coin), steady saver (three coin
stacks rising) and honest tracker (a notebook with a tick), each on a round medal, plus a grey
"not earned yet" version. Every pixel is a FAST palette colour (afternoon), alpha 0 or 255, and the
pictures are scaled up by whole numbers only, so pixels stay square (spec §1).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .furniture import savings_plant
from .palette import BASE, IDX, TRANSPARENT, to_rgba

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "app"
PREVIEWS = Path(__file__).resolve().parent / "previews"
C = IDX
BACKGROUND = "wall_cream"                       # icon and splash background (app.json backgroundColor)
SAFE = 0.66                                     # Android adaptive icon: the part that is never cropped

COIN = [".kkk.",
        "kYyyk",
        "kYyyk",
        "kyyyk",
        ".kkk."]
COIN_KEY = {"k": "coin_dark", "y": "coin_mid", "Y": "coin_light"}
COINS_AT = [(13, 2), (1, 10), (15, 14)]         # where coins grow among the leaves (x, y in the plant's crop)
FONT = {"F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
        "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
        "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
        "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."]}


def _crop(a: np.ndarray) -> np.ndarray:
    rows, cols = np.flatnonzero((a >= 0).any(axis=1)), np.flatnonzero((a >= 0).any(axis=0))
    return a[rows.min():rows.max() + 1, cols.min():cols.max() + 1]


def _stamp(canvas, rows, key, x, y):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != ".":
                canvas[y + j, x + i] = C[key[ch]]


def emblem() -> np.ndarray:
    """The money plant with gold coins growing among its leaves, as palette indices (small: scaled up
    later)."""
    canvas = _crop(savings_plant(4)).copy()
    for x, y in COINS_AT:
        _stamp(canvas, COIN, COIN_KEY, x, y)
    return canvas


def wordmark(colour: str = "outline") -> np.ndarray:
    out = np.full((7, 4 * 6 - 1), TRANSPARENT, np.int16)
    for k, ch in enumerate("FAST"):
        _stamp(out, FONT[ch], {"#": colour}, 6 * k, 0)
    return out


def _place(size: int, art: np.ndarray, scale: int, centre_y: float = 0.5) -> np.ndarray:
    out = np.full((size, size), TRANSPARENT, np.int16)
    big = np.kron(art, np.ones((scale, scale), dtype=np.int16))
    h, w = big.shape
    y0, x0 = int(size * centre_y - h / 2), (size - w) // 2
    out[y0:y0 + h, x0:x0 + w] = big
    return out


def _fit(art: np.ndarray, box: int) -> int:
    return max(1, box // max(art.shape))


def app_icon() -> np.ndarray:
    art = emblem()
    out = _place(1024, art, _fit(art, int(1024 * 0.62)), 0.52)
    out[out < 0] = C[BACKGROUND]
    return out


def adaptive_foreground() -> np.ndarray:
    art = emblem()
    return _place(1024, art, _fit(art, int(1024 * SAFE * 0.92)), 0.5)


def splash() -> np.ndarray:
    art, word = emblem(), wordmark()
    scale = _fit(art, 420)
    big_art = np.kron(art, np.ones((scale, scale), dtype=np.int16))
    big_word = np.kron(word, np.ones((scale, scale), dtype=np.int16))
    out = np.full((1024, 1024), TRANSPARENT, np.int16)
    gap = 4 * scale
    total = big_art.shape[0] + gap + big_word.shape[0]
    y = (1024 - total) // 2
    for block in (big_art, big_word):
        h, w = block.shape
        x = (1024 - w) // 2
        out[y:y + h, x:x + w] = np.where(block >= 0, block, out[y:y + h, x:x + w])
        y += h + gap
    return out


# ---------------------------------------------------------------- badges (shared/game.json "badges")
BADGE_COLOURS = {"cushion_builder": ("blue_light", "accent_blue", "accent_blue_dark"),
                 "steady_saver": ("green_light", "green_mid", "green_dark"),
                 "honest_tracker": ("roof_light", "roof_mid", "roof_dark")}
LOCKED = ("stone_light", "stone_soft", "stone_mid")
SYMBOLS = {
    "cushion_builder": (["...yyyy...",                      # a coin resting on a cushion
                         "..yYYyyy..",
                         "...yyyy...",
                         ".cccccccc.",
                         "cCCCCCCCcd",
                         "cCCCCCCcdd",
                         ".cddddddd."], {"y": "coin_mid", "Y": "coin_light", "c": "wall_cream", "C": "tile_light",
                                         "d": "wall_shadow"}),
    "steady_saver": ([".......yy.",                         # three coin stacks, rising
                      ".......YY.",
                      "....yy.yy.",
                      "....YY.YY.",
                      ".yy.yy.yy.",
                      ".YY.YY.YY.",
                      ".yy.yy.yy."], {"y": "coin_mid", "Y": "coin_light"}),
    "honest_tracker": (["pppppp....",                       # a notebook page and a big tick across it
                        "pLLLLp....",
                        "pppppp...g",
                        "pLLLLp..gg",
                        "pppppp.gg.",
                        "pgLLLpgg..",
                        "pggppgg...",
                        "ppgggg....",
                        "pppgg....."], {"p": "wall_cream", "L": "stone_soft", "g": "green_dark"}),
}


def badge(name: str, earned: bool = True) -> np.ndarray:
    """A 24 x 24 round medal: a rim, a lit fill (light from the upper left), the badge's symbol."""
    light, mid, dark = (BADGE_COLOURS[name] if earned else LOCKED)
    ys, xs = np.mgrid[0:24, 0:24] + 0.5
    d = np.hypot(xs - 12, ys - 12)
    out = np.full((24, 24), TRANSPARENT, np.int16)
    out[d <= 11.5] = C["outline_soft"]
    out[d <= 10.5] = C[dark]
    out[d <= 9.0] = C[mid]
    out[(d <= 9.0) & ((xs - 12) + (ys - 12) < -6)] = C[light]
    rows, key = SYMBOLS[name]
    sym = np.full((len(rows), len(rows[0])), TRANSPARENT, np.int16)
    _stamp(sym, rows, key if earned else {k: LOCKED[2] if i % 2 else LOCKED[0] for i, k in enumerate(key)}, 0, 0)
    y0, x0 = 12 - len(rows) // 2, 12 - len(rows[0]) // 2
    region = out[y0:y0 + sym.shape[0], x0:x0 + sym.shape[1]]
    region[sym >= 0] = sym[sym >= 0]
    return out


# ---------------------------------------------------------------- export
def _png(indexed: np.ndarray, path: Path, scale: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    big = np.kron(indexed, np.ones((scale, scale), dtype=np.int16)) if scale > 1 else indexed
    Image.fromarray(to_rgba(big, "afternoon"), "RGBA").save(path)


def outputs() -> dict[str, tuple[np.ndarray, int]]:
    out = {"icon.png": (app_icon(), 1), "adaptive-icon.png": (adaptive_foreground(), 1), "splash.png": (splash(), 1),
           "favicon.png": (_place(48, emblem(), _fit(emblem(), 44), 0.5), 1)}
    for name in BADGE_COLOURS:
        for earned in (True, False):
            for scale in (1, 4, 8):
                suffix = "" if earned else "_locked"
                out[f"badges/{name}{suffix}@{scale}x.png"] = (badge(name, earned), scale)
    return out


def build(out_dir: Path = OUT) -> list[Path]:
    paths = []
    for rel, (arr, scale) in outputs().items():
        _png(arr, out_dir / rel, scale)
        paths.append(out_dir / rel)
    return paths


def preview() -> Path:
    """The icon as a launcher would show it (square, squircle, circle), the splash, and the badges."""
    bg = tuple(int(BASE[BACKGROUND][i:i + 2], 16) for i in (1, 3, 5))
    sheet = Image.new("RGBA", (1560, 760), (40, 36, 44, 255))
    icon = Image.fromarray(to_rgba(app_icon(), "afternoon")).resize((240, 240), Image.NEAREST)
    fg = Image.fromarray(to_rgba(adaptive_foreground(), "afternoon")).resize((240, 240), Image.NEAREST)
    ys, xs = np.mgrid[0:240, 0:240]
    circle = Image.fromarray(((np.hypot(xs - 120, ys - 120) <= 120) * 255).astype(np.uint8))
    squircle = Image.fromarray(((np.abs((xs - 120) / 120) ** 4 + np.abs((ys - 120) / 120) ** 4 <= 1) * 255).astype(np.uint8))
    sheet.alpha_composite(icon, (20, 20))
    for k, mask in enumerate((squircle, circle)):
        tile = Image.new("RGBA", (240, 240), (*bg, 255))
        tile.alpha_composite(fg)
        sheet.paste(tile, (280 + 260 * k, 20), mask)
    splash_img = Image.new("RGBA", (300, 300), (*bg, 255))
    splash_img.alpha_composite(Image.fromarray(to_rgba(splash(), "afternoon")).resize((300, 300), Image.NEAREST))
    sheet.alpha_composite(splash_img, (820, 0))
    for k, name in enumerate(BADGE_COLOURS):
        for j, earned in enumerate((True, False)):
            b = Image.fromarray(to_rgba(np.kron(badge(name, earned), np.ones((8, 8), dtype=np.int16)), "afternoon"))
            sheet.alpha_composite(b, (40 + 230 * k + 0, 340 + 210 * j))
    path = PREVIEWS / "app_icons.png"
    sheet.save(path)
    return path


def main() -> None:
    paths = build()
    print(f"{len(paths)} files -> {OUT}\npreview -> {preview()}")


if __name__ == "__main__":
    main()
