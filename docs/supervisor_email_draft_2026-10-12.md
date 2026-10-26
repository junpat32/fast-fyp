# Draft email to supervisor (Patrick to edit and send)

**Attach:** `docs/frozen/generator_spec_v1.0.md` (and optionally `docs/OBJECTIVES.md`)

---

**Subject:** FYP2 (FAST): pre-registered O2 evaluation plan, plus two quick questions

Dear [Supervisor's name],

I hope you are well. A short update on my FYP2 project, FAST (Financial Advisory and Safety Tracker).

**1. Pre-registration of the O2 machine-learning experiment**

Before running the experiment, I have frozen the evaluation plan so that the success
criterion cannot be changed after I see the results. The attached specification (v1.0,
frozen on 12 October 2026) defines the synthetic data, the label, the baselines and the
pass/fail rule. Its SHA-256 fingerprint is:

`6849e796c2d27f53c19e8eb3f4ce751b10c5e4109723b176edcb9ef2521f5aa1`

In brief:
- **Task:** predict whether a user's financial situation gets worse in the next 3 months
  (their DSR band worsens, or they run out of cash).
- **Data:** 1,000 synthetic users aged 18–35, calibrated to DOSM (wages, HES/HIES 2024),
  BNM and World Bank Findex 2025 figures. No real financial data is used.
- **Comparison:** logistic regression, random forest and XGBoost against three baselines
  (base rates, a rule heuristic and a Markov chain), split by user.
- **Success criterion:** the 95% bootstrap confidence interval for [PR-AUC of the best ML
  model − PR-AUC of the best baseline] must lie above zero (medium-noise setting). A
  negative result will be reported as a valid finding.

I plan to run the experiment around **25 October**. If you would like any changes to the
criterion, I would be grateful to hear by **[date, e.g. 20 October]**, so that any
amendment is recorded before any results exist.

**2. Objectives**

The measurable targets for O1–O6 are in the attached OBJECTIVES.md (e.g. SUS ≥ 68 and ≥ 70%
comprehension in the user study). Could you confirm they are acceptable?

**3. Ethics approval for the user study**

In late December I plan a persona-based usability study (15–20 participants, pre-loaded
synthetic data, no real financial data collected, anonymous responses). Could you advise
whether this needs approval from the MMU Research Ethics Committee, which form to use, and
whether your signature is required? I would like to submit by the end of October.

I am happy to meet briefly if that is easier.

Thank you very much.

Best regards,
Patrick Wong Jun Wen
[Student ID] · BSc Computer Science (Hons) AI, Multimedia University
