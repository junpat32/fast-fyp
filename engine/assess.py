"""assess(): the one call the API and app use. Everything FAST computes about a user's latest month.

    band (shown, with improvement confirmation D-49) + raw band, DSR, DTI, cushion
    health score (D-48) with its four indicators
    forecast: calibrated 3-month risk + top-3 reasons (needs >= 3 months of records)
    user-facing flags only (S14, D-41)
    ranked advice from the rule engine

Invariants
  Q1  deterministic: same profile + records -> same output
  Q2  uses only the user's own records and profile (no other user's data, no hidden traits)
  Q3  the output contains numbers and rule ids only, so it can be summarised for Groq without
      raw transactions (CLAUDE.md rule 10)
  Q4  no forecast while income is too low to judge (the INSUFFICIENT state): O2 left those months
      out of training (spec §11), so the model has never seen one; a short note says so (D-90)
  Q5  when the model's own band for the month is Red (spec v1 rule, the band its label compares),
      the band can't get worse, so the forecast only measures running short (spec §11 property 1);
      a note says so and R10 words it that way (W3, D-93). Keyed on the model's band, not the shown
      one: a user shown Red while an improvement waits (D-49) can still go back to Red
"""
from __future__ import annotations

from dataclasses import asdict

from .bands import NAMES, load_thresholds
from .features import UserProfile, features_at, user_flags
from .forecast import forecast
from .health import health_score
from .rules import Context, advise
from .state import MonthRecord, compute_states

RED_NOTE = "You're already in Red, so this is the chance of running short of money."   # Q5; DRAFT wording (W3)


def assess(profile: UserProfile, records: list[MonthRecord], next_target="keep") -> dict:
    if not records:
        raise ValueError("at least one month of records is needed")
    t = load_thresholds()
    states = compute_states(records, t)
    s, last = states[-1], records[-1]
    win = records[-3:]
    hs = health_score(s, t)

    fc, flags_now, fc_note, in_red = None, {}, None, False
    if len(records) >= 3:
        fl = user_flags(records, profile, t["flags"], next_target)
        i = len(records) - 1
        flags_now = {k: bool(v[i] == 1) for k, v in fl.items() if k in t["user_facing_flags"]}
        if s.insufficient_income:                                        # Q4
            fc_note = "No forecast while income is too low to judge."
        else:
            feats = features_at(profile, records, i, fl)
            fc = forecast(feats)
            in_red = feats["band_RED"] == 1                              # Q5

    ctx = Context(state=s, debt_payments=last.debt_payments,
                  essentials_and_debts=sum(r.essential_spending + r.debt_payments for r in win) / len(win),
                  cash=last.cash,
                  bnpl_plans=(records[-2].bnpl_new_count if len(records) > 1 else 0) + last.bnpl_new_count,
                  bnpl_monthly=last.bnpl_instalments, flags=flags_now,
                  festive_month=profile.festive_month is not None and profile.festive_month == last.month,
                  forecast_risk=fc.probability if fc else None, forecast_in_red=in_red)
    advice = advise(ctx, t)
    return {
        "month": last.month,
        "band": s.band_name, "raw_band_this_month": NAMES[s.raw_band],
        "insufficient_income": s.insufficient_income,
        "dsr": round(s.dsr, 4), "dti": round(s.dti, 4), "cushion_months": round(s.cushion_months, 2),
        "health": {"score": hs.score, "tier": hs.tier, "indicators": hs.indicators},
        "forecast": None if fc is None else {"probability": fc.probability, "base_rate": fc.base_rate,
                                             "version": fc.version, "reasons": [asdict(r) for r in fc.reasons],
                                             "note": fc.note, "red_note": RED_NOTE if in_red else None},
        "forecast_note": fc_note,
        "flags": flags_now,
        "advice": [{"rule": a.rule, "priority": a.priority, "title": a.title, "short": a.short, "text": a.text}
                   for a in advice],
    }
