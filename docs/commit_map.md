# Commit map: hashes before and after the rewrites (D-146, D-155)

On 2026-10-29, before the first push to GitHub, the author and committer email of every commit was changed
from a personal address to GitHub's no-reply address. Nothing else changed: each commit's file tree,
dates, author name and message are identical (checked for all 30), so the order and timing that the
integrity record relies on ("plan committed before the run", D-132) still hold. Only the hashes changed.
Decisions, reports and results written before then quote the old hashes; this table translates them.

| Old | New | Date (MYT) | Commit |
|---|---|---|---|
| `b5bf3de` | `315738c` | 2026-10-26 19:04 | Import the FAST project as copied from the old laptop |
| `115a5e2` | `be69ddb` | 2026-10-26 19:04 | Set up the new development laptop (D-128) |
| `ab878b0` | `d2a1e57` | 2026-10-26 19:25 | Protect hashed files, pause ethics, add the hybrid check (D-129, D-130) |
| `0b26fc7` | `9171ceb` | 2026-10-26 19:27 | Hybrid check result: keep forecast_v1 (D-130) |
| `9eb852b` | `491238a` | 2026-10-26 19:37 | Add property-based engine tests; fix the health tier at 80 and 40 (D-131) |
| `f5b07ca` | `f03a998` | 2026-10-26 20:16 | 26 Oct round, phases 0-1 and the secondary comparison plan (D-132-D-134) |
| `3e92e40` | `d218ce9` | 2026-10-26 20:22 | Secondary comparison result (phase 2, D-134) |
| `883f4c4` | `e3178b2` | 2026-10-26 20:31 | Study materials v0.4 and a future validation protocol (phase 3, D-135) |
| `86d38ec` | `e76458d` | 2026-10-26 20:50 | Clean-up: retire Codex, remove one-off files (D-136) |
| `d150bd0` | `4032737` | 2026-10-26 21:02 | Explanations: disclose left-out factors (P9); fairness analysis plan; track app/src/data (D-137, D-138) |
| `5eb991c` | `a22a165` | 2026-10-26 21:04 | Explanations and subgroup reliability result (phase 6, D-137) |
| `f9f8317` | `b091918` | 2026-10-26 21:14 | Structural robustness: alternative worlds in the generator, and the plan (D-139) |
| `6bbd924` | `833ef8d` | 2026-10-26 21:16 | Structural robustness result and the assumption audit (phase 4, D-139) |
| `1e2b1cd` | `64bdfff` | 2026-10-26 21:25 | Codex instructions and task specs (D-140) |
| `6512d74` | `8ce6758` | 2026-10-26 21:46 | Add offline assistant safety checks |
| `409d827` | `c5e0351` | 2026-10-26 21:54 | Align assistant API test with computed band |
| `9b06ead` | `24aacd5` | 2026-10-26 21:58 | Record CX-1 hand-back and AI use |
| `67ce464` | `e6d0679` | 2026-10-26 22:17 | Close assistant band-check bypass |
| `dfdcc14` | `baa7687` | 2026-10-26 23:16 | Keep status subjects across punctuation; excuse only linked hedges |
| `196d470` | `fa05af1` | 2026-10-26 23:16 | Merge codex/cx-1: money helper safety checks (CX-1, phase 7) |
| `3401a63` | `e436592` | 2026-10-26 23:17 | Record the CX-1 merge (D-141) |
| `82f4f11` | `06ddc43` | 2026-10-26 23:24 | Monte Carlo coverage: conformal adjustment and its plan (phase 5, D-142) |
| `0bfa1c1` | `799e1b0` | 2026-10-26 23:28 | Monte Carlo conformal offsets, fitted once on seeds 62001-62009 (D-142) |
| `15a639a` | `ef853c3` | 2026-10-26 23:31 | Monte Carlo conformal evaluation, run once on seeds 63001-63006 (D-142) |
| `db53efc` | `92e64b2` | 2026-10-26 23:36 | Future Self shows the conformal range; phase 5 report (D-142) |
| `c67bfc6` | `a53960f` | 2026-10-26 23:46 | Markov months to recover: chain, plan and tests; drop the true ceiling (D-143) |
| `deae1e1` | `ca0166a` | 2026-10-26 23:46 | Markov months to recover: the one run on the master data (D-143) |
| `33faaf2` | `ddfa68d` | 2026-10-26 23:49 | Markov months to recover: reading and records (D-143) |
| `012db36` | `b072baa` | 2026-10-27 00:03 | Debts: optional interest rate and "Which to pay off first?" (WP-14c, D-144) |
| `5719706` | `9bcbb70` | 2026-10-27 00:34 | Sign-in and the live data layer, before the Supabase project (D-145) |

## Second rewrite: the AI co-author lines (D-155)

On 2026-10-30 the `Co-authored-by: Claude ...` and `Co-authored-by: Codex ...` lines were removed from the end of
41 commit messages (GitHub listed both as contributors because of them). Nothing else changed: each commit's file
tree, author and committer (name, email, date) and parents are identical, and each message is the old one less
those lines (checked for all 42). GitHub's own first commit (`03313d9`, signed by GitHub) was left as it was. The AI
assistance stays declared where it always was: `docs/ai_use_log.md` and the report. A hash quoted in a document
written before 2026-10-30 is in the left column; one older than 2026-10-29 goes through the table above first.

| Before | After | Date (MYT) | Commit |
|---|---|---|---|
| `315738c` | `1525c78` | 2026-10-26 19:04 | Import the FAST project as copied from the old laptop |
| `be69ddb` | `8f857b7` | 2026-10-26 19:04 | Set up the new development laptop (D-128) |
| `d2a1e57` | `fb1cb73` | 2026-10-26 19:25 | Protect hashed files, pause ethics, add the hybrid check (D-129, D-130) |
| `9171ceb` | `b9010fc` | 2026-10-26 19:27 | Hybrid check result: keep forecast_v1 (D-130) |
| `491238a` | `5d155fb` | 2026-10-26 19:37 | Add property-based engine tests; fix the health tier at 80 and 40 (D-131) |
| `f03a998` | `88e14e6` | 2026-10-26 20:16 | 26 Oct round, phases 0-1 and the secondary comparison plan (D-132-D-134) |
| `d218ce9` | `3091f0e` | 2026-10-26 20:22 | Secondary comparison result (phase 2, D-134) |
| `e3178b2` | `a25b018` | 2026-10-26 20:31 | Study materials v0.4 and a future validation protocol (phase 3, D-135) |
| `e76458d` | `8debe9b` | 2026-10-26 20:50 | Clean-up: retire Codex, remove one-off files (D-136) |
| `4032737` | `4bd7ce9` | 2026-10-26 21:02 | Explanations: disclose left-out factors (P9); fairness analysis plan; track app/src/data (D-137, D-138) |
| `a22a165` | `d22b21a` | 2026-10-26 21:04 | Explanations and subgroup reliability result (phase 6, D-137) |
| `b091918` | `ee3c260` | 2026-10-26 21:14 | Structural robustness: alternative worlds in the generator, and the plan (D-139) |
| `833ef8d` | `f5198cf` | 2026-10-26 21:16 | Structural robustness result and the assumption audit (phase 4, D-139) |
| `64bdfff` | `9875738` | 2026-10-26 21:25 | Codex instructions and task specs (D-140) |
| `8ce6758` | `c4f2123` | 2026-10-26 21:46 | Add offline assistant safety checks |
| `c5e0351` | `931d3dc` | 2026-10-26 21:54 | Align assistant API test with computed band |
| `24aacd5` | `1d1bc36` | 2026-10-26 21:58 | Record CX-1 hand-back and AI use |
| `e6d0679` | `f98abb5` | 2026-10-26 22:17 | Close assistant band-check bypass |
| `baa7687` | `60899f3` | 2026-10-26 23:16 | Keep status subjects across punctuation; excuse only linked hedges |
| `fa05af1` | `5d39f71` | 2026-10-26 23:16 | Merge codex/cx-1: money helper safety checks (CX-1, phase 7) |
| `e436592` | `beb1800` | 2026-10-26 23:17 | Record the CX-1 merge (D-141) |
| `06ddc43` | `4bf6615` | 2026-10-26 23:24 | Monte Carlo coverage: conformal adjustment and its plan (phase 5, D-142) |
| `799e1b0` | `81bf06c` | 2026-10-26 23:28 | Monte Carlo conformal offsets, fitted once on seeds 62001-62009 (D-142) |
| `ef853c3` | `9f4fd37` | 2026-10-26 23:31 | Monte Carlo conformal evaluation, run once on seeds 63001-63006 (D-142) |
| `92e64b2` | `efce65a` | 2026-10-26 23:36 | Future Self shows the conformal range; phase 5 report (D-142) |
| `a53960f` | `58a5169` | 2026-10-26 23:46 | Markov months to recover: chain, plan and tests; drop the true ceiling (D-143) |
| `ca0166a` | `414819f` | 2026-10-26 23:46 | Markov months to recover: the one run on the master data (D-143) |
| `ddfa68d` | `ebf282e` | 2026-10-26 23:49 | Markov months to recover: reading and records (D-143) |
| `b072baa` | `1db653b` | 2026-10-27 00:03 | Debts: optional interest rate and "Which to pay off first?" (WP-14c, D-144) |
| `9bcbb70` | `974b9cb` | 2026-10-27 00:34 | Sign-in and the live data layer, before the Supabase project (D-145) |
| `a9d5aed` | `a7745ca` | 2026-10-29 16:50 | Commit map and record for the no-reply email rewrite (D-146) |
| `03313d9` | `03313d9` | 2026-10-29 16:45 | Initial commit |
| `1533a8c` | `17ddb21` | 2026-10-29 16:55 | Merge GitHub's initial README into the project |
| `16b8321` | `bdfbe76` | 2026-10-29 17:42 | Supabase live: migration fix, URL tolerance, setup record (D-147) |
| `4513214` | `12e6bab` | 2026-10-29 18:47 | Core flow works live on the phone; Render is live (D-148) |
| `2d55120` | `c86fcf9` | 2026-10-29 19:01 | Upgrade the app to Expo SDK 58 (CX-4, D-149) |
| `065b3cd` | `db38901` | 2026-10-29 19:03 | SDK 58 checked on the phone and merged (D-149) |
| `1bd7e99` | `ec5707d` | 2026-10-29 19:16 | Personas live; forecast seed from the facts, not the account (D-150) |
| `6fcd95e` | `9692ee8` | 2026-10-29 19:50 | Web study build trial; API allows the web site's browser calls (D-151) |
| `5b84215` | `58b1bc2` | 2026-10-30 11:26 | UI polish batch 1: web tab bar, Money tiles, Debts sums (D-152) |
| `cafa3c9` | `801bb69` | 2026-10-30 12:55 | UI polish batch 2: daytime contrast, sign-in and sign-up (D-153) |
| `bb54135` | `a5f9247` | 2026-10-30 14:03 | Motion batch 3: tap feedback, count-up, growing bars, sliding details (D-154) |
