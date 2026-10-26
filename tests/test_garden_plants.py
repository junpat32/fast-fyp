"""T-22 batch 2 (D-84): bed plants, tiers 1-2 (docs/assets/FAST_ASSET_SPEC_BATCH2.md §5)."""
from functools import cache

import numpy as np
import pytest

from engine.game import load_game
from tools.asset_generation.garden_plants import BASE, PLANT_PIECES, STAGES, TIER_1_2
from tools.asset_generation.palette import IDX, NIGHT_OVERRIDES

GREENS = [IDX["green_light"], IDX["green_mid"], IDX["green_dark"]]


@cache
def img(name):
    return next(p for p in PLANT_PIECES if p.name == name).render()


def height(a):
    rows = np.flatnonzero((a >= 0).any(axis=1))
    return BASE[1] - rows.min()


def test_names_follow_the_game_rules():
    """Tier 1-2 plants of shared/game.json, each in engine.game.plant_stage's three stages, normal and
    drooping, plus the free seedling (D-69)."""
    tiers = load_game()["garden"]["plants"]
    assert set(TIER_1_2) == {p for p, t in tiers.items() if t <= 2}
    names = {p.name for p in PLANT_PIECES}
    for plant in TIER_1_2:
        for stage in STAGES:
            assert {f"plant_{plant}_{stage}", f"plant_{plant}_{stage}_droop"} <= names
    assert {"plant_free_seedling", "plant_free_seedling_droop"} <= names


@pytest.mark.parametrize("plant", TIER_1_2)
def test_stages_grow_to_the_spec_heights(plant):
    """Spec §2: seedling about 6 px, young about 12, full 18-24 (a little outline either way)."""
    h = [height(img(f"plant_{plant}_{s}")) for s in STAGES]
    assert h[0] < h[1] < h[2], h
    assert h[0] <= 9 and 9 <= h[1] <= 16 and 16 <= h[2] <= 27, h


@pytest.mark.parametrize("plant", TIER_1_2)
@pytest.mark.parametrize("stage", STAGES)
def test_drooping_stays_green_present_and_in_flower(plant, stage):
    """D-73: a drooping plant hangs lower and darker but is never dead or gone; flowers stay."""
    normal, droop = img(f"plant_{plant}_{stage}"), img(f"plant_{plant}_{stage}_droop")
    assert np.isin(droop, GREENS).sum() >= 0.5 * np.isin(normal, GREENS).sum()
    assert height(droop) <= height(normal)
    flowers = [IDX[c] for c in ("accent_red", "pink_light", "pink_mid", "orange")]
    if np.isin(normal, flowers).any():
        assert np.isin(droop, flowers).any()


@pytest.mark.parametrize("plant, colour", [("chilli", "accent_red"), ("bunga_raya", "accent_red"),
                                           ("bougainvillea", "pink_mid"), ("ixora", "orange")])
def test_flowering_plants_flower_when_full(plant, colour):
    assert np.isin(img(f"plant_{plant}_full"), [IDX[colour]]).any()
    assert not np.isin(img(f"plant_{plant}_seedling"), [IDX[colour]]).any()


@pytest.mark.parametrize("piece", PLANT_PIECES, ids=lambda p: p.name)
def test_garden_outline_no_glow_and_on_the_soil(piece):
    """Garden pieces use the soft outline (spec §1), nothing glows at night, and the plant stands on
    its cell's centre: nothing below the base point."""
    a = img(piece.name)
    assert (a == IDX["outline_soft"]).any() and not (a == IDX["outline"]).any()
    assert not np.isin(a, [IDX[n] for n in NIGHT_OVERRIDES]).any()
    below = 6 if piece.name.startswith("plant_jade_vine") else 1    # its trellis's front post: still in the cell
    assert not (a[BASE[1] + below:] >= 0).any()
