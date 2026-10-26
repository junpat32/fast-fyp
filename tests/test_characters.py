"""T-22 batch 2 (D-84, D-86): the six chibi avatars (docs/assets/FAST_ASSET_SPEC_BATCH2.md §7)."""
from functools import cache

import numpy as np
import pytest

from engine.game import GameState
from tools.asset_generation.characters import (AVATAR_PIECES, AVATARS, BEDS, FOOT, MOODS, SEATS, HIP,
                                               characters_json, frames, glasses_front)
from tools.asset_generation.furniture import mattress, single_bed
from tools.asset_generation.geometry import struct_canvas
from tools.asset_generation.palette import BASE, IDX, NIGHT_OVERRIDES, SKIN_NAMES, SKIN_TONES, skin_tones, to_rgba

FRAMES = {lk.name: {n: a for n, (a, _) in frames(lk).items()} for lk in AVATARS}
META = {lk.name: {n: m for n, (_, m) in frames(lk).items()} for lk in AVATARS}
NAMES = list(FRAMES["avatar_01"])
STANDING = [n for n in NAMES if not n.startswith(("sit", "sleep"))]
ALL = [(a, n) for a in FRAMES for n in NAMES]


@cache
def body(avatar, name):
    """The frame without its flat shadow."""
    a = FRAMES[avatar][name].copy()
    a[a == IDX["recess"]] = -1
    return a


def test_six_avatars_with_the_same_frames():
    """Spec §7: 6 avatars (3 feminine, 3 masculine, one wearing a tudung) sharing one set of poses:
    idle 2 and walk 4 per drawn view, the moods, using a phone, sitting, and asleep in bed."""
    assert len(AVATARS) == 6 and len({lk.name for lk in AVATARS}) == 6
    assert sum("feminine" in lk.who for lk in AVATARS) == 3 and sum("masculine" in lk.who for lk in AVATARS) == 3
    assert [lk.hair_style for lk in AVATARS].count("tudung") == 1
    assert all(list(f) == NAMES for f in FRAMES.values())
    names = set(NAMES)
    for view in ("front", "back"):
        assert {f"{view}_idle_{k}" for k in range(2)} | {f"{view}_walk_{k}" for k in range(4)} <= names
    assert {"relaxed", "calm", "focused", "concerned_hopeful"} | {"celebrating"} == set(MOODS)
    assert {f"mood_{m}" for m in MOODS} | {"phone_0", "phone_1", "sit_0", "sit_1", "sit_back_0"} <= names
    assert {f"sleep_{bed}_{k}" for bed in BEDS for k in range(4)} <= names
    assert [p.name for p in AVATAR_PIECES] == [f"{a}_{n}" for a in FRAMES for n in NAMES] + ["glasses_front"]
    assert hasattr(GameState, "mood")


def test_avatars_look_different():
    idle = [FRAMES[a]["front_idle_0"] for a in FRAMES]
    assert all(not (idle[i] == idle[j]).all() for i in range(6) for j in range(i + 1, 6))


@pytest.mark.parametrize("avatar,name", [(a, n) for a in FRAMES for n in STANDING])
def test_same_height_and_feet_on_the_base_point(avatar, name):
    """Spec §7: 56 px chibi, feet on the same base point in every standing frame, nothing cut off."""
    a = body(avatar, name)
    rows = np.flatnonzero((a >= 0).any(axis=1))
    assert rows.max() == FOOT[1] - 1                                                  # the soles
    if not name.endswith("celebrating"):
        assert 54 <= FOOT[1] - rows.min() <= 59, FOOT[1] - rows.min()
    cols = np.flatnonzero((a >= 0).any(axis=0))
    assert cols.min() > 0 and cols.max() < a.shape[1] - 1                             # not cut off at the sides


@pytest.mark.parametrize("avatar,name", [(a, n) for a in FRAMES for n in STANDING])
def test_flat_shadow_under_the_feet(avatar, name):
    """Spec §1 (E2): a small flat shadow, 2 rows, under characters."""
    a = FRAMES[avatar][name]
    low = a[FOOT[1] - 6:]                                     # around the feet (the eyes are recess too)
    rows = FOOT[1] - 6 + np.flatnonzero((low == IDX["recess"]).any(axis=1))
    assert set(rows) <= {FOOT[1] - 1, FOOT[1]} and len(rows) >= 1, rows
    assert ((a[FOOT[1]] == IDX["recess"]).sum()) >= 8                                 # wider than the feet


@pytest.mark.parametrize("avatar", list(FRAMES))
def test_sitting_raises_the_hips_to_the_seat_and_the_feet_dangle(avatar):
    """Sitting on the sofa (front, 15 px) or the desk chair (back, 18 px): hips on the seat, no floor
    shadow (the avatar is on furniture), the chibi's short legs leave the feet off the floor."""
    assert SEATS == {"front": 15, "back": 18}
    for name in ("sit_0", "sit_back_0"):
        a = FRAMES[avatar][name]
        assert not (a[FOOT[1]] >= 0).any()                                            # no shadow row
        rows = np.flatnonzero((a >= 0).any(axis=1))
        assert rows.max() < FOOT[1] - 1                                               # the feet dangle
        view = "front" if name == "sit_0" else "back"
        assert META[avatar][name]["head_dy"] == SEATS[view] - HIP
        stand = np.flatnonzero((body(avatar, f"{view}_idle_0") >= 0).any(axis=1)).min()
        assert rows.min() == stand - (SEATS[view] - HIP)                              # the head rises with the hips


@pytest.mark.parametrize("avatar", list(FRAMES))
def test_asleep_in_bed(avatar):
    """At night the avatar sleeps in its bed: a 1 x 2 overlay on the bed (mattress at room level 1,
    bed from level 2), head on the pillow, eyes closed, the blanket rising and falling."""
    w, h, _ = struct_canvas((1, 2))
    for bed, base in (("mattress", mattress()), ("bed", single_bed())):
        fs = [FRAMES[avatar][f"sleep_{bed}_{k}"] for k in range(4)]
        assert all(f.shape == (h, w) for f in fs)
        assert not (fs[0] == fs[1]).all() and (fs[1] != fs[2]).any()                  # breathing, the z drifts
        head = (fs[0] >= 0) & (base < 0)
        assert head.any()                                                             # the head is above the bed
        rows = np.flatnonzero((fs[0] >= 0).any(axis=1))
        bed_top = np.flatnonzero((base >= 0).any(axis=1)).min()
        assert rows.max() <= np.flatnonzero((base >= 0).any(axis=1)).max()            # never below the bed
        assert rows.min() >= bed_top - 40
        assert all(META[avatar][f"sleep_{bed}_{k}"]["cells"] == [1, 2] for k in range(4))


def test_sleeping_z_stays_readable_at_night():
    """D-87: the sleeping "z" uses the symbol colour, which keeps a pale moonlit white at night (the
    usual night transform made it a dim grey-blue); only sleep frames use it, and it lights nothing."""
    from tools.asset_generation.palette import SYMBOL_NIGHT, palettes
    assert set(SYMBOL_NIGHT) == {"zed"} and "zed" not in NIGHT_OVERRIDES
    night = palettes()["night"]["zed"]
    assert sum(int(night[i:i + 2], 16) for i in (1, 3, 5)) > 600                      # still light at night
    for avatar, name in ALL:
        assert (FRAMES[avatar][name] == IDX["zed"]).any() == name.startswith("sleep"), name


def test_back_view_shows_no_face():
    for avatar, name in ALL:
        if name.startswith(("back", "sit_back")):
            assert not (FRAMES[avatar][name] == IDX["red_dark"]).any()


def test_moods_and_idle_frames_differ():
    for f in FRAMES.values():
        moods = [f[f"mood_{m}"] for m in MOODS]
        assert all(not (moods[i] == moods[j]).all() for i in range(len(moods)) for j in range(i + 1, len(moods)))
        assert not (f["front_idle_0"] == f["front_idle_1"]).all()                     # breathing and blink
        assert not (f["front_walk_0"] == f["front_walk_2"]).all()                     # each leg steps in turn


def test_tudung_covers_the_hair():
    tud = next(lk.name for lk in AVATARS if lk.hair_style == "tudung")
    for name in ("front_idle_0", "back_idle_0", "front_walk_1", "sit_0", "sleep_bed_0"):
        assert not np.isin(FRAMES[tud][name], [IDX["hair_dark"], IDX["hair_shine"]]).any(), name


@pytest.mark.parametrize("avatar,name", ALL)
def test_soft_outline_and_no_glow(avatar, name):
    a = FRAMES[avatar][name]
    assert (a == IDX["outline_soft"]).any()
    if not name.startswith("sleep"):                                                  # bedding uses the room outline
        assert not (a == IDX["outline"]).any()
    assert not np.isin(a, [IDX[n] for n in NIGHT_OVERRIDES]).any()


def test_six_skin_tones_by_palette_swap():
    """Spec §7: 6 skin tones, a palette swap of the 3 skin colours; tone index 2 is the drawn skin."""
    assert len(SKIN_TONES) == 6 and all(len(t) == 3 for t in SKIN_TONES)
    assert tuple(BASE[n] for n in SKIN_NAMES) == SKIN_TONES[2]
    lum = [sum(int(t[1][i:i + 2], 16) for i in (1, 3, 5)) for t in SKIN_TONES]
    assert lum == sorted(lum, reverse=True)                                           # light to deep
    a = FRAMES["avatar_01"]["front_idle_0"]
    skin = np.isin(a, [IDX[n] for n in SKIN_NAMES])
    for k in range(6):
        rgba = to_rgba(a, "afternoon", tone=k)
        assert tuple(rgba[skin][0][:3]) in {tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in SKIN_TONES[k]}
        assert (rgba[~skin] == to_rgba(a, "afternoon")[~skin]).all()                 # only the skin changes
    assert len(skin_tones()) == 6 and set(skin_tones()[0]) == {"morning", "afternoon", "night"}


def test_glasses_sit_on_the_eyes_and_follow_the_head():
    g = glasses_front()
    a = FRAMES["avatar_01"]["front_idle_0"]
    eyes = np.argwhere((a == IDX["recess"])[: FOOT[1] - 6])
    glass = np.argwhere(g >= 0)
    assert glass[:, 0].min() <= eyes[:, 0].min() and glass[:, 0].max() >= eyes[:, 0].max()
    j = characters_json()
    assert j["glasses"]["piece"] == "glasses_front" and len(j["avatars"]) == 6 and len(j["skin_tones"]) == 6
    m = j["avatars"][0]["frames"]
    assert m["front_idle_1"]["head_dy"] == 1 and m["front_idle_0"]["glasses"] and not m["back_idle_0"]["glasses"]
    assert not m["sleep_bed_0"]["glasses"]
