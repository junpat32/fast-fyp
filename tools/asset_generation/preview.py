"""Previews (style guide §15): contact sheet, phone-screen alignment scene (+ grid overlay),
garden levels, time of day. Scenes are drawn from the PNG files on disk (what the app will load),
laid out by scenes.py. Labels appear only in the previews, never inside the asset PNGs.

Phone frame: 540 x 1200 art pixels = the Redmi Note 11 Pro 5G screen (1080 x 2400) at 2x, the
fit-to-width view (D-58). Zoom and panning are decided in the app (T-16).
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .geometry import cell_screen, diamond_mask
from .scenes import LEVEL_NAMES, MAX_BED_STEPS, home_scene

ROOT = Path(__file__).resolve().parents[2]
KIT = ROOT / "assets" / "isometric"
PREVIEWS = Path(__file__).resolve().parent / "previews"
PHONE = (540, 1200)
ROOM_TOP = (270, 330)            # where the room's back corner (cell (0, 0) top vertex) sits on screen


def _load(manifest, name, time="afternoon"):
    e = next(p for p in manifest["pieces"] if p["name"] == name)
    return Image.open(KIT / e["files"][time]).convert("RGBA"), tuple(e["footprint_origin"])


def _checker(w, h, s=8):
    ys, xs = np.mgrid[0:h, 0:w]
    v = np.where(((xs // s) + (ys // s)) % 2 == 0, 226, 240).astype(np.uint8)
    return Image.fromarray(np.dstack([v, v, v, np.full_like(v, 255)]), "RGBA")


def _crop(img):
    bbox = img.getbbox()
    return img.crop((max(bbox[0] - 2, 0), max(bbox[1] - 2, 0), bbox[2] + 2, bbox[3] + 2))


def contact_sheet(manifest, scale=3, per_row=8, path=None):
    """One-cell pieces at 3x; multi-cell pieces (houses, long props) at 1x so the sheet stays usable."""
    font = ImageFont.load_default()
    items = []
    for p in manifest["pieces"]:
        img = _crop(_load(manifest, p["name"])[0])
        s = scale if p["cells"] == [1, 1] else 1
        items.append((p["name"], img.resize((img.width * s, img.height * s), Image.NEAREST)))
    scale = 1
    cw = max(i.width for _, i in items) * scale + 16
    ch = max(i.height for _, i in items) * scale + 30
    rows = (len(items) + per_row - 1) // per_row
    sheet = _checker(cw * per_row, ch * rows)
    d = ImageDraw.Draw(sheet)
    for k, (name, img) in enumerate(items):
        x, y = (k % per_row) * cw, (k // per_row) * ch
        big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
        sheet.alpha_composite(big, (x + (cw - big.width) // 2, y + ch - 22 - big.height))
        d.text((x + 4, y + ch - 16), name, fill=(40, 30, 20, 255), font=font)
    sheet.save(path or PREVIEWS / "contact_sheet.png")
    return sheet


def _blit(dst: np.ndarray, src: np.ndarray, x: int, y: int) -> None:
    """Copy the opaque pixels of src onto dst at (x, y), clipped to dst (the app does the same)."""
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x0 >= x1 or y0 >= y1:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x]
    m = s[..., 3] == 255
    dst[y0:y1, x0:x1][m] = s[m]


class Kit:
    def __init__(self, manifest, time):
        self.time = time
        self.entries = {p["name"]: p for p in manifest["pieces"]}
        self.cache = {}

    def get(self, name):
        """A piece's pixels and footprint origin; "name|flip" = mirrored (its footprint turns from
        W x D into D x W, so the origin moves to w - x - 64)."""
        if name not in self.cache:
            base, _, flip = name.partition("|")
            e = self.entries[base]
            img = np.asarray(Image.open(KIT / e["files"][self.time]).convert("RGBA"))
            ox, oy = e["footprint_origin"]
            if flip:
                img, ox = img[:, ::-1], img.shape[1] - ox - 64
            self.cache[name] = (img, (ox, oy))
        return self.cache[name]


def phone_scene(manifest, level, time="afternoon", grid=False, size=PHONE, room_top=ROOM_TOP,
                scene=None) -> Image.Image:
    W, H = size
    ox, oy = room_top[0] - 32, room_top[1]               # map origin = cell (0, 0) box
    kit, sc = Kit(manifest, time), scene or home_scene(level)
    img = np.zeros((H, W, 4), np.uint8)
    s_range = range(math.floor((-oy - 32) / 16), math.ceil((H - oy) / 16) + 1)
    t_range = range(math.floor((-ox - 64) / 32), math.ceil((W - ox) / 32) + 1)
    cells = [((s + t) // 2, (s - t) // 2) for s in s_range for t in t_range if (s + t) % 2 == 0]
    for gx, gy in cells:                                 # every visible cell gets a ground tile
        tile, (fx, fy) = kit.get(sc["ground"].get((gx, gy), sc["default"]))
        sx, sy = cell_screen(gx, gy)
        _blit(img, tile, ox + sx - fx, oy + sy - fy)
    for (gx, gy), name in sc.get("decals", []):          # floor overlays (rugs) before any structure
        piece, (fx, fy) = kit.get(name)
        sx, sy = cell_screen(gx, gy)
        _blit(img, piece, ox + sx - fx, oy + sy - fy)
    if grid:
        dm = diamond_mask()
        pad = np.pad(dm, 1)
        edge = dm & (~pad[1:-1, 2:] | ~pad[1:-1, :-2])
        g = np.zeros((32, 64, 4), np.uint8)
        g[edge] = (255, 0, 255, 255)
        for gx, gy in cells:
            sx, sy = cell_screen(gx, gy)
            _blit(img, g, ox + sx, oy + sy)
    for (gx, gy), name in sc["background"] + sc["structs"]:     # neighbourhood first: it is behind the plot
        piece, (fx, fy) = kit.get(name)
        sx, sy = cell_screen(gx, gy)
        _blit(img, piece, ox + sx - fx, oy + sy - fy)
    return Image.fromarray(img, "RGBA")


def _strip(frames, labels, gap=12, band=34):
    font = ImageFont.load_default(size=18)
    w, h = frames[0].size
    out = Image.new("RGBA", (len(frames) * w + (len(frames) - 1) * gap, h + band), (40, 36, 44, 255))
    d = ImageDraw.Draw(out)
    for k, (f, label) in enumerate(zip(frames, labels)):
        x = k * (w + gap)
        out.alpha_composite(f, (x, band))
        d.text((x + 8, 8), label, fill=(240, 232, 216, 255), font=font)
    return out


ROOM_CROP = (36, 210, 504, 600)          # the 7 x 7 room on the phone screen, walls included


def room_view(manifest, room, time="afternoon", garden=0, zoom=2) -> Image.Image:
    """The room at a room level, cropped from the phone screen and enlarged for review."""
    img = phone_scene(manifest, garden, time, scene=home_scene(garden, room_state=room)).crop(ROOM_CROP)
    return img.resize((img.width * zoom, img.height * zoom), Image.NEAREST)


def object_strip(manifest, names, labels, zoom=4, time="afternoon") -> Image.Image:
    """Close-ups of interactive-object states (coin jar fills, savings plant stages)."""
    crops = [_crop(_load(manifest, n, time)[0]) for n in names]
    w = max(c.width for c in crops) * zoom + 24
    h = max(c.height for c in crops) * zoom + 24
    frames = []
    for c in crops:
        f = _checker(w, h)
        big = c.resize((c.width * zoom, c.height * zoom), Image.NEAREST)
        f.alpha_composite(big, ((w - big.width) // 2, h - 12 - big.height))
        frames.append(f)
    return _strip(frames, labels, band=30)


def room_previews(manifest):
    """Batch 2 review (D-84): the room at each built room level, three times of day; the states of
    the interactive objects close up."""
    from .scenes import ROOM_LAYOUT, ROOM_LEVEL_NAMES
    for lv in sorted(ROOM_LAYOUT):
        times = ("morning", "afternoon", "night")
        room = {"level": lv, "jar": 2, "plant": 2}
        _strip([room_view(manifest, room, t) for t in times],
               [f"{ROOM_LEVEL_NAMES[lv]} - {t}" for t in times]).save(PREVIEWS / f"room_level_{lv}.png")
    _strip([room_view(manifest, {"level": lv, "jar": min(lv - 1, 4), "plant": min(lv - 1, 4)}, zoom=1)
            for lv in sorted(ROOM_LAYOUT)], [ROOM_LEVEL_NAMES[lv] for lv in sorted(ROOM_LAYOUT)]) \
        .save(PREVIEWS / "room_levels.png")
    jars = [f"coin_jar_table_{k}" for k in range(5)]
    object_strip(manifest, jars, ["0 months", "0.5", "1", "2", "3+"]).save(PREVIEWS / "coin_jar_fills.png")
    plants = [f"savings_plant_{k}" for k in range(5)] + [f"savings_plant_{k}_droop" for k in range(5)]
    labels = ["sprout", "1 month", "2", "3", "6"] + ["droop: sprout", "1", "2", "3", "6"]
    object_strip(manifest, plants, labels, zoom=3).save(PREVIEWS / "savings_plant_stages.png")


def plant_previews(manifest):
    """Bed plants (D-84): every plant x stage, normal and drooping, close up; and a planted bed in
    the G2 garden by day and night, then the complete G4 bed with a mix of stages."""
    from .garden_plants import STAGES, TIER_1_2
    from .scenes import bed_cells
    for droop, fname in (("", "bed_plants.png"), ("_droop", "bed_plants_droop.png")):
        names = [f"plant_{n}_{s}{droop}" for n in TIER_1_2 for s in STAGES] + [f"plant_free_seedling{droop}"]
        labels = [f"{n.replace('_', ' ')} {s}" for n in TIER_1_2 for s in STAGES] + ["free seedling"]
        object_strip(manifest, names, labels, zoom=3).save(PREVIEWS / fname)
    g2 = sorted(bed_cells(2))
    full = {c: f"plant_{n}_full" for c, n in zip(g2, TIER_1_2)}
    crop = (40, 380, 500, 860)
    times = ("afternoon", "night")
    _strip([phone_scene(manifest, 2, t, scene=home_scene(2, plants=full)).crop(crop) for t in times],
           [f"G2 bed, all six full grown - {t}" for t in times]).save(PREVIEWS / "garden_planted.png")
    from .scenes import MAX_BED_STEPS
    g4 = sorted(bed_cells(4, MAX_BED_STEPS))
    mix = {c: (f"plant_{TIER_1_2[k % 6]}_{STAGES[(k // 6) % 3]}" if k % 7 else "plant_free_seedling")
           for k, c in enumerate(g4)}
    _strip([phone_scene(manifest, 4, "afternoon", scene=home_scene(4, MAX_BED_STEPS, plants=mix)).crop(crop)],
           ["Complete bed: plants at different stages, free seedlings"]).save(PREVIEWS / "garden_bed_mix.png")


def _tone_frame(manifest, name, tone, time="afternoon", glasses=False, crop=(14, 60, 66, 132)):
    """An avatar frame recoloured to a skin tone (the app's palette swap), optionally with glasses."""
    from .palette import NAMES, lut
    rgba = np.asarray(_load(manifest, name, time)[0]).copy()
    if tone is not None:                          # swap the three skin colours: the base table -> the tone's
        base, new = lut(time), lut(time, tone)
        for n in ("skin_light", "skin_mid", "skin_dark"):
            i = NAMES.index(n)
            m = (rgba[..., :3] == base[i, :3]).all(axis=-1) & (rgba[..., 3] == 255)
            rgba[m, :3] = new[i, :3]
    img = Image.fromarray(rgba, "RGBA")
    if glasses:
        img.alpha_composite(_load(manifest, "glasses_front", time)[0])
    return img.crop(crop)


def _tile_row(imgs, zoom, bg=(175, 121, 80, 255), gap=4):
    w, h = imgs[0].size
    out = Image.new("RGBA", (len(imgs) * (w + gap) + gap, h + 2 * gap), bg)
    for k, im in enumerate(imgs):
        out.alpha_composite(im, (gap + k * (w + gap), gap))
    return out.resize((out.width * zoom, out.height * zoom), Image.NEAREST)


def avatar_previews(manifest):
    """The six avatars (D-86): a lineup; the six skin tones and glasses; every frame of each avatar
    close up; a walking loop; and the avatar's day in the room (sitting on the sofa and at the desk,
    asleep in bed at night)."""
    from .characters import AVATARS
    lineup = [_tone_frame(manifest, f"{lk.name}_{f}", lk.tone) for lk in AVATARS
              for f in ("front_idle_0", "back_idle_0", "mood_celebrating")]
    _strip([_tile_row(lineup[k * 3:k * 3 + 3], 4) for k in range(6)],
           [f"{lk.name.replace('_', ' ')} (tone {lk.tone + 1})" for lk in AVATARS], gap=8).save(PREVIEWS / "avatars_lineup.png")
    tones = [_tile_row([_tone_frame(manifest, f"{lk.name}_front_idle_0", t) for t in range(6)]
                       + [_tone_frame(manifest, f"{lk.name}_front_idle_0", lk.tone, glasses=True)], 3)
             for lk in AVATARS[:3]]
    _strip(tones, ["skin tones 1-6, then glasses"] * 3, gap=8).save(PREVIEWS / "avatar_skin_tones.png")
    for lk in AVATARS:
        names = [p["name"] for p in manifest["pieces"] if p["name"].startswith(lk.name + "_")
                 and "sleep" not in p["name"]]
        object_strip(manifest, names, [n[len(lk.name) + 1:].replace("_", " ") for n in names], zoom=3) \
            .save(PREVIEWS / f"{lk.name}_frames.png")
    seq = ([("front_walk", k % 4, False) for k in range(12)] + [("front_idle", 0, False)] * 4
           + [("front_idle", 1, False)] + [("front_idle", 0, False)] * 3
           + [("back_walk", k % 4, False) for k in range(12)] + [("front_walk", k % 4, True) for k in range(12)]
           + [("back_walk", k % 4, True) for k in range(12)])
    imgs = []
    for kind, k, flip in seq:
        row = [_tone_frame(manifest, f"{lk.name}_{kind}_{k}", lk.tone, crop=(14, 64, 66, 132)) for lk in AVATARS]
        if flip:
            row = [im.transpose(Image.FLIP_LEFT_RIGHT) for im in row]
        imgs.append(_tile_row(row, 3))
    imgs[0].save(PREVIEWS / "avatars_walk.gif", save_all=True, append_images=imgs[1:], duration=140, loop=0)
    # a day in the room (room level 4: sofa, desk, bed); sitting on the sofa is the front frame mirrored
    # (the sofa faces +a), at the desk the back frame mirrored (facing the desk, -b)
    day = [((2, 3), "avatar_04_sit_0|flip", (1, 2), 0.35), ((2, 1), "avatar_03_sit_back_0|flip", (1, 1), 0.25),
           ((4, 4), "avatar_02_front_idle_0", (1, 1), 0.3), ((5, 3), "avatar_05_phone_0", (1, 1), 0.3)]
    night = [((0, 0), "avatar_01_sleep_bed_1", (1, 2), 0.35)]
    starter = [((0, 0), "avatar_06_sleep_mattress_2", (1, 2), 0.35)]
    shots = [(4, "afternoon", day, "Room 4 - afternoon: sofa, desk, phone"),
             (4, "night", night, "Room 4 - night: asleep in bed"),
             (1, "night", starter, "Room 1 - night: asleep on the mattress")]
    _strip([phone_scene(manifest, 0, t, scene=home_scene(0, room_state={"level": lv, "jar": 2, "plant": 2},
                                                         extras=ex)).crop(ROOM_CROP).resize((936, 780), Image.NEAREST)
            for lv, t, ex, _ in shots], [label for *_, label in shots]).save(PREVIEWS / "avatar_in_room.png")


def decoration_previews(manifest):
    """Decorations (D-86): the room with every room decoration; the garden decorations close up and
    placed on the G4 lawn with the tree; the tree's stages; tier 3-4 plants; chickens."""
    from .garden_decor import DECOR
    from .garden_plants import STAGES, TIER_3_4
    from .garden_tree import STAGES as TREE_STAGES
    from .scenes import TREE_SPOT, bed_cells, decor_spots
    decor = ["dining_set", "storage_cabinet", "curtains_sage", "rug_blue", "wall_art_kampung", "wall_art_flowers",
             "desk_plant"]
    shots = [({"level": 5, "jar": 3, "plant": 3, "decor": decor}, "afternoon", "Room 5 with every kind of decoration"),
             ({"level": 5, "jar": 3, "plant": 3, "decor": decor}, "night", "night"),
             ({"level": 1, "jar": 0, "plant": 0, "decor": ["desk_plant", "curtains_peach", "rug_green"]}, "afternoon",
              "Room 1 with a desk plant, curtains, a rug")]
    _strip([room_view(manifest, rs, t) for rs, t, _ in shots], [label for *_, label in shots]) \
        .save(PREVIEWS / "room_decorations.png")
    names = [n for n, *_ in DECOR]
    object_strip(manifest, names, [n.replace("_", " ") for n in names], zoom=3).save(PREVIEWS / "garden_decor_pieces.png")
    object_strip(manifest, names, [n.replace("_", " ") for n in names], zoom=3, time="night") \
        .save(PREVIEWS / "garden_decor_pieces_night.png")
    used, extras = set(), [(TREE_SPOT, "tree_6_flowering", (2, 2), 0)]
    for name, _, size, _ in DECOR:                  # each on its first suggested spot, kept a cell apart
        spot = decor_spots(4, size, used)[0]
        used |= {(spot[0] + i, spot[1] + j) for i in range(-1, size[0] + 1) for j in range(-1, size[1] + 1)}
        extras.append((spot, name, size, 0))
    plants = {c: f"plant_{TIER_3_4[k % 4]}_full" for k, c in enumerate(sorted(bed_cells(4)))}
    crop = (0, 300, 540, 960)
    _strip([phone_scene(manifest, 4, t, scene=home_scene(4, plants=plants, extras=extras)).crop(crop)
            for t in ("afternoon", "night")], ["G4: the tree, decorations on suggested spots, tier 3-4 plants",
                                              "night: lamp and lantern glow"]).save(PREVIEWS / "garden_decorated.png")
    trees = [f"tree_{k}_{s}" for k, s in enumerate(TREE_STAGES)]
    object_strip(manifest, trees + [t + "_droop" for t in trees], [s for s in TREE_STAGES]
                 + [f"droop: {s}" for s in TREE_STAGES], zoom=2).save(PREVIEWS / "tree_stages.png")
    for droop, fname in (("", "bed_plants_tier34.png"), ("_droop", "bed_plants_tier34_droop.png")):
        pn = [f"plant_{n}_{s}{droop}" for n in TIER_3_4 for s in STAGES]
        object_strip(manifest, pn, [f"{n.replace('_', ' ')} {s}" for n in TIER_3_4 for s in STAGES], zoom=3) \
            .save(PREVIEWS / fname)
    chick = [p["name"] for p in manifest["pieces"] if p["name"].startswith("chicken_")]
    object_strip(manifest, chick, [n[8:].replace("_", " ") for n in chick], zoom=4).save(PREVIEWS / "chickens.png")


def main():
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((KIT / "manifest.json").read_text(encoding="utf-8"))
    contact_sheet(manifest)
    room_previews(manifest)
    plant_previews(manifest)
    avatar_previews(manifest)
    decoration_previews(manifest)
    for grid, fname in ((False, "alignment_test.png"), (True, "alignment_test_grid.png")):
        s = phone_scene(manifest, 3, grid=grid)          # G3 shows the most piece types together
        s.resize((s.width * 2, s.height * 2), Image.NEAREST).save(PREVIEWS / fname)   # = phone pixels
    levels = range(5)
    _strip([phone_scene(manifest, lv) for lv in levels], [LEVEL_NAMES[lv] for lv in levels]) \
        .save(PREVIEWS / "garden_levels.png")
    times = ("morning", "afternoon", "night")
    _strip([phone_scene(manifest, 3, t) for t in times], list(times)).save(PREVIEWS / "time_of_day.png")
    mid = MAX_BED_STEPS // 2
    growth = [(0, "G4 - 6 months"), (mid, f"{6 + mid} months"),
              (MAX_BED_STEPS, f"Bed complete - {6 + MAX_BED_STEPS} months")]
    _strip([phone_scene(manifest, 4, scene=home_scene(4, bed_steps=k)) for k, _ in growth],
           [label for _, label in growth]).save(PREVIEWS / "garden_growth.png")
    # the whole garden journey in one strip, cropped to the garden (qualifying months, D-68)
    journey = [(1, 0, "Opens (0)"), (2, 0, "G2 (2)"), (3, 0, "G3 (4)"), (4, 0, "G4 (6)"),
               (4, mid, f"{6 + mid} months"), (4, MAX_BED_STEPS, f"Complete ({6 + MAX_BED_STEPS})")]
    _strip([phone_scene(manifest, lv, scene=home_scene(lv, bed_steps=k)).crop((0, 300, 540, 900))
            for lv, k, _ in journey], [label for *_, label in journey]).save(PREVIEWS / "garden_journey.png")
    print(f"previews -> {PREVIEWS}")


if __name__ == "__main__":
    main()
