# Phase gates

Automated sign-off lives in `tests/gates/test_phase_N.py`. A phase may start only after the previous gate passes on `main`.

| Phase | Gate | Owners |
|-------|------|--------|
| 0. Setup | Repo layout, `AGENTS.md`, `contracts.py`, `series_registry.yaml`, this file, `STATE.md`, `BACKLOG.md`, and package scaffolding exist | Orchestrator |
| 1. Data | One command refreshes raw store; `as_of` leakage test passes | Ingestion, Data Quality |
| 2. Features and baselines | Baselines run end-to-end through backtest harness | Feature, Modeling, Evaluation |
| 3. Models | Each model evaluated; report states which beat baseline | Modeling, Evaluation |
| 4. Live and app | Scheduled run logs prediction; dashboard deployed; security review done | Live, Dashboard, Security |
| 5. Ship | README, model card, interview notes, resume bullets done | Documentation, Orchestrator |

Honest-result rule: if no model beats the baseline, v1 still ships.

## Phase 0 checklist

- [x] Directory layout per build plan
- [x] `AGENTS.md` with the ten rules
- [x] `src/nowcaster/contracts.py`
- [x] Empty `series_registry.yaml` with schema documented
- [x] `docs/gates.md`, root `STATE.md`, `BACKLOG.md`
- [x] Package scaffolding (`pyproject.toml`, pinned deps, `.gitignore`, `.env.example`, package `__init__.py` files)
- [x] Stub `tests/gates/test_phase_0.py`

## Phase 1 checklist

- [x] One command refreshes all registry series into the raw store (Ingestion)
- [x] `as_of(date)` never returns a value with release date after date (Data Quality; `tests/gates/test_phase_1.py`)
- [x] Validation checks + release calendar + pseudo-real-time lags (`src/nowcaster/quality/`)
- [x] Series data-quality status report (`docs/quality_report.md`)

## Phase 2 checklist

- [x] Leakage-safe `build_features(as_of_date)` + `features_hash` (`src/nowcaster/features/`; Feature)
- [x] MoM / YoY / log-diff / rolling / lags + ragged-edge strategies (carry, AR1, leave_missing)
- [x] Feature leakage nesting tests + Feature-half gate (`tests/gates/test_phase_2.py`)
- [x] Feature summary table (`docs/feature_summary.md`)
- [x] Baselines only: `last_value`, `ar1`, `rolling_mean` implementing `NowcastModel` (Modeling)
- [x] Registry (`create_baseline` / `iter_baselines`) so Evaluation runs baselines without editing model bodies (Modeling)
- [x] One-page plain-language docs per baseline under `docs/models/` (Modeling)
- [x] Expanding-window walk-forward harness + metrics scaffolding (Evaluation)
- [x] COVID headline/full metric variants; leakage audit hooks; holdout lock docs
- [x] Joint gate: Feature leakage tests + `build_features` → baselines → walk-forward
  (`tests/gates/test_phase_2.py`)

## Phase 3 checklist

- [x] Modeling candidates registered (`list_candidates` / `create_candidate`) @ 0.1.0 (#21)
- [x] Expanding-window walk-forward with COVID headline vs full-sample metrics (Evaluation)
- [x] RMSE/MAE ratios, directional accuracy, 80%/95% coverage (Evaluation)
- [x] Classifier metrics: confusion / precision / recall / F1 + calibration plot (Evaluation)
- [x] Diebold-Mariano + bootstrap CI on RMSE ratios (Evaluation)
- [x] Leakage audits: shuffled targets + feature-timing scramble (Evaluation)
- [x] Holdout once-per-version API (`evaluate_holdout_once`, `score_holdout_only`)
- [x] `docs/evaluation_report.md` with plain-language verdicts (honest-result rule)
- [x] `tests/gates/test_phase_3.py`
- [x] Holdout touched once per final candidate version (`bridge`, `dynamic_factor`,
  `gradient_boosting`, `direction_classifier`, `direction_boosting` @ 0.1.0)

## Phase 4 checklist

- [x] Security review + failure modes (`docs/security_review.md`, `docs/failure_modes.md`)
- [x] Streamlit dashboard from stored logs (`src/nowcaster/app/`, `streamlit_app.py`)
- [x] Human Cloud deploy doc (`docs/streamlit_deploy.md`) — URL is a human tap, not a gate
- [x] Scheduled live predict/score with AR(1) production (`src/nowcaster/live/`)

## Phase 5 checklist

- [x] README: problem, honest result, architecture, how to run, limits
- [x] Model card (`docs/model_card.md`)
- [x] Interview notes (`docs/interview_notes.md`) including three resume bullets
  using only numbers from `docs/evaluation_report.md`
- [x] `STATE.md` final summary at top; Phase 5 done
- [x] Streamlit deploy taps kept current (`docs/streamlit_deploy.md`)
- [x] Gate tests (`tests/gates/test_phase_5.py`)
