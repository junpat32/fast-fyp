"""Animated creatures (D-66), first test: an ayam kampung (village chicken).

Organic shapes look blocky as boxes, so creatures are drawn as small pixel templates (one letter
per palette colour) for each body part. A pose places the parts with pixel offsets, so walking
(leg swap + body bob), pecking (head down) and blinking come from moving parts, not redrawing.
The usual pipeline then applies: palette indices, automatic soft outline, mirroring for the
opposite direction, and the three time-of-day palettes.

Scale (D-59): 1 m of height = 39 px. A real chicken is ~0.4 m (16 px); animals are drawn at
about 1.5x real size (this one ~27 px; Patrick, D-66) so they read on a phone, in the same
exaggerated spirit as the chibi character. Bigger sizes are redrawn, never stretched: stretching
pixel art by 1.5 makes uneven pixels.

    .venv\\Scripts\\python -m tools.asset_generation.creatures   # writes the test GIFs to previews/
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from .geometry import outline
from .palette import IDX, TRANSPARENT, to_rgba

C = IDX
# beak and near leg in the coin gold (D-86): same colour as brass by day, but brass glints at night
# (lamp glint, NIGHT_OVERRIDES) and only lamps and lanterns may glow (spec §1, E3)
KEY = {"r": "accent_red", "y": "coin_mid", "k": "outline", "h": "wood_light",
       "H": "wood_warm", "M": "wood_mid", "S": "wood_dark", "G": "green_dark", "D": "outline_soft",
       "L": "coin_mid", "l": "sand_dark", "z": "wall_cream"}
ZED = ["zzzzz", "...z.", "..z..", ".z...", "zzzzz"]      # the sleeping "z", drifting up

# Drawn at 1.5x a real chicken (D-66: Patrick chose bigger animals): ~27 px tall.
HEAD = ["...r.r....",
        "..rrrrr...",
        "..rrrrrr..",
        "..hhhhhh..",
        ".hhHHHHHh.",
        "yhHkHHHHH.",
        "yyyHHHHHH.",
        ".yHHHHHHH.",
        ".rrHHHHHH.",
        ".rrrHHHH..",
        "..rr.HH..."]
# body and tail as one shape: the back sweeps up into dark green-black tail feathers
BODY = ["................GD...",
        "...............GGD...",
        "..............GGGDD..",
        ".............GGGGDD..",
        "....hhhhhhh..GGGGDD..",
        "..hhHHHHHHHhhGGGGDD..",
        ".hHHHHHHHHHHHGGGGD...",
        "hHHHHHHMMMMMMMGGGD...",
        "HHHHHHMMMMMMMMMGGD...",
        "HHHHHMMMMMMMMMMSGD...",
        "HHHHHMMMMMMMMMSSDD...",
        ".HHHHHMMMMMMMSSSD....",
        ".HHHHHHMMMMMSSSS.....",
        "..SHHHHHHHHSSSS......",
        "...SSHHHHHSSSS.......",
        ".....SSSSSSS........."]
# legs: near leg L (lit), far leg l (shaded); 3 rows under the body
LEGS = {"stand": ["........L...l.......", "........L...l.......", ".......LL..ll......."],
        "stride_a": ["......L......l......", ".....L........l.....", "....LL........ll...."],   # near leg forward
        "pass": ["........Ll..........", "........Ll..........", ".......LLll........."],
        "stride_b": ["......l......L......", ".....l........L.....", "....ll........LL...."]}   # far leg forward

W, H = 30, 29          # canvas; feet at FOOT
FOOT = (14, 28)
BODY_AT = (6, 10)
assert len({len(r) for r in HEAD}) == len({len(r) for r in BODY}) == 1


def _stamp(canvas, rows, x, y):
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != "." and 0 <= y + j < canvas.shape[0] and 0 <= x + i < canvas.shape[1]:
                canvas[y + j, x + i] = C[KEY[ch]]


def stamp_zed(canvas, x, y, rows=ZED):
    """The sleeping "z" (animals and avatars, D-87): drawn after the outline in the symbol colour
    that stays readable at night, with its own thin soft outline round it on empty pixels only."""
    mark = np.zeros(canvas.shape, bool)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != "." and 0 <= y + j < canvas.shape[0] and 0 <= x + i < canvas.shape[1]:
                mark[y + j, x + i] = True
    pad = np.pad(mark, 1)
    ring = ~mark & (pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]) & (canvas < 0)
    canvas[mark] = C["zed"]
    canvas[ring] = C["outline_soft"]


def chicken(legs="stand", bob=0, head=(2, 5), blink=False, asleep=False, zed=None) -> np.ndarray:
    """One frame facing left (towards -b on screen: walking down-left along +gy). asleep: sitting
    on the ground (no legs), head tucked low, eyes shut; zed = (x, y) of the drifting "z"."""
    canvas = np.full((H, W), TRANSPARENT, np.int16)
    sit = 3 if asleep else 0
    _stamp(canvas, BODY, BODY_AT[0], BODY_AT[1] + sit - bob)
    head_rows = [r.replace("k", "S") for r in HEAD] if (blink or asleep) else HEAD
    _stamp(canvas, head_rows, head[0], head[1] - bob)
    if not asleep:
        _stamp(canvas, LEGS[legs], 5, 26)
    outline(canvas, C["outline_soft"], "full")
    if zed is not None:
        stamp_zed(canvas, *zed)
    return canvas


def chicken_frames() -> dict[str, list[np.ndarray]]:
    walk = [chicken("stride_a", head=(1, 5)), chicken("pass", bob=1),
            chicken("stride_b", head=(1, 5)), chicken("pass", bob=1)]
    peck = [chicken("stand", head=(1, 10)), chicken("stand", head=(0, 15)),
            chicken("stand", head=(0, 15)), chicken("stand", head=(1, 10))]
    idle = [chicken("stand"), chicken("stand", blink=True)]
    # night (19:00-05:59, D-52): asleep, slow breathing (4 frames in, 4 out), a "z" drifting up
    sleep = [chicken(asleep=True, head=(4, 12), bob=1 if i >= 4 else 0,
                     zed=(2 + i // 3, 6 - i // 2) if i >= 2 else None) for i in range(8)]
    return {"walk": walk, "peck": peck, "idle": idle, "sleep": sleep}


# ---------------------------------------------------------------- kit pieces (D-86)
KIT_FOOT = (40, 127)            # the feet's row sits on the cell centre (a = b = 8), like the avatars'


def kit_frame(frame: np.ndarray) -> np.ndarray:
    """A chicken frame on the 1 x 1 struct canvas, feet at the cell centre, with the small flat shadow
    of characters and animals (spec §1, E2): 2 rows of recess, only where nothing else is drawn."""
    from .geometry import STRUCT_H, STRUCT_W
    out = np.full((STRUCT_H, STRUCT_W), TRANSPARENT, np.int16)
    x0, y0 = KIT_FOOT[0] - FOOT[0], KIT_FOOT[1] - FOOT[1]
    out[y0:y0 + H, x0:x0 + W] = frame
    ys, xs = np.mgrid[0:STRUCT_H, 0:STRUCT_W] + 0.5
    shadow = (((xs - 40) / 7.5) ** 2 + ((ys - 128) / 1.0) ** 2 <= 1) & (out < 0)
    out[shadow] = C["recess"]
    return out


def _kit_pieces():
    from .pieces import Piece
    notes = {"walk": "walking (down-left; mirror for the other directions)", "peck": "pecking at the ground",
             "idle": "standing, blinking", "sleep": "asleep at the coop's sleep cell at night (19:00-05:59)"}
    out = []
    for kind, n in (("walk", 4), ("peck", 4), ("idle", 2), ("sleep", 8)):
        for k in range(n):
            out.append(Piece(f"chicken_{kind}_{k}", "garden/animals", "struct",
                             (lambda kind=kind, k=k: kit_frame(chicken_frames()[kind][k])),
                             f"ayam kampung (D-66), {notes[kind]}, frame {k + 1} of {n}"))
    return out


ANIMAL_PIECES = _kit_pieces()


# ---------------------------------------------------------------- test previews
def _rgba(frame, time, flip):
    img = to_rgba(frame[:, ::-1] if flip else frame, time)
    return img


def _blit(dst, src, x, y):
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x0 < x1 and y0 < y1:
        s = src[y0 - y:y1 - y, x0 - x:x1 - x]
        m = s[..., 3] == 255
        dst[y0:y1, x0:x1][m] = s[m]


def _route():
    """A loop on the lawn: (dx, dy) per ground unit and whether the sprite is mirrored (facing right).
    One cell = 16 units; walking along +gy moves (-2, +1) px per unit on screen."""
    legs = [((-2, 1), False), ((2, 1), True), ((2, -1), True), ((-2, -1), False)]
    seq = []
    for (dx, dy), flip in legs:
        seq += [("walk", i, (dx, dy), flip) for i in range(16)]
        seq += [("peck", i, (0, 0), flip) for i in range(4)] * 2
        seq += [("idle", i % 2 if i in (2, 3) else 0, (0, 0), flip) for i in range(4)]
    return seq


def test_gifs(out_dir: Path):
    from .preview import KIT, phone_scene
    frames = chicken_frames()
    # 1) close-up, 6x, on plain lawn colour: judge the drawing
    seq = [("walk", i // 2 % 4, False) for i in range(16)] + [("peck", i, False) for i in range(4)] * 2 \
        + [("idle", 0, False)] * 3 + [("idle", 1, False)] + [("idle", 0, False)] * 2 \
        + [("sleep", i // 2 % 8, False) for i in range(32)]
    lawn = np.array([143, 170, 96, 255], np.uint8)
    imgs = []
    for kind, i, flip in seq:
        bg = np.tile(lawn, (H + 6, W + 6, 1))
        _blit(bg, _rgba(frames[kind][i], "afternoon", flip), 3, 3)
        imgs.append(Image.fromarray(bg, "RGBA").resize(((W + 6) * 6, (H + 6) * 6), Image.NEAREST))
    imgs[0].save(out_dir / "test_chicken_closeup.gif", save_all=True, append_images=imgs[1:], duration=110,
                 loop=0, disposal=2)
    # 2) in the G3 garden at true phone size (2x): walking a loop in front of the coop by day,
    #    asleep at the coop's sleep cell at night (D-67)
    from .preview import ROOM_TOP
    from .scenes import ANIMAL_HOMES
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    sx, sy = ANIMAL_HOMES["chickens"]["sleep"]
    home = (ROOM_TOP[0] + (sx - sy) * 32, ROOM_TOP[1] + (sx + sy) * 16 + 16)    # sleep cell centre, 1x
    for time in ("afternoon", "night"):
        scene = np.asarray(phone_scene(manifest, 3, time)).copy()
        crop = (home[0] - 140, home[1] - 150, home[0] + 130, home[1] + 50)      # coop and lawn, 1x
        x, y = home
        imgs = []
        route = _route() if time != "night" else [("sleep", i % 8, (0, 0), False) for i in range(32)]
        for kind, i, (dx, dy), flip in route:
            if kind == "walk":
                x, y = x + dx, y + dy
                f = frames["walk"][i // 2 % 4]
            else:
                f = frames[kind][i]
            frame = scene.copy()
            _blit(frame, _rgba(f, time, flip), x - (W - 1 - FOOT[0] if flip else FOOT[0]), y - FOOT[1])
            c = frame[crop[1]:crop[3], crop[0]:crop[2]]
            imgs.append(Image.fromarray(c, "RGBA").resize((c.shape[1] * 2, c.shape[0] * 2), Image.NEAREST))
        imgs[0].save(out_dir / f"test_chicken_garden_{time}.gif", save_all=True, append_images=imgs[1:],
                     duration=90 if time != "night" else 220, loop=0, disposal=2)


if __name__ == "__main__":
    from .preview import PREVIEWS
    test_gifs(PREVIEWS)
    print(f"test GIFs -> {PREVIEWS}")
