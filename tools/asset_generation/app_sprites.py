"""Sprites the app shows outside the isometric scene (D-111), drawn by the kit's own code:

    .venv\\Scripts\\python -m tools.asset_generation.app_sprites    # -> assets/app/sprites/

React Native scales images smoothly, which blurs pixel art (it has no nearest-neighbour option;
Skia will, with the Home scene). So these are cut out and enlarged here, nearest-neighbour, and the
phone shows them at about one image pixel per screen pixel:
  plant_<stage>.png            the savings plant at each stage (the Money screen's progress row)
  crop_<plant>_<stage>.png      each bed plant at each stage (the Home cards' seed picker, D-115)
  jar_<fill>.png                the coin jar at each fill (the Home coin jar card, D-115)
  decor_<item>.png, tree_<stage>.png, chicken.png   the Home extras' picker (D-120): each decoration
                                (a room one by its first piece), the tree's 7 stages, a chicken
  badge_<name>[_locked|_small].png   the game's three badges, earned or not yet (the Home points panel,
                                D-127; app_icons.py draws them), and a half-size earned one for the pill
in each time of day, plus sprites.json (each sprite's files and size). Run it after the kit changes:
the art itself still comes only from characters.py and furniture.py. (The avatar portraits are no
longer cut here: since D-125 the app paints them with Skia from the atlas, in the user's skin tone and
glasses, through the same PORTRAIT_BOX, which app/src/lib/character.ts repeats. A sprite no longer
made is removed from assets/app/sprites/ when this runs.)

It also packs the isometric kit into one atlas per time of day (D-114): assets/app/atlas/<time>.png
and atlas.json, {piece: [x, y, w, h, ox, oy]}, each piece's opaque pixels at (x, y) in the atlas,
w x h, which sit at (ox, oy) on the piece's own canvas. The Home scene draws sub-rectangles of three
images instead of naming 1,224 files (Metro ran out of file handles), and its taps use the same boxes,
so they find the piece really drawn under the finger rather than its mostly empty canvas.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from engine.game import load_game

from .palette import TIMES, TRANSPARENT, to_rgba

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "assets" / "app" / "sprites"
PORTRAIT_BOX = (16, 66, 64, 114)        # x0, y0, x1, y1 on the 80 x 152 canvas: hair, face, shoulders
PLANT_SCALE = 3
BADGE_SCALE = 4                         # 24 x 24 medal -> 96 px (about 35 dp on a 2.75x phone); _small is x2
TILE_PX = 112                           # the Home extras' tiles: about 40 dp tall on a 2.75x phone


def enlarge(indexed: np.ndarray, k: int) -> np.ndarray:
    """Nearest-neighbour: every art pixel becomes a k x k block."""
    return np.repeat(np.repeat(indexed, k, axis=0), k, axis=1)


def trim(indexed: np.ndarray) -> np.ndarray:
    """Cut to the opaque pixels (the kit's canvases are mostly empty, for placing in the room)."""
    ys, xs = np.nonzero(indexed != TRANSPARENT)
    return indexed[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def sprites() -> dict[str, np.ndarray]:
    out = {}
    from .kit import PIECES                                             # the kit's savings plant (D-84)
    plants = {p.name: p for p in PIECES if p.name.startswith("savings_plant_") and not p.name.endswith("_droop")}
    for name in sorted(plants):
        out[f"plant_{name.rsplit('_', 1)[1]}"] = enlarge(trim(plants[name].render()), PLANT_SCALE)
    by_name = {p.name: p for p in PIECES}
    for plant in load_game()["garden"]["plants"]:                       # the bed plants (D-86) and the jar
        for stage in ("seedling", "young", "full"):
            out[f"crop_{plant}_{stage}"] = enlarge(trim(by_name[f"plant_{plant}_{stage}"].render()), PLANT_SCALE)
    for fill in range(len(load_game()["coin_jar_fills_at_cushion"]) + 1):
        out[f"jar_{fill}"] = enlarge(trim(by_name[f"coin_jar_table_{fill}"].render()), PLANT_SCALE)
    from .scenes import ROOM_DECOR                                       # the Home extras' picker (D-120)
    decor = load_game()["decorations"]
    for item in decor["room"]:                                           # a room decoration's first piece
        out[f"decor_{item}"] = tile(by_name[ROOM_DECOR[item][1][0][1]].render())
    for item in decor["garden"]:
        out[f"decor_{item}"] = tile(by_name[item].render())
    for name in sorted(n for n in by_name if n.startswith("tree_") and not n.endswith("_droop")):
        out[f"tree_{name.split('_')[1]}"] = tile(by_name[name].render())
    out["chicken"] = tile(by_name["chicken_idle_0"].render())
    from .app_icons import BADGE_COLOURS, badge                          # the game's badges (D-127)
    for name in BADGE_COLOURS:
        out[f"badge_{name}"] = enlarge(badge(name), BADGE_SCALE)
        out[f"badge_{name}_locked"] = enlarge(badge(name, earned=False), BADGE_SCALE)
        out[f"badge_{name}_small"] = enlarge(badge(name), BADGE_SCALE // 2)
    return out


def tile(indexed: np.ndarray, target: int = TILE_PX, most: int = 6) -> np.ndarray:
    """Trimmed and enlarged by a whole number so it stands about `target` px tall: the picker's tiles
    look alike in size whatever the piece (a lantern or a fountain), and stay crisp."""
    art = trim(indexed)
    return enlarge(art, max(1, min(most, round(target / art.shape[0]))))


def build(out: Path = OUT) -> dict:
    index = {}
    made = sprites()
    for t in TIMES:                                                      # a sprite no longer made goes too
        for old in (out / t).glob("*.png") if (out / t).is_dir() else []:
            if old.stem not in made:
                old.unlink()
    for name, idx in made.items():
        files = {}
        for t in TIMES:
            rel = Path(t) / f"{name}.png"
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(to_rgba(idx, t), "RGBA").save(out / rel)
            files[t] = rel.as_posix()
        index[name] = {"files": files, "size": [int(idx.shape[1]), int(idx.shape[0])]}
    doc = {"made_by": "tools/asset_generation/app_sprites.py (D-111)", "plant_scale": PLANT_SCALE, "sprites": index}
    (out / "sprites.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return doc


KIT = ROOT / "assets" / "isometric"
ATLAS = ROOT / "assets" / "app" / "atlas"
ATLAS_W = 1024                          # one page per time of day; the kit's opaque pixels need ~1.1 Mpx
GUTTER = 1                              # a transparent pixel between pieces


def piece_boxes() -> dict[str, tuple[int, int, int, int]]:
    """{piece: (x0, y0, x1, y1)} opaque bounding box on its canvas (the afternoon PNG; every time of day
    has the same shape). A fully transparent piece gets (0, 0, 0, 0)."""
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    return {p["name"]: Image.open(KIT / p["files"]["afternoon"]).getchannel("A").getbbox() or (0, 0, 0, 0)
            for p in manifest["pieces"]}


def atlas_layout(boxes: dict) -> tuple[dict[str, list[int]], int]:
    """Shelf packing, tallest first: rows left to right, a new row when one is full.
    Returns {piece: [x, y, w, h, ox, oy]} and the page height. O(n log n)."""
    order = sorted(boxes, key=lambda n: (-(boxes[n][3] - boxes[n][1]), -(boxes[n][2] - boxes[n][0]), n))
    out, x, y, row = {}, 0, 0, 0
    for n in order:
        x0, y0, x1, y1 = boxes[n]
        w, h = x1 - x0, y1 - y0
        if w == 0 or h == 0:
            out[n] = [0, 0, 0, 0, 0, 0]
            continue
        if x + w > ATLAS_W:
            x, y, row = 0, y + row + GUTTER, 0
        out[n] = [x, y, w, h, x0, y0]
        x, row = x + w + GUTTER, max(row, h)
    return out, y + row


def build_atlas(out: Path = ATLAS) -> dict:
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    layout, height = atlas_layout(piece_boxes())
    out.mkdir(parents=True, exist_ok=True)
    for t in TIMES:
        page = Image.new("RGBA", (ATLAS_W, height), (0, 0, 0, 0))
        for p in manifest["pieces"]:
            x, y, w, h, ox, oy = layout[p["name"]]
            if w:
                page.paste(Image.open(KIT / p["files"][t]).convert("RGBA").crop((ox, oy, ox + w, oy + h)), (x, y))
        page.save(out / f"{t}.png")
    doc = {"made_by": "tools/asset_generation/app_sprites.py (D-114)", "size": [ATLAS_W, height],
           "files": {t: f"{t}.png" for t in TIMES}, "pieces": layout}
    (out / "atlas.json").write_text(json.dumps(doc), encoding="utf-8")
    return doc


def main() -> None:
    doc = build()
    print(f"{len(doc['sprites'])} sprites x {len(TIMES)} times -> {OUT}")
    a = build_atlas()
    print(f"atlas {a['size'][0]} x {a['size'][1]} px, {len(a['pieces'])} pieces x {len(TIMES)} times -> {ATLAS}")


if __name__ == "__main__":
    main()
