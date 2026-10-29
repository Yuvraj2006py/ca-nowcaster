# Streamlit Community Cloud deploy (human taps)

The dashboard code ships in-repo. **Public hosting needs a one-time human
deploy** — agents cannot complete this step. Do not block the Dashboard PR on
a live URL.

App entrypoint: `streamlit_app.py` (repo root) → `nowcaster.app.streamlit_app`.
The page reads stored logs only (or bundled fixtures). No secrets required for v1.

## Tap-by-tap

1. Open [https://share.streamlit.io/](https://share.streamlit.io/) and sign in
   with the GitHub account that owns `Yuvraj2006py/ca-nowcaster`.
2. Click **Create app** (or **New app**).
3. **Repository:** `Yuvraj2006py/ca-nowcaster`
4. **Branch:** `main` (after the Dashboard PR merges)
5. **Main file path:** `streamlit_app.py`
6. **App URL** (optional): e.g. `ca-nowcaster` →
   `https://ca-nowcaster.streamlit.app`
7. Open **Advanced settings** → **Python version:** `3.11`
8. Leave secrets empty for v1 (public data / fixture logs only).
9. Click **Deploy**. Wait for the build to finish (pip install from
   `pyproject.toml`).
10. Open the public URL. You should see either live logged nowcasts or the
    **sample logs** banner if `data/logs/` is empty on the Cloud host.
11. Paste the public URL into `STATE.md` under human taps / dashboard URL so
    Documentation can link it from the README.

## Optional: point Cloud at live logs later

When the Live Pipeline writes logs into the repo working tree or a mounted
store, set environment variables in Streamlit Cloud **Settings → Secrets**
only if needed (still no API keys for v1):

```toml
NOWCASTER_PREDICTION_LOG = "data/logs/predictions.csv"
NOWCASTER_SCORE_LOG = "data/logs/scores.csv"
NOWCASTER_PRODUCTION_MODEL = "ar1"
NOWCASTER_BASELINE_MODEL = "last_value"
```

Until those files exist on the host, the app uses bundled fixtures under
`src/nowcaster/app/fixtures/` automatically.

## Local smoke check

```bash
pip install -e ".[dev]"
streamlit run streamlit_app.py
```

No free-text inputs; phone-width layout uses Streamlit’s centered container.
