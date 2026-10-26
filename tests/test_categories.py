"""shared/categories.json (D-112): one category list for the app's Add screen and the personas' data,
so a typed entry means to the engine exactly what a synthetic one does (rule 5)."""
import json
from pathlib import Path

from api import money as m
from tools.personas import build

ROOT = Path(__file__).resolve().parents[1]
CATS = json.loads((ROOT / "shared" / "categories.json").read_text(encoding="utf-8"))
OUT_KEYS = {c["key"] for c in CATS["out"]}
IN_KEYS = {c["key"] for c in CATS["in"]}


def test_keys_are_unique_and_fit_the_database():
    for side in ("out", "in"):
        keys = [c["key"] for c in CATS[side]]
        assert len(keys) == len(set(keys)), side
        assert all(1 <= len(k) <= 40 for k in keys)                        # transactions.category check
    assert all(c["group"] in CATS["groups"] for c in CATS["out"])


def test_essentials_follow_d28():
    """HES 2024 by Engel's law: housing, food at home, transport, communication, health, education."""
    assert {c["key"] for c in CATS["out"] if c["essential"]} == {
        "housing", "food_home", "transport", "communication", "health", "education"}
    assert build.ESSENTIAL == {c["key"] for c in CATS["out"] if c["essential"]}   # the personas read the same list


def test_the_keys_the_api_reads_exist():
    assert {m.FAMILY, m.EDUCATION, m.FEES} <= OUT_KEYS


def test_debt_payments_and_own_transfers_are_flagged():
    assert {c["key"] for c in CATS["out"] if c.get("debt_payment")} == {
        "ptptn", "car_loan", "motorbike_loan", "personal_loan", "credit_card", "bnpl_instalment",
        "home_loan", "other_debt"}                                       # D-126: every debts-list kind has one
    assert not any(c.get("essential") for c in CATS["out"] if c.get("debt_payment") or c.get("own_transfer"))
    assert "own_transfer" in OUT_KEYS and "own_transfer" in IN_KEYS


def test_quick_add_words_are_lowercase_and_never_shared_within_a_side():
    """D-126: the quick-add box matches these; one word or phrase points to one category."""
    for side in ("out", "in"):
        words = [w for c in CATS[side] for w in c["words"]]
        assert all(c["words"] for c in CATS[side]), side
        assert all(w == w.lower().strip() and w for w in words)
        assert len(words) == len(set(words)), [w for w in words if words.count(w) > 1]


def test_every_category_the_personas_use_is_in_the_list():
    personas = json.loads(build.OUT.read_text(encoding="utf-8"))["personas"]
    used_out = {t["category"] for p in personas for t in p["transactions"] if t["direction"] == "out"}
    used_in = {t["category"] for p in personas for t in p["transactions"] if t["direction"] == "in"}
    assert used_out <= OUT_KEYS, used_out - OUT_KEYS
    assert used_in <= IN_KEYS, used_in - IN_KEYS
