# Life-event deck: shocks for the FAST generator and Future Self cards

Version: **v0.2 DRAFT** (2026-10-09, `k` adopted) · Task T-04 · Drafted by Claude, **to be edited by Patrick
from real experience** · Feeds `generator_spec.md` §7 (C-20), the Monte Carlo stress test
(T-15) and the life-event cards (T-07)

## How to read this

- **Cost range (RM):** the generator draws the cost uniformly within the range. Where a price
  was found, the source is given; otherwise the range is labelled an assumption.
- **Freq/yr:** expected occurrences per year for an **eligible** person. **Every frequency is
  an assumption.** No Malaysian source gives per-person incidence of these events.
- **p/month** = Freq/yr ÷ 12 (Bernoulli per eligible user per month).
- **Who:** `all`, `emp` (employee), `gig`, `stu` (student), `moto` / `car` (holds that vehicle),
  `nonstu` (not a student; assumed to rent or run a household).
- **Size:** `minor` (expected cost < RM300) or `shock` (≥ RM300). Only shocks become
  life-event cards in the app; minor events just appear as spending in the generator.
- **Patrick's edit:** fill in from your own or friends' experience (cost actually paid, how often).

## Deck

| ID | Event | Who | Cost range (RM) | Freq/yr | p/month | Size | Txn category | Cost basis | Patrick's edit |
|---|---|---|---|---|---|---|---|---|---|
| L-01 | Motorbike minor repair (tyre, battery, brake pads, chain set) | moto | 80–300 | 1.0 | 0.083 | minor | transport | Assumption | |
| L-02 | Motorbike major repair (engine/clutch work, accident damage) | moto | 400–1,200 | 0.2 | 0.017 | shock | transport | Assumption | |
| L-03 | Car minor repair (battery, pair of tyres) | car | 250–700 | 0.5 | 0.042 | shock | transport | Battery RM200–450 (MyMechanic, Kepong workshop 2025); tyres RM240–340 each (Lim Tayar, date unclear) | |
| L-04 | Car major repair (aircon compressor, suspension, accident excess) | car | 800–2,500 | 0.2 | 0.017 | shock | transport | Aircon compressor RM1,100 (one 2025 owner's bill on Mudah: an anecdote, not a benchmark); rest assumption | |
| L-05 | Traffic summons (saman) | moto, car | 150–300 | 0.3 | 0.025 | minor | transport | Assumption (PDRM/JPJ compound amounts: **VERIFY**) | |
| L-06 | Phone screen crack | all | 150–800 | 0.15 | 0.013 | shock | communication | RM150–300 budget/mid-range, RM800+ flagship (CelcomDigi 2026 blog; vendor source). Samsung RRP list exists (labour RM60–85 + parts) | |
| L-07 | Phone lost, stolen or dead: replacement | all | 600–2,000 | 0.05 | 0.004 | shock | communication | Assumption | |
| L-08 | Laptop failure or replacement | all (**stu ×2**) | 1,500–3,000 | 0.05 | 0.004 | shock | education (stu) / other | Spec §7 placeholder; assumption | |
| L-09 | GP clinic visit + medicine (private) | all | 40–150 | 1.0 | 0.083 | minor | health | 2025 regulated GP fee was RM10–35 + medicine; fees were revised upward from 2 Apr 2026 (P.U.(A) 150/2026). The synthetic year is 2025 | |
| L-10 | Dental treatment (filling, extraction, scaling) | all | 100–600 | 0.2 | 0.017 | shock | health | Assumption | |
| L-11 | Private specialist or hospital outpatient, uninsured | all | 300–2,000 | 0.05 | 0.004 | shock | health | Assumption | |
| L-12 | Family emergency: money sent home (parent hospitalised, house repair) | all | 300–1,500 | 0.15 | 0.013 | shock | other (transfer out) | Spec §7 placeholder (RM500–1,500); assumption | |
| L-13 | Funeral: contribution + unplanned trip back to hometown | all | 200–800 | 0.1 | 0.008 | shock | other | Assumption | |
| L-14 | Wedding / kenduri contribution and outfit (outside the festive month) | all | 100–500 | 0.5 | 0.042 | minor | other | Assumption | |
| L-15 | Forced move: new rental deposit (2+1 months is common) or deposit lost | nonstu | 800–2,500 | 0.05 | 0.004 | shock | housing | Assumption (deposit convention: **VERIFY**) | |
| L-16 | Home appliance breakdown (fridge, washing machine, water heater) | nonstu | 300–1,500 | 0.1 | 0.008 | shock | housing | Assumption | |
| L-17 | Utility bill spike (electricity/water, heatwave or leak) | nonstu | 100–300 | 0.2 | 0.017 | minor | housing | Assumption | |
| L-18 | Scam loss (online purchase, fake investment, phishing) | all | 200–3,000 | 0.03 | 0.0025 | shock | other | Assumption. Context: NSRC 997 hotline (D-20, T-19). Look for PDRM/NSRC loss statistics for a better figure | |
| L-19 | Repeating a course / resit fee | stu | 300–1,200 | 0.1 | 0.008 | shock | education | Assumption (MMU fee per credit hour: **VERIFY**) | |
| L-20 | Unplanned academic cost (equipment, printing, field trip, software) | stu | 100–400 | 0.3 | 0.025 | minor | education | Assumption | |
| L-21 | Gig work-equipment loss (phone mount, delivery bag, rain gear, helmet) | gig | 80–400 | 0.3 | 0.025 | minor | transport | Assumption | |

### Multipliers (from spec §3a and §7)

| Rule | Applies to | Value | Type |
|---|---|---|---|
| Gig workers wear out their vehicle and phone faster | L-01 to L-04, L-06, L-07 for `gig` | Freq ×1.8 | Assumption (spec §3a) |
| Students break or replace laptops more often | L-08 for `stu` | Freq ×2 | Assumption (spec §7) |
| Clustering ("bad months come together") | All events, if any shock happened in m−1 | Freq ×1.5 | Assumption (spec §7, world-only, not in the app's Monte Carlo: D-14) |

## Implied rates and the shock scale `k`

| Persona (no multipliers) | All events / month | Shocks only (≥ RM300) / month |
|---|---|---|
| Employee with a motorbike, no car | ≈ 0.34 | ≈ 0.094 |
| Employee with a car | ≈ 0.30 | ≈ 0.14 |
| Student, no vehicle (laptop ×2 applied) | ≈ 0.23 | ≈ 0.08 |

(Claude's arithmetic from the table; recompute after Patrick's edits.)

The shock-only rate (≈ 0.08–0.14) is close to the earlier placeholder of 0.12 shocks per
month, so the deck is consistent with the spec's order of magnitude.

**Adopted 2026-10-09 (Decision G, D-29):** the generator draws per-event Bernoulli events
from this deck, with **one global scale factor `k`** (default 1.0) that multiplies every
frequency. `k` is the only shock setting the §11 tuning rule may change. Test range:
`k` ∈ 0.5–1.7 (spec §16). See `generator_spec.md` §7.

## What is still open

- [ ] Patrick edits costs and frequencies from real experience (the "Patrick's edit" column)
- [ ] VERIFY rows: L-05 (summons amounts), L-15 (rental deposit convention), L-19 (MMU resit fee)
- [x] `k` adopted; `generator_spec.md` §7, §11 and §16 updated (2026-10-09)
- [x] For the app (T-07): the weekly stress-test cards use the suggestion (L-02/L-04, L-06, L-08,
  L-10, L-12, L-16, L-18: common, relatable, a mix of small and large); the funeral card (L-13) is
  left out on purpose (D-117, `engine/cards.yaml`)
