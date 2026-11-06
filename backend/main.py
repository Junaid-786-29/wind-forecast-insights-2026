"""
Wind Forecast Analytics — FastAPI application entry point.

API v1 endpoints
----------------
GET /api/v1/health
    Service health check.

GET /api/v1/wind/actuals
    Actual half-hourly wind generation for January 2026 (FUELHH, WIND fuel).
    Optional query params:
        date_from (str, yyyy-MM-dd, default 2026-01-01)
        date_to   (str, yyyy-MM-dd, default 2026-01-31)

GET /api/v1/wind/forecasts
    Wind generation forecasts published over the January 2026 period (WINDFOR).
    Optional query params:
        publish_from        (str, ISO-8601, default 2025-12-31T00:00:00Z)
        publish_to          (str, ISO-8601, default 2026-01-31T23:59:59Z)
        day_ahead_only      (bool, default false) — if true, apply day-ahead
                            cutoff filtering via select_day_ahead_forecasts().
        cutoff_hour_utc     (int, default from env DAY_AHEAD_CUTOFF_HOUR_UTC)
                            — hour on D-1 used as the gate closure cutoff.
"""

import logging
import os
import sys
from datetime import date, datetime

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.services.elexon import (
    DAY_AHEAD_CUTOFF_HOUR_UTC,
    ACTUALS_DATE_FROM,
    ACTUALS_DATE_TO,
    FORECASTS_PUBLISH_FROM,
    FORECASTS_PUBLISH_TO,
    fetch_actual_generation,
    fetch_wind_forecasts,
    select_day_ahead_forecasts,
)
from app.services.analysis import run_forecast_accuracy_analysis
from schemas import (
    ActualRecord,
    ActualsResponse,
    AnalysisIntervalRecord,
    AnalysisResponse,
    ErrorResponse,
    ForecastRecord,
    ForecastsResponse,
    HealthResponse,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Wind Forecast Analytics API",
    description=(
        "Retrieves and exposes January 2026 actual and forecast wind "
        "generation data from the Elexon BMRS API."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS using environment variable for permitted frontend origins (Render/Vercel).
cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
)
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()]
cors_origin_regex = os.getenv("CORS_ORIGIN_REGEX", None)

cors_kwargs = {
    "allow_origins": allow_origins,
    "allow_credentials": False,
    "allow_methods": ["GET", "OPTIONS", "HEAD"],
    "allow_headers": ["*"],
}
if cors_origin_regex:
    cors_kwargs["allow_origin_regex"] = cors_origin_regex

app.add_middleware(CORSMiddleware, **cors_kwargs)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_date(value: str, param_name: str) -> None:
    """Raise 422 if value is not a valid yyyy-MM-dd date string."""
    try:
        date.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"'{param_name}' must be a valid date in yyyy-MM-dd format, got: {value!r}",
        )


def _validate_datetime(value: str, param_name: str) -> None:
    """Raise 422 if value is not a parseable ISO-8601 datetime string."""
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=(
                f"'{param_name}' must be a valid ISO-8601 datetime string "
                f"(e.g. 2026-01-01T00:00:00Z), got: {value!r}"
            ),
        )


def _handle_elexon_error(exc: Exception) -> HTTPException:
    """Convert known exception types into appropriate HTTP errors."""
    if isinstance(exc, requests.Timeout):
        logger.error("Elexon API request timed out: %s", exc)
        return HTTPException(
            status_code=504,
            detail="Upstream Elexon API request timed out. Please try again.",
        )
    if isinstance(exc, requests.HTTPError):
        status = exc.response.status_code if exc.response is not None else 502
        logger.error("Elexon API HTTP error %s: %s", status, exc)
        return HTTPException(
            status_code=502,
            detail=f"Upstream Elexon API returned HTTP {status}: {exc}",
        )
    if isinstance(exc, (ValueError, KeyError)):
        logger.error("Elexon API response parse error: %s", exc)
        return HTTPException(
            status_code=502,
            detail=f"Could not parse Elexon API response: {exc}",
        )
    logger.exception("Unexpected error calling Elexon API")
    return HTTPException(status_code=500, detail=f"Internal server error: {exc}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Service health check",
)
def health() -> HealthResponse:
    """Return a simple alive signal."""
    return HealthResponse(status="ok")


@app.get(
    "/api/v1/wind/actuals",
    response_model=ActualsResponse,
    tags=["Wind"],
    summary="Actual half-hourly wind generation (FUELHH)",
    responses={
        502: {"model": ErrorResponse, "description": "Elexon API error"},
        504: {"model": ErrorResponse, "description": "Elexon API timeout"},
    },
)
def get_wind_actuals(
    date_from: str = Query(
        default=ACTUALS_DATE_FROM,
        description="Settlement date range start (yyyy-MM-dd).",
    ),
    date_to: str = Query(
        default=ACTUALS_DATE_TO,
        description="Settlement date range end inclusive (yyyy-MM-dd).",
    ),
) -> ActualsResponse:
    """
    Retrieve actual half-hourly wind generation from Elexon FUELHH dataset.

    Records are filtered to fuelType == WIND, timestamps are UTC-normalised,
    generation values are validated, and duplicates are removed.
    """
    _validate_date(date_from, "date_from")
    _validate_date(date_to, "date_to")
    if date.fromisoformat(date_from) > date.fromisoformat(date_to):
        raise HTTPException(
            status_code=422, detail="'date_from' must be on or before 'date_to'."
        )

    try:
        records = fetch_actual_generation(date_from=date_from, date_to=date_to)
    except Exception as exc:
        raise _handle_elexon_error(exc) from exc

    return ActualsResponse(
        date_from=date_from,
        date_to=date_to,
        record_count=len(records),
        records=[ActualRecord(**r) for r in records],
    )


@app.get(
    "/api/v1/wind/forecasts",
    response_model=ForecastsResponse,
    tags=["Wind"],
    summary="Wind generation forecasts (WINDFOR)",
    responses={
        502: {"model": ErrorResponse, "description": "Elexon API error"},
        504: {"model": ErrorResponse, "description": "Elexon API timeout"},
    },
)
def get_wind_forecasts(
    publish_from: str = Query(
        default=FORECASTS_PUBLISH_FROM,
        description=(
            "Retrieve forecasts published from this ISO-8601 datetime. "
            "Defaults to 2025-12-31T00:00:00Z to capture D-1 day-ahead runs."
        ),
    ),
    publish_to: str = Query(
        default=FORECASTS_PUBLISH_TO,
        description="Retrieve forecasts published up to this ISO-8601 datetime.",
    ),
    day_ahead_only: bool = Query(
        default=False,
        description=(
            "If true, apply day-ahead gate-closure filtering: for each "
            "delivery period return only the latest forecast whose publishTime "
            "is before the cutoff on D-1."
        ),
    ),
    cutoff_hour_utc: int = Query(
        default=DAY_AHEAD_CUTOFF_HOUR_UTC,
        ge=0,
        le=23,
        description=(
            "Hour (UTC, 0-23) on D-1 used as the day-ahead gate closure "
            "cutoff when day_ahead_only=true. "
            "ASSUMPTION: defaults to 10 (GB N2EX/EPEX market close). "
            "Override with DAY_AHEAD_CUTOFF_HOUR_UTC env var."
        ),
    ),
) -> ForecastsResponse:
    """
    Retrieve WINDFOR wind generation forecasts from the Elexon BMRS API.

    All publishTime values are preserved on each record.  Use day_ahead_only=true
    to filter to the latest day-ahead forecast per delivery period (see the
    cutoff assumption in the response body).
    """
    _validate_datetime(publish_from, "publish_from")
    _validate_datetime(publish_to, "publish_to")

    try:
        records = fetch_wind_forecasts(
            publish_from=publish_from, publish_to=publish_to
        )
    except Exception as exc:
        raise _handle_elexon_error(exc) from exc

    if day_ahead_only:
        records = select_day_ahead_forecasts(
            records, cutoff_hour_utc=cutoff_hour_utc
        )

    return ForecastsResponse(
        publish_from=publish_from,
        publish_to=publish_to,
        record_count=len(records),
        day_ahead_cutoff_hour_utc=cutoff_hour_utc if day_ahead_only else None,
        records=[ForecastRecord(**r) for r in records],
    )


@app.get(
    "/api/v1/wind/analysis",
    response_model=AnalysisResponse,
    tags=["Wind"],
    summary="Wind forecast selection and accuracy analysis",
    responses={
        502: {"model": ErrorResponse, "description": "Elexon API error"},
        504: {"model": ErrorResponse, "description": "Elexon API timeout"},
    },
)
def get_wind_analysis(
    date_from: str = Query(
        default=ACTUALS_DATE_FROM,
        description="Analysis date range start (yyyy-MM-dd).",
    ),
    date_to: str = Query(
        default=ACTUALS_DATE_TO,
        description="Analysis date range end inclusive (yyyy-MM-dd).",
    ),
    cutoff_hour_utc: int = Query(
        default=DAY_AHEAD_CUTOFF_HOUR_UTC,
        ge=0,
        le=23,
        description=(
            "Hour (UTC, 0-23) on D-1 used as the day-ahead gate closure cutoff. "
            "Defaults to 10:00 UTC (GB market auction assumption)."
        ),
    ),
) -> AnalysisResponse:
    """
    Perform wind forecast selection, matching, and accuracy metric calculation for January 2026.

    Matches actual generation (FUELHH) with the latest day-ahead forecast (WINDFOR)
    published at or before the decision cutoff.
    Calculates interval-level errors and aggregate metrics (MAE, RMSE, Bias, MAPE).
    """
    _validate_date(date_from, "date_from")
    _validate_date(date_to, "date_to")
    if date.fromisoformat(date_from) > date.fromisoformat(date_to):
        raise HTTPException(
            status_code=422, detail="'date_from' must be on or before 'date_to'."
        )

    try:
        analysis_data = run_forecast_accuracy_analysis(
            date_from=date_from,
            date_to=date_to,
            cutoff_hour_utc=cutoff_hour_utc,
        )
    except Exception as exc:
        raise _handle_elexon_error(exc) from exc

    return AnalysisResponse(
        date_from=analysis_data["date_from"],
        date_to=analysis_data["date_to"],
        day_ahead_cutoff_hour_utc=analysis_data["day_ahead_cutoff_hour_utc"],
        cutoff_assumption=analysis_data["cutoff_assumption"],
        total_actual_intervals=analysis_data["total_actual_intervals"],
        total_forecast_intervals=analysis_data["total_forecast_intervals"],
        matched_interval_count=analysis_data["matched_interval_count"],
        unmatched_actual_count=analysis_data["unmatched_actual_count"],
        unmatched_forecast_count=analysis_data["unmatched_forecast_count"],
        unmatched_interval_count=analysis_data["unmatched_interval_count"],
        mape_excluded_count=analysis_data["mape_excluded_count"],
        mae=analysis_data["mae"],
        rmse=analysis_data["rmse"],
        bias=analysis_data["bias"],
        mape=analysis_data["mape"],
        intervals=[AnalysisIntervalRecord(**r) for r in analysis_data["intervals"]],
    )


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    logger.info("Starting FastAPI server on 0.0.0.0:%d (PORT env: %s)", port, os.getenv("PORT"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)



