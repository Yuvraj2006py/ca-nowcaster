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

- [ ] One command refreshes all registry series into the raw store (Ingestion)
- [x] `as_of(date)` never returns a value with release date after date (Data Quality; `tests/gates/test_phase_1.py`)
- [x] Validation checks + release calendar + pseudo-real-time lags (`src/nowcaster/quality/`)
- [x] Series data-quality status report (`docs/quality_report.md`)
