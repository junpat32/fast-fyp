"""Request validation (T-13). Every field is typed and bounded; unknown fields are rejected, so a
request can't smuggle in a `user_id` (the user is always the token's, api/auth.py)."""
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Money = Annotated[float, Field(ge=0, le=10_000_000)]        # RM; amounts are never negative
Count = Annotated[int, Field(ge=0, le=100)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileIn(Strict):
    employment_type: Literal["employee", "gig", "student"]
    age: int = Field(ge=16, le=80)
    lives_with_parents: bool = False
    family_support: bool = False
    festive_month: int | None = Field(default=None, ge=1, le=12)


class MonthIn(Strict):
    """One month, as engine.state.MonthRecord (see its comments for each field's meaning)."""
    net_income: Money
    debt_payments: Money
    outstanding_debt: Money
    cash: Money
    essential_spending: Money
    total_spending: Money = 0.0
    family_support: Money = 0.0
    shortfall: bool = False
    month: int | None = Field(default=None, ge=1, le=12)
    bnpl_purchases: Money = 0.0
    bnpl_new_count: Count = 0
    bnpl_instalments: Money = 0.0
    personal_loan_balance: Money = 0.0
    event_costs: Money = 0.0
    shock_count: Count = 0
    other_fees: Money = 0.0
    savings_target: Money | None = None


class AssessIn(Strict):
    profile: ProfileIn
    months: list[MonthIn] = Field(min_length=1, max_length=36)       # oldest first; 3 years at most
    next_target: Literal["keep"] | Money | None = "keep"


class AssistantIn(Strict):
    """A question for the money helper (T-17). Never stored."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=500)


class TimeTravelIn(Strict):
    """A persona's time travel (A4, D-90): a month forward or back, or to either end of its range."""
    step: Literal["next", "previous", "first", "last"]


class CardIn(Strict):
    """The answer to this week's life-event card (G-08, D-117); the event and the week are the server's."""
    response: Literal["use_savings", "cut_spending", "set_goal", "not_this_week"]


Cell = Annotated[int, Field(ge=-50, le=50)]
NEEDS = {                                 # which fields each game action takes (same as the database's checks)
    "plant": {"cell", "item"}, "dig": {"cell"}, "buy_tree": set(),
    "decorate": {"item", "spot"}, "move_decoration": {"item", "spot"},
    "choose_animal": {"item"}, "add_animal": {"item"},
}


class GameActionIn(Strict):
    """One thing the user does in the game (D-74): the rules are checked by the replay, the shape here."""
    kind: Literal["plant", "dig", "buy_tree", "decorate", "move_decoration", "choose_animal", "add_animal"]
    cell: tuple[Cell, Cell] | None = None
    item: Annotated[str, Field(pattern=r"^[a-z_]{1,40}$")] | None = None     # plant, decoration or animal
    spot: Annotated[str, Field(min_length=1, max_length=40)] | None = None

    @model_validator(mode="after")
    def _fields_match_kind(self):
        given = {f for f in ("cell", "item", "spot") if getattr(self, f) is not None}
        if given != NEEDS[self.kind]:
            raise ValueError(f"{self.kind} takes {sorted(NEEDS[self.kind]) or 'no other fields'}")
        return self

    def row(self) -> dict:
        """As a game_actions row (no user_id: the database sets it from the token)."""
        gx, gy = self.cell if self.cell else (None, None)
        return {"kind": self.kind, "gx": gx, "gy": gy, "item": self.item, "spot": self.spot}
