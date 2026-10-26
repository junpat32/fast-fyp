"""Palettes (style guide §7 + D-52). Pieces are drawn as palette INDICES, then mapped to colours,
so every pixel is an exact palette colour or fully transparent (no anti-aliasing possible).

Base = the style-guide palette (afternoon), plus a few colours in the same families for
glass, kitchen tiles, recesses and paving. Morning and night are explicit transforms of the
base, written out in full to assets/isometric/palettes.json.
"""
from __future__ import annotations

import numpy as np

BASE = {
    # outlines / deep accents (style guide)
    "outline": "#49311F", "outline_soft": "#5B3D28",
    # wood (style guide)
    "wood_dark": "#7A4E2D", "wood_mid": "#A66E3B", "wood_warm": "#C88A4D", "wood_light": "#D9A467",
    "wood_high": "#E8BE83",
    # walls (style guide)
    "wall_cream": "#E8DFC9", "wall_beige": "#D8CDB7", "wall_shadow": "#B9AD98",
    # stone / neutral (style guide + one in-between grey)
    "stone_light": "#C8C6BE", "stone_soft": "#B4B2AA", "stone_mid": "#9D9B94", "stone_dark": "#66635E",
    # garden greens (style guide)
    "green_dark": "#49663A", "green_mid": "#6F8B4E", "green_grass": "#8FAA60", "green_light": "#AFC979",
    # soil (style guide)
    "soil_dark": "#6B4730", "soil_mid": "#8A5D3B", "soil_light": "#A87950",
    # additions in the same families
    "tile_light": "#E9E4D8", "tile_shade": "#D6CFC0", "grout": "#AAA394",
    "glass": "#9DBFCF", "glass_light": "#C9DFE8", "recess": "#3B2A1D",
    "sand_light": "#DCC49A", "sand_mid": "#C6A675", "sand_dark": "#A08159", "brass": "#C9A24A",
    # neighbours (D-59): terracotta roof tiles; one muted fabric/paint accent. Not glass or brass,
    # which change at night (lit windows, lamp glint)
    "roof_light": "#C47A52", "roof_mid": "#A35E3E", "roof_dark": "#7C442D",
    "accent_blue": "#5E7FA3", "accent_blue_dark": "#4A6585",
    # neighbours' wall paint (D-60): muted Malaysian terrace colours, lit + shaded face each
    "house_peach": "#E2C6AA", "house_peach_shade": "#C2A68B",
    "house_sage": "#C6D0B2", "house_sage_shade": "#A6B193",
    "house_blue": "#C0CCD4", "house_blue_shade": "#A0ACB5",
    # creatures (D-66): a clear red for combs and wattles (terracotta disappears against ginger)
    "accent_red": "#C2473B",
    # batch 2 (D-84): a glass jar and coins that do NOT glow at night ("glass" and "brass" change at
    # night for lit windows and lamp glint; a coin jar must not look lit)
    "jar_light": "#D4E3E1", "jar_mid": "#AFC6C4",
    "coin_light": "#E6C761", "coin_mid": "#C9A13E", "coin_dark": "#97752C",
    # lamp shades: the only furniture that glows at night (spec §1, E3; night values below)
    "lamp_shade": "#E8D9AE", "lamp_shade_dark": "#CDBB8E",
    # sky seen through the windows (room level 5) and in pictures; it darkens at night, never glows
    "sky": "#A9C9DB", "sky_light": "#CFE3EC",
    # a lighter top for blue fabric (the sofa, matching the blanket's accent blue)
    "blue_light": "#7E9DBE",
    # flowers (bed plants, D-84): bougainvillea magenta, ixora orange, a deep red for petal shade
    "pink_light": "#E58FB8", "pink_mid": "#C7477F", "pink_dark": "#93305C",
    "orange": "#E07B39", "red_dark": "#8E2E27",
    # characters (spec §7): one skin tone as 3 shades, swapped for the 6 skin-tone choices later;
    # dark hair with a shine
    "skin_light": "#E8B98F", "skin_mid": "#D39A6C", "skin_dark": "#A9714B",
    "hair_dark": "#33251F", "hair_shine": "#5A463C",
    # a soft rose for a tudung; purple (orchids) and jade (jade vine) for tier 3-4 flowers
    "rose_light": "#E9B9C2", "rose_mid": "#D392A0", "rose_dark": "#A86775",
    "purple_light": "#C9A7E0", "purple_mid": "#9A72BE",
    "jade_light": "#8BD8C8", "jade_mid": "#45AE9E",
    # polish (D-87): a plum for avatar 02's long skirt (blue read as jeans); the sleeping "z", a
    # symbol that must stay readable at night (SYMBOL_NIGHT below; it lights nothing)
    "purple_dark": "#7A579E", "purple_deep": "#5C4079",
    "zed": "#F4F1EA",
}
# The 6 skin tones the user chooses from (spec §7): each replaces skin_light / skin_mid / skin_dark.
# Tone 3 is the base palette's own skin, so frames are drawn once and recoloured by palette swap.
SKIN_TONES = [("#F5D5BA", "#E4B996", "#C29170"), ("#EDC3A0", "#DAA67F", "#B47C59"),
              ("#E8B98F", "#D39A6C", "#A9714B"), ("#C98F63", "#B0774D", "#8A5A37"),
              ("#A9714A", "#8F5C39", "#6E4429"), ("#7E5236", "#664029", "#4B2D1C")]
SKIN_NAMES = ("skin_light", "skin_mid", "skin_dark")
NAMES = list(BASE)
IDX = {n: i for i, n in enumerate(NAMES)}
TRANSPARENT = -1
TIMES = ("afternoon", "morning", "night")


def _rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _hex(c) -> str:
    return "#{:02X}{:02X}{:02X}".format(*c)


def _clamp(v) -> int:
    return int(max(0, min(255, round(v))))


def _morning(c):        # warm, golden, slightly brighter
    r, g, b = c
    return _clamp(r * 1.03 + 8), _clamp(g * 1.00 + 3), _clamp(b * 0.88)


def _night(c):          # darker, cooler
    r, g, b = c
    return _clamp(r * 0.48 + 4), _clamp(g * 0.54 + 8), _clamp(b * 0.68 + 30)


NIGHT_OVERRIDES = {"glass": "#E9C46A", "glass_light": "#F6DFA0", "brass": "#D9B45A",   # lit windows, lamp glint
                   "lamp_shade": "#F6D884", "lamp_shade_dark": "#E6BE5E"}              # lamps switched on
# Symbols, not light: the sleeping "z" keeps a pale moonlit white at night so it can still be read
# (the usual night transform made it a dim grey-blue). Cool, never the lamps' warm yellow.
SYMBOL_NIGHT = {"zed": "#DCE6F5"}


def palettes() -> dict[str, dict[str, str]]:
    out = {"afternoon": dict(BASE)}
    out["morning"] = {n: _hex(_morning(_rgb(h))) for n, h in BASE.items()}
    night = {n: _hex(_night(_rgb(h))) for n, h in BASE.items()}
    night.update(NIGHT_OVERRIDES)
    night.update(SYMBOL_NIGHT)
    out["night"] = night
    return out


def skin_tones() -> list[dict[str, list[str]]]:
    """Each skin tone's three colours at each time of day (the app swaps them into the palette)."""
    out = []
    for tone in SKIN_TONES:
        rgb = [_rgb(h) for h in tone]
        out.append({"afternoon": list(tone), "morning": [_hex(_morning(c)) for c in rgb],
                    "night": [_hex(_night(c)) for c in rgb]})
    return out


def lut(time: str, tone: int | None = None) -> np.ndarray:
    """(n + 1) x 4 RGBA table; the last row is transparent (for index -1). tone: a skin tone 0-5
    swapped in for the three skin colours (characters)."""
    p = dict(palettes()[time])
    if tone is not None:
        p.update(zip(SKIN_NAMES, skin_tones()[tone][time]))
    rows = [(*_rgb(p[n]), 255) for n in NAMES] + [(0, 0, 0, 0)]
    return np.array(rows, dtype=np.uint8)


def to_rgba(indexed: np.ndarray, time: str, tone: int | None = None) -> np.ndarray:
    table = lut(time, tone)
    idx = np.where(indexed < 0, len(NAMES), indexed)
    return table[idx]
