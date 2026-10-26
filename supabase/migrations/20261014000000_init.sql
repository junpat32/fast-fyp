-- FAST database schema v3 (T-12; D-71, D-75, D-76). Apply in the Supabase dashboard: SQL editor -> paste -> Run.
--
-- Rules this file enforces (CLAUDE.md §5):
--   rule 8  Row Level Security on EVERY table: a user sees and changes only rows where
--           user_id = auth.uid(). The backend queries as the signed-in user; the service-role key
--           is for admin scripts only (e.g. seeding the user-study personas).
--   rule 9  money is NUMERIC(12,2), never float.
--   rule 12 synthetic data only during the FYP.
-- The game (D-76): points, levels and the garden are NEVER stored. The backend replays the user's
-- own facts (sign-up, check-ins, logging days, cards, goal changes, game actions) through
-- engine/game.py on every request, so there is nothing a user could write to award themselves
-- points, and the rules live in one place. Facts must therefore never rewrite history:
-- Game-integrity rules (D-75; docs/game_design.md §3a), enforced here so the app can't bypass them (C4):
--   C3  the SERVER's clock decides when something arrived (created_at is always set by the server);
--       a check-in only for a month since sign-up, from its last day until 7 days after it (D-77);
--       entries may be logged offline up to 24 hours before they reach the server; check-ins and
--       entries can be edited for 48 hours, then they are locked; check-ins are never deleted;
--       the game's sign-up numbers lock after 48 hours (goals change through goal_changes)
--   each check-in keeps the month's logged totals as they were when it was made (or edited), so
--   deleting old entries (retention) or adding late ones never changes a past month; and what was
--   logged after the month ended, so the game uses money and debt as at the END of the month
--   (D-77), the same period as the month's entries, whatever day the user checks in
-- Admin scripts (service_role, or postgres in the SQL editor and pg_cron) skip the time checks so
-- personas with past months can be seeded for the user study (CLAUDE.md §7, Must).
-- Deleting a user (auth.users) deletes all their rows (on delete cascade).
-- Retention: details older than 36 months are deleted nightly; only the dates the game needs are
-- kept (activity_days), so deletion never lowers a level.

-- ---------------------------------------------------------------- helpers
create or replace function public.set_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.updated_at = now();
  return new;
end $$;

-- admin scripts (persona seeding, retention) may write history; users never can
create or replace function public.is_admin() returns boolean
language sql stable set search_path = '' as $$
  select current_user in ('postgres', 'service_role')
$$;

-- user-study personas (A4, D-90): their clock is the study date, at noon Malaysia time; everyone
-- else's is the real clock. security definer so it can read the persona flag whatever the caller.
-- It answers only for the caller (security review S-5, D-93): any signed-in user can call a public
-- function through the API, and must not learn whether another account is a persona
create or replace function public.study_now(uid uuid) returns timestamptz
language sql stable security definer set search_path = '' as $$
  select coalesce((select (p.study_date + time '12:00') at time zone 'Asia/Kuala_Lumpur'
                     from public.profiles p
                    where p.user_id = uid and p.is_persona and uid = (select auth.uid())), now())
$$;

create or replace function public.study_today(uid uuid) returns date
language sql stable set search_path = '' as $$
  select (public.study_now(uid) at time zone 'Asia/Kuala_Lumpur')::date
$$;

-- C3: the server decides when a row arrived; a client-sent created_at is ignored (a persona's rows
-- arrive on its study date, so what a participant does shows up on the persona's day)
create or replace function public.set_created_at() returns trigger
language plpgsql set search_path = '' as $$
begin
  if public.is_admin() then
    if tg_op = 'UPDATE' then
      new.created_at = old.created_at;
    end if;
    return new;
  end if;
  if tg_op = 'INSERT' then
    new.created_at = public.study_now(new.user_id);
  else
    new.created_at = old.created_at;
  end if;
  return new;
end $$;

-- a persona's entries and taps are "saved on the phone" on its study date too (the 24-hour
-- offline check compares the two)
create or replace function public.persona_client_time() returns trigger
language plpgsql set search_path = '' as $$
begin
  if not public.is_admin() and exists (select 1 from public.profiles p where p.user_id = new.user_id and p.is_persona) then
    new.client_logged_at = new.created_at;
  end if;
  return new;
end $$;

-- only the admin script makes a persona or sets its study range; the persona's own account may move
-- its study date within that range (time travel; the table's checks enforce the range)
create or replace function public.guard_study_clock() returns trigger
language plpgsql set search_path = '' as $$
begin
  if public.is_admin() then
    return new;
  end if;
  if tg_op = 'INSERT' then
    new.is_persona = false;
    new.study_date = null;
    new.study_first = null;
    new.study_last = null;
  else
    new.is_persona = old.is_persona;
    new.study_first = old.study_first;
    new.study_last = old.study_last;
  end if;
  return new;
end $$;

-- availability (security review S-6, D-93): the API reads all of a user's rows on every request, so
-- one account adding rows without end could exhaust the server for everyone. A cap per user per day
-- on the add-only tables (the argument), far above any honest use; admin scripts are exempt
create or replace function public.limit_daily_rows() returns trigger
language plpgsql set search_path = '' as $$
declare
  n integer;
begin
  if public.is_admin() then
    return new;
  end if;
  execute format('select count(*) from public.%I where user_id = $1 and created_at > $2 - interval ''1 day''',
                 tg_table_name) into n using new.user_id, new.created_at;
  if n >= tg_argv[0]::integer then
    raise exception 'that is a lot for one day; please try again tomorrow';
  end if;
  return new;
end $$;

-- PDPA (security review S-1, S-2, D-93): a user deletes their own account, and with it every row
-- about them (on delete cascade), as privacy Screen 3 promises. Users can't delete their profile row
-- on its own (that would reopen the sign-up numbers). security definer: only the owner may delete
-- from auth.users, and it deletes the caller only. Study personas are reset by the researcher
create or replace function public.delete_my_account() returns void
language plpgsql security definer set search_path = '' as $$
begin
  if (select auth.uid()) is null then
    raise exception 'not signed in';
  end if;
  if exists (select 1 from public.profiles p where p.user_id = (select auth.uid()) and p.is_persona) then
    raise exception 'study accounts are reset by the researcher';
  end if;
  delete from auth.users where id = (select auth.uid());
end $$;
revoke execute on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;

-- today in Malaysia (game days start at 00:00 MYT: shared/game.json day_starts_utc_offset_hours)
create or replace function public.my_today() returns date
language sql stable set search_path = '' as $$
  select (now() at time zone 'Asia/Kuala_Lumpur')::date
$$;

-- ---------------------------------------------------------------- user-written tables
create table public.profiles (
  user_id uuid primary key default auth.uid() references auth.users (id) on delete cascade,
  -- the current situation (editable; the risk engine reads these)
  employment_type text not null check (employment_type in ('employee', 'gig', 'student')),
  birth_year smallint not null check (birth_year between 1940 and 2015),
  lives_with_parents boolean not null default false,
  family_support boolean not null default false,
  festive_month smallint check (festive_month between 1 and 12),
  vehicle text not null default 'none' check (vehicle in ('none', 'motorcycle', 'car', 'both')),   -- D-35
  typical_monthly_costs numeric(12,2) check (typical_monthly_costs >= 0),    -- null: "not sure"
  -- the sign-up check-in (C6) and goal: lock after 48 hours
  declared_income numeric(12,2) not null check (declared_income >= 0),       -- net, a month
  onboarding_counted_money numeric(12,2) not null check (onboarding_counted_money >= 0),
  onboarding_other_money numeric(12,2) not null default 0 check (onboarding_other_money >= 0),
  onboarding_debt numeric(12,2) not null default 0 check (onboarding_debt >= 0),
  savings_goal_monthly numeric(12,2) check (savings_goal_monthly >= 0),      -- employees, students
  savings_goal_share numeric(4,3) check (savings_goal_share > 0 and savings_goal_share <= 1),   -- gig
  -- the game's copy of the situation at sign-up (set by the server, locked after 48 hours), so a
  -- later change (a student starts work, moves out) can't rewrite past months
  game_employment_type text check (game_employment_type in ('employee', 'gig', 'student')),
  game_lives_with_parents boolean,
  game_typical_costs numeric(12,2) check (game_typical_costs >= 0),
  -- the character the user chose at sign-up (D-124; the kit's avatar_01-06 and its 6 skin tones), any time
  avatar smallint check (avatar between 1 and 6),
  skin_tone smallint check (skin_tone between 1 and 6),
  glasses boolean not null default false,
  -- user-study personas only (A4, D-90): seeded by the admin script, never set by a user. The server
  -- treats study_date as "today" for these accounts; time travel moves it between first and last
  is_persona boolean not null default false,
  study_date date,
  study_first date,
  study_last date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (is_persona = (study_date is not null) and is_persona = (study_first is not null)
         and is_persona = (study_last is not null)),
  check (not is_persona or study_date between study_first and study_last)
);

create or replace function public.lock_sign_up_numbers() returns trigger
language plpgsql set search_path = '' as $$
begin
  if public.is_admin() then
    return new;
  end if;
  if tg_op = 'INSERT' or old.created_at >= now() - interval '48 hours' then
    new.game_employment_type = new.employment_type;               -- still fixing sign-up typos
    new.game_lives_with_parents = new.lives_with_parents;
    new.game_typical_costs = new.typical_monthly_costs;
    return new;
  end if;
  if new.declared_income is distinct from old.declared_income
    or new.onboarding_counted_money is distinct from old.onboarding_counted_money
    or new.onboarding_other_money is distinct from old.onboarding_other_money
    or new.onboarding_debt is distinct from old.onboarding_debt
    or new.savings_goal_monthly is distinct from old.savings_goal_monthly
    or new.savings_goal_share is distinct from old.savings_goal_share then
    raise exception 'sign-up numbers lock after 48 hours; a new goal goes in goal_changes';
  end if;
  new.game_employment_type = old.game_employment_type;
  new.game_lives_with_parents = old.game_lives_with_parents;
  new.game_typical_costs = old.game_typical_costs;
  return new;
end $$;

create table public.goal_changes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  amount numeric(12,2) check (amount >= 0),
  share numeric(4,3) check (share > 0 and share <= 1),
  created_at timestamptz not null default now(),                           -- applies from next month
  check (amount is not null or share is not null)
);
create index goal_changes_user on public.goal_changes (user_id, created_at);

create table public.transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  occurred_on date not null,                                                -- any date (C3)
  direction text not null check (direction in ('in', 'out')),
  amount numeric(12,2) not null check (amount > 0),
  category text not null check (char_length(category) between 1 and 40),
  is_essential boolean not null default false,
  is_bnpl boolean not null default false,                                   -- a BNPL plan (forecast input)
  on_credit boolean not null default false,                                 -- card or BNPL: money leaves when paid
  is_debt_payment boolean not null default false,
  is_own_transfer boolean not null default false,                           -- between own pockets, EPF top-ups
  is_unexpected boolean not null default false,
  note text check (char_length(note) <= 120),
  source text not null default 'typed' check (source in ('typed', 'pasted', 'receipt')),
  client_logged_at timestamptz not null default now(),                      -- when the phone saved it
  created_at timestamptz not null default now(),                            -- when the server got it
  check (client_logged_at between created_at - interval '24 hours' and created_at + interval '5 minutes')
);
create index transactions_user_date on public.transactions (user_id, occurred_on desc);

create table public.debts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  kind text not null check (kind in ('ptptn', 'car', 'housing', 'personal', 'credit_card', 'bnpl', 'other')),
  label text check (char_length(label) <= 40),
  monthly_payment numeric(12,2) not null check (monthly_payment >= 0),
  outstanding numeric(12,2) not null check (outstanding >= 0),
  deducted_from_salary boolean not null default false,                      -- e.g. PTPTN potongan gaji
  annual_rate numeric(5,4) check (annual_rate is null or annual_rate between 0 and 1),  -- 0.18 = 18% a year; null = not given (D-144)
  starts_on date,
  ends_on date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (ends_on is null or starts_on is null or ends_on >= starts_on)
);
create index debts_user on public.debts (user_id);

create table public.budgets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  category text not null check (char_length(category) between 1 and 40),
  monthly_limit numeric(12,2) not null check (monthly_limit > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, category)
);

create table public.monthly_checkins (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  month date not null check (month = date_trunc('month', month)::date),     -- first day of the month
  -- money sections (C6): the first three are "counted money" (the cushion)
  cash_bank_ewallet numeric(12,2) not null check (cash_bank_ewallet >= 0),
  epf_fleksibel numeric(12,2) not null default 0 check (epf_fleksibel >= 0),
  others_emergency numeric(12,2) not null default 0 check (others_emergency >= 0),
  others numeric(12,2) not null default 0 check (others >= 0),             -- e.g. ASB not for emergencies
  epf_retirement numeric(12,2) check (epf_retirement >= 0),                -- Persaraan + Sejahtera: shown only
  epf_voluntary numeric(12,2) not null default 0 check (epf_voluntary >= 0),               -- top-ups, i-Saraan
  epf_compulsory_to_fleksibel numeric(12,2) not null default 0 check (epf_compulsory_to_fleksibel >= 0),
  debt_total numeric(12,2) not null check (debt_total >= 0),
  net_income numeric(12,2) check (net_income >= 0),
  bills_paid_on_time boolean not null,
  ran_short boolean not null default false,                                -- ran out of cash or missed a payment
  -- the month's logged totals, set by the server from the user's entries (option 2, D-75)
  logged_in numeric(12,2) not null default 0,
  logged_out numeric(12,2) not null default 0,
  logged_costs numeric(12,2) not null default 0,                           -- essentials + debt payments
  logged_debt_paid numeric(12,2) not null default 0,
  -- what was logged after the month ended, up to the check-in (D-77): the balances above are as at
  -- the check-in; minus these, they are as at the end of the month, the same period as the entries
  after_month_net numeric(12,2) not null default 0,                       -- money in - out since month end
  after_month_debt numeric(12,2) not null default 0,                      -- bought on credit - debt paid since
  created_at timestamptz not null default now(),
  unique (user_id, month)
);

-- option 2 (D-75, D-77), set by the server, whatever the client sends:
--   the month's logged money: entries dated in the month that arrived before the check-in (or
--   before an edit, within 48 hours, so late-logged entries can still be added);
--   since the month ended: entries dated after it, up to the check-in day, that arrived before the
--   check-in (the balances are as at the check-in, even after an edit).
-- Purchases on credit count when they are paid; moving money between one's own pockets is neither
-- in nor out.
create or replace function public.freeze_logged_sums() returns trigger
language plpgsql set search_path = '' as $$
declare
  arrived_by timestamptz := case when tg_op = 'UPDATE' then now() else new.created_at end;
  month_end date := (new.month + interval '1 month' - interval '1 day')::date;
  checkin_day date := (new.created_at at time zone 'Asia/Kuala_Lumpur')::date;
begin
  select coalesce(sum(t.amount) filter (where t.direction = 'in' and not t.is_own_transfer), 0),
         coalesce(sum(t.amount) filter (where t.direction = 'out' and not t.is_own_transfer
                                              and not t.on_credit and not t.is_bnpl), 0),
         coalesce(sum(t.amount) filter (where t.direction = 'out' and (t.is_essential or t.is_debt_payment)), 0),
         coalesce(sum(t.amount) filter (where t.direction = 'out' and t.is_debt_payment), 0)
    into new.logged_in, new.logged_out, new.logged_costs, new.logged_debt_paid
    from public.transactions t
   where t.user_id = new.user_id
     and t.occurred_on between new.month and month_end
     and t.created_at <= arrived_by;
  select coalesce(sum(t.amount) filter (where t.direction = 'in' and not t.is_own_transfer), 0)
         - coalesce(sum(t.amount) filter (where t.direction = 'out' and not t.is_own_transfer
                                                and not t.on_credit and not t.is_bnpl), 0),
         coalesce(sum(t.amount) filter (where t.direction = 'out' and (t.on_credit or t.is_bnpl)), 0)
         - coalesce(sum(t.amount) filter (where t.direction = 'out' and t.is_debt_payment), 0)
    into new.after_month_net, new.after_month_debt
    from public.transactions t
   where t.user_id = new.user_id
     and t.occurred_on > month_end and t.occurred_on <= checkin_day
     and t.created_at <= new.created_at;
  return new;
end $$;

-- C3, D-77: only months since sign-up, from the month's last day until 7 days after it (game.json
-- checkin_grace_days), by the server's Malaysian date; the month itself can never change
create or replace function public.check_checkin_window() returns trigger
language plpgsql set search_path = '' as $$
declare
  today date := public.study_today(new.user_id);
  joined date;
begin
  if tg_op = 'UPDATE' and new.month <> old.month then
    raise exception 'the month of a check-in cannot change';
  end if;
  if tg_op = 'UPDATE' or public.is_admin() then
    return new;
  end if;
  select (p.created_at at time zone 'Asia/Kuala_Lumpur')::date into joined
    from public.profiles p where p.user_id = new.user_id;
  if joined is null then
    raise exception 'finish sign-up first';
  end if;
  if new.month < date_trunc('month', joined)::date then
    raise exception 'no check-ins for months before you joined';
  end if;
  if today < (new.month + interval '1 month' - interval '1 day')::date
     or today > (new.month + interval '1 month' - interval '1 day')::date + 7 then
    raise exception 'a month can be checked in from its last day until a week after it';
  end if;
  return new;
end $$;

create table public.life_event_answers (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  week date not null,                                                       -- Monday, set by the server
  event_id text not null check (char_length(event_id) <= 40),
  response text not null check (response in ('use_savings', 'cut_spending', 'set_goal', 'not_this_week')),
  created_at timestamptz not null default now(),
  unique (user_id, week)
);

create or replace function public.set_card_week() returns trigger
language plpgsql set search_path = '' as $$
begin
  if not public.is_admin() then
    new.week = date_trunc('week', public.study_today(new.user_id))::date;
  end if;
  return new;
end $$;

-- days that count for the logging streak beyond what the entries show: "No spending today" taps
-- (dated by when the phone saved them, at most 24 hours before they arrive, like entries), and the
-- dates kept when old entries and cards are deleted (retention)
create table public.activity_days (
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  day date not null,
  no_spend boolean not null default false,
  logged boolean not null default false,                                    -- retention: entries arrived that day
  card boolean not null default false,                                      -- retention: a card answered that day
  client_logged_at timestamptz not null default now(),                      -- when the phone saved the tap
  created_at timestamptz not null default now(),                            -- when the server got it
  primary key (user_id, day),
  check (client_logged_at between created_at - interval '24 hours' and created_at + interval '5 minutes')
);

create or replace function public.no_spend_day() returns trigger
language plpgsql set search_path = '' as $$
begin
  if not public.is_admin() then
    new.day = (new.client_logged_at at time zone 'Asia/Kuala_Lumpur')::date;
    new.no_spend = true;
    new.logged = false;
    new.card = false;
  end if;
  return new;
end $$;

-- what the user did in the game (plant, dig, buy the tree, decorate, choose or add an animal).
-- Add-only; the engine replays them and skips any the rules don't allow (C4)
create table public.game_actions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  kind text not null check (kind in ('plant', 'dig', 'buy_tree', 'decorate', 'move_decoration',
                                     'choose_animal', 'add_animal')),
  gx smallint check (gx between -50 and 50),
  gy smallint check (gy between -50 and 50),
  item text check (item ~ '^[a-z_]{1,40}$'),                                -- plant, decoration or animal
  spot text check (char_length(spot) between 1 and 40),
  created_at timestamptz not null default now(),
  check ((kind in ('plant', 'dig')) = (gx is not null and gy is not null)),
  check ((kind in ('plant', 'decorate', 'move_decoration', 'choose_animal', 'add_animal')) = (item is not null)),
  check ((kind in ('decorate', 'move_decoration')) = (spot is not null))
);
create index game_actions_user on public.game_actions (user_id, created_at);

-- caches of what the engine computed (only ever the user's own view)
create table public.assessments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  month date not null check (month = date_trunc('month', month)::date),
  model_version text not null,
  result jsonb not null,
  created_at timestamptz not null default now(),
  unique (user_id, month)
);

create table public.bias_flags (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users (id) on delete cascade,
  month date not null check (month = date_trunc('month', month)::date),
  flag text not null check (flag in ('impulsivity', 'overconfidence', 'delayed_correction')),
  value numeric(8,4),
  shown boolean not null default false,
  unique (user_id, month, flag)
);

-- ---------------------------------------------------------------- the game's logging days
-- One row per Malaysian day: entries that day (by when the phone saved them, C3), "No spending
-- today", answered cards, and the dates kept by retention. security_invoker: the user's own RLS
-- applies, so a user sees only their own days.
create view public.game_days with (security_invoker = true) as
  select user_id, day, sum(entries)::integer as entries, bool_or(no_spend) as no_spend, bool_or(card) as card
  from (
    select user_id, (client_logged_at at time zone 'Asia/Kuala_Lumpur')::date as day, 1 as entries,
           false as no_spend, false as card
      from public.transactions
    union all
    select user_id, (created_at at time zone 'Asia/Kuala_Lumpur')::date, 0, false, true
      from public.life_event_answers where response <> 'not_this_week'
    union all
    select user_id, day, case when logged then 1 else 0 end, no_spend, card
      from public.activity_days
  ) d
  group by user_id, day;

-- ---------------------------------------------------------------- triggers
create trigger profiles_updated before update on public.profiles
  for each row execute function public.set_updated_at();
create trigger debts_updated before update on public.debts
  for each row execute function public.set_updated_at();
create trigger budgets_updated before update on public.budgets
  for each row execute function public.set_updated_at();

-- C3: arrival times come from the server, for every table whose timing earns or unlocks anything.
-- Triggers on one table fire in name order: arrival time first, then what depends on it.
create trigger profiles_arrival before insert or update on public.profiles
  for each row execute function public.set_created_at();
create trigger profiles_lock before insert or update on public.profiles
  for each row execute function public.lock_sign_up_numbers();
create trigger profiles_study before insert or update on public.profiles
  for each row execute function public.guard_study_clock();
create trigger goal_changes_arrival before insert or update on public.goal_changes
  for each row execute function public.set_created_at();
create trigger transactions_arrival before insert or update on public.transactions
  for each row execute function public.set_created_at();
create trigger transactions_clock before insert on public.transactions
  for each row execute function public.persona_client_time();
create trigger checkins_arrival before insert or update on public.monthly_checkins
  for each row execute function public.set_created_at();
create trigger checkins_sums before insert or update on public.monthly_checkins
  for each row execute function public.freeze_logged_sums();
create trigger checkins_window before insert or update on public.monthly_checkins
  for each row execute function public.check_checkin_window();
create trigger cards_arrival before insert or update on public.life_event_answers
  for each row execute function public.set_created_at();
create trigger cards_week before insert or update on public.life_event_answers
  for each row execute function public.set_card_week();
create trigger activity_arrival before insert or update on public.activity_days
  for each row execute function public.set_created_at();
create trigger activity_clock before insert on public.activity_days          -- before activity_no_spend
  for each row execute function public.persona_client_time();
create trigger activity_no_spend before insert on public.activity_days
  for each row execute function public.no_spend_day();
create trigger game_actions_arrival before insert or update on public.game_actions
  for each row execute function public.set_created_at();

-- S-6: daily caps, after the arrival time is set (names sort after *_arrival)
create trigger transactions_limit before insert on public.transactions
  for each row execute function public.limit_daily_rows('200');
create trigger game_actions_limit before insert on public.game_actions
  for each row execute function public.limit_daily_rows('100');
create trigger goal_changes_limit before insert on public.goal_changes
  for each row execute function public.limit_daily_rows('20');

-- ---------------------------------------------------------------- Row Level Security (rule 8)
-- (select auth.uid()) is evaluated once per query, not once per row (Supabase's advice).
alter table public.profiles enable row level security;
alter table public.goal_changes enable row level security;
alter table public.transactions enable row level security;
alter table public.debts enable row level security;
alter table public.budgets enable row level security;
alter table public.monthly_checkins enable row level security;
alter table public.life_event_answers enable row level security;
alter table public.activity_days enable row level security;
alter table public.game_actions enable row level security;
alter table public.assessments enable row level security;
alter table public.bias_flags enable row level security;

-- user-written tables: own rows only, for every command
create policy "own rows" on public.debts for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "own rows" on public.budgets for all to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

-- the profile: read, create, edit; never delete on its own (S-1: deleting and re-creating it would
-- reopen the sign-up numbers); the whole account goes with delete_my_account()
create policy "read own row" on public.profiles for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own row" on public.profiles for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "edit own row" on public.profiles for update to authenticated
  using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

-- the engine's caches: read and add only, so a saved month can't be rewritten or removed (S-3, M4)
create policy "read own rows" on public.assessments for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own rows" on public.assessments for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "read own rows" on public.bias_flags for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own rows" on public.bias_flags for insert to authenticated
  with check ((select auth.uid()) = user_id);

-- entries: add any time; edit or delete within 48 hours of arriving (C3), by the user's own clock:
-- the real one, or a study persona's study date (S-10, D-96), so a participant can fix a typo in an
-- entry they just added (it arrives on the study date, which the real clock passed long ago)
create policy "read own rows" on public.transactions for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own rows" on public.transactions for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "edit own rows for 48 hours" on public.transactions for update to authenticated
  using ((select auth.uid()) = user_id
         and created_at > (select public.study_now((select auth.uid()))) - interval '48 hours')
  with check ((select auth.uid()) = user_id);
create policy "delete own rows for 48 hours" on public.transactions for delete to authenticated
  using ((select auth.uid()) = user_id
         and created_at > (select public.study_now((select auth.uid()))) - interval '48 hours');

-- check-ins: edit within 48 hours, never delete (C3)
create policy "read own rows" on public.monthly_checkins for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own rows" on public.monthly_checkins for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "edit own rows for 48 hours" on public.monthly_checkins for update to authenticated
  using ((select auth.uid()) = user_id and created_at > now() - interval '48 hours')
  with check ((select auth.uid()) = user_id);

-- add and read only: weekly cards, goal changes, "No spending today", game actions
create policy "read own rows" on public.life_event_answers for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own rows" on public.life_event_answers for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "read own rows" on public.goal_changes for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own rows" on public.goal_changes for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "read own rows" on public.activity_days for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own rows" on public.activity_days for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "read own rows" on public.game_actions for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "add own rows" on public.game_actions for insert to authenticated
  with check ((select auth.uid()) = user_id);

-- ---------------------------------------------------------------- retention (pg_cron)
-- Nightly at 03:30 Malaysia time (19:30 UTC): delete details older than 36 months. First keep the
-- dates the logging streak and the cards need (activity_days), so a replay never loses a reward;
-- check-ins keep their logged totals, so past months stay verified.
create extension if not exists pg_cron;
select cron.schedule('fast-retention-36-months', '30 19 * * *', $$
  insert into public.activity_days (user_id, day, logged)
    select distinct user_id, (client_logged_at at time zone 'Asia/Kuala_Lumpur')::date, true
      from public.transactions where occurred_on < current_date - interval '36 months'
    on conflict (user_id, day) do update set logged = true;
  insert into public.activity_days (user_id, day, card)
    select distinct user_id, (created_at at time zone 'Asia/Kuala_Lumpur')::date, true
      from public.life_event_answers
     where week < current_date - interval '36 months' and response <> 'not_this_week'
    on conflict (user_id, day) do update set card = true;
  delete from public.transactions       where occurred_on < current_date - interval '36 months';
  delete from public.assessments        where month       < current_date - interval '36 months';
  delete from public.bias_flags         where month       < current_date - interval '36 months';
  delete from public.life_event_answers where week        < current_date - interval '36 months';
$$);
