# ca-nowcaster agent rules

Read this file and `src/nowcaster/contracts.py` before touching code.

## Mission

Build a live, self-scoring nowcasting system for Canadian economic data: pull Statistics Canada and Bank of Canada series, build leakage-safe monthly features, train honest models against baselines, evaluate with walk-forward backtests, publish predictions before official releases, score afterward, and serve a small public dashboard.

## Target and scope (v1, frozen)

- **Primary target:** month-over-month growth of Canada's real GDP at basic prices (monthly GDP by industry; verify exact table/vector via StatCan metadata; expected table 36-10-0434-01).
- **Secondary target:** binary classification — did growth beat the previous month.
- **Candidate indicators** (verify before use): LFS employment/hours (14-10-0287-01), CPI (18-10-0004-01), retail trade (20-10-0008-01), manufacturing sales (16-10-0047-01), housing starts (34-10-0143-01), BoC Valet policy rate, CAD exchange rates, commodity price index.
- **Out of scope:** deep learning, paid data, user accounts, trading/betting, regional breakdowns. New ideas go in `BACKLOG.md` only.

## Team roles

1. Ingestion Engineer — `src/nowcaster/ingest/`
2. Data Quality and Timing Engineer — `src/nowcaster/quality/`
3. Feature Engineer — `src/nowcaster/features/`
4. Modeling Engineer — `src/nowcaster/models/`
5. Evaluation Skeptic — `src/nowcaster/evaluation/` (read-only on model/feature code)
6. Live Pipeline Engineer — `src/nowcaster/live/`
7. Dashboard Engineer — `src/nowcaster/app/`
8. Security and Reliability Reviewer — CI/config; read-only on feature code
9. Documentation and Interview Coach — docs and README
10. DevOps and Release Agent — `.github/`, CI/CD, merge policy
11. Orchestrator — contracts, gates, `STATE.md`, merge review

## Rules for every agent

1. Read AGENTS.md and the contracts before touching code.
2. Work only in your own branch and your own directories. If you need a change in someone else's area, write a request in `docs/requests/<role>-<topic>.md` instead of editing their code.
3. Every function that touches data has a docstring stating inputs, outputs, and what time it is allowed to know.
4. Every PR includes tests, a short summary, and a "how I could be wrong" note.
5. No secrets in code, logs, or commits. Use environment variables and `.env.example`.
6. Never use information that was not public as of the as-of date (no look-ahead). When in doubt, assume the data was published later.
7. Never invent a table ID, vector ID, or API field. Verify against the live metadata endpoint, and record what you verified in the series registry.
8. Every model must be compared against the baselines. A model that does not beat the baseline is reported as such, not hidden.
9. Scope freeze: nothing outside "Target and scope" gets built until v1 is deployed. New ideas go in `BACKLOG.md`.
10. The Evaluation Skeptic's verdict on a model is final unless the Orchestrator overrules it in writing.

## Phase gates

Do not start a phase until the previous gate is signed off via `tests/gates/test_phase_N.py` on main. See `docs/gates.md`.

## Autonomous mode

Agents open PRs; nothing reaches main unless CI is green. DevOps owns CI, auto-merge, and the holdout guard. Orchestrator updates `STATE.md` at the start and end of every run.
