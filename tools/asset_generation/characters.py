"""The chibi avatars (T-22 batch 2; spec §7, D-72, D-84, D-85, D-86).

Six 56 px chibis (a big head on a small body, ~2.2 heads tall) built from parts drawn as shapes on
the pixel grid: shoes, legs or skirt, top, arms, neck, head, hair or tudung, ears, face. A pose moves
the parts (stride, bob, arm swing, raised arms, holding a phone, sitting, lying in bed) and a face
sets the expression, so all six avatars share every pose: an avatar is only a Look (hair or tudung,
clothes). Skin is drawn in the three skin colours of the palette; the user's skin tone (6, spec §7)
is a palette swap of those three (palette.SKIN_TONES), done by the app. Glasses are an overlay
(glasses_front) placed at each front frame's head position (characters.json).

Views (spec §7): FRONT faces down-left (the face turned to the viewer's left), BACK faces up-left;
the other two directions are these mirrored. Lit from the upper left. Soft outline (characters,
spec §1), except round hair, whose own darkest colour is its edge (a brown line round dark hair
looks like a halo). A small flat shadow under standing feet (spec §1, E2). Feet always on the same
base point: the cell's centre.

Frames per avatar: front idle 2 (breathing, blink), front walk 4, back idle 2, back walk 4; the five
moods on the front view (relaxed, calm, focused, concerned_hopeful = engine.game moods, and
celebrating), each with a breathing and a blinking frame for the Home scene's idle (D-116); using a
phone 2; sitting 2 (on the sofa, which faces +a: shown mirrored); asleep in bed 4 for the mattress
and 4 for the bed (at night, 19:00-05:59, like the chickens).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .geometry import STRUCT_H, STRUCT_W, struct_canvas
from .palette import IDX, TRANSPARENT
from .pieces import Piece

C = IDX
OL = C["outline_soft"]
FOOT = (40, 128)                                   # the cell centre on the ground (a = b = 8)
SKIN = ("skin_light", "skin_mid", "skin_dark")
# Proportions (px above the feet): shoes 0-3, legs 3-12, top 12-24, neck, head centre at 39 (26 px
# tall), hair to ~55. Sitting raises the hips to the seat: the sofa's cushions (15 px; seen from the
# front, mirrored) or the desk chair (18 px; seen from the back, at the desk).
HIP, SHOULDER, HEAD_Y, HEAD_R = 12, 24, 39, 13
SEATS = {"front": 15, "back": 18}
# Sitting, the thighs point the way the avatar faces: 4 units (2:1 projection) down-left towards the
# viewer in the front view, up-left away from the viewer (behind the body) in the back view
KNEE = {"front": lambda x, y: (x - 8, y + 4), "back": lambda x, y: (x - 8, y - 4)}
CX = 38.5                                          # the head's centre line


def _grid(w=STRUCT_W, h=STRUCT_H):
    ys, xs = np.mgrid[0:h, 0:w] + 0.5
    return xs, ys


XS, YS = _grid()


@dataclass(frozen=True)
class Look:
    name: str
    who: str
    hair_style: str = "short"                      # short, side_part, bob, ponytail, wavy, tudung
    top: str = "tshirt"                            # tshirt, polo, long, hoodie
    top_colours: tuple = ("green_light", "green_mid", "green_dark")
    lower: str = "jeans"                           # jeans (or trousers: same shape), skirt
    lower_colours: tuple = ("blue_light", "accent_blue", "accent_blue_dark")
    shoes: tuple = ("wall_cream", "stone_soft")
    scarf: tuple = ("rose_light", "rose_mid", "rose_dark")   # tudung colours
    hair: tuple = ("hair_shine", "hair_dark")
    tone: int = 2                                  # suggested skin tone 0-5; the user can pick any


AVATARS = [
    Look("avatar_01", "masculine; short hair; green T-shirt, jeans"),
    Look("avatar_02", "feminine; tudung; long-sleeved top, long skirt, flats", hair_style="tudung", top="long",
         top_colours=("wall_cream", "wall_beige", "wall_shadow"), lower="skirt",
         lower_colours=("purple_mid", "purple_dark", "purple_deep"), shoes=("roof_mid", "roof_dark"), tone=1),
    Look("avatar_03", "masculine; side-parted hair; light-blue polo, khaki trousers", hair_style="side_part",
         top="polo", top_colours=("sky_light", "sky", "accent_blue"),
         lower_colours=("sand_light", "sand_mid", "sand_dark"), shoes=("stone_mid", "stone_dark"), tone=0),
    Look("avatar_04", "feminine; bob with a fringe; mustard T-shirt, jeans", hair_style="bob",
         top_colours=("coin_light", "coin_mid", "coin_dark"), tone=0),
    Look("avatar_05", "feminine; ponytail; terracotta T-shirt, grey trousers", hair_style="ponytail",
         top_colours=("roof_light", "roof_mid", "roof_dark"), lower_colours=("stone_soft", "stone_mid", "stone_dark"),
         tone=4),
    Look("avatar_06", "masculine; wavy hair; sage hoodie, jeans", hair_style="wavy", top="hoodie",
         top_colours=("house_sage", "house_sage_shade", "green_mid"), shoes=("stone_mid", "stone_dark"), tone=3),
]


# ---------------------------------------------------------------- drawing helpers
def _ell(cx, cy, rx, ry, xs=None, ys=None):
    xs, ys = (XS, YS) if xs is None else (xs, ys)
    return ((xs - cx) / rx) ** 2 + ((ys - cy) / ry) ** 2 <= 1


def _rect(x0, y0, x1, y1, xs=None, ys=None):
    xs, ys = (XS, YS) if xs is None else (xs, ys)
    return (xs >= x0) & (xs < x1) & (ys >= y0) & (ys < y1)


def _capsule(x0, y0, x1, y1, r, xs=None, ys=None):
    """A thick line (an arm) from (x0, y0) to (x1, y1), radius r."""
    xs, ys = (XS, YS) if xs is None else (xs, ys)
    dx, dy = x1 - x0, y1 - y0
    t = np.clip(((xs - x0) * dx + (ys - y0) * dy) / max(dx * dx + dy * dy, 1e-9), 0, 1)
    return np.hypot(xs - (x0 + t * dx), ys - (y0 + t * dy)) <= r


def _shade(c, mask, colours, x_lit, x_dark, xs=None):
    """Fill a part: light left of x_lit, dark right of x_dark, mid between (light from the left)."""
    xs = XS if xs is None else xs
    lit, mid, dark = colours
    c[mask] = C[mid]
    c[mask & (xs < x_lit)] = C[lit]
    c[mask & (xs >= x_dark)] = C[dark]


def _px(c, pts, colour):
    for x, y in pts:
        if 0 <= y < c.shape[0] and 0 <= x < c.shape[1]:
            c[y, x] = C[colour]


def _outline(c, hair_mask, feet_y=None):
    """Soft outline on the silhouette; hair keeps its own dark edge; no line under the feet."""
    sil = c >= 0
    pad = np.pad(sil, 1)
    up, down, left, right = pad[:-2, 1:-1], pad[2:, 1:-1], pad[1:-1, :-2], pad[1:-1, 2:]
    edge = sil & (~up | ~left | ~right)
    edge &= ~(sil & ~down & up & left & right)
    c[edge & ~hair_mask] = OL
    c[edge & hair_mask] = C["hair_dark"]


# ---------------------------------------------------------------- the head (every pose uses it)
def _head(c, look, cx, hy, view, xs, ys):
    """Head, hair or tudung, ears. Returns the hair mask (for the outline rule)."""
    head = _ell(cx, hy, HEAD_R - 0.5, HEAD_R, xs, ys)
    cap = _ell(cx + 0.8, hy - 2.2, HEAD_R + 0.6, HEAD_R - 0.6, xs, ys)
    s = look.hair_style
    sk_l, sk_m, _ = SKIN
    c[head] = C[sk_l]
    none = np.zeros(c.shape, bool)
    if s == "tudung":
        wrap = _ell(cx + 0.5, hy - 0.5, HEAD_R + 1.4, HEAD_R + 1.2, xs, ys)
        if view == "front":
            face_m = _ell(cx - 1.5, hy + 2, 8.6, 9.6, xs, ys) & head
            c[face_m & (ys >= hy + HEAD_R - 3)] = C[sk_m]
            tud = (wrap | head) & ~face_m
        else:
            tud = wrap | head
        _shade(c, tud, look.scarf, cx - 6, cx + 6, xs)
        return none
    if s == "wavy":                                                      # bumpy outline of curls
        for k in range(9):
            ang = np.pi * (1.05 + 0.9 * k / 8)
            cap |= _ell(cx + 0.8 + (HEAD_R + 0.2) * np.cos(ang), hy - 2.2 + (HEAD_R - 1) * np.sin(ang), 3.2, 3.0, xs, ys)
    if s == "side_part":
        cap = _ell(cx + 0.8, hy - 2.8, HEAD_R + 0.8, HEAD_R - 0.2, xs, ys)
    bob_hair = _ell(cx + 0.6, hy + 2.5, HEAD_R + 1.2, HEAD_R - 0.5, xs, ys)
    if view == "front":
        fringe = {"short": hy - 9 + 0.42 * (xs - (cx - 13)),
                  "side_part": hy - 3.8 - 0.36 * (xs - (cx - 13)),
                  "bob": hy - 5 + 0.8 * np.sin(xs * 1.7),
                  "ponytail": hy - 9 + 0.04 * (xs - (cx - 2)) ** 2,
                  "wavy": hy - 7 + 1.4 * np.sin(xs * 1.25)}[s]
        if s == "bob":
            face_m = head & (ys >= fringe) & (xs >= cx - 10) & (xs <= cx + 5.4)
            hair = (cap | bob_hair) & ~face_m & (ys <= hy + 9.5)
        else:
            face_m = head & (ys >= fringe) & (xs <= cx + 7.4)
            hair = (cap | head) & ~face_m & (ys <= hy + (5 if s == "side_part" else 7 if s == "wavy" else 6))
        # towards the ear: shade along the head's curve (a crescent), not a straight cut, so the face
        # reads round when shown large (the Future screen's portraits, D-111)
        rim = ((xs - (cx - 3.0)) / (HEAD_R - 1.0)) ** 2 + ((ys - (hy + 1.0)) / (HEAD_R + 2.5)) ** 2
        c[face_m & (xs >= cx + 3) & (rim > 0.78)] = C[sk_m]
        c[face_m & (ys >= hy + HEAD_R - 2.5)] = C[sk_m]                  # under the chin
        c[head & ~face_m & ~hair] = C[sk_m]                              # back of the jaw, below the hair
        ears = [] if s == "bob" else [cx + 8.8]
    else:
        hair = ((cap | bob_hair) & (ys <= hy + 10)) if s == "bob" else ((cap | head) & (ys <= hy + 7))
        c[head & ~hair] = C[sk_m]                                        # the nape
        ears = [] if s == "bob" else [cx - 11.6, cx + 11.6]
    d = ((xs - cx - 0.8) / (HEAD_R + 0.6)) ** 2 + ((ys - hy + 2.2) / (HEAD_R - 0.6)) ** 2
    c[hair] = C[look.hair[1]]
    c[hair & (d > 0.45) & (d < 0.66) & (xs < cx - 1) & (ys < hy - 3)] = C[look.hair[0]]   # shine arc
    for ex in ears:
        ear = _ell(ex, hy + 1.5, 1.7, 2.3, xs, ys)
        c[ear] = C[sk_m]
        hair &= ~ear
    return hair


def _ponytail(c, look, cx, hy, view, xs, ys):
    """Drawn behind the head in the front view (it hangs from the back of the head, which is to the
    right when the face turns left) and over the back in the back view: one smooth tail tapering
    from the tie, as a chain of shrinking circles along a gentle curve."""
    tail = np.zeros(c.shape, bool)
    for t in np.linspace(0, 1, 24):
        if view == "front":
            px, py, r = cx + 12.0 + 3.0 * t - 0.6 * t * t, hy - 1 + 14 * t, 3.5 - 1.7 * t
        else:
            px, py, r = cx + 0.5 + 0.8 * np.sin(t * 2.5), hy + 6 + 13 * t, 2.8 - 1.5 * t
        tail |= np.hypot(xs - px, ys - py) <= r
    c[tail] = C[look.hair[1]]
    lit = tail & (xs < (cx + 13.5 if view == "front" else cx))           # a little shine on the lit side
    c[lit & ((ys - hy) % 4 < 1)] = C[look.hair[0]]
    tie = (cx + 12.4, hy + 0.5) if view == "front" else (cx + 0.5, hy + 6.3)
    band = _ell(*tie, 2.6 if view == "front" else 2.4, 1.0, xs, ys)
    c[band] = C["accent_red"]
    return tail & ~band


def _face(c, cx, hy, face, blink):
    """Eyes, brows and mouth on the front view (face turned to the viewer's left)."""
    dx = round(cx - CX)
    eyes = ((31 + dx, hy + 1), (37 + dx, hy + 1))
    if face == "phone":                                                  # looking down at the screen
        for x, y in eyes:
            _px(c, [(x, y + 2), (x + 1, y + 2)], "recess")
            _px(c, [(x, y + 3), (x + 1, y + 3)], "recess")
    elif blink or face in ("relaxed", "sleep"):
        for x, y in eyes:
            if face == "relaxed" and not blink:
                _px(c, [(x, y + 1), (x + 1, y), (x + 2, y + 1)], "recess")
            else:
                _px(c, [(x, y + 2), (x + 1, y + 2), (x + 2, y + 2)], "recess")
    else:
        for x, y in eyes:
            _px(c, [(x + i, y + j) for i in range(2) for j in range(3)], "recess")
            _px(c, [(x, y)], "wall_cream")                               # catch-light
    if face == "focused":                                                # determined, not cross: level brows
        _px(c, [(30 + dx, hy - 2), (31 + dx, hy - 2), (32 + dx, hy - 2)], "hair_dark")   # (angled-in brows read
        _px(c, [(37 + dx, hy - 2), (38 + dx, hy - 2), (39 + dx, hy - 2)], "hair_dark")   # as angry, D-111)
    elif face == "concerned_hopeful":                                    # worried brows, small hopeful smile
        _px(c, [(30 + dx, hy - 1), (31 + dx, hy - 1), (32 + dx, hy - 2), (33 + dx, hy - 2)], "hair_dark")
        _px(c, [(36 + dx, hy - 2), (37 + dx, hy - 2), (38 + dx, hy - 1), (39 + dx, hy - 1)], "hair_dark")
    my = hy + 7
    if face in ("relaxed", "calm", "phone", "focused"):                  # focused: a small, sure smile
        pts = [(33 + dx, my), (34 + dx, my + 1), (35 + dx, my + 1), (36 + dx, my)]
        if face == "relaxed":
            pts += [(32 + dx, my - 1), (37 + dx, my - 1)]
        _px(c, pts, "red_dark")
    elif face == "concerned_hopeful":
        _px(c, [(34 + dx, my), (35 + dx, my + 1), (36 + dx, my)], "red_dark")
    elif face == "sleep":
        _px(c, [(34 + dx, my), (35 + dx, my)], "red_dark")
    elif face == "celebrating":                                          # open grin
        _px(c, [(x + dx, my) for x in range(33, 37)], "wall_cream")
        _px(c, [(x + dx, my + 1) for x in range(33, 37)] + [(34 + dx, my + 2), (35 + dx, my + 2)], "red_dark")
    if face in ("relaxed", "celebrating"):
        _px(c, [(30 + dx, hy + 5), (39 + dx, hy + 5)], "pink_light")    # rosy cheeks


# ---------------------------------------------------------------- standing, walking, phone, sitting
def avatar(look: Look, view="front", stride=0, bob=0, swing=0, arms="down", face="calm", blink=False,
           pose="stand") -> np.ndarray:
    """One frame. stride: -1/0/+1 which leg is forward; bob: 1 lifts the upper body (passing step);
    swing: arm swing; arms: 'down' or 'up' (celebrating); pose: 'stand', 'phone' or 'sit'."""
    c = np.full((STRUCT_H, STRUCT_W), TRANSPARENT, np.int16)
    fx, fy = FOOT
    sit = pose == "sit"
    seat = SEATS[view] if sit else HIP                                  # the hips' height
    lap = fy - seat
    up = bob + seat - HIP
    sk_l, sk_m, _ = SKIN
    long_sleeves = look.top in ("long", "hoodie")

    def leg(x_hip, x_off, colours, far):
        y_shoe = fy - 1.7
        if sit and view == "back":                                       # seen from behind, the lower legs
            if look.lower != "skirt":                                    # are under the seat: only the seat
                _shade(c, _rect(x_hip - 0.5, lap, x_hip + 6.5, lap + 3), colours, x_hip + 1, x_hip + 5)
            return                                                       # of the trousers shows
        if sit:
            kx, ky = KNEE[view](x_hip + 3, lap)
            if look.lower != "skirt":
                if view == "front":                                      # the thigh, towards the viewer
                    _shade(c, _capsule(x_hip + 3, lap, kx, ky, 2.6), colours, kx + 1, x_hip + 4.5)
                _shade(c, _rect(kx - 2.5, ky, kx + 2.5, ky + 7), colours, kx - 1, kx + 1)   # the shin hangs
            x_shoe, y_shoe = kx, ky + 8.3                                # a chibi's feet dangle
        else:
            top, bottom = fy - HIP, fy - 3
            shift = np.clip((YS - top) / (bottom - top), 0, 1) * x_off
            m = (XS - shift >= x_hip) & (XS - shift < x_hip + 6) & (YS >= top) & (YS < bottom)
            if look.lower != "skirt":
                _shade(c, m, colours, x_hip + 1.5 + x_off, x_hip + 4.5 + x_off)
            x_shoe = x_hip + 3 + x_off - (0.6 if not far else 0)
        shoe = _ell(x_shoe, y_shoe, 3.8, 2.0)
        c[shoe] = C[look.shoes[0]]
        c[shoe & (YS >= y_shoe + 0.8)] = C[look.shoes[1]]                # sole

    def arm(x_sh, x_hand, y_hand, hand):
        sh_y = fy - SHOULDER + 1.5 - up
        m = _capsule(x_sh, sh_y, x_hand, y_hand, 2.1)
        if long_sleeves:
            _shade(c, m, look.top_colours, x_sh - 0.5, x_sh + 1.5)
        else:
            _shade(c, m, SKIN, x_sh - 0.5, x_sh + 1.5)
            _shade(c, m & (np.hypot(XS - x_sh, YS - sh_y) < 4.6), look.top_colours, x_sh, x_sh + 2)
        c[_ell(x_hand, y_hand, 2.1, 2.1)] = C[hand]

    near, far = {1: (-2, 1), 0: (0, 0), -1: (1, -1)}[stride]
    hand_y = fy - HIP - 1 - up
    hy = fy - HEAD_Y - up
    tail = np.zeros(c.shape, bool)
    if look.hair_style == "ponytail" and view == "front":
        tail = _ponytail(c, look, CX, hy, view, XS, YS)                  # behind the head
    if pose == "phone":
        arm(47.3, 42.5, fy - 21 - up, sk_m)
    elif sit:
        arm(47.3, 41.5 if view == "front" else 48, lap + (2 if view == "front" else -2), sk_m)
    elif arms == "down":
        arm(47.3, 49 - swing * 2, hand_y, sk_m)
    else:
        arm(47.3, 57.5, hy - 7, sk_m)                                    # arms up in a wide V, clear of
                                                                         # the head (narrow read as ears)
    def lower_near():
        if look.lower == "skirt" and not sit:                            # a long, modest A-line skirt
            t = np.clip((YS - (fy - HIP)) / (HIP - 1), 0, 1)
            x0, x1 = 31 - 3 * t + min(near, 0), 48 + 3 * t + max(far, 0)
            skirt = (XS >= x0) & (XS < x1) & (YS >= fy - HIP) & (YS < fy - 1)
            _shade(c, skirt, look.lower_colours, 34, 45)
            for f in (0.36, 0.68):                                       # two soft folds down to the hem
                c[skirt & (np.abs(XS - (x0 + f * (x1 - x0))) < 0.5) & (YS >= fy - HIP + 3)] = C[look.lower_colours[2]]
            c[skirt & (YS >= fy - 2)] = C[look.lower_colours[2]]          # the hem
        elif look.lower == "skirt":                                      # sitting: over the lap, to the ankles
            (k0, ky), (k1, _) = KNEE[view](35, lap), KNEE[view](43.5, lap)
            if view == "front":
                m = (_rect(k0 - 3, ky, k1 + 3, ky + 8) | _capsule(35, lap, k0, ky, 3.2) | _capsule(43.5, lap, k1, ky, 3.2)
                     | _rect(k0, lap - 1, 47, ky + 1))
            else:                                                        # from behind: under the hem only
                m, k0, k1 = _rect(30, lap - 1, 48, lap + 3), 34, 44
            _shade(c, m, look.lower_colours, k0, k1 + 1)
        leg(32.0, near, look.lower_colours, far=False)

    behind = sit and view == "back"                                      # legs in front of the body, away from us
    leg(40.5, far, (look.lower_colours[1], look.lower_colours[1], look.lower_colours[2]), far=True)
    if behind:
        lower_near()
    tor = _rect(30.5, fy - SHOULDER + 2 - up, 48, lap + 1) | _ell(39.2, fy - SHOULDER + 2.5 - up, 8.8, 3.2)
    _shade(c, tor, look.top_colours, 33.5, 44.5)
    c[tor & (YS >= lap)] = C[look.top_colours[2]]                       # hem
    if look.top == "polo":                                               # collar and buttons
        _px(c, [(37, fy - SHOULDER + 1 - up), (38, fy - SHOULDER + 2 - up), (41, fy - SHOULDER + 1 - up),
                (40, fy - SHOULDER + 2 - up)], look.top_colours[0])
        _px(c, [(39, fy - SHOULDER + 4 - up), (39, fy - SHOULDER + 6 - up)], look.top_colours[2])
    if look.top == "hoodie" and view == "front":                         # drawstrings, pocket
        _px(c, [(37, fy - SHOULDER + 3 - up + k) for k in range(4)] + [(41, fy - SHOULDER + 3 - up + k)
                                                                     for k in range(4)], "wall_cream")
        _px(c, [(x, fy - HIP - 4 - up) for x in range(34, 45)], look.top_colours[2])
    if look.hair_style == "tudung":                                      # the tudung drapes over the chest
        drape = _ell(CX + 1, fy - SHOULDER + 2 - up, 11.5, 4.5) & (YS >= hy + 6)
        _shade(c, drape, look.scarf, CX - 5, CX + 6)
    if not behind:
        lower_near()
    if pose == "phone":
        arm(31.2, 35.5, fy - 21 - up, sk_l)
        c[_rect(35, fy - 26 - up, 41, fy - 18 - up)] = C["stone_dark"]   # the phone
        c[_rect(36, fy - 25 - up, 40, fy - 20 - up)] = C["sky_light" if not blink else "sky"]
    elif sit:
        arm(31.2, 30.5 if view == "front" else 30, lap + (3 if view == "front" else -2), sk_l)
    elif arms == "down":
        arm(31.2, 29 + swing * 2, hand_y, sk_l)
    else:
        arm(31.2, 20.5, hy - 7, sk_l)
    c[_rect(36, fy - SHOULDER - 2 - up, 42, fy - SHOULDER + 2 - up)] = C[sk_m]   # neck
    if look.hair_style == "tudung":
        c[_rect(36, fy - SHOULDER - 2 - up, 42, fy - SHOULDER + 2 - up)] = C[look.scarf[1]]
    hair = _head(c, look, CX, hy, view, XS, YS)
    if look.hair_style == "ponytail" and view == "back":
        hair |= _ponytail(c, look, CX, hy, view, XS, YS)
    hair |= tail & np.isin(c, [C[n] for n in look.hair])                 # the visible tail keeps hair's edge
    _outline(c, hair)
    if view == "front":
        _face(c, CX, round(hy), "phone" if pose == "phone" else face, blink)
    if not sit:
        c[_ell(fx, fy, 8.5, 1.0) & (c < 0)] = C["recess"]                # flat shadow, 2 rows (spec E2)
    return c


# ---------------------------------------------------------------- asleep in bed (night)
# The pillow and the top of the bedding of each bed (furniture.py): mattress (room level 1), bed (2+)
BEDS = {"mattress": {"pillow_top": 9, "blanket_top": 8}, "bed": {"pillow_top": 18, "blanket_top": 17.5}}
ZED = ["zzzz", "..z.", ".z..", "zzzz"]


def asleep(look: Look, bed: str, k: int) -> np.ndarray:
    """Lying in bed (the 1 x 2 bed canvas, drawn over the bed): head on the pillow, eyes closed,
    tucked in under a blanket that rises and falls (4 frames), a "z" drifting up."""
    from .geometry import Box
    from .pieces import boxes, solid, tone
    w, h, (ox, oy) = struct_canvas((1, 2))
    xs, ys = _grid(w, h)
    c = np.full((h, w), TRANSPARENT, np.int16)
    spec = BEDS[bed]
    cx = ox + 32 + 2 * 8 - 2 * 5                                         # pillow centre (a = 8, b = 5)
    hy = oy + 8 + 5 - (spec["pillow_top"] + 6)
    hair = _head(c, look, cx, hy, "front", xs, ys)
    _outline(c, hair)
    _face(c, cx, round(hy), "sleep", True)
    breath = (0, 1, 1, 0)[k]
    top = spec["blanket_top"]

    def quilt(a, b):
        out = np.full(a.shape, C["accent_blue"], np.int16)
        out[b < 9.5] = C["wall_cream"]                                   # the sheet turned down
        out[(b >= 9.5) & (((b - 9.5) % 5) < 0.6)] = C["accent_blue_dark"]
        return out
    blanket = solid(boxes(Box(1.6, 14.4, 7.5, 29.6, top, top + 2.5, top=quilt, left=C["accent_blue_dark"],
                              right=C["accent_blue_dark"]),
                          Box(3.5, 12.5, 10.5, 25, top + 2.5, top + 4 + breath, top=quilt,
                              **{k_: C["accent_blue_dark"] for k_ in ("left", "right")})),
                    cells=(1, 2), line=C["outline"])                     # bedding: the room outline
    c[blanket >= 0] = blanket[blanket >= 0]                              # tucked in: over the chin
    from .creatures import stamp_zed
    stamp_zed(c, cx + 9 + k, hy - 13 - 2 * k, ZED)                       # the "z" drifts up and away
    return c


# ---------------------------------------------------------------- glasses (an overlay)
def glasses_front() -> np.ndarray:
    """Glasses for the front view, drawn for the standing head (bob 0); characters.json gives each
    front frame's head offset, so the app moves this overlay with the head."""
    c = np.full((STRUCT_H, STRUCT_W), TRANSPARENT, np.int16)
    hy = FOOT[1] - HEAD_Y
    for x0 in (30, 36):
        _px(c, [(x0 + i, hy) for i in range(4)] + [(x0 + i, hy + 4) for i in range(4)]
            + [(x0, hy + j) for j in range(5)] + [(x0 + 3, hy + j) for j in range(5)], "stone_dark")
    _px(c, [(34, hy + 1), (35, hy + 1)] + [(x, hy + 1) for x in range(40, 46)], "stone_dark")
    return c


# ---------------------------------------------------------------- frames and registry
WALK = [dict(stride=1, swing=-1), dict(stride=0, bob=1), dict(stride=-1, swing=1), dict(stride=0, bob=1)]
MOODS = ("relaxed", "calm", "focused", "concerned_hopeful", "celebrating")


def frames(look: Look = AVATARS[0]) -> dict[str, tuple[np.ndarray, dict]]:
    """name -> (frame, meta). meta: view, cells, head_dy (px the head sits above the standing head:
    for the glasses overlay), glasses (True on front frames with an open or closed face)."""
    out = {}

    def add(name, arr, view="front", dy=0, glasses=True, cells=(1, 1)):
        out[name] = (arr, {"view": view, "cells": list(cells), "head_dy": dy, "glasses": glasses and view == "front"})
    for view in ("front", "back"):
        add(f"{view}_idle_0", avatar(look, view), view)
        add(f"{view}_idle_1", avatar(look, view, bob=1, blink=view == "front"), view, 1)
        for k, pose in enumerate(WALK):
            add(f"{view}_walk_{k}", avatar(look, view, **pose), view, pose.get("bob", 0))
    for mood in MOODS:
        arms = "up" if mood == "celebrating" else "down"
        add(f"mood_{mood}", avatar(look, "front", face=mood, arms=arms))
        # the Home scene's idle animation (D-116): breathing (the upper body up 1 px) and a blink,
        # in the same mood, so the character never changes expression while it idles
        add(f"mood_{mood}_breathe", avatar(look, "front", face=mood, arms=arms, bob=1), dy=1)
        add(f"mood_{mood}_blink", avatar(look, "front", face=mood, arms=arms, blink=True))
    add("phone_0", avatar(look, "front", pose="phone"))
    add("phone_1", avatar(look, "front", pose="phone", blink=True))
    for view, name in (("front", "sit"), ("back", "sit_back")):
        dy = SEATS[view] - HIP
        add(f"{name}_0", avatar(look, view, pose="sit"), view, dy)
        add(f"{name}_1", avatar(look, view, pose="sit", bob=1, blink=True), view, dy + 1)
    for bed in BEDS:
        for k in range(4):
            add(f"sleep_{bed}_{k}", asleep(look, bed, k), glasses=False, cells=(1, 2))
    return out


def characters_json() -> dict:
    """For the app: avatars, skin tones and how to place each frame (assets/isometric/characters.json)."""
    from .palette import skin_tones
    return {
        "avatars": [{"name": lk.name, "who": lk.who, "suggested_tone": lk.tone,
                     "frames": {n: m for n, (_, m) in frames(lk).items()}} for lk in AVATARS],
        "skin_tones": skin_tones(),
        "skin_palette_names": list(SKIN),
        "glasses": {"piece": "glasses_front", "use": "draw over a front frame whose 'glasses' is true, moved up "
                                                   "by its head_dy"},
        "draw": "feet at the cell centre (a piece's footprint origin as for any 1 x 1 struct); front = facing "
                "down-left, back = up-left, mirror for down-right / up-right. Recolour the three skin colours "
                "to the chosen skin tone (palette swap). Asleep at night (19:00-05:59): sleep_<bed>_k over the "
                "bed's cell, bed = 'mattress' at room level 1, 'bed' from level 2. Sitting on the sofa: sit_k "
                "mirrored (the sofa faces +a), feet at the sofa's front cell",
    }


AVATAR_PIECES = []
for _look in AVATARS:
    for _name, (_arr, _meta) in frames(_look).items():
        AVATAR_PIECES.append(Piece(f"{_look.name}_{_name}", f"characters/{_look.name}", "struct",
                                   (lambda lk=_look, n=_name: frames(lk)[n][0]),
                                   f"{_look.who}: {_name.replace('_', ' ')}", tuple(_meta["cells"])))
AVATAR_PIECES.append(Piece("glasses_front", "characters", "struct", glasses_front,
                           "glasses overlay for front frames (characters.json: glasses, head_dy)"))
