"""
Phase 2 Test Suite: Wind Forecast Selection and Accuracy Analysis.

Covers all 14 requirements specified in Phase 2:
1. Latest eligible forecast selection.
2. Exclusion of forecasts published after cutoff.
3. Correct matching by startTime.
4. Timezone handling (naive, UTC, offsets).
5. Duplicate records (actuals and forecasts).
6. Missing actual values.
7. Missing eligible forecasts.
8. MAE calculation.
9. RMSE calculation.
10. Bias calculation.
11. MAPE calculation.
12. Zero and near-zero actual values.
13. Empty datasets.
14. API response structure (/api/v1/wind/analysis).

All tests use mocked data and test clients without making live API calls.
"""

import math
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient

from app.services.analysis import (
    CUTOFF_ASSUMPTION_NOTE,
    ZERO_ACTUAL_THRESHOLD,
    calculate_accuracy_metrics,
    calculate_interval_errors,
    ensure_utc_datetime,
    get_day_ahead_decision_cutoff,
    match_actuals_and_forecasts,
    run_forecast_accuracy_analysis,
    select_latest_eligible_forecast,
)
from main import app

client = TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

def _make_utc_dt(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, 0, tzinfo=timezone.utc)


# ===========================================================================
# 1. Latest eligible forecast selection
# ===========================================================================

class TestForecastSelection:

    def test_selects_latest_eligible_forecast(self):
        """Among multiple runs published prior to cutoff, select the one with the latest publishTime."""
        target_delivery = _make_utc_dt(2026, 1, 15, 12, 0)
        cutoff = _make_utc_dt(2026, 1, 14, 10, 0)  # 10:00 UTC on D-1

        forecast_early = {
            "start_time": target_delivery,
            "publish_time": _make_utc_dt(2026, 1, 14, 3, 30),
            "generation": 3500.0,
        }
        forecast_mid = {
            "start_time": target_delivery,
            "publish_time": _make_utc_dt(2026, 1, 14, 5, 30),
            "generation": 3800.0,
        }
        forecast_latest_eligible = {
            "start_time": target_delivery,
            "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
            "generation": 4000.0,
        }

        forecasts = [forecast_early, forecast_latest_eligible, forecast_mid]
        selected = select_latest_eligible_forecast(forecasts, cutoff)

        assert selected is not None
        assert selected["publish_time"] == _make_utc_dt(2026, 1, 14, 8, 30)
        assert selected["generation"] == 4000.0

    def test_selection_ignores_error_value(self):
        """Selection must NEVER pick a forecast because it is closer to actual."""
        target_delivery = _make_utc_dt(2026, 1, 15, 12, 0)
        cutoff = _make_utc_dt(2026, 1, 14, 10, 0)

        # Early run (e.g. perfect match to future actual), late run (higher deviation)
        f_early = {
            "start_time": target_delivery,
            "publish_time": _make_utc_dt(2026, 1, 14, 3, 30),
            "generation": 5000.0,
        }
        f_late = {
            "start_time": target_delivery,
            "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
            "generation": 6000.0,
        }

        selected = select_latest_eligible_forecast([f_early, f_late], cutoff)
        assert selected["publish_time"] == _make_utc_dt(2026, 1, 14, 8, 30)


# ===========================================================================
# 2. Exclusion of forecasts published after cutoff
# ===========================================================================

class TestCutoffExclusion:

    def test_excludes_forecasts_published_after_cutoff(self):
        """Forecasts published strictly after the cutoff timestamp must be excluded."""
        target_delivery = _make_utc_dt(2026, 1, 15, 12, 0)
        cutoff = _make_utc_dt(2026, 1, 14, 10, 0)

        post_cutoff_run = {
            "start_time": target_delivery,
            "publish_time": _make_utc_dt(2026, 1, 14, 10, 30),
            "generation": 4500.0,
        }
        day_of_run = {
            "start_time": target_delivery,
            "publish_time": _make_utc_dt(2026, 1, 15, 6, 0),
            "generation": 4900.0,
        }

        selected = select_latest_eligible_forecast([post_cutoff_run, day_of_run], cutoff)
        assert selected is None

    def test_forecast_published_at_exact_cutoff_is_eligible(self):
        """A forecast published at or before the cutoff is eligible."""
        target_delivery = _make_utc_dt(2026, 1, 15, 12, 0)
        cutoff = _make_utc_dt(2026, 1, 14, 10, 0)

        exact_cutoff_run = {
            "start_time": target_delivery,
            "publish_time": cutoff,
            "generation": 4200.0,
        }
        just_after = {
            "start_time": target_delivery,
            "publish_time": cutoff + timedelta(seconds=1),
            "generation": 4300.0,
        }

        selected = select_latest_eligible_forecast([exact_cutoff_run, just_after], cutoff)
        assert selected is not None
        assert selected["publish_time"] == cutoff


# ===========================================================================
# 3. Correct matching by startTime
# ===========================================================================

class TestMatchingByStartTime:

    def test_zero_minute_actual_mapping(self):
        """:00 actual interval maps to the corresponding :00 hourly forecast."""
        slot = _make_utc_dt(2026, 1, 15, 14, 0)
        actuals = [{"start_time": slot, "generation": 3500.0}]
        forecasts = [
            {
                "start_time": slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3600.0,
            }
        ]
        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 1
        assert counts["unmatched_actual_count"] == 0
        assert matched[0]["startTime"] == slot
        assert matched[0]["actualGeneration"] == 3500.0
        assert matched[0]["forecastGeneration"] == 3600.0
        assert matched[0]["forecastPublishTime"] == _make_utc_dt(2026, 1, 14, 8, 30)

    def test_thirty_minute_actual_mapping(self):
        """:30 actual interval maps to the :00 hourly forecast of the same hour."""
        act_slot = _make_utc_dt(2026, 1, 15, 14, 30)
        fc_slot = _make_utc_dt(2026, 1, 15, 14, 0)
        actuals = [{"start_time": act_slot, "generation": 3700.0}]
        forecasts = [
            {
                "start_time": fc_slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3600.0,
            }
        ]
        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 1
        assert counts["unmatched_actual_count"] == 0
        assert matched[0]["startTime"] == act_slot  # Preserves :30 timestamp
        assert matched[0]["actualGeneration"] == 3700.0
        assert matched[0]["forecastGeneration"] == 3600.0
        assert matched[0]["forecastPublishTime"] == _make_utc_dt(2026, 1, 14, 8, 30)

    def test_both_half_hourly_periods_use_same_hourly_forecast(self):
        """Both :00 and :30 intervals in the same hour map to the same hourly forecast."""
        slot_00 = _make_utc_dt(2026, 1, 15, 14, 0)
        slot_30 = _make_utc_dt(2026, 1, 15, 14, 30)
        fc_slot = _make_utc_dt(2026, 1, 15, 14, 0)

        actuals = [
            {"start_time": slot_00, "generation": 3000.0},
            {"start_time": slot_30, "generation": 3200.0},
        ]
        forecasts = [
            {
                "start_time": fc_slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3100.0,
            }
        ]

        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 2
        assert counts["unmatched_actual_count"] == 0
        assert counts["unmatched_forecast_count"] == 0

        # First interval (:00)
        assert matched[0]["startTime"] == slot_00
        assert matched[0]["actualGeneration"] == 3000.0
        assert matched[0]["forecastGeneration"] == 3100.0
        assert matched[0]["forecastError"] == 100.0  # 3100 - 3000

        # Second interval (:30)
        assert matched[1]["startTime"] == slot_30
        assert matched[1]["actualGeneration"] == 3200.0
        assert matched[1]["forecastGeneration"] == 3100.0  # Same hourly forecast
        assert matched[1]["forecastError"] == -100.0  # 3100 - 3200

    def test_preserves_original_half_hourly_timestamps(self):
        """Matched records must retain their exact original 30-minute timestamps."""
        slot_00 = _make_utc_dt(2026, 1, 15, 15, 0)
        slot_30 = _make_utc_dt(2026, 1, 15, 15, 30)
        actuals = [
            {"start_time": slot_00, "generation": 4000.0},
            {"start_time": slot_30, "generation": 4100.0},
        ]
        forecasts = [
            {
                "start_time": slot_00,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 4050.0,
            }
        ]
        matched, _ = match_actuals_and_forecasts(actuals, forecasts)
        assert matched[0]["startTime"] == slot_00
        assert matched[1]["startTime"] == slot_30
        assert matched[0]["startTime"].minute == 0
        assert matched[1]["startTime"].minute == 30

    def test_missing_hourly_forecast_leaves_actuals_unmatched(self):
        """When an hourly forecast is missing, both constituent half-hours remain unmatched."""
        slot_00 = _make_utc_dt(2026, 1, 15, 16, 0)
        slot_30 = _make_utc_dt(2026, 1, 15, 16, 30)
        # Forecast only exists for hour 14
        actuals = [
            {"start_time": slot_00, "generation": 3000.0},
            {"start_time": slot_30, "generation": 3200.0},
        ]
        forecasts = [
            {
                "start_time": _make_utc_dt(2026, 1, 15, 14, 0),
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3100.0,
            }
        ]
        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 0
        assert counts["total_actual_intervals"] == 2
        assert counts["unmatched_actual_count"] == 2
        assert counts["unmatched_forecast_count"] == 1  # 14:00 forecast was never matched
        assert len(matched) == 0

    def test_forecast_publication_after_cutoff_is_excluded(self):
        """Forecast published after D-1 gate closure (10:00 UTC) is excluded."""
        slot_00 = _make_utc_dt(2026, 1, 15, 14, 0)
        slot_30 = _make_utc_dt(2026, 1, 15, 14, 30)
        actuals = [
            {"start_time": slot_00, "generation": 3000.0},
            {"start_time": slot_30, "generation": 3200.0},
        ]
        # Published at 16:30 on D-1 (after 10:00 cutoff)
        forecasts = [
            {
                "start_time": slot_00,
                "publish_time": _make_utc_dt(2026, 1, 14, 16, 30),
                "generation": 3100.0,
            }
        ]
        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 0
        assert counts["unmatched_actual_count"] == 2
        assert counts["unmatched_forecast_count"] == 0  # No eligible forecasts in selected_forecasts

    def test_correct_matched_and_unmatched_counts(self):
        """Verify counts across multiple hours and extra forecast horizons."""
        # 4 actual intervals (hours 14 and 15)
        actuals = [
            {"start_time": _make_utc_dt(2026, 1, 15, 14, 0), "generation": 3000.0},
            {"start_time": _make_utc_dt(2026, 1, 15, 14, 30), "generation": 3200.0},
            {"start_time": _make_utc_dt(2026, 1, 15, 15, 0), "generation": 3400.0},
            {"start_time": _make_utc_dt(2026, 1, 15, 15, 30), "generation": 3600.0},
        ]
        # 3 hourly forecasts: 14:00, 15:00, and 16:00 (no actuals for 16:00)
        forecasts = [
            {
                "start_time": _make_utc_dt(2026, 1, 15, 14, 0),
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3100.0,
            },
            {
                "start_time": _make_utc_dt(2026, 1, 15, 15, 0),
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3500.0,
            },
            {
                "start_time": _make_utc_dt(2026, 1, 15, 16, 0),
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3800.0,
            },
        ]
        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["total_actual_intervals"] == 4
        assert counts["total_forecast_intervals"] == 3
        assert counts["matched_interval_count"] == 4
        assert counts["unmatched_actual_count"] == 0
        assert counts["unmatched_forecast_count"] == 1  # 16:00 forecast has no actuals
        assert counts["unmatched_interval_count"] == 1

    def test_metric_calculations_after_half_hourly_mapping(self):
        """Error and metric calculations accurately reflect half-hourly mapping."""
        # Hour 14: actual 3000 & 3200, forecast 3100 -> errors: +100, -100
        # Hour 15: actual 3500 & 3500, forecast 3600 -> errors: +100, +100
        actuals = [
            {"start_time": _make_utc_dt(2026, 1, 15, 14, 0), "generation": 3000.0},
            {"start_time": _make_utc_dt(2026, 1, 15, 14, 30), "generation": 3200.0},
            {"start_time": _make_utc_dt(2026, 1, 15, 15, 0), "generation": 3500.0},
            {"start_time": _make_utc_dt(2026, 1, 15, 15, 30), "generation": 3500.0},
        ]
        forecasts = [
            {
                "start_time": _make_utc_dt(2026, 1, 15, 14, 0),
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3100.0,
            },
            {
                "start_time": _make_utc_dt(2026, 1, 15, 15, 0),
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 3600.0,
            },
        ]
        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 4

        unrounded = [m["_unrounded"] for m in matched]
        metrics = calculate_accuracy_metrics(unrounded)

        # Errors: [+100, -100, +100, +100]
        # Absolute errors: [100, 100, 100, 100] -> MAE = 100.0
        # Squared errors: [10000, 10000, 10000, 10000] -> RMSE = 100.0
        # Bias: (100 - 100 + 100 + 100) / 4 = 50.0
        assert metrics["mae"] == 100.0
        assert metrics["rmse"] == 100.0
        assert metrics["bias"] == 50.0


# ===========================================================================
# 4. Timezone handling
# ===========================================================================

class TestTimezoneHandling:

    def test_naive_datetime_treated_as_utc(self):
        """Naive datetime strings/objects are normalized to UTC without dropping."""
        naive_dt = datetime(2026, 1, 15, 12, 0)
        utc_dt = ensure_utc_datetime(naive_dt)
        assert utc_dt is not None
        assert utc_dt.tzinfo == timezone.utc

    def test_non_utc_offset_normalized_to_utc(self):
        """ISO strings with offsets (+02:00) are converted to UTC."""
        dt_str = "2026-01-15T14:00:00+02:00"
        normalized = ensure_utc_datetime(dt_str)
        assert normalized == _make_utc_dt(2026, 1, 15, 12, 0)

    def test_matching_across_timezone_representations(self):
        """Actual with 'Z' and forecast with '+00:00' match cleanly."""
        actuals = [{"start_time": "2026-01-15T12:00:00Z", "generation": 4000.0}]
        forecasts = [
            {
                "start_time": "2026-01-15T12:00:00+00:00",
                "publish_time": "2026-01-14T08:30:00Z",
                "generation": 4100.0,
            }
        ]

        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 1
        assert matched[0]["startTime"] == _make_utc_dt(2026, 1, 15, 12, 0)


# ===========================================================================
# 5. Duplicate records
# ===========================================================================

class TestDuplicateHandling:

    def test_duplicate_actuals_deduplicated(self):
        """Duplicate actual records for the same interval are collapsed."""
        slot = _make_utc_dt(2026, 1, 15, 12, 0)
        actuals = [
            {"start_time": slot, "generation": 4000.0},
            {"start_time": slot, "generation": 4050.0},  # duplicate
        ]
        forecasts = [
            {
                "start_time": slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 4000.0,
            }
        ]

        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["total_actual_intervals"] == 1
        assert counts["matched_interval_count"] == 1
        assert len(matched) == 1

    def test_duplicate_forecasts_deduplicated(self):
        """Duplicate forecast records with identical (startTime, publishTime) are collapsed."""
        slot = _make_utc_dt(2026, 1, 15, 12, 0)
        actuals = [{"start_time": slot, "generation": 4000.0}]
        forecasts = [
            {
                "start_time": slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 4100.0,
            },
            {
                "start_time": slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 4100.0,
            },
        ]

        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 1
        assert len(matched) == 1


# ===========================================================================
# 6. Missing actual values
# ===========================================================================

class TestMissingActuals:

    def test_null_generation_actual_excluded(self):
        """Actual record with null generation is excluded from matching."""
        slot = _make_utc_dt(2026, 1, 15, 12, 0)
        actuals = [{"start_time": slot, "generation": None}]
        forecasts = [
            {
                "start_time": slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 4000.0,
            }
        ]

        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 0
        assert counts["total_actual_intervals"] == 0
        assert len(matched) == 0

    def test_negative_generation_actual_excluded(self):
        """Actual record with negative generation is treated as invalid and excluded."""
        slot = _make_utc_dt(2026, 1, 15, 12, 0)
        actuals = [{"start_time": slot, "generation": -50.0}]
        forecasts = [
            {
                "start_time": slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 8, 30),
                "generation": 4000.0,
            }
        ]

        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 0


# ===========================================================================
# 7. Missing eligible forecasts
# ===========================================================================

class TestMissingEligibleForecasts:

    def test_actual_without_eligible_forecast_is_unmatched(self):
        """Actual interval with all forecasts post-cutoff is recorded as unmatched actual."""
        slot = _make_utc_dt(2026, 1, 15, 12, 0)
        actuals = [{"start_time": slot, "generation": 4000.0}]
        # All forecasts published after 10:00 cutoff on D-1
        forecasts = [
            {
                "start_time": slot,
                "publish_time": _make_utc_dt(2026, 1, 14, 16, 30),
                "generation": 4200.0,
            }
        ]

        matched, counts = match_actuals_and_forecasts(actuals, forecasts)
        assert counts["matched_interval_count"] == 0
        assert counts["unmatched_actual_count"] == 1
        assert len(matched) == 0


# ===========================================================================
# 8. MAE calculation
# ===========================================================================

class TestMAECalculation:

    def test_mae_accurate(self):
        """
        Errors: [20, -20, 50]
        Absolute errors: [20, 20, 50]
        MAE = (20 + 20 + 50) / 3 = 30.0 MW
        """
        interval_errors = [
            {"forecast_error": 20.0, "absolute_error": 20.0, "squared_error": 400.0, "absolute_percentage_error": 20.0},
            {"forecast_error": -20.0, "absolute_error": 20.0, "squared_error": 400.0, "absolute_percentage_error": 10.0},
            {"forecast_error": 50.0, "absolute_error": 50.0, "squared_error": 2500.0, "absolute_percentage_error": 16.67},
        ]

        metrics = calculate_accuracy_metrics(interval_errors)
        assert metrics["mae"] == 30.0


# ===========================================================================
# 9. RMSE calculation
# ===========================================================================

class TestRMSECalculation:

    def test_rmse_accurate(self):
        """
        Squared errors: [400, 400, 2500] -> sum = 3300, mean = 1100
        RMSE = sqrt(1100) = 33.1662479... -> rounded to 33.17 MW
        """
        interval_errors = [
            {"forecast_error": 20.0, "absolute_error": 20.0, "squared_error": 400.0, "absolute_percentage_error": 20.0},
            {"forecast_error": -20.0, "absolute_error": 20.0, "squared_error": 400.0, "absolute_percentage_error": 10.0},
            {"forecast_error": 50.0, "absolute_error": 50.0, "squared_error": 2500.0, "absolute_percentage_error": 16.67},
        ]

        metrics = calculate_accuracy_metrics(interval_errors)
        expected_rmse = round(math.sqrt(3300.0 / 3.0), 2)
        assert metrics["rmse"] == expected_rmse
        assert metrics["rmse"] == 33.17


# ===========================================================================
# 10. Bias calculation
# ===========================================================================

class TestBiasCalculation:

    def test_bias_accurate(self):
        """
        Errors: [20, -20, 50] -> sum = 50, mean = 50 / 3 = 16.666... -> rounded to 16.67 MW
        """
        interval_errors = [
            {"forecast_error": 20.0, "absolute_error": 20.0, "squared_error": 400.0, "absolute_percentage_error": 20.0},
            {"forecast_error": -20.0, "absolute_error": 20.0, "squared_error": 400.0, "absolute_percentage_error": 10.0},
            {"forecast_error": 50.0, "absolute_error": 50.0, "squared_error": 2500.0, "absolute_percentage_error": 16.67},
        ]

        metrics = calculate_accuracy_metrics(interval_errors)
        assert metrics["bias"] == 16.67

    def test_negative_bias_under_forecast(self):
        """Under-forecasting produces negative bias."""
        interval_errors = [
            {"forecast_error": -30.0, "absolute_error": 30.0, "squared_error": 900.0, "absolute_percentage_error": 15.0},
            {"forecast_error": -10.0, "absolute_error": 10.0, "squared_error": 100.0, "absolute_percentage_error": 5.0},
        ]
        metrics = calculate_accuracy_metrics(interval_errors)
        assert metrics["bias"] == -20.0


# ===========================================================================
# 11. MAPE calculation
# ===========================================================================

class TestMAPECalculation:

    def test_mape_accurate(self):
        """
        Actuals: [100.0, 200.0]
        Forecasts: [110.0, 180.0]
        APE: [10.0%, 10.0%]
        MAPE: 10.0%
        """
        e1 = calculate_interval_errors(actual=100.0, forecast=110.0)
        e2 = calculate_interval_errors(actual=200.0, forecast=180.0)

        metrics = calculate_accuracy_metrics([e1, e2])
        assert metrics["mape"] == 10.0
        assert metrics["mape_excluded_count"] == 0


# ===========================================================================
# 12. Zero and near-zero actual values
# ===========================================================================

class TestZeroActualHandling:

    def test_zero_actual_sets_percentage_error_none(self):
        """When actual == 0, absolutePercentageError is None and not a division-by-zero crash."""
        errors = calculate_interval_errors(actual=0.0, forecast=100.0)
        assert errors["absolute_percentage_error"] is None
        assert errors["forecast_error"] == 100.0
        assert errors["absolute_error"] == 100.0

    def test_near_zero_actual_below_threshold_excluded(self):
        """Actual below ZERO_ACTUAL_THRESHOLD (0.001 MW) sets APE to None."""
        errors = calculate_interval_errors(actual=0.0005, forecast=50.0)
        assert errors["absolute_percentage_error"] is None

    def test_zero_actual_excluded_from_mape_and_counted(self):
        """Zero actual is excluded from MAPE; mape_excluded_count is incremented."""
        e_valid = calculate_interval_errors(actual=100.0, forecast=110.0)  # APE = 10%
        e_zero = calculate_interval_errors(actual=0.0, forecast=50.0)      # APE = None

        metrics = calculate_accuracy_metrics([e_valid, e_zero])
        assert metrics["mape"] == 10.0
        assert metrics["mape_excluded_count"] == 1

    def test_all_zero_actuals_returns_mape_none(self):
        """If all intervals have zero actual generation, MAPE is None without error."""
        e_zero1 = calculate_interval_errors(actual=0.0, forecast=50.0)
        e_zero2 = calculate_interval_errors(actual=0.0, forecast=60.0)

        metrics = calculate_accuracy_metrics([e_zero1, e_zero2])
        assert metrics["mape"] is None
        assert metrics["mape_excluded_count"] == 2


# ===========================================================================
# 13. Empty datasets
# ===========================================================================

class TestEmptyDatasets:

    def test_empty_records_return_none_metrics(self):
        """When no matched intervals exist, metrics are safely None."""
        metrics = calculate_accuracy_metrics([])
        assert metrics["mae"] is None
        assert metrics["rmse"] is None
        assert metrics["bias"] is None
        assert metrics["mape"] is None
        assert metrics["mape_excluded_count"] == 0

    def test_pipeline_with_empty_inputs(self):
        """End-to-end pipeline handles empty lists without crashing."""
        analysis = run_forecast_accuracy_analysis(
            date_from="2026-01-01",
            date_to="2026-01-02",
            actuals=[],
            forecasts=[],
        )
        assert analysis["matched_interval_count"] == 0
        assert analysis["total_actual_intervals"] == 0
        assert analysis["total_forecast_intervals"] == 0
        assert analysis["mae"] is None
        assert analysis["intervals"] == []


# ===========================================================================
# 14. API response structure (/api/v1/wind/analysis)
# ===========================================================================

class TestAnalysisEndpoint:

    @patch("main.run_forecast_accuracy_analysis")
    def test_analysis_endpoint_200_success(self, mock_run):
        """GET /api/v1/wind/analysis returns 200 with complete envelope structure."""
        slot = _make_utc_dt(2026, 1, 15, 12, 0)
        pub = _make_utc_dt(2026, 1, 14, 8, 30)

        mock_run.return_value = {
            "date_from": "2026-01-15",
            "date_to": "2026-01-15",
            "day_ahead_cutoff_hour_utc": 10,
            "cutoff_assumption": CUTOFF_ASSUMPTION_NOTE,
            "total_actual_intervals": 1,
            "total_forecast_intervals": 1,
            "matched_interval_count": 1,
            "unmatched_actual_count": 0,
            "unmatched_forecast_count": 0,
            "unmatched_interval_count": 0,
            "mape_excluded_count": 0,
            "mae": 100.0,
            "rmse": 100.0,
            "bias": -100.0,
            "mape": 2.5,
            "intervals": [
                {
                    "startTime": slot,
                    "actualGeneration": 4000.0,
                    "forecastGeneration": 3900.0,
                    "forecastPublishTime": pub,
                    "forecastError": -100.0,
                    "absoluteError": 100.0,
                    "squaredError": 10000.0,
                    "absolutePercentageError": 2.5,
                }
            ],
        }

        response = client.get("/api/v1/wind/analysis?date_from=2026-01-15&date_to=2026-01-15")
        assert response.status_code == 200

        data = response.json()
        assert data["date_from"] == "2026-01-15"
        assert data["date_to"] == "2026-01-15"
        assert data["day_ahead_cutoff_hour_utc"] == 10
        assert "cutoff_assumption" in data
        assert data["total_actual_intervals"] == 1
        assert data["matched_interval_count"] == 1
        assert data["mae"] == 100.0
        assert data["rmse"] == 100.0
        assert data["bias"] == -100.0
        assert data["mape"] == 2.5
        assert len(data["intervals"]) == 1

        interval = data["intervals"][0]
        assert "startTime" in interval
        assert interval["actualGeneration"] == 4000.0
        assert interval["forecastGeneration"] == 3900.0
        assert interval["forecastPublishTime"] == "2026-01-14T08:30:00Z"
        assert interval["forecastError"] == -100.0
        assert interval["absoluteError"] == 100.0
        assert interval["squaredError"] == 10000.0
        assert interval["absolutePercentageError"] == 2.5

    def test_analysis_endpoint_invalid_date(self):
        """Invalid date format returns 422."""
        response = client.get("/api/v1/wind/analysis?date_from=invalid-date")
        assert response.status_code == 422

    def test_analysis_endpoint_reversed_date_range(self):
        """date_from > date_to returns 422."""
        response = client.get("/api/v1/wind/analysis?date_from=2026-01-31&date_to=2026-01-01")
        assert response.status_code == 422

    @patch("main.run_forecast_accuracy_analysis")
    def test_analysis_endpoint_timeout_504(self, mock_run):
        """Upstream timeout propagates as 504."""
        mock_run.side_effect = requests.Timeout("Connection timed out")
        response = client.get("/api/v1/wind/analysis")
        assert response.status_code == 504

    @patch("main.run_forecast_accuracy_analysis")
    def test_analysis_endpoint_http_error_502(self, mock_run):
        """Upstream HTTP error propagates as 502."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_run.side_effect = requests.HTTPError(response=mock_resp)
        response = client.get("/api/v1/wind/analysis")
        assert response.status_code == 502

