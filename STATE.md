phase: 4
tasks:
  - id: CN-1
    role: human
    status: done
    pr: null
  - id: CN-2
    role: Orchestrator
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/1
  - id: CN-3
    role: DevOps
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/11
  - id: CN-9
    role: Ingestion
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/14
  - id: CN-10
    role: Data Quality
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/13
  - id: CN-13
    role: Modeling
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/16
  - id: CN-12
    role: Feature
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/17
  - id: CN-14
    role: Evaluation
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/18
  - id: CN-15
    role: Modeling
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/21
    note: "Phase 3 candidates (bridge, DFM, GBM, direction) merged to main"
  - id: CN-16
    role: Evaluation
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/20
    note: "Candidate verdicts + holdout burns @ 0.1.0; production_model hint ar1"
  - id: CN-19
    role: Security
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/24
    note: "security_review + CI harden merged; re-check dashboard after #25 lands"
  - id: CN-18
    role: Dashboard
    status: done
    pr: https://github.com/Yuvraj2006py/ca-nowcaster/pull/25
    note: "CLEAN + CI pending post-rebase onto main+#24; Cloud URL needs human"
  - id: CN-17
    role: Live Pipeline
    status: doing
    pr: null
next_action: DevOps squash-merge Dashboard #25 when CI green; Live Pipeline write prediction/score logs; human Streamlit Cloud deploy per docs/streamlit_deploy.md; Security re-check dashboard after merge.
last_updated: 2026-10-29T15:42:00Z

## Status note

Phase 3 complete on `main` (#20 / #21 / #23). Honest result: **no candidate beats
AR(1)**. Phase 4: Security [#24](https://github.com/Yuvraj2006py/ca-nowcaster/pull/24)
merged. Dashboard [#25](https://github.com/Yuvraj2006py/ca-nowcaster/pull/25) reads
prediction/score logs only (fixture fallback); rebased onto main post-#24.
Public Streamlit URL is a **human** step — do not block the Dashboard PR on deploy.

### PRs

| PR | Result |
|----|--------|
| [#1](https://github.com/Yuvraj2006py/ca-nowcaster/pull/1) | Merged — Phase 0 skeleton |
| [#2](https://github.com/Yuvraj2006py/ca-nowcaster/pull/2) | Merged — CI workflow + holdout guard |
| [#11](https://github.com/Yuvraj2006py/ca-nowcaster/pull/11) | Merged green — pip-audit freeze |
| [#13](https://github.com/Yuvraj2006py/ca-nowcaster/pull/13) | Merged — Data Quality |
| [#14](https://github.com/Yuvraj2006py/ca-nowcaster/pull/14) | Merged — Ingestion |
| [#15](https://github.com/Yuvraj2006py/ca-nowcaster/pull/15) | Merged — Phase 1 complete |
| [#16](https://github.com/Yuvraj2006py/ca-nowcaster/pull/16) | Merged — Phase 2 baselines |
| [#17](https://github.com/Yuvraj2006py/ca-nowcaster/pull/17) | Merged — Feature frame |
| [#18](https://github.com/Yuvraj2006py/ca-nowcaster/pull/18) | Merged — Evaluation harness Phase 2 |
| [#19](https://github.com/Yuvraj2006py/ca-nowcaster/pull/19) | Merged — Phase 2 → 3 |
| [#21](https://github.com/Yuvraj2006py/ca-nowcaster/pull/21) | Merged — Phase 3 candidates @ 0.1.0 |
| [#22](https://github.com/Yuvraj2006py/ca-nowcaster/pull/22) | Merged — STATE wait for #20 |
| [#20](https://github.com/Yuvraj2006py/ca-nowcaster/pull/20) | Merged green — Skeptic verdicts + holdout burns |
| [#23](https://github.com/Yuvraj2006py/ca-nowcaster/pull/23) | Merged — Phase 3 complete; next_action Phase 4 |
| [#24](https://github.com/Yuvraj2006py/ca-nowcaster/pull/24) | Merged — Security Phase 4 review + CI harden |
| [#25](https://github.com/Yuvraj2006py/ca-nowcaster/pull/25) | Open — Dashboard Streamlit (rebased onto main+#24) |

### Human taps — Streamlit Community Cloud (Dashboard)

Exact steps: **`docs/streamlit_deploy.md`**. Short version:

1. https://share.streamlit.io/ → sign in with GitHub
2. **Create app** → repo `Yuvraj2006py/ca-nowcaster` → branch `main`
3. **Main file path:** `streamlit_app.py`
4. Python **3.11** · no secrets for v1 → **Deploy**
5. Paste public URL back into this file / README when live

### Auto-merge / branch protection (still recommended)

1. https://github.com/Yuvraj2006py/ca-nowcaster/settings → **Allow auto-merge**
2. Branch ruleset on `main`: require PR + require status check **`ci`** + block force pushes
3. Actions: allow GitHub Actions to create/approve PRs (Dependabot)
