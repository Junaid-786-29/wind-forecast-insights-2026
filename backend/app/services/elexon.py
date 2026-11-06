"""
Elexon BMRS API integration service.

Data sources
------------
Actuals : GET /datasets/FUELHH/stream
  Filter by settlementDateFrom / settlementDateTo (yyyy-MM-dd).
  Further filtered to fuelType == "WIND".
  Fields used: startTime, generation, fuelType.

Forecasts : GET /datasets/WINDFOR/stream
  Filter by publishDateTimeFrom / publishDateTimeTo.
  For January 2026 delivery we request forecasts published between
  2025-12-31T00:00:00Z and 2026-01-31T23:59:59Z so we capture every
  day-ahead run that covers a January settlement period.
  Fields used: startTime, publishTime, generation.

API base URL : https://data.elexon.co.uk/bmrs/api/v1
No authentication required (public API).

Day-ahead forecast cutoff
--------------------------
WINDFOR is published up to 8 times per day at approximately
03:30, 05:30, 08:30, 10:30, 12:30, 16:30, 19:30, 23:30 UTC.

The GB Day-Ahead electricity market (N2EX / EPEX SPOT) gate closes at
approximately 10:00 UTC on day D-1.  The last WINDFOR run *before* that
gate is typically the 08:30 UTC publication on D-1.

We therefore default the cutoff to 10:00 UTC (D-1), which is exposed as
DAY_AHEAD_CUTOFF_HOUR_UTC in this module and can be overridden by callers
or via an environment variable.

IMPORTANT: This cutoff is an assumption derived from published market
documentation and WINDFOR publication schedule.  It has not been verified
against a primary Elexon contractual source.  The business team must
confirm before using this for procurement decisions.
"""

import logging
import os
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

# January 2026 is the target month for actuals.
ACTUALS_DATE_FROM = "2026-01-01"
ACTUALS_DATE_TO = "2026-01-31"

# For forecasts we pull publications from D-1 (31 Dec 2025) through end of
# January so we capture all day-ahead runs for every January settlement period.
FORECASTS_PUBLISH_FROM = "2025-12-31T00:00:00Z"
FORECASTS_PUBLISH_TO = "2026-01-31T23:59:59Z"

# Request settings
REQUEST_TIMEOUT: int = 60          # seconds per HTTP request
CHUNK_DAYS: int = 7                # days per chunk for FUELHH
INTER_REQUEST_DELAY: float = 0.25  # seconds between chunked requests

# Day-ahead gate closure hour (UTC).  Configurable; see module docstring.
DAY_AHEAD_CUTOFF_HOUR_UTC: int = int(
    os.getenv("DAY_AHEAD_CUTOFF_HOUR_UTC", "10")
)


# ---------------------------------------------------------------------------
# Low-level HTTP helper
# ---------------------------------------------------------------------------

def _get(url: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Perform a GET request and return the parsed JSON list.

    The Elexon BMRS stream endpoints return a JSON array directly.
    Raises requests.HTTPError on non-2xx responses.
    Raises requests.Timeout if the server does not respond within
    REQUEST_TIMEOUT seconds.
    """
    logger.debug("GET %s params=%s", url, params)
    response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        # Some error envelopes are dicts — surface them clearly.
        raise ValueError(
            f"Unexpected response shape from {url}: expected list, "
            f"got {type(data).__name__}. Body: {str(data)[:300]}"
        )
    return data


# ---------------------------------------------------------------------------
# Timestamp normalisation
# ---------------------------------------------------------------------------

def _parse_utc_timestamp(raw: Any, field_name: str) -> datetime | None:
    """
    Parse an ISO-8601 timestamp string into a timezone-aware UTC datetime.

    Returns None if the value is missing or cannot be parsed, logging a
    warning rather than raising so that one bad record does not abort a batch.
    """
    if raw is None:
        logger.warning("Field '%s' is null — skipping timestamp parse.", field_name)
        return None
    if not isinstance(raw, str):
        logger.warning(
            "Field '%s' has unexpected type %s (value: %r) — skipping.",
            field_name, type(raw).__name__, raw,
        )
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        # Ensure the result is always UTC-aware even if the string had an offset.
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        logger.warning(
            "Could not parse '%s' value %r as ISO-8601: %s", field_name, raw, exc
        )
        return None


# ---------------------------------------------------------------------------
# Data-level validation helpers
# ---------------------------------------------------------------------------

def _parse_generation(raw: Any, context: str) -> float | None:
    """
    Coerce a generation value to float.

    Returns None for null, non-numeric, or negative values, logging a warning
    each time so silent data corruption is avoided.
    """
    if raw is None:
        logger.warning("generation is null in record %s — excluded.", context)
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        logger.warning(
            "generation %r is non-numeric in record %s — excluded.", raw, context
        )
        return None
    if value < 0:
        logger.warning(
            "generation %.2f is negative in record %s — excluded.", value, context
        )
        return None
    return value


# ---------------------------------------------------------------------------
# Actual generation (FUELHH)
# ---------------------------------------------------------------------------

def _fetch_fuelhh_chunk(date_from: str, date_to: str) -> list[dict[str, Any]]:
    """Fetch a single FUELHH chunk using settlement date range."""
    url = f"{BASE_URL}/datasets/FUELHH/stream"
    params = {
        "settlementDateFrom": date_from,
        "settlementDateTo": date_to,
    }
    return _get(url, params)


def _chunk_date_range(
    start: date, end: date, chunk_size_days: int
) -> list[tuple[date, date]]:
    """
    Split [start, end] inclusive into chunks of at most chunk_size_days days.
    Returns a list of (chunk_start, chunk_end) tuples.
    """
    chunks: list[tuple[date, date]] = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_size_days - 1), end)
        chunks.append((current, chunk_end))
        current = chunk_end + timedelta(days=1)
    return chunks


def fetch_actual_generation(
    date_from: str = ACTUALS_DATE_FROM,
    date_to: str = ACTUALS_DATE_TO,
) -> list[dict[str, Any]]:
    """
    Retrieve half-hourly actual wind generation from FUELHH for the given
    settlement date range (inclusive, format: yyyy-MM-dd).

    Steps
    -----
    1. Chunk the date range into CHUNK_DAYS-day windows to avoid oversized
       responses.
    2. Filter to fuelType == "WIND".
    3. Normalise startTime to UTC-aware datetimes.
    4. Validate generation values.
    5. Deduplicate by (startTime, settlementPeriod) keeping the last seen
       record (consistent with Elexon re-publication behaviour).

    Returns a list of dicts with keys:
        start_time  : datetime (UTC-aware)
        generation  : float (MW)
        settlement_date : str (yyyy-MM-dd, as returned by API)
        settlement_period : int | None
    """
    start_dt = date.fromisoformat(date_from)
    end_dt = date.fromisoformat(date_to)
    chunks = _chunk_date_range(start_dt, end_dt, CHUNK_DAYS)

    raw_records: list[dict[str, Any]] = []
    for chunk_start, chunk_end in chunks:
        logger.info(
            "Fetching FUELHH actuals: %s to %s", chunk_start, chunk_end
        )
        chunk_data = _fetch_fuelhh_chunk(
            chunk_start.isoformat(), chunk_end.isoformat()
        )
        raw_records.extend(chunk_data)
        if len(chunks) > 1:
            time.sleep(INTER_REQUEST_DELAY)

    logger.info("FUELHH raw records (all fuels): %d", len(raw_records))

    # --- Filter to WIND ---
    wind_records = [
        r for r in raw_records if r.get("fuelType") == "WIND"
    ]
    logger.info("FUELHH WIND records before dedup: %d", len(wind_records))

    # --- Normalise and validate ---
    seen: dict[tuple, dict[str, Any]] = {}  # (start_time_iso, period) -> record
    skipped = 0
    for record in wind_records:
        start_time = _parse_utc_timestamp(record.get("startTime"), "startTime")
        if start_time is None:
            skipped += 1
            continue

        generation = _parse_generation(
            record.get("generation"),
            context=f"startTime={record.get('startTime')}",
        )
        if generation is None:
            skipped += 1
            continue

        settlement_date = record.get("settlementDate")
        settlement_period = record.get("settlementPeriod")

        dedup_key = (start_time.isoformat(), settlement_period)
        seen[dedup_key] = {
            "start_time": start_time,
            "generation": generation,
            "settlement_date": settlement_date,
            "settlement_period": settlement_period,
        }

    if skipped:
        logger.warning(
            "Skipped %d WIND records due to missing/invalid fields.", skipped
        )

    result = list(seen.values())
    # Sort by start_time for a predictable output order
    result.sort(key=lambda r: r["start_time"])
    logger.info("Returning %d validated actual wind records.", len(result))
    return result


# ---------------------------------------------------------------------------
# Wind generation forecasts (WINDFOR)
# ---------------------------------------------------------------------------

def _fetch_windfor_chunk(
    publish_from: str, publish_to: str
) -> list[dict[str, Any]]:
    """
    Fetch a single WINDFOR chunk filtered by publish timestamp range.

    The WINDFOR stream endpoint uses publishDateTimeFrom / publishDateTimeTo
    (ISO-8601 datetime strings) rather than settlement date parameters.
    """
    url = f"{BASE_URL}/datasets/WINDFOR/stream"
    params = {
        "publishDateTimeFrom": publish_from,
        "publishDateTimeTo": publish_to,
    }
    return _get(url, params)


def fetch_wind_forecasts(
    publish_from: str = FORECASTS_PUBLISH_FROM,
    publish_to: str = FORECASTS_PUBLISH_TO,
) -> list[dict[str, Any]]:
    """
    Retrieve wind generation forecasts from WINDFOR.

    Fetches all forecasts published between publish_from and publish_to
    (ISO-8601 strings).  By default this covers D-1 (31 Dec 2025) through
    the end of January 2026, capturing every day-ahead run relevant to
    January delivery periods.

    publishTime is preserved on every record so that callers can apply their
    own version-selection logic (e.g., day-ahead cutoff filtering).

    Returns a list of dicts with keys:
        start_time   : datetime (UTC-aware) — target delivery period
        publish_time : datetime (UTC-aware) — when this forecast was published
        generation   : float (MW)
    """
    logger.info(
        "Fetching WINDFOR forecasts published between %s and %s",
        publish_from,
        publish_to,
    )
    raw_records = _fetch_windfor_chunk(publish_from, publish_to)
    logger.info("WINDFOR raw records: %d", len(raw_records))

    seen: dict[tuple, dict[str, Any]] = {}  # (start_time_iso, publish_time_iso) -> record
    skipped = 0

    for record in raw_records:
        start_time = _parse_utc_timestamp(record.get("startTime"), "startTime")
        publish_time = _parse_utc_timestamp(record.get("publishTime"), "publishTime")
        generation = _parse_generation(
            record.get("generation"),
            context=(
                f"startTime={record.get('startTime')} "
                f"publishTime={record.get('publishTime')}"
            ),
        )

        if start_time is None or publish_time is None or generation is None:
            skipped += 1
            continue

        # Dedup key: same (delivery period, publish run) is one unique forecast.
        dedup_key = (start_time.isoformat(), publish_time.isoformat())
        seen[dedup_key] = {
            "start_time": start_time,
            "publish_time": publish_time,
            "generation": generation,
        }

    if skipped:
        logger.warning(
            "Skipped %d forecast records due to missing/invalid fields.", skipped
        )

    result = list(seen.values())
    result.sort(key=lambda r: (r["start_time"], r["publish_time"]))
    logger.info("Returning %d validated forecast records.", len(result))
    return result


# ---------------------------------------------------------------------------
# Day-ahead forecast version selection (business logic, separate from fetch)
# ---------------------------------------------------------------------------

def select_day_ahead_forecasts(
    forecasts: list[dict[str, Any]],
    cutoff_hour_utc: int = DAY_AHEAD_CUTOFF_HOUR_UTC,
) -> list[dict[str, Any]]:
    """
    For each delivery date, select the latest forecast whose publishTime is
    strictly before the day-ahead gate closure on D-1.

    The gate closure is modelled as HH:00 UTC on the day before delivery
    (D-1), where HH = cutoff_hour_utc (default 10, configurable).

    ASSUMPTION: The day-ahead cutoff is taken as 10:00 UTC on D-1, consistent
    with the GB N2EX / EPEX SPOT day-ahead market auction close.  This has not
    been confirmed against a primary Elexon contractual document.  Set the
    DAY_AHEAD_CUTOFF_HOUR_UTC environment variable or pass cutoff_hour_utc to
    override.

    Parameters
    ----------
    forecasts : list of dicts as returned by fetch_wind_forecasts()
    cutoff_hour_utc : int — hour of day (UTC) on D-1 that acts as the cutoff

    Returns
    -------
    List of one record per delivery half-hour, each being the latest forecast
    published before the cutoff for that delivery day.  Records that have no
    eligible forecast before the cutoff are omitted.
    """
    # Group by delivery date (UTC date of start_time)
    from collections import defaultdict

    by_delivery_date: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for fc in forecasts:
        delivery_date = fc["start_time"].date()
        by_delivery_date[delivery_date].append(fc)

    result: list[dict[str, Any]] = []
    for delivery_date, recs in sorted(by_delivery_date.items()):
        # Cutoff = cutoff_hour_utc:00 on D-1
        gate_closure = datetime(
            delivery_date.year,
            delivery_date.month,
            delivery_date.day,
            cutoff_hour_utc,
            0,
            0,
            tzinfo=timezone.utc,
        ) - timedelta(days=1)

        # Keep only forecasts published at or before gate closure (D-1 cutoff)
        eligible = [r for r in recs if r["publish_time"] <= gate_closure]
        if not eligible:
            logger.debug(
                "No eligible day-ahead forecast for delivery date %s "
                "(cutoff %s UTC).",
                delivery_date,
                gate_closure,
            )
            continue

        # For each half-hour slot, take the latest eligible publication
        by_slot: dict[str, dict[str, Any]] = {}
        for rec in eligible:
            slot_key = rec["start_time"].isoformat()
            if slot_key not in by_slot or rec["publish_time"] > by_slot[slot_key]["publish_time"]:
                by_slot[slot_key] = rec

        result.extend(sorted(by_slot.values(), key=lambda r: r["start_time"]))

    logger.info(
        "select_day_ahead_forecasts: returning %d records "
        "(cutoff_hour_utc=%d).",
        len(result),
        cutoff_hour_utc,
    )
    return result
