/**
 * Where check-ins go (D-118). With Supabase this is public.monthly_checkins, as the user (RLS, rule 8):
 * an insert in the month's window, or an update within 48 hours; the database adds the month's logged
 * totals and what was logged after the month ended (D-77). Until the project exists, sample data mode
 * keeps them on the phone for the session, per persona, and says so.
 */
import { myDate, type CheckinRow, type NewCheckin } from '../lib/checkin.ts';

export interface CheckinStore {
  /** The user's check-ins, oldest first. */
  list(): Promise<CheckinRow[]>;
  /** A new month's check-in, or the fix of one made in the last 48 hours. */
  save(row: NewCheckin): Promise<CheckinRow>;
  /** True when check-ins live only on this phone (sample data mode). */
  readonly local: boolean;
}

const num = (s: string) => Number(s);

/**
 * In memory, over the persona's own check-ins. `seed` gives the rows the database shows on the user's
 * date now and `now` is the user's clock (a persona's study date at noon), so both follow time travel
 * (D-119); what the session saved is kept and shown from the month after its own, as the database
 * shows rows (a month's row appears once the month is over). A new row's after-month figures are 0
 * here: only the database can work them out.
 */
export function memoryCheckins(seed: () => CheckinRow[], now: () => Date): CheckinStore {
  const saved = new Map<string, CheckinRow>();               // the session's check-ins and fixes, by month
  const rows = () => {
    const thisMonth = `${myDate(now().toISOString()).slice(0, 7)}-01`;
    const byMonth = new Map(seed().map((r) => [r.month, r]));
    for (const [month, r] of saved) if (month < thisMonth) byMonth.set(month, r);
    return [...byMonth.values()].sort((a, b) => a.month.localeCompare(b.month));
  };
  return {
    local: true,
    async list() {
      return rows();
    },
    async save(r) {
      const values = {
        cash_bank_ewallet: num(r.cash_bank_ewallet), epf_fleksibel: num(r.epf_fleksibel),
        others_emergency: num(r.others_emergency), others: num(r.others),
        epf_retirement: r.epf_retirement === null ? null : num(r.epf_retirement), debt_total: num(r.debt_total),
        net_income: r.net_income === null ? null : num(r.net_income), bills_paid_on_time: r.bills_paid_on_time,
        ran_short: r.ran_short,
      };
      const old = rows().find((x) => x.month === r.month);
      const row: CheckinRow = old ? { ...old, ...values }          // a fix keeps when it was made (C3)
        : { month: r.month, created_at: now().toISOString(), ...values, after_month_net: 0, after_month_debt: 0 };
      saved.set(r.month, row);
      return row;
    },
  };
}
