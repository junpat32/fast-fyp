# FAST FYP2 — Research Strengthening, Model Validation, and System Improvements

You are continuing the development of my Final Year Project, **FAST (Financial Advisory and Safety Tracker)**, a Malaysian-focused, gamified, AI-driven personal financial risk management system.

Your responsibility is to strengthen the scientific credibility, predictive reliability, explainability, practical usefulness, and deployment readiness of the existing FYP2 system.

**This is an improvement and validation task, not a request to rebuild the project.**

## 1. Mandatory Project Review

Before making any changes:

1. Read `AGENTS.md`, followed by `CLAUDE.md`, followed by `docs/TASKS.md`.
2. Read all other relevant documentation concerning the ML experiments, synthetic-data generator, financial risk engine, Monte Carlo simulation, financial assistant, user interface, and testing.
3. Identify the current implementation, dependencies, architecture, tests, and outstanding tasks.
4. Treat all established repository instructions as binding, regardless of whether they refer to Claude, Codex, or another AI agent.
5. Identify which improvements below are already implemented, partially implemented, or missing.
6. Do not duplicate completed work or overwrite validated functionality.

Before coding, produce a concise audit and implementation plan. Explain which improvements will require changes to experiments, which affect production functionality, and which only require documentation.

**Wait for my explicit `go` before modifying files.**

## 2. Non-Negotiable Research Integrity

FAST's original FYP2 experiment was pre-registered and frozen on 12 October 2026.

The frozen protocol includes its outcome definition, feature specification, baselines, evaluation metric, pass criteria, and SHA-256 fingerprint.

You must:

- Preserve the original frozen protocol, data splits, experimental outputs, and results.
- Never retroactively modify pre-registration conditions, pass thresholds, or reported findings.
- Clearly distinguish original confirmatory experiments from subsequent exploratory or secondary analyses.
- Ensure any newly proposed confirmatory experiment has its evaluation rules committed before execution.
- Prevent test-set leakage, preprocessing leakage, user overlap between splits, and tuning based on final evaluation results.
- Maintain reproducibility through documented seeds, configurations, data versions, code revisions, and results.
- Report unsuccessful, inconclusive, and contradictory experiments without concealing them.
- Never invent results, external validation, empirical data, or citations.

Changes affecting deployed components must not silently alter the historical research artifacts.

## 3. Improvement A — Evaluate Whether ML Adds Genuine Value

**Priority: Critical**

The existing system has reported approximately:

| Approach | PR-AUC |
|---|---|
| Logistic regression | 0.440 |
| Monte Carlo | 0.427 |
| Financial health score | 0.416 |
| Best original baseline | 0.284 |

The original improvement over the registered baseline is meaningful. However, subsequent findings suggest that simpler methods may rank financial deterioration almost as effectively as ML.

### Required work

1. Inspect how all four approaches produce their predictions or rankings.
2. Verify that their outputs measure the same target event and prediction horizon.
3. Construct a fair, paired evaluation using identical held-out cases wherever methodologically appropriate.
4. Include a transparent cash-runway baseline.
5. Evaluate PR-AUC, calibration, Brier score, and, where appropriate, ROC-AUC and threshold-based usefulness.
6. Compute uncertainty intervals for paired performance differences using person-level clustered resampling.
7. Investigate probability calibration for each method. If scores require calibration, use training or validation data only, never the final test set.
8. Determine whether ML offers meaningful improvements in probability estimation, not merely ranking.
9. Evaluate whether simpler calibrated predictors could offer comparable reliability and explanations.

Do not assume that ML must outperform every alternative.

If the simpler methods perform comparably, report this as a legitimate research finding.

**Deliverable:** Reproducible secondary comparative evaluation, results, interpretation, and documentation.

## 4. Improvement B — Strengthen Synthetic Data Validity

**Priority: Critical**

The generator produces synthetic Malaysian financial histories using statistical benchmarks from sources including DOSM, Bank Negara Malaysia, the Labour Force Survey, the World Bank Global Findex, and population statistics.

The existing generator passed thirteen realism checks and subsequent sensitivity analyses.

However, matching selected statistical benchmarks does not prove that the underlying financial relationships are realistic.

### Required work

**A. Audit all statistical assumptions**

- Trace major generator parameters to their original sources.
- Check the correct population, age group, survey year, statistical definition, and unit.
- Distinguish individuals from households.
- Distinguish gross income from disposable income.
- Distinguish ratios of population averages from averages of individual ratios.
- Review how the DOSM-derived spending-to-income ratio of approximately 60.8% is applied.
- Check that financial characteristics are not incorrectly assumed independent when evidence suggests relationships.
- Identify unsupported parameters and preserve explicit assumption labels and defensible ranges.
- Do not modify the generator merely to improve model performance.

**B. Structural robustness testing**

The current sensitivity tests vary assumptions within the established generator.

Introduce additional testing that changes selected behavioural mechanisms themselves, such as:

- Different relationships between financial stress and discretionary spending.
- More persistent income or employment shocks.
- Correlated unexpected expenses.
- Different saving and borrowing responses to financial strain.
- Heterogeneous financial behaviours between population subgroups.
- Plausible relationships between employment, income volatility and emergency expenses.

Create a clearly separated alternative simulation configuration or simulator variant.

Evaluate the unchanged original trained model on independent data generated under these alternative mechanisms. Do not retrain unless the experimental design explicitly calls for a separate adaptation experiment.

Compare discrimination and calibration deterioration under these distribution shifts.

Do not label synthetic-to-synthetic transfer as real-world external validation.

**Deliverable:** Statistical-assumption audit, structural robustness framework, reproducible tests, and documented findings.

## 5. Improvement C — Investigate the Financial Deterioration Outcome

**Priority: High**

The existing target predicts whether a user experiences a worsening DSR risk band or cash depletion over the next three months.

Approximately 72% of positive outcomes reportedly involve cash depletion.

This means the primary outcome may be driven more by liquidity problems than debt-band deterioration.

### Required work

Preserve the original frozen composite target.

Add secondary analyses of:

1. Cash-shortfall events.
2. DSR-band worsening.
3. DSR deterioration even when the person remains within the same band.
4. Performance by initial Green, Yellow, and Red bands.
5. Cases where a person is already Red and cannot move into a worse categorical band.
6. Cases where debt pressure increases but the original composite label remains negative.

Determine whether the current forecasting capability is better described as liquidity-risk prediction, debt-pressure prediction, or general short-term financial deterioration.

Investigate whether separate cash-shortfall and debt-pressure indicators would benefit users.

Do not deploy additional ML predictions without appropriate training, evaluation, and calibration.

**Deliverable:** Secondary outcome analysis and a justified recommendation for how the app should present financial deterioration.

## 6. Improvement D — Improve Monte Carlo Uncertainty Calibration

**Priority: Critical**

The existing Monte Carlo simulation generates ranges of possible financial futures.

Its nominal 80% prediction interval currently achieves approximately 73% coverage, with additional subgroup weaknesses.

The goal is to improve uncertainty estimation rather than simply increasing simulation counts.

### Required work

1. Audit the current Monte Carlo implementation and calibration tests.
2. Identify causes of undercoverage, including the limited three-month historical window.
3. Investigate parameter uncertainty in estimated income and expenditure averages.
4. Evaluate hierarchical or Bayesian shrinkage approaches that borrow information from an appropriate reference population.
5. Consider persistent income shocks, correlated expenses, and employment-specific volatility.
6. Test interval coverage across prediction horizons and employment categories.
7. Evaluate overall interval coverage, conditional subgroup coverage, and interval width.
8. Prevent artificially wide intervals being treated as automatically better.
9. Use independent evaluation samples and avoid test-informed calibration adjustments.
10. Verify compatibility with the app's existing simulation interfaces.

Seek approximately nominal 80% coverage without hiding substantial undercoverage within important population groups.

Do not guarantee successful calibration.

If acceptable coverage cannot be achieved, retain honest conditional-scenario language and document the limitations.

**Deliverable:** Evaluated uncertainty improvements, regression tests, and updated methodological documentation.

## 7. Improvement E — Strengthen Explanations, Fairness and Interpretability

**Priority: High**

The deployed logistic regression already provides exact contributions to its linear prediction function.

However, exact mathematical contributions are not necessarily causal explanations.

### Required work

- Confirm that explanation calculations accurately reflect the model's actual transformed features and coefficients.
- Clarify whether contributions are expressed in log-odds, probability differences, or another unit.
- Never misrepresent feature contributions as proven causal effects.
- Check that user-facing explanations are understandable and not misleading.
- Avoid explanations that reverse obvious financial meaning because of correlated features without adequate justification.
- Preserve the existing policy of excluding age and employment type from user-facing reasons.
- Preserve the existing validity gate for behavioural flags.
- Ensure that excluded explanations do not cause the displayed reasoning to misrepresent the model.
- Verify that the existing protection against displaying 0% or 100% probabilities remains intact.

Evaluate subgroup calibration and performance, including age and employment categories.

Pay particular attention to the previously observed under-warning of gig workers when age and employment information was removed, as well as calibration concerns involving 18–19-year-olds.

Do not assume that removing sensitive or demographic features automatically improves fairness.

Compare predictive reliability, subgroup errors, transparency, and alternative mitigation strategies.

Use minimum subgroup sample sizes and uncertainty estimates to avoid making strong claims from insufficient data.

**Deliverable:** Explainability audit, subgroup evaluation, fairness limitations, and automated tests.

## 8. Improvement F — Develop an Interactive Financial What-If Simulator

**Priority: High**

FAST currently forecasts risk, but users should also be able to explore how financial decisions could affect their financial position.

Implement or improve a **What-If Financial Simulator**, preferably integrated into the existing Future Self experience.

### Suggested inputs

- Monthly income.
- Monthly essential and discretionary spending.
- Starting available cash.
- Debt repayments.
- One-off unexpected expenses.
- Temporary income reductions.
- Changes in savings or spending behaviour.

### Suggested outputs

- Monthly projected cash flow.
- Projected remaining cash over three months.
- Potential cash shortfall.
- Changes in calculated DSR, where applicable.
- Comparisons between original and modified scenarios.
- Optional Monte Carlo uncertainty ranges, if properly supported.

### Requirements

1. Use transparent, deterministic calculations for simple scenarios.
2. Reuse validated financial engine functions where possible.
3. Do not imply that changing an input has a scientifically established causal effect on ML risk probability.
4. Do not dynamically alter ML probability unless the changed inputs, feature-generation process, and forecast remain valid under the original model's intended use.
5. Clearly label forecasts as conditional scenarios.
6. Show assumptions and limitations in understandable language.
7. Keep interfaces practical for a mobile device.
8. Follow existing React Native/Expo architectural and design conventions if applicable.
9. Provide tests for calculations, edge cases, input validation, and consistency with the existing risk engine.

Favor reliable functionality over visually impressive but unsupported features.

**Deliverable:** Tested What-If Simulator, user-facing explanations, and integration documentation.

## 9. Improvement G — Real-User Evaluation

**Priority: High**

FAST's ML findings come from synthetic data, not real financial outcomes.

Develop an ethical and practical user-evaluation framework.

Separate two types of validation.

### A. Usability and comprehension testing

Design a study suitable for approximately 30–50 consenting adult participants, subject to actual recruitment feasibility.

Participants should be able to evaluate the app using fictional financial personas without disclosing their personal finances.

Measure:

- Comprehension of financial risk bands.
- Interpretation of risk probabilities.
- Understanding of uncertainty ranges.
- Ability to identify useful next actions.
- Distinction between forecasts and guarantees.
- Perceived clarity, usefulness, and trust.
- User-interface navigation and task completion.

Prepare the study protocol, questionnaire, tasks, scoring scheme, and analysis plan.

### B. Real-world predictive validation

Prepare a separate prospective study design using consenting adults' minimal financial summaries and subsequent observed outcomes.

Do not assume actual financial data or participants are available.

Identify what would be necessary to conduct this study responsibly, including recruitment, informed consent, appropriate university ethics review, secure handling, data minimisation, retention limits and outcome collection.

A small pilot must not be presented as conclusive predictive validation.

**Deliverable:** Ready-to-use usability evaluation materials and a documented future longitudinal validation protocol.

## 10. Improvement H — Complete Financial Assistant Safety Evaluation

**Priority: High**

The financial assistant uses a large language model but receives only constrained financial summaries rather than full transaction histories.

Maintain the existing security and privacy boundaries.

### Required work

Audit and test:

- Numerical consistency with supplied financial data.
- Fabricated financial values.
- Inappropriate or unsupported financial advice.
- False claims of guaranteed financial outcomes.
- Prompt injection and attempts to override system constraints.
- Accidental disclosure of private information.
- Contradictions between assistant advice and validated risk-engine calculations.
- Responses to financial distress or crisis situations.
- Explanation consistency with the underlying financial model.

Preserve the restriction against recommending specific financial products where it is already required.

Never let the assistant independently alter financial engine calculations or claim authority beyond its scope.

Inspect existing red-team tests before adding new ones.

If live Groq API credentials are unavailable, implement and run offline tests where possible and clearly identify live tests that remain unexecuted.

Never fabricate successful API results.

**Deliverable:** Safety audit, automated tests, outstanding live-test instructions and documentation.

## 11. Improvement I — Correct Methodological Claims

**Priority: High**

Review research documentation, experiment reports, and user-facing claims for scientific accuracy.

Pay particular attention to these distinctions.

### Oracle benchmark

The latent-trait-informed oracle is not necessarily a theoretical performance ceiling.

Its reported PR-AUC of approximately 0.435 does not prove that other models have exhausted all possible predictive information.

Describe it appropriately as a latent-trait-informed benchmark.

If feasible, separately investigate a generator-informed approximation of conditional event probabilities across repeated simulated futures.

### Synthetic realism

Passing thirteen realism checks establishes conformity with thirteen selected criteria, not proof of real-world population validity.

### Explanation fidelity

Exact logistic regression contributions explain model arithmetic, not necessarily real-world causes.

### DSR boundaries

Preserve FAST's established 60% Red-band convention where required by existing specifications.

However, do not state that all Malaysian banks universally apply exactly the same DSR threshold. Distinguish application conventions from institution-specific lending practices.

### Research conclusions

State clearly which results are:

- Confirmatory.
- Exploratory.
- Synthetic-only.
- Empirically validated.
- Pending validation.
- Inconclusive.

**Deliverable:** Methodological corrections and consistency checks across the affected documentation.

## 12. Testing and Quality Standards

For every implemented improvement:

1. Use the project's existing testing framework and conventions.
2. Add focused unit tests and integration tests.
3. Test numerical boundaries, missing inputs, zero values, unusual financial circumstances, and relevant subgroup cases.
4. Run affected existing regression tests.
5. Prevent modifications that silently break deployed functionality.
6. Document reproducible commands and experimental configurations.
7. Avoid unnecessary dependencies or expensive infrastructure.
8. Prefer efficient implementations that remain usable on limited development hardware.
9. Do not bypass failing tests or weaken acceptance criteria merely to obtain passing results.
10. Record what was actually executed and what remains unverified.

Do not increase simulator complexity unless it addresses a defined validity problem.

## 13. Implementation Priorities

Follow this order unless repository dependencies justify a different sequence.

| Phase | Work |
|---|---|
| 0 | Repository audit, task planning and preservation checks |
| 1 | ML versus simpler-model comparison |
| 2 | Research claims and statistical-assumption audit |
| 3 | Secondary financial deterioration analysis |
| 4 | Monte Carlo uncertainty improvement |
| 5 | Structural robustness testing |
| 6 | Explainability and subgroup reliability |
| 7 | Interactive What-If Simulator |
| 8 | Real-user study preparation |
| 9 | Financial assistant safety testing |
| 10 | Final documentation, integration and regression testing |

Update `docs/TASKS.md` in accordance with the project's existing task-management rules.

Implement in small, verifiable increments rather than changing all subsystems simultaneously.

At the end of each phase, report:

- Files changed.
- Work implemented.
- Tests executed and their results.
- Findings and limitations.
- Any changes to previously stated assumptions.
- Remaining work.

If the original hypothesis does not hold under a stronger test, report that result faithfully.

## 14. Final Objective

The goal is **not** to make machine learning appear more impressive.

The goal is to make FAST a scientifically defensible, transparent, practical and trustworthy financial risk management system.

The improved project should be able to answer:

1. Does machine learning genuinely add value beyond transparent financial forecasting methods?
2. How robust are the results when synthetic-world assumptions change?
3. Does the prediction accurately communicate financial deterioration, particularly cash-shortfall and debt-pressure risks?
4. Are financial forecasts and uncertainty ranges properly calibrated?
5. Are model explanations accurate, understandable and non-misleading?
6. Does the application perform reliably across different user groups?
7. Can users translate forecasts into informed financial decisions?
8. Are privacy, safety, research limitations, and scientific integrity maintained?

**Your first response must only provide the repository audit, an assessment of which improvements are needed, a prioritized implementation plan, and any important technical concerns. Do not write code or modify files until I reply `go`.**
