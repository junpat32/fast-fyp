"""The app computes forecast features and flags exactly as the O2 pipeline did (T-14a, serving).

For synthetic users we rebuild each user's months as app records (engine.state.MonthRecord) and
compare engine.features / engine.flags with ml.features / the generator's flags. Small differences
can only come from the stored data being rounded (money to 2 dp, ratios to 4 dp).
"""
import numpy as np
import pandas as pd
import pytest
import yaml

from engine.bands import load_thresholds
from engine.features import FEATURES as ENGINE_FEATURES
from engine.features import UserProfile, features_at, user_flags
from engine.state import MonthRecord
from generator.run import ROOT, generate
from ml.features import FEATURES as ML_FEATURES
from ml.features import build_features

ROUNDED = {"dsr_t", "dti_t", "cushion_t", "savings_rate3", "inc_cv3", "disc_cv3", "essential_share3"}


@pytest.fixture(scope="module")
def data():
    cfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text(encoding="utf-8"))
    cfg["n_users"] = 150
    return cfg, generate(cfg, "medium", 4242, with_transactions=False)


def records_of(mo_user: pd.DataFrame) -> list[MonthRecord]:
    return [MonthRecord(net_income=r.net_income, debt_payments=r.commitments_total, outstanding_debt=r.outstanding_debt,
                        cash=r.cash, essential_spending=r.spend_essential, total_spending=r.spend_total,
                        family_support=r.family_support, shortfall=bool(r.shortfall), month=int(r.month),
                        bnpl_purchases=r.bnpl_purchases, bnpl_new_count=int(r.bnpl_new_purchases),
                        personal_loan_balance=r.bal_personal_loan, event_costs=r.event_shock_cost + r.event_minor_cost,
                        shock_count=int(r.shock_count), other_fees=r.late_fees, savings_target=r.savings_target)
            for r in mo_user.sort_values("month").itertuples()]


def profile_of(u) -> UserProfile:
    return UserProfile(employment_type=u.employment_type, age=int(u.age), lives_with_parents=bool(u.lives_with_parents),
                       family_support=bool(u.family_support), festive_month=int(u.festive_month))


def test_same_feature_list_and_order():
    assert list(ENGINE_FEATURES) == list(ML_FEATURES)


def test_flag_thresholds_match_the_generator(data):
    cfg, _ = data
    live = load_thresholds()["flags"]
    for k, v in cfg["flags"].items():
        assert live[k] == v, k
    assert live["budget_factor"] == cfg["spending"]["budget_factor"]


def test_features_and_flags_match_the_o2_pipeline(data):
    cfg, t = data
    ml = build_features(t["monthly"], t["users"], t["flags"]).set_index(["user_id", "t"])
    gen_flags = t["flags"].set_index(["user_id", "month"])
    fcfg = load_thresholds()["flags"]
    exact_mismatch, flag_mismatch, n_feat, n_flag = {}, {}, 0, 0
    for u in t["users"].itertuples():
        recs = records_of(t["monthly"][t["monthly"].user_id == u.user_id])
        prof = profile_of(u)
        fl = user_flags(recs, prof, fcfg, next_target=None)     # generator has no month-13 goal
        for k in fl:
            g = gen_flags.loc[u.user_id][k].astype("Float64").to_numpy(dtype=float, na_value=np.nan)
            same_nan = np.isnan(g) == np.isnan(fl[k])
            assert same_nan.all(), (u.user_id, k)
            ok = np.isnan(g) | (g == fl[k])
            flag_mismatch[k] = flag_mismatch.get(k, 0) + int((~ok).sum())
            n_flag += int((~np.isnan(g)).sum())
        for tt in range(3, 10):
            x = features_at(prof, recs, tt - 1, fl)
            row = ml.loc[(u.user_id, tt)]
            n_feat += 1
            for f in ENGINE_FEATURES:
                tol = 2e-3 if f in ROUNDED else 1e-9
                if not np.isclose(x[f], row[f], atol=tol, rtol=1e-3 if f in ROUNDED else 0):
                    exact_mismatch[f] = exact_mismatch.get(f, 0) + 1
    # Rounding of stored data can flip a borderline comparison (budget overruns, flags) very rarely.
    worst = max([v / n_feat for v in exact_mismatch.values()] + [0])
    worst_flag = max([v / max(n_flag, 1) for v in flag_mismatch.values()] + [0])
    print(f"\nfeature mismatches {exact_mismatch} over {n_feat} rows; flag mismatches {flag_mismatch} over {n_flag}")
    assert worst <= 0.005, exact_mismatch
    assert worst_flag <= 0.005, flag_mismatch
