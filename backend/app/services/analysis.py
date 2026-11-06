"""
Wind Forecast Accuracy Analysis Service.

Responsibilities:
1. Day-ahead decision cutoff calculation (configurable, defaulting to 10:00 UTC on D-1).
2. Interval-level forecast selection: selecting the latest forecast published at or before
   the decision cutoff for every target delivery interval, preserving publishTime.
3. Matching actual wind generation (FUELHH) with selected forecasts (WINDFOR) by normalized startTime.
4. Calculating interval-level forecast error, absolute error, squared error, and absolute percentage error.
5. Calculating aggregate accuracy metrics: MAE, RMSE, Bias, and MAPE.
6. Handling zero and near-zero actual generation according to utility analytics standards.
7. Tracking matched and unmatched interval counts.
"""

import logging
import math
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.services.elexon import (
    ACTUALS_DATE_FROM,
    ACTUALS_DATE_TO,
    DAY_AHEAD_CUTOFF_HOUR_UTC,
    FORECASTS_PUBLISH_FROM,
    FORECASTS_PUBLISH_TO,
    fetch_actual_generation,
    fetch_wind_forecasts,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants & Configuration
# ---------------------------------------------------------------------------

# Zero/near-zero threshold for wind generation in Megawatts (MW).
# Wind output <= 0.001 MW (1 kW) is effectively zero / calm.
# Dividing by zero or near-zero produces extreme percentage error distortions
# (e.g. division by 0.0001 yields astronomical numbers).
# Therefore, intervals where actual generation <= ZERO_ACTUAL_THRESHOLD
# have absolute_percentage_error = None and are excluded from the MAPE metric.
ZERO_ACTUAL_THRESHOLD: float = 0.001

CUTOFF_ASSUMPTION_NOTE: str = (
    "Day-ahead decision cutoff defaults to 10:00 UTC on D-1 (day prior to delivery), "
    "aligning with the GB Day-Ahead power auction gate closure (N2EX / EPEX SPOT). "
    "This assumption is configurable via DAY_AHEAD_CUTOFF_HOUR_UTC or endpoint parameters."
)


# ---------------------------------------------------------------------------
# Decision Cutoff & Timestamp Helpers
# ---------------------------------------------------------------------------

def ensure_utc_datetime(dt: Any) -> datetime | None:
    """
    Ensure a datetime object or ISO-8601 string is converted to a timezone-aware UTC datetime.
    Returns None if parsing fails.
    """
    if dt is None:
        return None
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            # Naive datetime: assume UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    if isinstance(dt, str):
        try:
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc)
        except (ValueError, TypeError):
            logger.warning("Could not parse datetime string: %r", dt)
            return None
    return None


def get_day_ahead_decision_cutoff(
    delivery_date: date,
    cutoff_hour_utc: int = DAY_AHEAD_CUTOFF_HOUR_UTC,
) -> datetime:
    """
    Calculate the day-ahead decision cutoff timestamp (UTC) for a given delivery date.

    Convention:
        cutoff = cutoff_hour_utc:00:00 UTC on D-1 (the day before delivery).
        e.g., For delivery on 2026-01-15 with cutoff_hour_utc=10,
        the gate closure cutoff is 2026-01-14 10:00:00 UTC.

    Only forecasts published at or before this timestamp are eligible for selection.
    """
    d_minus_1 = delivery_date - timedelta(days=1)
    return datetime(
        d_minus_1.year,
        d_minus_1.month,
        d_minus_1.day,
        cutoff_hour_utc,
        0,
        0,
        tzinfo=timezone.utc,
    )


# ---------------------------------------------------------------------------
# Forecast Selection Logic
# ---------------------------------------------------------------------------

def select_latest_eligible_forecast(
    forecasts_for_interval: list[dict[str, Any]],
    cutoff_time: datetime,
) -> dict[str, Any] | None:
    """
    Select the latest eligible forecast for a specific delivery interval.

    Rules:
    1. Only consider forecasts published at or before cutoff_time (publish_time <= cutoff_time).
    2. Select the forecast with the latest publish_time among eligible records.
    3. If multiple records share the same latest publish_time, the last one is chosen.
    4. If no forecast was published at or before cutoff_time, return None.
    5. Forecast accuracy/error is NEVER considered in selection.
    """
    eligible = [
        f for f in forecasts_for_interval
        if f.get("publish_time") is not None and f["publish_time"] <= cutoff_time
    ]

    if not eligible:
        return None

    # Maximize by publish_time
    return max(eligible, key=lambda f: f["publish_time"])


# ---------------------------------------------------------------------------
# Interval Error & Aggregate Accuracy Calculations
# ---------------------------------------------------------------------------

def calculate_interval_errors(
    actual: float,
    forecast: float,
    zero_threshold: float = ZERO_ACTUAL_THRESHOLD,
) -> dict[str, float | None]:
    """
    Calculate forecast errors for a single matched interval.

    Formulas:
    - forecast_error = forecast - actual (positive = over-forecast, negative = under-forecast)
    - absolute_error = abs(forecast - actual)
    - squared_error  = (forecast - actual) ** 2
    - absolute_percentage_error = (abs(forecast - actual) / actual) * 100
      (Only computed when actual > zero_threshold; otherwise None)

    Values returned here are unrounded to preserve floating point precision
    for downstream aggregate calculations.
    """
    error = forecast - actual
    abs_error = abs(error)
    sq_error = error ** 2

    if actual > zero_threshold:
        ape = (abs_error / actual) * 100.0
    else:
        ape = None

    return {
        "forecast_error": error,
        "absolute_error": abs_error,
        "squared_error": sq_error,
        "absolute_percentage_error": ape,
    }


def calculate_accuracy_metrics(
    interval_errors: list[dict[str, Any]],
    zero_threshold: float = ZERO_ACTUAL_THRESHOLD,
) -> dict[str, float | int | None]:
    """
    Calculate overall aggregate forecast accuracy metrics across all matched intervals.

    Metrics:
    - MAE  = mean(abs(forecast - actual))
    - RMSE = sqrt(mean((forecast - actual) ** 2))
    - Bias = mean(forecast - actual)
    - MAPE = mean(abs((forecast - actual) / actual)) * 100 (for actual > zero_threshold)
    - mape_excluded_count = count of intervals where actual <= zero_threshold

    Handling of empty datasets:
    - If no matched intervals exist, MAE, RMSE, Bias, and MAPE are None.
    - If all matched intervals have actual <= zero_threshold, MAPE is None.

    Rounding:
    - Final metric float values are rounded to 2 decimal places.
    """
    n = len(interval_errors)
    if n == 0:
        return {
            "mae": None,
            "rmse": None,
            "bias": None,
            "mape": None,
            "mape_excluded_count": 0,
        }

    sum_abs_err = sum(item["absolute_error"] for item in interval_errors)
    sum_sq_err = sum(item["squared_error"] for item in interval_errors)
    sum_err = sum(item["forecast_error"] for item in interval_errors)

    mae = round(sum_abs_err / n, 2)
    rmse = round(math.sqrt(sum_sq_err / n), 2)
    bias = round(sum_err / n, 2)

    # MAPE calculation excluding zero/near-zero actuals
    valid_apes = [
        item["absolute_percentage_error"]
        for item in interval_errors
        if item.get("absolute_percentage_error") is not None
    ]
    mape_excluded_count = n - len(valid_apes)

    if valid_apes:
        mape = round(sum(valid_apes) / len(valid_apes), 2)
    else:
        mape = None

    return {
        "mae": mae,
        "rmse": rmse,
        "bias": bias,
        "mape": mape,
        "mape_excluded_count": mape_excluded_count,
    }


# ---------------------------------------------------------------------------
# Matching & Analysis Pipeline
# ---------------------------------------------------------------------------

def match_actuals_and_forecasts(
    actuals: list[dict[str, Any]],
    forecasts: list[dict[str, Any]],
    cutoff_hour_utc: int = DAY_AHEAD_CUTOFF_HOUR_UTC,
    zero_threshold: float = ZERO_ACTUAL_THRESHOLD,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """
    Match actual wind generation records (FUELHH, half-hourly) with the latest
    eligible day-ahead forecast (WINDFOR, hourly) for each 30-minute delivery interval.

    Granularity & Mapping Convention:
    - FUELHH provides actual generation on a 30-minute cadence (:00 and :30).
    - WINDFOR provides forecast generation on a 60-minute cadence (:00).
    - Each half-hourly actual interval maps to the corresponding hourly forecast
      by flooring its timestamp to the beginning of the hour (e.g. 14:00 and 14:30
      both map to the 14:00 hourly forecast).
    - The original half-hourly startTime is preserved in the matched output.
    - The selected forecast's original forecastPublishTime is preserved.
    - Resolves duplicate actuals by keeping the last valid record.
    - Resolves duplicate forecasts by keeping the latest publication.
    - Ignores actuals with null/invalid/negative generation.
    - Ignores intervals where no forecast was published prior to cutoff.
    - Maintains strict chronological ordering of output intervals.

    Returns:
    - matched_records: list of dicts with interval details and calculated errors.
    - counts: metadata dictionary with:
        total_actual_intervals
        total_forecast_intervals
        matched_interval_count
        unmatched_actual_count
        unmatched_forecast_count
        unmatched_interval_count
    """
    # 1. Clean and normalize actuals
    cleaned_actuals: dict[datetime, float] = {}
    for r in actuals:
        st = ensure_utc_datetime(r.get("start_time") or r.get("startTime"))
        gen = r.get("generation")
        if st is None or gen is None:
            continue
        try:
            val = float(gen)
            if val >= 0:
                cleaned_actuals[st] = val
        except (ValueError, TypeError):
            continue

    # 2. Clean and group forecasts by startTime
    forecasts_by_interval: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for f in forecasts:
        st = ensure_utc_datetime(f.get("start_time") or f.get("startTime"))
        pt = ensure_utc_datetime(f.get("publish_time") or f.get("publishTime"))
        gen = f.get("generation")
        if st is None or pt is None or gen is None:
            continue
        try:
            val = float(gen)
            if val >= 0:
                forecasts_by_interval[st].append({
                    "start_time": st,
                    "publish_time": pt,
                    "generation": val,
                })
        except (ValueError, TypeError):
            continue

    # Deduplicate forecasts with identical (start_time, publish_time)
    for st, f_list in list(forecasts_by_interval.items()):
        seen_pt: dict[datetime, dict[str, Any]] = {}
        for f in f_list:
            seen_pt[f["publish_time"]] = f
        forecasts_by_interval[st] = list(seen_pt.values())

    # 3. For every forecast interval, select latest eligible day-ahead forecast
    selected_forecasts: dict[datetime, dict[str, Any]] = {}
    for st, f_list in forecasts_by_interval.items():
        delivery_date = st.date()
        cutoff_dt = get_day_ahead_decision_cutoff(delivery_date, cutoff_hour_utc)
        selected = select_latest_eligible_forecast(f_list, cutoff_dt)
        if selected is not None:
            selected_forecasts[st] = selected

    # 4. Match actuals and selected forecasts by flooring actual timestamp to the hour
    matched_records: list[dict[str, Any]] = []
    matched_forecast_slots: set[datetime] = set()

    for act_st, act_val in sorted(cleaned_actuals.items()):
        # Floor actual timestamp to the beginning of the hour (e.g. 14:00 and 14:30 -> 14:00)
        fc_st = act_st.replace(minute=0, second=0, microsecond=0)

        # Check if an eligible forecast exists for this hourly interval
        fc_record = selected_forecasts.get(fc_st)
        if fc_record is None:
            continue

        matched_forecast_slots.add(fc_st)
        fc_val = fc_record["generation"]
        fc_publish_time = fc_record["publish_time"]

        errors = calculate_interval_errors(act_val, fc_val, zero_threshold=zero_threshold)

        matched_records.append({
            "startTime": act_st,
            "actualGeneration": round(act_val, 2),
            "forecastGeneration": round(fc_val, 2),
            "forecastPublishTime": fc_publish_time,
            "forecastError": round(errors["forecast_error"], 2),
            "absoluteError": round(errors["absolute_error"], 2),
            "squaredError": round(errors["squared_error"], 2),
            "absolutePercentageError": (
                round(errors["absolute_percentage_error"], 2)
                if errors["absolute_percentage_error"] is not None
                else None
            ),
            # Internal unrounded values for metric aggregation
            "_unrounded": errors,
        })

    # Calculate interval counts
    all_actual_slots = set(cleaned_actuals.keys())
    all_forecast_slots = set(selected_forecasts.keys())
    total_actual_count = len(all_actual_slots)
    total_forecast_count = len(forecasts_by_interval.keys())
    matched_count = len(matched_records)
    unmatched_actual_count = total_actual_count - matched_count
    unmatched_forecast_count = len(all_forecast_slots - matched_forecast_slots)
    total_unmatched_count = unmatched_actual_count + unmatched_forecast_count

    counts = {
        "total_actual_intervals": total_actual_count,
        "total_forecast_intervals": total_forecast_count,
        "matched_interval_count": matched_count,
        "unmatched_actual_count": unmatched_actual_count,
        "unmatched_forecast_count": unmatched_forecast_count,
        "unmatched_interval_count": total_unmatched_count,
    }

    return matched_records, counts


def run_forecast_accuracy_analysis(
    date_from: str = ACTUALS_DATE_FROM,
    date_to: str = ACTUALS_DATE_TO,
    cutoff_hour_utc: int = DAY_AHEAD_CUTOFF_HOUR_UTC,
    actuals: list[dict[str, Any]] | None = None,
    forecasts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    End-to-end analysis orchestration:
    1. Retrieve FUELHH actual wind generation if not provided.
    2. Retrieve WINDFOR forecast wind generation if not provided.
    3. Match actual and eligible forecast records.
    4. Calculate interval errors and overall metrics (MAE, RMSE, Bias, MAPE).
    5. Construct complete result dictionary.
    """
    logger.info(
        "Running wind forecast accuracy analysis: %s to %s (cutoff_hour_utc=%d)",
        date_from,
        date_to,
        cutoff_hour_utc,
    )

    if actuals is None:
        actuals = fetch_actual_generation(date_from=date_from, date_to=date_to)

    if forecasts is None:
        # Pull publications starting from D-1 (31 Dec 2025) through the end date
        # to ensure all day-ahead runs are captured
        forecasts = fetch_wind_forecasts(
            publish_from=FORECASTS_PUBLISH_FROM,
            publish_to=f"{date_to}T23:59:59Z",
        )

    matched_records, counts = match_actuals_and_forecasts(
        actuals=actuals,
        forecasts=forecasts,
        cutoff_hour_utc=cutoff_hour_utc,
        zero_threshold=ZERO_ACTUAL_THRESHOLD,
    )

    # Calculate overall metrics using unrounded interval error values
    unrounded_errors = [r["_unrounded"] for r in matched_records]
    metrics = calculate_accuracy_metrics(unrounded_errors, zero_threshold=ZERO_ACTUAL_THRESHOLD)

    # Clean internal unrounded fields from records before returning
    for r in matched_records:
        r.pop("_unrounded", None)

    return {
        "date_from": date_from,
        "date_to": date_to,
        "day_ahead_cutoff_hour_utc": cutoff_hour_utc,
        "cutoff_assumption": CUTOFF_ASSUMPTION_NOTE,
        "total_actual_intervals": counts["total_actual_intervals"],
        "total_forecast_intervals": counts["total_forecast_intervals"],
        "matched_interval_count": counts["matched_interval_count"],
        "unmatched_actual_count": counts["unmatched_actual_count"],
        "unmatched_forecast_count": counts["unmatched_forecast_count"],
        "unmatched_interval_count": counts["unmatched_interval_count"],
        "mape_excluded_count": metrics["mape_excluded_count"],
        "mae": metrics["mae"],
        "rmse": metrics["rmse"],
        "bias": metrics["bias"],
        "mape": metrics["mape"],
        "intervals": matched_records,
    }

