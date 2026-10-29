# Interview notes — ca-nowcaster

Plain-language answers for recruiter / technical screens. Numbers below appear in
[`evaluation_report.md`](evaluation_report.md) only — do not invent metrics.

---

## Why ship a baseline?

A baseline is the honest bar: “if a fancy model cannot beat last-month / AR(1)
behavior under the same leakage rules, you have not earned complexity.”

We trained bridge regression, a dynamic factor model, and gradient boosting, then
compared them to AR(1) with walk-forward RMSE, Diebold-Mariano tests, and bootstrap
confidence intervals on the RMSE ratio. **No regression candidate cleared that bar.**
Under the project’s honest-result rule, v1 still ships — with **AR(1)** as production
(`headline RMSE = 0.5876`, `n = 42`). That is a stronger interview story than hiding
a weak model behind a dashboard.

---

## What is leakage, and how did you prevent it?

**Leakage** means the model used information that was not public yet at prediction
time (for example, a GDP value or retail print that had not been released).

Prevention:

1. Every observation stores a `release_timestamp` (when it became public).
2. `as_of(date)` returns only values with `release_timestamp <= date`.
3. `build_features(as_of_date)` builds the monthly frame under that cutoff and
   records a `features_hash`.
4. Tests and Evaluation audits (shuffled targets, feature-timing scramble) try to
   break the harness; Phase 1–3 gates fail CI on look-ahead.

Rule of thumb from `AGENTS.md`: when unsure, assume the data was published later.

---

## What is a confusion matrix?

For the **direction** task (“did MoM growth beat last month?”), each forecast is
right or wrong in four ways:

|  | Actual: did **not** beat | Actual: **beat** |
|--|--------------------------|------------------|
| Predicted: no | True negative (TN) | False negative (FN) |
| Predicted: yes | False positive (FP) | True positive (TP) |

Example from the evaluation report for `direction_classifier` (sign / class of point):
confusion matrix `[[TN, FP], [FN, TP]]` = `[[14, 5], [4, 18]]`, with
accuracy ≈ 0.7805 and F1 = 0.8 (`n = 41`).

Accuracy alone hides whether you always say “up.” Precision, recall, F1, and the
matrix make that visible. Regression models also report a sign-of-forecast matrix
for interview practice; production still uses AR(1) for the GDP MoM **point**.

---

## Why do prediction intervals matter?

A point guess without a range looks more confident than the data support. Every
model implements 80% and 95% intervals. Coverage asks: “over many months, did the
actual fall inside the band about as often as the label claims?”

On the headline walk-forward panel, production **AR(1)** had Cov80 = **0.857** and
Cov95 = **0.905** (`n = 42`). That is useful even when you are not beating a
baseline on RMSE: recruiters can see you care about uncertainty, not just a single
number.

---

## What about data revisions?

Statistics Canada revises history. If you overwrite the only copy of an old print,
you lose what the world knew on the day you predicted.

We store **append-only vintages** (`retrieved_at` + `release_timestamp`). Scoring
uses the official value once it is public. Deep revision-analysis (first print vs
final) is intentionally out of v1 scope — track it in `BACKLOG.md` rather than
pretending the first dashboard already solved it.

---

## What would you do with more time?

Only after v1 is deployed (scope freeze). Candidates for `BACKLOG.md`:

- Re-run evaluation on **live** StatCan vintages (report metrics today are synthetic-panel).
- Version-bump candidates and burn holdout again only after real changes.
- First-print vs revised actual scoring.
- Stronger interval calibration and regime-aware baselines.
- Public Streamlit Cloud URL (human deploy; see `streamlit_deploy.md`).

Do **not** add deep learning or paid data under the current freeze.

---

## Three resume bullet options

Use one. Form: built X using Y, result Z. **Only** numbers from
`docs/evaluation_report.md`.

1. Built a live, self-scoring Canadian GDP MoM nowcasting system using Statistics Canada and Bank of Canada data (Python, DuckDB, statsmodels, scikit-learn, GitHub Actions, Streamlit); expanding-window walk-forward evaluation (headline n=42) found no regression candidate cleared Diebold-Mariano + 95% bootstrap CI versus an AR(1) baseline (headline RMSE 0.5876), so v1 ships AR(1) under an honest-result rule.

2. Built leakage-safe GDP nowcasts with publication-timing cutoffs and 80%/95% prediction intervals using Python, DuckDB, and Streamlit; production AR(1) posted 85.7% 80%-interval coverage and 90.5% 95%-interval coverage over 42 walk-forward months (COVID shock months 2020-03..2020-08 excluded from headline metrics).

3. Built an honest model bake-off for Canadian GDP MoM nowcasts using Diebold-Mariano tests and 300-draw bootstrap RMSE-ratio CIs (Python, statsmodels, scikit-learn) on a synthetic monthly panel (2015-01..2022-12; holdout final 24 months burned once per model@0.1.0); no candidate beat AR(1) despite some point RMSE ratios below 1 (e.g. bridge ratio 0.1110, DM p=0.2641).

---

## One-liner for “tell me about a project”

“I built a Canadian GDP nowcaster that refuses to cheat on publication timing, compared
several models to AR(1) with proper significance tests, and shipped the baseline when
nothing beat it — then wired scheduled predict/score jobs and a Streamlit scoreboard
so the system grades itself in public.”
