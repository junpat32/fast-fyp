"""Generator invariants (spec §3 G1-G4, §8, §9, §10, §11). Runs on a small population for speed."""
import hashlib

import numpy as np
import pandas as pd
import pytest
import yaml

from generator.bands import band_array
from generator.flags import compute_flags
from generator.population import build_population
from generator.run import ROOT, generate, make_rngs, write
from generator.simulate import simulate

CFG_PATH = ROOT / "generator" / "config.yaml"
HIDDEN = {"imp", "dis", "ovc", "sigma_inc", "consumption_ratio", "hidden_cost", "start_cushion_months"}


@pytest.fixture(scope="module")
def cfg():
    c = yaml.safe_load(CFG_PATH.read_text(encoding="utf-8"))
    c["n_users"] = 300
    return c


@pytest.fixture(scope="module")
def tables(cfg):
    return generate(cfg, "medium", 123)


@pytest.fixture(scope="module")
def raw(cfg):
    rngs = make_rngs(123)
    p = build_population(cfg, rngs["population"])
    return p, simulate(p, cfg, "medium", rngs)


def _hashes(folder):
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.iterdir())}


def test_G1_same_seed_byte_identical(cfg, tmp_path):
    for d in ("a", "b"):
        write(generate(cfg, "medium", 7), tmp_path / d, CFG_PATH, "medium", 7, cfg["n_users"])
    assert _hashes(tmp_path / "a") == _hashes(tmp_path / "b")


def test_G1_different_seed_differs(cfg):
    a = generate(cfg, "medium", 1)["monthly"]
    b = generate(cfg, "medium", 2)["monthly"]
    assert not a.equals(b)


def test_G2_hidden_traits_only_in_latent(tables):
    for name in ("users", "monthly", "transactions", "flags", "labels"):
        assert not HIDDEN & set(tables[name].columns), name


def test_G3_money_two_dp_and_finite(tables):
    mo = tables["monthly"]
    for c in mo.columns:
        if mo[c].dtype == float and c not in ("dsr", "dti", "cushion_months"):
            assert np.isfinite(mo[c]).all(), c
            assert np.allclose(mo[c], mo[c].round(2)), c
    assert np.isfinite(tables["transactions"].amount).all()


def test_E1_E2_cash_and_balances_never_negative(tables):
    mo = tables["monthly"]
    for c in ["cash", "arrears", "outstanding_debt"] + [c for c in mo.columns if c.startswith("bal_")]:
        assert (mo[c] >= 0).all(), c


def test_bnpl_is_a_payment_method_not_extra_spending(raw):
    _, r = raw
    assert np.allclose(r["cash_spend"] + r["bnpl_buy"], r["ess"] + r["disc"])
    assert (r["bnpl_buy"] <= r["disc"] + 1e-9).all()


def test_bands_match_shared_thresholds(raw):
    _, r = raw
    with np.errstate(divide="ignore", invalid="ignore"):
        for m in range(r["band"].shape[1]):
            med3 = np.median(r["income"][:, max(0, m - 2):m + 1], axis=1)
            prev = r["band"][:, m - 1] if m else None
            expect = band_array(np.minimum(r["dsr"][:, m], 9.99), med3, prev)
            assert (expect == r["band"][:, m]).all(), m


def test_students_never_repay_ptptn_or_hold_vehicle_loans(tables):
    u = tables["users"]
    s = u[u.employment_type == "student"]
    assert not s.has_ptptn.any() and not s.has_car_loan.any() and not s.has_motorbike_loan.any()
    assert not s.has_credit_card.any()


def test_credit_card_rules(tables):
    u, lat = tables["users"], tables["latent"]
    holders = u[u.has_credit_card].merge(lat[["user_id", "gross_base"]], on="user_id")
    assert (holders.age >= 21).all() and (holders.gross_base >= 2000).all()
    assert np.allclose(holders.credit_limit, (2 * holders.gross_base).round(2), atol=0.02)


def test_labels_months_and_exclusions(tables):
    lab = tables["labels"]
    assert set(lab.t.unique()) == set(range(3, 10))
    ex = lab[lab.exclusion_reason != ""]
    assert ex.y.isna().all()
    assert ((ex.band_t == "INSUFFICIENT_INCOME") | (ex.band_t3 == "INSUFFICIENT_INCOME")).all()
    kept = lab[lab.exclusion_reason == ""]
    assert (kept.y == (kept.worsened | kept.shortfall_t1_t3).astype(int)).all()


def test_flags_have_no_look_ahead(raw, cfg):
    """F1: flags up to month m must not change when months after m are altered."""
    p, r = raw
    full = compute_flags(r, p["festive_month"], cfg["flags"])
    cut = 7
    trunc = {k: (v[:, :cut + 1] if isinstance(v, np.ndarray) and v.ndim == 2 else v) for k, v in r.items()}
    part = compute_flags(trunc, p["festive_month"], cfg["flags"])
    for k in full:
        # overconfidence at m uses the target for m+1 (set from data up to m), so compare up to cut-1
        last = cut - 1 if k == "overconfidence" else cut
        a, b = full[k][:, :last + 1], part[k][:, :last + 1]
        assert np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(np.nan_to_num(a), np.nan_to_num(b)), k


@pytest.mark.parametrize("category", ["housing", "food_home", "transport", "health"])
def test_transactions_match_monthly_spending(tables, category):
    """T1: routine spending transactions (life events excluded) sum to the monthly figure.
    Essential categories only: discretionary ones are split into cash-paid and BNPL-paid parts."""
    tx, mo = tables["transactions"], tables["monthly"]
    tx = tx[(tx.kind == "spending") & (tx.category == category)]
    got = tx.assign(month=tx.date.dt.month).groupby(["user_id", "month"]).amount.sum()
    want = mo.set_index(["user_id", "month"])[f"spend_{category}"]
    want = want[want > 0.005]
    # each transaction is rounded to 2 dp, so allow a few sen per transaction
    assert np.allclose(got.reindex(want.index).fillna(0), want, atol=0.10)


def test_no_real_brand_names(tables):
    merchants = " ".join(tables["transactions"].merchant.unique()).upper()
    for brand in ("MAYBANK", "CIMB", "GRAB", "SHOPEE", "ATOME", "TNG", "LAZADA"):
        assert brand not in merchants
