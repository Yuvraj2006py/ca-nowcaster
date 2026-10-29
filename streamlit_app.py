"""Repo-root entrypoint for Streamlit Community Cloud.

Delegates to nowcaster.app.streamlit_app so the Cloud "Main file path"
can stay a short top-level path.
"""

from nowcaster.app.streamlit_app import render

render()
