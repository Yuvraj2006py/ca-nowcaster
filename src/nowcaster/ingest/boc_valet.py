"""Bank of Canada Valet API client for rates, FX, and commodity series.

Inputs: Valet series names (e.g. STATIC_ATABLE_V39079, FXMUSDCAD, M.BCPI).
Outputs: series detail metadata and observation rows with date + value.
Time allowed to know: observation dates from Valet only; Valet does not always
publish a separate release timestamp, so callers must document how they stamp
release_timestamp (see refresh module).
"""

from __future__ import annotations

import logging
import os
from typing import Any

from nowcaster.ingest.http import RateLimitedSession

logger = logging.getLogger(__name__)

DEFAULT_BOC_VALET_BASE_URL = "https://www.bankofcanada.ca/valet"


class BocValetError(RuntimeError):
    """Raised when a Valet response is missing expected fields."""


class BocValetClient:
    """REST client for Bank of Canada Valet JSON endpoints."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        session: RateLimitedSession | None = None,
    ) -> None:
        env_url = os.environ.get("BOC_VALET_BASE_URL") or ""
        self.base_url = (base_url or env_url or DEFAULT_BOC_VALET_BASE_URL).rstrip("/")
        self.session = session or RateLimitedSession()

    def get_series_detail(self, series_name: str) -> dict[str, Any]:
        """Fetch series metadata (label, description, frequency).

        Inputs: Valet series name.
        Outputs: seriesDetail entry for that name.
        Time allowed to know: metadata only; no observation values required.
        """
        url = f"{self.base_url}/observations/{series_name}/json"
        data = self.session.request_json("GET", url, params={"recent": 1})
        detail = (data or {}).get("seriesDetail") or {}
        if series_name not in detail:
            raise BocValetError(f"Valet seriesDetail missing for {series_name}: {data}")
        return detail[series_name]

    def get_observations(
        self,
        series_name: str,
        *,
        recent: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Fetch observations for one Valet series.

        Inputs: series name; either recent=N or start_date/end_date (YYYY-MM-DD).
        Outputs: (seriesDetail entry, list of raw observation dicts).
        Time allowed to know: observation dates (`d`) from Valet only.
        """
        params: dict[str, Any] = {}
        if recent is not None:
            params["recent"] = int(recent)
        if start_date is not None:
            params["start_date"] = start_date
        if end_date is not None:
            params["end_date"] = end_date
        if not params:
            params["recent"] = 24

        url = f"{self.base_url}/observations/{series_name}/json"
        data = self.session.request_json("GET", url, params=params)
        detail_map = (data or {}).get("seriesDetail") or {}
        if series_name not in detail_map:
            raise BocValetError(f"Valet seriesDetail missing for {series_name}")
        observations = (data or {}).get("observations")
        if not isinstance(observations, list):
            raise BocValetError(f"Valet observations missing for {series_name}")
        return detail_map[series_name], observations

    def get_group(self, group_name: str) -> dict[str, Any]:
        """Fetch a Valet group detail (for discovery / verification).

        Inputs: group name (e.g. BCPI_MONTHLY).
        Outputs: groupDetail object including groupSeries map.
        Time allowed to know: metadata only.
        """
        url = f"{self.base_url}/groups/{group_name}/json"
        data = self.session.request_json("GET", url)
        detail = (data or {}).get("groupDetail")
        if not isinstance(detail, dict):
            raise BocValetError(f"Valet groupDetail missing for {group_name}")
        return detail

    @staticmethod
    def parse_observation_value(observation: dict[str, Any], series_name: str) -> tuple[str, float]:
        """Extract (date_str, value) from one Valet observation row.

        Inputs: raw observation dict and series name key.
        Outputs: (YYYY-MM-DD, float value).
        Time allowed to know: observation date string only.
        """
        date_str = observation.get("d")
        if not date_str:
            raise BocValetError(f"Observation missing date: {observation}")
        cell = observation.get(series_name)
        if not isinstance(cell, dict) or "v" not in cell:
            raise BocValetError(f"Observation missing value for {series_name}: {observation}")
        raw = cell.get("v")
        if raw is None or raw == "":
            raise BocValetError(f"Empty Valet value for {series_name} on {date_str}")
        return str(date_str), float(raw)
