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

The chickens are kit pieces (`ANIMAL_PIECES`, built by `tools.asset_generation.build`); the one-off
test GIFs that showed the first chicken (D-66) were retired on 2026-10-26 (D-136).
"""
from __future__ import annotations

import numpy as np

from .geometry import outline
from .palette import IDX, TRANSPARENT

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
