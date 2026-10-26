"""End-to-end: a persona's months in, the full assessment out (engine.assess)."""
from engine.assess import assess
from engine.features import UserProfile, features_at, user_flags
from engine.forecast import forecast
from engine.bands import load_thresholds
from engine.state import MonthRecord


def gig_rider():
    """24-year-old p-hailing rider, celebrates Hari Raya (March), heavy BNPL user, thin cushion."""
    prof = UserProfile(employment_type="gig", age=24, festive_month=3, family_support=True)
    recs = []
    for k, (inc, cash, bnpl_n, shock) in enumerate([(2600, 900, 3, 0), (1900, 600, 4, 0), (2400, 500, 5, 1),
                                                     (1700, 250, 4, 0), (2200, 150, 6, 1), (1800, 60, 5, 0)]):
        recs.append(MonthRecord(net_income=inc, debt_payments=520 + 25 * bnpl_n, outstanding_debt=9000,
                                cash=cash, essential_spending=1250, total_spending=1950 + 40 * k,
                                family_support=200, month=4 + k, bnpl_purchases=180, bnpl_new_count=bnpl_n,
                                bnpl_instalments=25 * bnpl_n, event_costs=450 * shock, shock_count=shock,
                                savings_target=300))
    return prof, recs


def steady_employee():
    prof = UserProfile(employment_type="employee", age=29, festive_month=1)
    recs = [MonthRecord(net_income=3600, debt_payments=600, outstanding_debt=20000, cash=7000 + 300 * k,
                        essential_spending=1500, total_spending=2400, month=4 + k, savings_target=300)
            for k in range(6)]
    return prof, recs


def test_no_forecast_while_income_is_too_low_to_judge():
    """Q4 (D-90): O2 left insufficient-income months out of training; the engine shows a note instead."""
    prof, recs = steady_employee()
    lost = [MonthRecord(**{**r.__dict__, "net_income": 0.0}) for r in recs[-3:]]
    out = assess(prof, recs[:-3] + lost)
    assert out["band"] == "INSUFFICIENT_INCOME" and out["forecast"] is None
    assert out["forecast_note"] == "No forecast while income is too low to judge."
    assert assess(*steady_employee())["forecast_note"] is None


def test_forecast_is_never_shown_as_certain():
    """P7 (D-90): the shown probability stays within 2-98%, on the same side of the base rate."""
    prof, recs = gig_rider()
    broke = [MonthRecord(**{**r.__dict__, "cash": 0.0, "shortfall": True, "event_costs": 2000, "shock_count": 3})
             for r in recs]
    out = assess(prof, broke)["forecast"]
    assert 0.02 <= out["probability"] <= 0.98 and out["probability"] > out["base_rate"]


def test_full_assessment_shape_and_ranges():
    out = assess(*gig_rider())
    assert out["band"] in {"GREEN", "YELLOW", "RED", "INSUFFICIENT_INCOME"}
    assert 0 <= out["health"]["score"] <= 100 and out["health"]["tier"] in {"Healthy", "Coping", "Vulnerable"}
    assert 0 <= out["forecast"]["probability"] <= 1 and out["forecast"]["version"] == "forecast_v1"
    assert 1 <= len(out["forecast"]["reasons"]) <= 3
    assert set(out["flags"]) <= set(load_thresholds()["user_facing_flags"])
    rules = [a["rule"] for a in out["advice"]]
    assert "R07_bnpl_load" in rules and "R05_build_first_cushion" in rules


def test_riskier_persona_gets_higher_forecast():
    assert assess(*gig_rider())["forecast"]["probability"] > assess(*steady_employee())["forecast"]["probability"]


def test_deterministic():
    assert assess(*gig_rider()) == assess(*gig_rider())


def test_no_forecast_before_three_months():
    prof, recs = gig_rider()
    out = assess(prof, recs[:2])
    assert out["forecast"] is None and out["band"]


def test_reasons_never_cite_flags_that_failed_s14_or_demographics():
    prof, recs = gig_rider()
    fl = user_flags(recs, prof, load_thresholds()["flags"])
    x = features_at(prof, recs, len(recs) - 1, fl)
    x.update(flag_overconfidence=1.0, flag_delayed_correction=1.0)     # even if they fired
    cited = {r.feature for r in forecast(x).reasons}
    assert not cited & {"flag_overconfidence", "flag_delayed_correction"}
    assert not any(f.startswith(("type_", "age_")) for f in cited)


def test_reasons_are_readable_and_point_the_right_way():
    risky, steady = assess(*gig_rider())["forecast"], assess(*steady_employee())["forecast"]
    assert risky["probability"] > risky["base_rate"] and all(r["direction"] == "raises" for r in risky["reasons"])
    assert steady["probability"] <= steady["base_rate"] and all(r["direction"] == "lowers" for r in steady["reasons"])
    for fc in (risky, steady):
        for r in fc["reasons"]:
            assert not r["feature"].startswith(("band_", "type_", "age_"))
            if r["feature"] in {"has_personal_loan", "shortfall_last3", "festive_next3", "family_support"}:
                assert r["value"] == 1


def test_hidden_demographic_factor_is_disclosed_not_silently_dropped():
    """P6: when user type or age group is a top factor, the forecast says so."""
    prof, recs = gig_rider()
    fl = user_flags(recs, prof, load_thresholds()["flags"])
    x = features_at(prof, recs, len(recs) - 1, fl)
    from engine.forecast import _load, FEATURES
    art = _load()
    contrib = art["model"][0].transform([[x[f] for f in FEATURES]])[0] * art["model"][-1].coef_[0]
    top3 = sorted(range(len(FEATURES)), key=lambda j: -contrib[j])[:3]
    demo_in_top = any(FEATURES[j].startswith(("type_", "age_")) and x[FEATURES[j]] == 1 for j in top3)
    assert (forecast(x).note is not None) == demo_in_top


def test_output_has_no_raw_transactions_for_groq():
    out = assess(*gig_rider())
    text = repr(out).lower()
    for leak in ("merchant", "txn", "transaction_id", "description"):
        assert leak not in text
