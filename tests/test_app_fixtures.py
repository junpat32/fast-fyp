"""T-16 (D-104): the app's TypeScript ports are tested against fixtures generated from the Python
originals; this fails if a Python original changed and the fixture wasn't regenerated
(`python -m tools.app_fixtures`), which would leave the app's tests checking against stale answers."""
import json

from tools import app_fixtures as af


def test_depth_sort_fixture_is_up_to_date():
    assert json.loads(af.OUT.read_text(encoding="utf-8")) == af.build()


def test_the_fixture_makes_depth_sort_do_real_work():
    for case in af.build()["cases"]:
        assert any(i != j for i, j in enumerate(case["expected"])), case["name"]


def test_home_scene_fixture_is_up_to_date():
    """D-113: the app's scene composer is checked against these Python-drawn scenes; a change to the
    kit's layout or the previews' view must regenerate them."""
    assert json.loads(af.SCENE_OUT.read_text(encoding="utf-8")) == af.build_scenes()


def test_the_scene_fixture_covers_the_hard_cases():
    cases = af.build_scenes()["cases"]
    assert {c["input"]["level"] for c in cases} >= {0, 1, 2, 4}                    # before the garden to G4
    assert any(c["input"]["bed_steps"] for c in cases)                            # the bed's growth
    assert any(c["draws"]["decals"] for c in cases)                               # a rug
    assert any("|flip" in d[0] for c in cases for d in c["draws"]["structs"])     # a mirrored piece
    assert any(d[0].endswith("_droop") for c in cases for d in c["draws"]["structs"])


def test_debt_plans_fixture_is_up_to_date_and_covers_the_hard_cases():
    """D-144: the app's avalanche/snowball port is checked against compare_debt_plans."""
    data = af.build_debt_plans()
    assert json.loads(af.DEBT_PLAN_OUT.read_text(encoding="utf-8")) == data
    expected = [c["expected"] for c in data["cases"]]
    assert any(e["avalanche_months"] is None for e in expected)                            # never cleared
    assert any(e["avalanche_interest"] < e["snowball_interest"] - 1 for e in expected)     # the order matters
    assert all(e["avalanche_months"] != 0 for e in expected)                              # every case has work to do


def test_decor_spots_fixture_is_up_to_date_and_covers_crowding():
    """D-120: the app's spot finder is checked against the kit's decor_spots."""
    data = af.build_decor()
    assert json.loads(af.DECOR_OUT.read_text(encoding="utf-8")) == data
    crowded = [c for c in data["cases"] if c["used"]]
    assert crowded and all(c["expected"] for c in data["cases"])                 # every case has somewhere to go
    assert all(not ({tuple(x) for x in c["used"]} & {tuple(x) for x in c["expected"]}) for c in crowded)


def test_helper_fixture_is_up_to_date_and_covers_each_redaction():
    """D-123: the phone's redaction and crisis check are tested against the server's own."""
    data = af.build_helper()
    assert json.loads(af.HELPER_OUT.read_text(encoding="utf-8")) == data
    changed = [q for q, r in data["redact"] if q != r]
    assert len(changed) >= 9                                                      # IC, card, account, email, phone, TAC...
    assert {hit for _, hit in data["crisis"]} == {True, False}                   # both ways, incl. near misses


def test_character_fixture_is_up_to_date():
    """D-125: the app's skin-tone swap and glasses are checked against the kit's own recolouring."""
    data = af.build_character()
    assert json.loads(af.CHARACTER_OUT.read_text(encoding="utf-8")) == data
    assert {c["tone"] for c in data["cases"]} >= {1, 3, 5, 6} and any(c["head_dy"] for c in data["cases"])


def test_the_sign_up_fixtures_are_up_to_date():
    """D-124: the sign-up card with what the study's check expects, and a new user's day one (the
    endpoints' own output for the card's details: no months yet, the welcome points and choice)."""
    assert json.loads(af.ONBOARDING_OUT.read_text(encoding="utf-8")) == af.build_onboarding()
    new = af.build_new_user()
    assert json.loads(af.NEW_USER.read_text(encoding="utf-8")) == new
    assert new["study"] == {"persona": False} and new["game"]["choices"]["available"] >= 1
    assert new["assess"]["months"][-1]["source"] == "this month so far" and not new["future"]["available"]


def test_the_apps_sample_data_is_what_the_backend_sends_now():
    """D-106: app/src/data/samples are the endpoints' own output for the personas; regenerate them
    (`python -m tools.app_fixtures`) whenever the engine, the game or the personas change."""
    for key, sample in af.build_samples().items():
        assert json.loads((af.SAMPLES / f"{key}.json").read_text(encoding="utf-8")) == sample, key


def test_the_time_travel_data_is_what_the_backend_sends_on_each_date():
    """D-119: sample data mode's time travel reads app/src/data/travel, one bundle per later study date."""
    samples = af.build_samples()
    for key, t in af.build_travel().items():
        assert json.loads((af.TRAVEL / f"{key}.json").read_text(encoding="utf-8")) == t, key
        study = samples[key]["study"]
        dates = [study["first"], *t["dates"]]
        assert dates[-1] == study["last"] and len(dates) == 7 and dates == sorted(dates)
        for d, bundle in t["dates"].items():
            assert bundle["assess"]["as_of"] == bundle["game"]["as_of"] == d
            assert all(c["month"] < d for c in bundle["checkins"])
