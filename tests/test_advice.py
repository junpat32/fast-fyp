"""Advice and reason wording (T-11, D-92): every text fills in, the numbers in it come from
shared/thresholds.json (rule 5), and every forecast reason has plain words for the user's side."""
import re

import pytest

import engine.forecast as fc
import engine.rules as rules
from engine.bands import RED, YELLOW, load_thresholds
from engine.features import FEATURES
from engine.forecast import REASON_WORDS, against_common_sense
from engine.rules import Context, advise
from engine.state import MonthState

SAMPLE = {"shortfalls": 1, "debt_payments": "RM400", "dsr_pct": "57%", "cushion_months": "0.5",
          "gap_to_first": "RM600", "gap_to_next": "RM3,000", "bnpl_plans": 2, "bnpl_monthly": "RM150",
          "risk_pct": "34%", "overspend_pct": "10%", "new_band": "Green"}


def state(**over) -> MonthState:
    base = dict(index=2, month=5, income_median3=3000.0, dsr=0.4, dti=0.5, band=YELLOW, band_name="YELLOW",
                raw_band=YELLOW, cushion_months=2.0, savings_rate3=0.05, shortfalls_last3=0, insufficient_income=False)
    return MonthState(**{**base, **over})


def test_every_advice_text_fills_in_with_no_braces_left():
    fixed = rules.limits(load_thresholds())
    for rule, texts in rules._ADVICE.items():
        for key, text in texts.items():
            filled = text.format(**fixed, **SAMPLE)
            assert "{" not in filled and "}" not in filled, (rule, key)


def test_no_threshold_is_typed_into_the_advice_texts():
    """Band limits, goals and the income floor are placeholders (A5): no "60%", "55%", "RM300"..."""
    t = load_thresholds()
    typed = {f"{t['dsr'][k]:.0%}" for k in ("green_below", "red_at_or_above", "leave_red_below")}
    typed.add(f"RM{t['insufficient_income_below_rm']}")
    for rule, texts in rules._ADVICE.items():
        for text in texts.values():
            assert not any(x in text for x in typed), rule
            rest = text.replace("in the next 3 months", "")          # the forecast's horizon: fixed by the frozen spec
            assert not re.search(r"\b\d+[- ]months?\b", rest), rule          # goals and windows too


def test_every_rule_has_a_short_action_first_line():
    """D-108: the Money screen shows the short line first; it must stay one short line."""
    fixed = rules.limits(load_thresholds())
    for rule, texts in rules._ADVICE.items():
        assert "short" in texts, rule
        for key in [k for k in texts if k.startswith("short")]:
            line = texts[key].format(**fixed, **SAMPLE)
            assert len(line) <= 70 and line.endswith("."), (rule, key, len(line))


def test_advice_items_carry_their_short_line():
    red = state(band=RED, raw_band=YELLOW, band_name="RED", dsr=0.52)               # out of Red, waiting (D-49)
    improving = next(a for a in advise(Context(state=red)) if a.rule == "R03_red_band")
    assert improving.short.startswith("Keep going")
    held = next(a for a in advise(Context(state=state(band=RED, raw_band=RED, band_name="RED", dsr=0.57)))
                if a.rule == "R03_red_band")
    assert "AKPK" in held.short


def test_changing_a_threshold_changes_the_words():
    t = load_thresholds()
    t["dsr"]["red_at_or_above"] = 0.65
    t["advice"]["cushion_first_goal_months"] = 2
    adv = {a.rule: a for a in advise(Context(state=state(dsr=0.52), essentials_and_debts=1000, cash=500), t)}
    assert "Red starts at 65%" in adv["R04_near_red"].text
    s = state(cushion_months=0.5)
    first = next(a for a in advise(Context(state=s, essentials_and_debts=1000, cash=500), t)
                 if a.rule == "R05_build_first_cushion")
    assert first.title == "First goal: 2 months saved" and "Getting to 2 months" in first.text


def test_red_at_or_above_the_line_keeps_the_plain_text():
    red = next(a for a in advise(Context(state=state(band=RED, raw_band=RED, band_name="RED", dsr=0.62)))
               if a.rule == "R03_red_band")
    assert "Red is 60% or more" in red.text


# ---------------------------------------------------------------- reasons (P8)
ELIGIBLE = [f for f in FEATURES if not f.startswith(("type_", "age_", "band_"))]


def test_every_feature_that_can_be_a_reason_has_words():
    assert set(REASON_WORDS) == set(ELIGIBLE)
    binary = fc.BINARY
    for f in ELIGIBLE:
        w = REASON_WORDS[f]
        assert w["expected"] in ("raises", "lowers") and w["high"]
        if f not in binary:
            assert w["low"] and w["low"] != w["high"]
        for side in ("high", "low"):
            if side in w:
                assert not re.search(r"\b(raises|lowers|risk)\b", w[side], re.I), (f, side)   # the header says it


def test_reasons_get_the_words_for_the_users_side():
    feats = {f: 0.0 for f in FEATURES}
    feats.update({"inc_median3": 1200, "cushion_t": 0.1, "dsr_t": 0.55, "type_employee": 1, "age_20-24": 1,
                  "band_YELLOW": 1, "shortfall_last3": 1})
    r = fc.forecast(feats)
    scaler = fc._load()["model"][0]
    z = dict(zip(FEATURES, scaler.transform([[feats[f] for f in FEATURES]])[0]))
    assert r.reasons
    for x in r.reasons:                                  # above the training average -> "high" words
        assert x.text == REASON_WORDS[x.feature]["high" if z[x.feature] > 0 else "low"]
    assert any(x.text == "Your cash cushion is smaller than average" for x in r.reasons)


def test_counterintuitive_reasons_can_be_left_out(monkeypatch):
    """forecast_v1's savings-rate and new-BNPL coefficients point against common sense (D-92, W1)."""
    coef = dict(zip(FEATURES, fc._load()["model"][-1].coef_[0]))
    odd = {f for f in ELIGIBLE if against_common_sense(f, coef[f])}
    assert {"savings_rate3", "bnpl_new3"} <= odd and "dsr_t" not in odd and "cushion_t" not in odd
    t = load_thresholds()
    t["explanations"]["drop_counterintuitive"] = True
    monkeypatch.setattr(fc, "load_thresholds", lambda: t)
    feats = {f: 0.0 for f in FEATURES}
    feats.update({"inc_median3": 3000, "cushion_t": 1.0, "dsr_t": 0.59, "bnpl_new3": 8, "savings_rate3": -0.3,
                  "type_employee": 1, "age_25-29": 1, "band_RED": 1})
    assert not any(x.feature in odd for x in fc.forecast(feats).reasons)


def test_the_filter_is_on_as_patrick_decided():
    """W1 (D-93): counterintuitive reasons are left out."""
    assert load_thresholds()["explanations"]["drop_counterintuitive"] is True


# ---------------------------------------------------------------- already Red (W3, Q5)
def test_r10_for_a_user_already_in_red_talks_only_about_running_short():
    adv = {a.rule: a for a in advise(Context(state=state(band=RED, raw_band=RED, band_name="RED", dsr=0.7),
                                             forecast_risk=0.4, forecast_in_red=True))}
    assert "40% chance of money running short" in adv["R10_forecast_elevated"].text
    assert "band gets worse" not in adv["R10_forecast_elevated"].text
    yellow = {a.rule: a for a in advise(Context(state=state(), forecast_risk=0.4))}
    assert "your band gets worse or money runs short" in yellow["R10_forecast_elevated"].text


def test_assess_adds_the_red_note_from_the_models_own_band():
    from engine.assess import RED_NOTE, assess
    from engine.features import UserProfile
    from engine.state import MonthRecord

    def month(debt, k):
        return MonthRecord(net_income=3000, debt_payments=debt, outstanding_debt=debt * 30, cash=2500,
                           essential_spending=1200, total_spending=1700, month=k)
    profile = UserProfile(employment_type="employee", age=26)
    red = assess(profile, [month(1900, k) for k in (3, 4, 5, 6)])                 # 63%: Red every month
    assert red["band"] == "RED" and red["forecast"]["red_note"] == RED_NOTE
    yellow = assess(profile, [month(1200, k) for k in (3, 4, 5, 6)])              # 40%
    assert yellow["forecast"]["red_note"] is None
