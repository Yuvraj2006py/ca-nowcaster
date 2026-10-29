"""Statistics Canada Web Data Service (WDS) client.

Inputs: product (cube) IDs, vector IDs, optional date ranges / latest-N.
Outputs: cube metadata dicts and lists of observation dicts with StatCan fields.
Time allowed to know: only timestamps present in the WDS payload (e.g. releaseTime);
does not invent publication lags.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from nowcaster.ingest.http import RateLimitedSession

logger = logging.getLogger(__name__)

DEFAULT_STATCAN_BASE_URL = "https://www150.statcan.gc.ca/t1/wds/rest"


class StatCanError(RuntimeError):
    """Raised when a WDS response status is not SUCCESS or payload is incomplete."""


class StatCanClient:
    """Thin REST client for selected StatCan WDS JSON endpoints."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        session: RateLimitedSession | None = None,
    ) -> None:
        env_url = os.environ.get("STATCAN_BASE_URL") or ""
        self.base_url = (base_url or env_url or DEFAULT_STATCAN_BASE_URL).rstrip("/")
        self.session = session or RateLimitedSession()

    def _post(self, endpoint: str, body: Any, *, use_cache: bool = True) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.session.request_json("POST", url, json_body=body, use_cache=use_cache)

    def _get(self, endpoint: str, *, use_cache: bool = True) -> Any:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        return self.session.request_json("GET", url, use_cache=use_cache)

    def get_cube_metadata(self, product_id: int | str) -> dict[str, Any]:
        """Look up cube metadata for one product ID.

        Inputs: StatCan productId (digits of table ID without dashes), e.g. 36100434.
        Outputs: cube metadata object from WDS.
        Time allowed to know: cube releaseTime from metadata only.
        """
        pid = int(str(product_id).replace("-", ""))
        data = self._post("getCubeMetadata", [{"productId": pid}])
        if not isinstance(data, list) or not data:
            raise StatCanError(f"Unexpected getCubeMetadata response for {pid}")
        item = data[0]
        if item.get("status") != "SUCCESS":
            raise StatCanError(f"getCubeMetadata failed for {pid}: {item}")
        obj = item.get("object")
        if not isinstance(obj, dict):
            raise StatCanError(f"Missing cube object for {pid}")
        return obj

    def get_series_info_from_coord(
        self, product_id: int | str, coordinate: str
    ) -> dict[str, Any]:
        """Resolve vector metadata from cube product ID + coordinate.

        Inputs: productId and 10-part coordinate string (e.g. '1.1.1.1.0.0.0.0.0.0').
        Outputs: series info object including vectorId and SeriesTitleEn.
        Time allowed to know: none beyond metadata fields returned by WDS.
        """
        pid = int(str(product_id).replace("-", ""))
        data = self._post(
            "getSeriesInfoFromCubePidCoord",
            [{"productId": pid, "coordinate": coordinate}],
        )
        if not isinstance(data, list) or not data:
            raise StatCanError("Unexpected getSeriesInfoFromCubePidCoord response")
        item = data[0]
        if item.get("status") != "SUCCESS":
            raise StatCanError(f"getSeriesInfoFromCubePidCoord failed: {item}")
        obj = item.get("object")
        if not isinstance(obj, dict):
            raise StatCanError("Missing series info object")
        if obj.get("responseStatusCode") not in (0, "0"):
            raise StatCanError(f"Coordinate not valid or empty series: {obj}")
        return obj

    def get_latest_n_periods(
        self, vector_id: int | str, latest_n: int = 24
    ) -> list[dict[str, Any]]:
        """Fetch the latest N observation periods for a vector.

        Inputs: vectorId, latest_n (>=1).
        Outputs: list of vectorDataPoint dicts (refPer, value, releaseTime, ...).
        Time allowed to know: releaseTime on each point as published by StatCan.
        """
        vid = _normalize_vector_id(vector_id)
        data = self._post(
            "getDataFromVectorsAndLatestNPeriods",
            [{"vectorId": vid, "latestN": int(latest_n)}],
        )
        return _extract_vector_points(data, endpoint="getDataFromVectorsAndLatestNPeriods")

    def get_bulk_range(
        self,
        vector_ids: list[int | str],
        start_release: str,
        end_release: str,
    ) -> dict[int, list[dict[str, Any]]]:
        """Fetch points whose release timestamps fall in [start_release, end_release].

        Inputs: vector IDs; ISO-like release bounds 'YYYY-MM-DDTHH:MM' (WDS format).
        Outputs: map vectorId -> list of vectorDataPoint dicts.
        Time allowed to know: releaseTime filter and per-point releaseTime from WDS.
        """
        vids = [_normalize_vector_id(v) for v in vector_ids]
        data = self._post(
            "getBulkVectorDataByRange",
            {
                "vectorIds": vids,
                "startDataPointReleaseDate": start_release,
                "endDataPointReleaseDate": end_release,
            },
        )
        if not isinstance(data, list):
            raise StatCanError(f"Unexpected getBulkVectorDataByRange response: {data}")
        out: dict[int, list[dict[str, Any]]] = {}
        for item in data:
            if item.get("status") != "SUCCESS":
                raise StatCanError(f"getBulkVectorDataByRange item failed: {item}")
            obj = item.get("object") or {}
            vid = int(obj.get("vectorId"))
            points = obj.get("vectorDataPoint") or []
            if not isinstance(points, list):
                raise StatCanError(f"Bad vectorDataPoint for vector {vid}")
            out[vid] = points
        return out

    def get_changed_series_list(self, *, use_cache: bool = False) -> list[dict[str, Any]]:
        """Return series that changed on the latest release day (WDS changed list).

        Inputs: none (server-side "today's changes").
        Outputs: list of {vectorId, productId, coordinate, releaseTime, ...}.
        Time allowed to know: releaseTime values supplied by WDS for changed series.
        """
        data = self._get("getChangedSeriesList", use_cache=use_cache)
        if not isinstance(data, dict) or data.get("status") != "SUCCESS":
            raise StatCanError(f"getChangedSeriesList failed: {data}")
        obj = data.get("object")
        if not isinstance(obj, list):
            raise StatCanError("getChangedSeriesList missing object list")
        return obj

    def changed_registry_vectors(
        self, vector_ids: set[int], *, use_cache: bool = False
    ) -> list[dict[str, Any]]:
        """Filter the changed-series list to vectors we care about.

        Inputs: set of registry vector IDs.
        Outputs: subset of changed-series rows matching those IDs.
        Time allowed to know: same as get_changed_series_list.
        """
        changed = self.get_changed_series_list(use_cache=use_cache)
        wanted = {int(v) for v in vector_ids}
        return [row for row in changed if int(row.get("vectorId", -1)) in wanted]


def _normalize_vector_id(vector_id: int | str) -> int:
    text = str(vector_id).strip().lower().lstrip("v")
    return int(text)


def _extract_vector_points(data: Any, *, endpoint: str) -> list[dict[str, Any]]:
    if not isinstance(data, list) or not data:
        raise StatCanError(f"Unexpected {endpoint} response")
    item = data[0]
    if item.get("status") != "SUCCESS":
        raise StatCanError(f"{endpoint} failed: {item}")
    obj = item.get("object") or {}
    points = obj.get("vectorDataPoint")
    if not isinstance(points, list):
        raise StatCanError(f"{endpoint} missing vectorDataPoint")
    return points


def product_id_from_table_id(table_id: str) -> int:
    """Convert a dashed table id like '36-10-0434-01' to WDS productId 36100434.

    StatCan display IDs are AA-BB-CCCC-DD; WDS productId is AABBCCCC (drops DD).
    """
    digits = table_id.replace("-", "")
    if not digits.isdigit():
        raise StatCanError(f"Invalid table_id (non-digit): {table_id}")
    if len(digits) == 10:
        return int(digits[:8])
    return int(digits)


def table_id_from_product_id(product_id: int | str, *, suffix: str = "01") -> str:
    """Best-effort display form for a productId (not used as a source of truth)."""
    digits = str(product_id).zfill(8)
    # Common StatCan display: AA-BB-CCCC-DD
    return f"{digits[0:2]}-{digits[2:4]}-{digits[4:8]}-{suffix}"
