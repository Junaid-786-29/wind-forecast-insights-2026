"""
Pydantic v2 response schemas for the Wind Forecast Analytics API.

All datetime fields are serialised as ISO-8601 UTC strings
(e.g. "2026-01-15T12:00:00Z") so JSON output is unambiguous.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


# ---------------------------------------------------------------------------
# Shared datetime serialiser mixin
# ---------------------------------------------------------------------------

class _DatetimeAsUTCStr(BaseModel):
    """Serialises every datetime field as a UTC ISO-8601 string."""

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    @field_serializer(
        "start_time",
        "publish_time",
        "forecast_publish_time",
        when_used="always",
        check_fields=False,
    )
    def _fmt_dt(self, v: Any) -> Any:  # noqa: D401
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%dT%H:%M:%SZ")
        return v


# ---------------------------------------------------------------------------
# Actual generation
# ---------------------------------------------------------------------------

class ActualRecord(_DatetimeAsUTCStr):
    """A single half-hourly actual wind generation record."""

    start_time: datetime
    generation: float
    settlement_date: str | None = None
    settlement_period: int | None = None


class ActualsResponse(BaseModel):
    """Response envelope for the /wind/actuals endpoint."""

    dataset: str = "FUELHH"
    fuel_type: str = "WIND"
    date_from: str
    date_to: str
    record_count: int
    records: list[ActualRecord]


# ---------------------------------------------------------------------------
# Wind generation forecasts
# ---------------------------------------------------------------------------

class ForecastRecord(_DatetimeAsUTCStr):
    """A single WINDFOR forecast record (one delivery slot, one publish run)."""

    start_time: datetime
    publish_time: datetime
    generation: float


class ForecastsResponse(BaseModel):
    """Response envelope for the /wind/forecasts endpoint."""

    dataset: str = "WINDFOR"
    publish_from: str
    publish_to: str
    record_count: int
    day_ahead_cutoff_hour_utc: int | None = None
    cutoff_assumption: str = (
        "Day-ahead cutoff defaults to 10:00 UTC on D-1 (GB N2EX/EPEX gate "
        "closure assumption — not confirmed against primary Elexon documentation). "
        "Set DAY_AHEAD_CUTOFF_HOUR_UTC env var or query param to override."
    )
    records: list[ForecastRecord]


# ---------------------------------------------------------------------------
# Forecast Accuracy Analysis (Phase 2)
# ---------------------------------------------------------------------------

class AnalysisIntervalRecord(_DatetimeAsUTCStr):
    """
    Interval-level comparison between actual and selected forecast generation.
    Field aliases match Section 7 specification (camelCase for dashboard consumption).
    """

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    start_time: datetime = Field(..., alias="startTime")
    actual_generation: float = Field(..., alias="actualGeneration")
    forecast_generation: float = Field(..., alias="forecastGeneration")
    forecast_publish_time: datetime = Field(..., alias="forecastPublishTime")
    forecast_error: float = Field(..., alias="forecastError")
    absolute_error: float = Field(..., alias="absoluteError")
    squared_error: float = Field(..., alias="squaredError")
    absolute_percentage_error: float | None = Field(None, alias="absolutePercentageError")


class AnalysisResponse(BaseModel):
    """Response envelope for the /wind/analysis endpoint."""

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    date_from: str
    date_to: str
    day_ahead_cutoff_hour_utc: int
    cutoff_assumption: str
    total_actual_intervals: int
    total_forecast_intervals: int
    matched_interval_count: int
    unmatched_actual_count: int
    unmatched_forecast_count: int
    unmatched_interval_count: int
    mape_excluded_count: int
    mae: float | None = None
    rmse: float | None = None
    bias: float | None = None
    mape: float | None = None
    intervals: list[AnalysisIntervalRecord]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Response for the /health endpoint."""

    status: str
    version: str = "1.0.0"
    service: str = "wind-forecast-analytics"


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: str
    detail: str | None = None
