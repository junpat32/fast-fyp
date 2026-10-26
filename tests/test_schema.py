"""T-12, offline: the migration SQL itself obeys the rules (no database needed). The live proof that
one user cannot read another's rows is tests/test_rls.py (needs the Supabase project)."""
import re
from pathlib import Path

import pytest

from engine.game import load_game

SQL = (Path(__file__).resolve().parents[1] / "supabase" / "migrations" / "20261014000000_init.sql").read_text(
    encoding="utf-8")
CODE = "\n".join(line.split("--")[0] for line in SQL.splitlines())        # comments removed
TABLES = dict(re.findall(r"create table public\.(\w+) \((.*?)\n\);", CODE, re.S))
POLICIES = re.findall(r'create policy "[^"]+" on public\.(\w+) for (\w+) to (\w+)\s+(.*?);', CODE, re.S)
TRIGGERS = re.findall(r"create trigger (\w+) before ([\w ]+?) on public\.(\w+)\s+for each row execute function "
                      r"public\.(\w+)\(\);", CODE)
MONEY = ["declared_income", "typical_monthly_costs", "onboarding_counted_money", "onboarding_other_money",
         "onboarding_debt", "savings_goal_monthly", "game_typical_costs", "amount", "monthly_payment", "outstanding",
         "monthly_limit", "cash_bank_ewallet", "epf_fleksibel", "others_emergency", "others", "epf_retirement",
         "epf_voluntary", "epf_compulsory_to_fleksibel", "debt_total", "net_income", "logged_in", "logged_out",
         "logged_costs", "logged_debt_paid", "after_month_net", "after_month_debt"]
EDIT_HOURS = load_game()["edit_window_hours"]                          # the one source: shared/game.json
LOCK_48H = f"created_at > now() - interval '{EDIT_HOURS} hours'"
# entries use the user's own clock (a persona's study date), so a participant can fix a typo (S-10)
LOCK_48H_ENTRIES = (f"created_at > (select public.study_now((select auth.uid()))) - interval '{EDIT_HOURS} hours'")


def commands(table: str) -> set[str]:
    return {command for t, command, *_ in POLICIES if t == table}


def policy(table: str, command: str) -> str:
    return next(body for t, c, _, body in POLICIES if t == table and c == command)


def function(name: str) -> str:
    return re.search(rf"function public\.{name}\([^)]*\).*?(end \$\$;|\$\$;)", CODE, re.S).group(0)


def triggers(table: str) -> list[tuple[str, str, str]]:
    """(name, events, function) of a table's triggers, in the order Postgres fires them (by name)."""
    return sorted((name, events, fn) for name, events, t, fn in TRIGGERS if t == table)


def test_tables_found():
    assert set(TABLES) == {"profiles", "goal_changes", "transactions", "debts", "budgets", "monthly_checkins",
                           "life_event_answers", "activity_days", "game_actions", "assessments", "bias_flags"}


@pytest.mark.parametrize("table", sorted(TABLES))
def test_every_table_has_rls_and_a_policy(table):
    """Rule 8: RLS on every table, with at least one policy (RLS with no policy would hide everything)."""
    assert f"alter table public.{table} enable row level security;" in CODE
    assert commands(table)


@pytest.mark.parametrize("table", sorted(TABLES))
def test_every_row_belongs_to_a_user_and_goes_with_them(table):
    """Each row has a user_id tied to auth.users; deleting the user deletes their rows."""
    assert re.search(r"user_id uuid (primary key |not null )?(default auth\.uid\(\) )?"
                     r"references auth\.users \(id\) on delete cascade", TABLES[table])


def test_policies_only_for_signed_in_users_and_own_rows():
    assert POLICIES
    for table, command, role, body in POLICIES:
        assert role == "authenticated", table                      # nothing for anonymous visitors
        if command != "insert":                                    # insert policies have only "with check"
            assert re.search(r"using \(\(select auth\.uid\(\)\) = user_id[\s)]", body), table
        if command in ("all", "insert", "update"):
            assert "with check ((select auth.uid()) = user_id)" in body, table


def test_the_game_view_obeys_rls():
    """game_days runs with the reader's rights, so each user sees only their own days."""
    assert "create view public.game_days with (security_invoker = true) as" in CODE


def test_no_points_or_levels_are_stored():
    """D-76: the game is replayed from facts, so there is nothing a user could write to award
    themselves points or levels."""
    for word in ("points", "game_state", "room_level", "garden_plants", "choices"):
        assert not any(word in name for name in TABLES), word
        assert not re.search(rf"\b{word}\b", "\n".join(TABLES.values())), word


def test_money_is_numeric_never_float():
    """Rule 9."""
    assert not re.search(r"\b(real|float\d*|double precision|money)\b", CODE, re.I)
    for column in MONEY:
        assert re.search(rf"\b{column} numeric\(12,2\)", CODE), column


# ---- C3/C4: time and edit rules enforced in the database
@pytest.mark.parametrize("table", ["profiles", "goal_changes", "transactions", "monthly_checkins",
                                   "life_event_answers", "activity_days", "game_actions"])
def test_the_server_sets_arrival_time_first(table):
    """Every table whose timing matters gets its created_at from the server, before any other
    trigger reads it."""
    first = triggers(table)[0]
    assert first[1:] == ("insert or update", "set_created_at")


def test_set_created_at_ignores_the_client_except_for_admin_scripts():
    """C3: the server's clock (study_now: the real clock, or a study persona's study date, D-90)."""
    body = function("set_created_at")
    assert "new.created_at = public.study_now(new.user_id);" in body and "new.created_at = old.created_at;" in body
    assert "public.is_admin()" in body
    assert "current_user in ('postgres', 'service_role')" in function("is_admin")
    clock = function("study_now")
    assert "p.is_persona" in clock and "), now())" in clock                      # everyone else: the real clock


def test_only_the_admin_script_makes_a_persona():
    """A4 (D-90): a user can't make their own account a persona or change its study range; a persona
    may move its study date only inside the range (the table's checks)."""
    guard = function("guard_study_clock")
    assert "if public.is_admin() then" in guard
    for col in ("is_persona", "study_date", "study_first", "study_last"):
        assert f"new.{col} = " in guard
    assert ("profiles_study", "insert or update", "guard_study_clock") in triggers("profiles")
    table = re.search(r"create table public\.profiles \((.*?)\n\);", CODE, re.S).group(1)
    assert "is_persona boolean not null default false" in table
    assert "check (not is_persona or study_date between study_first and study_last)" in table
    assert "is_persona = (study_date is not null)" in table
    assert "security definer" in re.search(r"function public\.study_now.*?\$\$;", CODE, re.S).group(0)


def test_a_personas_entries_are_saved_on_its_study_date():
    assert ("transactions_clock", "insert", "persona_client_time") in triggers("transactions")
    assert "new.client_logged_at = new.created_at;" in function("persona_client_time")
    assert "public.study_today(new.user_id)" in function("check_checkin_window")
    assert "public.study_today(new.user_id)" in function("set_card_week")


def test_check_ins_never_deleted_and_locked_after_48_hours():
    assert commands("monthly_checkins") == {"select", "insert", "update"}
    assert LOCK_48H in policy("monthly_checkins", "update")


def test_entries_editable_or_deletable_only_for_48_hours():
    """By the user's own clock (S-10, D-96): study_now is the real clock for everyone but a persona."""
    assert commands("transactions") == {"select", "insert", "update", "delete"}
    for command in ("update", "delete"):
        assert LOCK_48H_ENTRIES in " ".join(policy("transactions", command).split()), command


def test_check_ins_keep_the_real_clock():
    """A persona's seeded latest check-in must stay locked on its start date (participants don't edit it)."""
    assert "study_now" not in policy("monthly_checkins", "update")


@pytest.mark.parametrize("table", ["transactions", "activity_days"])
def test_entries_and_no_spend_taps_saved_offline_at_most_24_hours_earlier(table):
    assert ("check (client_logged_at between created_at - interval '24 hours' and created_at + "
            "interval '5 minutes')") in TABLES[table]


def test_check_in_window():
    """Only months since sign-up; during the month or the first 7 days after it (game.json)."""
    assert [t[0] for t in triggers("monthly_checkins")] == ["checkins_arrival", "checkins_sums", "checkins_window"]
    body = function("check_checkin_window")
    assert "before you joined" in body and "cannot change" in body
    grace = load_game()["checkin_grace_days"]
    month_end = "(new.month + interval '1 month' - interval '1 day')::date"
    assert f"today < {month_end}" in body                        # D-77: opens on the month's last day
    assert f"today > {month_end} + {grace}" in body


def test_check_ins_keep_the_months_logged_totals():
    """Option 2: the server sums the month's entries that arrived before the check-in (or an edit);
    credit purchases count when paid, own transfers never; what the client sends is overwritten."""
    body = function("freeze_logged_sums")
    assert "into new.logged_in, new.logged_out, new.logged_costs, new.logged_debt_paid" in body
    assert "t.created_at <= arrived_by" in body and body.count("t.user_id = new.user_id") == 2
    assert body.count("not t.on_credit and not t.is_bnpl") == 2 and body.count("not t.is_own_transfer") == 4


def test_check_ins_know_what_was_logged_after_the_month_ended():
    """D-77: entries dated after the month, up to the check-in day, that arrived before the check-in,
    so the game can use money and debt as at the end of the month."""
    body = function("freeze_logged_sums")
    assert "into new.after_month_net, new.after_month_debt" in body
    assert "t.occurred_on > month_end and t.occurred_on <= checkin_day" in body
    assert "t.created_at <= new.created_at;" in body                  # balances are as at the check-in
    assert "after_month_net numeric(12,2)" in TABLES["monthly_checkins"]


@pytest.mark.parametrize("table", ["life_event_answers", "goal_changes", "activity_days", "game_actions",
                                   "assessments", "bias_flags"])
def test_add_only_tables(table):
    """Facts and the engine's caches: a saved month can't be rewritten or removed (S-3, D-93)."""
    assert commands(table) == {"select", "insert"}


# ---- security review (D-93)
def test_a_profile_is_never_deleted_on_its_own():
    """S-1: deleting and re-creating the profile would reopen the sign-up numbers (48-hour lock, I1)."""
    assert commands("profiles") == {"select", "insert", "update"}


def test_users_can_delete_their_whole_account_but_personas_cannot():
    """S-2 (PDPA, privacy Screen 3): the account and, by cascade, every row about it."""
    body = function("delete_my_account")
    assert "security definer" in body and "delete from auth.users where id = (select auth.uid());" in body
    assert "p.is_persona" in body and "raise exception 'not signed in'" in body
    assert "revoke execute on function public.delete_my_account() from public, anon;" in CODE
    assert "grant execute on function public.delete_my_account() to authenticated;" in CODE


def test_the_persona_clock_answers_only_for_the_caller():
    """S-5: study_now is callable through the API; it must not reveal another account's persona flag."""
    assert "uid = (select auth.uid())" in function("study_now")


@pytest.mark.parametrize("table, cap", [("transactions", 200), ("game_actions", 100), ("goal_changes", 20)])
def test_daily_caps_on_add_only_rows(table, cap):
    """S-6: one account can't add rows without end (the API reads them all on every request)."""
    assert (f"create trigger {table}_limit before insert on public.{table}\n"
            f"  for each row execute function public.limit_daily_rows('{cap}');") in CODE
    assert f"{table}_arrival" < f"{table}_limit"                    # fires after the arrival time is set
    body = function("limit_daily_rows")
    assert "if public.is_admin() then" in body and "tg_argv[0]::integer" in body


def test_cards_and_no_spend_days_are_dated_by_the_server():
    assert ("cards_week", "insert or update", "set_card_week") in triggers("life_event_answers")
    assert [t[1:] for t in triggers("activity_days")] == [("insert or update", "set_created_at"),
                                                          ("insert", "persona_client_time"),     # D-90
                                                          ("insert", "no_spend_day")]
    body = function("no_spend_day")
    assert "new.day = (new.client_logged_at at time zone 'Asia/Kuala_Lumpur')::date;" in body
    assert "new.logged = false;" in body and "new.card = false;" in body


def test_the_edit_window_matches_the_game_config():
    """One source for the 48 hours: the database's locks and the app's "pending" points agree."""
    assert CODE.count(f"interval '{EDIT_HOURS} hours'") == 4               # 3 edit policies + the sign-up lock
    assert set(re.findall(r"interval '(\d+) hours'", CODE)) == {str(EDIT_HOURS), "24"}   # 24: offline allowance


def test_game_actions_shape_matches_the_api():
    from api.models import NEEDS
    kinds = set(re.findall(r"'(\w+)'", re.search(r"kind text not null check \(kind in \((.*?)\)\)",
                                                 TABLES["game_actions"], re.S).group(1)))
    assert kinds == set(NEEDS)


def test_sign_up_numbers_lock_and_the_game_keeps_its_own_copy():
    assert [t[0] for t in triggers("profiles")][:2] == ["profiles_arrival", "profiles_lock"]
    body = function("lock_sign_up_numbers")
    for column in ("declared_income", "onboarding_counted_money", "onboarding_debt", "savings_goal_monthly"):
        assert f"new.{column} is distinct from old.{column}" in body
    for column in ("employment_type", "lives_with_parents"):
        assert f"new.game_{column} = new.{column};" in body and f"new.game_{column} = old.game_{column};" in body


def test_functions_pin_search_path():
    """Supabase's linter: every function sets search_path, so a user can't shadow a table."""
    blocks = re.findall(r"create or replace function public\.\w+\([^)]*\)[^$]*?\$\$", CODE, re.S)
    assert len(blocks) == CODE.count("create or replace function") == 15
    for block in blocks:
        assert "set search_path = ''" in block


def test_retention_keeps_the_games_dates_then_deletes_details():
    job = re.search(r"cron\.schedule\('fast-retention-36-months'.*?\$\$\);", CODE, re.S).group(0)
    assert "create extension if not exists pg_cron;" in CODE
    for table in ("transactions", "assessments", "bias_flags", "life_event_answers"):
        assert re.search(rf"delete from public\.{table}\s+where \w+\s+< current_date - interval '36 months'", job)
    assert job.index("insert into public.activity_days (user_id, day, logged)") < job.index(
        "delete from public.transactions")
    assert job.index("insert into public.activity_days (user_id, day, card)") < job.index(
        "delete from public.life_event_answers")
    assert "monthly_checkins" not in job and "game_actions" not in job      # facts the game replays stay
