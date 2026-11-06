"""
Tests for the Elexon BMRS integration service and FastAPI endpoints.

All tests use mocked HTTP responses — no live API calls are made.

Run with:
    cd backend
    pytest tests/test_elexon.py -v
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import requests

# ---------------------------------------------------------------------------
# Fixtures — shared sample payloads
# ---------------------------------------------------------------------------

FUELHH_WIND_RECORD = {
    "startTime": "2026-01-15T12:00:00Z",
    "settlementDate": "2026-01-15",
    "settlementPeriod": 25,
    "fuelType": "WIND",
    "generation": 4823.5,
}

FUELHH_GAS_RECORD = {
    "startTime": "2026-01-15T12:00:00Z",
    "settlementDate": "2026-01-15",
    "settlementPeriod": 25,
    "fuelType": "GAS",
    "generation": 12000.0,
}

FUELHH_NUCLEAR_RECORD = {
    "startTime": "2026-01-15T12:00:00Z",
    "settlementDate": "2026-01-15",
    "settlementPeriod": 25,
    "fuelType": "NUCLEAR",
    "generation": 7500.0,
}

WINDFOR_RECORD_1 = {
    "startTime": "2026-01-15T12:00:00Z",
    "publishTime": "2026-01-14T08:30:00Z",   # day-ahead, before 10:00 cutoff
    "generation": 4700.0,
}

WINDFOR_RECORD_2 = {
    "startTime": "2026-01-15T12:00:00Z",
    "publishTime": "2026-01-14T23:30:00Z",   # day-of, after 10:00 cutoff
    "generation": 4850.0,
}

WINDFOR_RECORD_3 = {
    "startTime": "2026-01-16T00:00:00Z",
    "publishTime": "2026-01-15T08:30:00Z",   # day-ahead for 16th
    "generation": 5100.0,
}


def _mock_response(json_data: list, status_code: int = 200) -> MagicMock:
    """Build a mock requests.Response returning the given JSON list."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    if status_code >= 400:
        mock.raise_for_status.side_effect = requests.HTTPError(
            response=mock
        )
    else:
        mock.raise_for_status.return_value = None
    return mock


# ===========================================================================
# Tests: fetch_actual_generation
# ===========================================================================

class TestFetchActualGeneration:

    def test_returns_wind_records_only(self):
        """FUELHH records with fuelType != WIND must be filtered out."""
        from app.services.elexon import fetch_actual_generation

        payload = [FUELHH_WIND_RECORD, FUELHH_GAS_RECORD, FUELHH_NUCLEAR_RECORD]
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response(payload)
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert len(result) == 1
        assert result[0]["generation"] == 4823.5

    def test_normalises_start_time_to_utc(self):
        """startTime must be parsed into a UTC-aware datetime."""
        from app.services.elexon import fetch_actual_generation

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([FUELHH_WIND_RECORD])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        dt = result[0]["start_time"]
        assert isinstance(dt, datetime)
        assert dt.tzinfo is not None
        assert dt == datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_deduplicates_by_start_time_and_period(self):
        """Duplicate records (same startTime + settlementPeriod) are collapsed."""
        from app.services.elexon import fetch_actual_generation

        dup = {**FUELHH_WIND_RECORD, "generation": 9999.0}
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([FUELHH_WIND_RECORD, dup])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert len(result) == 1
        # Last-seen wins
        assert result[0]["generation"] == 9999.0

    def test_skips_record_with_null_generation(self):
        """Records with null generation must be skipped, not substituted."""
        from app.services.elexon import fetch_actual_generation

        bad_record = {**FUELHH_WIND_RECORD, "generation": None}
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([bad_record])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert result == []

    def test_skips_record_with_negative_generation(self):
        """Negative generation values are invalid and must be excluded."""
        from app.services.elexon import fetch_actual_generation

        bad_record = {**FUELHH_WIND_RECORD, "generation": -100.0}
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([bad_record])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert result == []

    def test_skips_record_with_non_numeric_generation(self):
        """Non-numeric generation strings must be excluded."""
        from app.services.elexon import fetch_actual_generation

        bad_record = {**FUELHH_WIND_RECORD, "generation": "N/A"}
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([bad_record])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert result == []

    def test_skips_record_with_missing_start_time(self):
        """Records missing startTime must be skipped."""
        from app.services.elexon import fetch_actual_generation

        bad_record = {**FUELHH_WIND_RECORD}
        del bad_record["startTime"]
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([bad_record])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert result == []

    def test_skips_record_with_malformed_start_time(self):
        """Records with unparseable timestamps must be skipped, not crash."""
        from app.services.elexon import fetch_actual_generation

        bad_record = {**FUELHH_WIND_RECORD, "startTime": "not-a-date"}
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([bad_record])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert result == []

    def test_empty_api_response(self):
        """An empty API response must return an empty list without error."""
        from app.services.elexon import fetch_actual_generation

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert result == []

    def test_raises_on_http_error(self):
        """HTTP 500 from Elexon must propagate as requests.HTTPError."""
        from app.services.elexon import fetch_actual_generation

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([], status_code=500)
            with pytest.raises(requests.HTTPError):
                fetch_actual_generation("2026-01-15", "2026-01-15")

    def test_raises_on_timeout(self):
        """A request timeout must propagate as requests.Timeout."""
        from app.services.elexon import fetch_actual_generation

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("timed out")
            with pytest.raises(requests.Timeout):
                fetch_actual_generation("2026-01-15", "2026-01-15")

    def test_uses_correct_fuelhh_url(self):
        """The FUELHH stream URL must match the official Elexon endpoint."""
        from app.services.elexon import fetch_actual_generation

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([])
            fetch_actual_generation("2026-01-15", "2026-01-15")

        called_url = mock_get.call_args[0][0]
        assert "FUELHH/stream" in called_url
        assert "data.elexon.co.uk" in called_url

    def test_uses_settlement_date_params(self):
        """FUELHH requests must use settlementDateFrom/To, not 'from'/'to'."""
        from app.services.elexon import fetch_actual_generation

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([])
            fetch_actual_generation("2026-01-01", "2026-01-07")

        called_params = mock_get.call_args[1]["params"]
        assert "settlementDateFrom" in called_params
        assert "settlementDateTo" in called_params
        # Old incorrect param names must not appear
        assert "from" not in called_params
        assert "to" not in called_params

    def test_chunks_long_date_ranges(self):
        """Date ranges exceeding CHUNK_DAYS must result in multiple API calls."""
        from app.services import elexon as elexon_module
        from app.services.elexon import fetch_actual_generation, CHUNK_DAYS

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([])
            fetch_actual_generation("2026-01-01", "2026-01-31")

        # 31 days with CHUNK_DAYS=7 → ceil(31/7) = 5 chunks
        expected_calls = -(-31 // CHUNK_DAYS)   # ceiling division
        assert mock_get.call_count == expected_calls

    def test_settlement_date_preserved(self):
        """settlement_date must be passed through from the raw API record."""
        from app.services.elexon import fetch_actual_generation

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([FUELHH_WIND_RECORD])
            result = fetch_actual_generation("2026-01-15", "2026-01-15")

        assert result[0]["settlement_date"] == "2026-01-15"
        assert result[0]["settlement_period"] == 25


# ===========================================================================
# Tests: fetch_wind_forecasts
# ===========================================================================

class TestFetchWindForecasts:

    def test_returns_forecast_records(self):
        """WINDFOR response must be returned as normalised dicts."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response(
                [WINDFOR_RECORD_1, WINDFOR_RECORD_2, WINDFOR_RECORD_3]
            )
            result = fetch_wind_forecasts()

        assert len(result) == 3

    def test_publish_time_preserved(self):
        """publishTime must appear on every forecast record as a UTC datetime."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([WINDFOR_RECORD_1])
            result = fetch_wind_forecasts()

        pt = result[0]["publish_time"]
        assert isinstance(pt, datetime)
        assert pt.tzinfo is not None
        assert pt == datetime(2026, 1, 14, 8, 30, 0, tzinfo=timezone.utc)

    def test_start_time_normalised(self):
        """startTime must be parsed into a UTC-aware datetime."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([WINDFOR_RECORD_1])
            result = fetch_wind_forecasts()

        st = result[0]["start_time"]
        assert isinstance(st, datetime)
        assert st.tzinfo is not None

    def test_skips_record_missing_publish_time(self):
        """Records without publishTime must be excluded."""
        from app.services.elexon import fetch_wind_forecasts

        bad = {**WINDFOR_RECORD_1}
        del bad["publishTime"]
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([bad])
            result = fetch_wind_forecasts()

        assert result == []

    def test_skips_record_missing_start_time(self):
        """Records without startTime must be excluded."""
        from app.services.elexon import fetch_wind_forecasts

        bad = {**WINDFOR_RECORD_1}
        del bad["startTime"]
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([bad])
            result = fetch_wind_forecasts()

        assert result == []

    def test_skips_record_missing_generation(self):
        """Records with null generation must be excluded."""
        from app.services.elexon import fetch_wind_forecasts

        bad = {**WINDFOR_RECORD_1, "generation": None}
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([bad])
            result = fetch_wind_forecasts()

        assert result == []

    def test_deduplicates_by_start_and_publish_time(self):
        """Identical (startTime, publishTime) pairs must be deduplicated."""
        from app.services.elexon import fetch_wind_forecasts

        dup = {**WINDFOR_RECORD_1, "generation": 9999.0}
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([WINDFOR_RECORD_1, dup])
            result = fetch_wind_forecasts()

        assert len(result) == 1
        assert result[0]["generation"] == 9999.0

    def test_empty_response(self):
        """Empty WINDFOR response must return empty list."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([])
            result = fetch_wind_forecasts()

        assert result == []

    def test_raises_on_timeout(self):
        """Timeout must propagate as requests.Timeout."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.side_effect = requests.Timeout("timed out")
            with pytest.raises(requests.Timeout):
                fetch_wind_forecasts()

    def test_raises_on_http_error(self):
        """HTTP errors must propagate as requests.HTTPError."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([], status_code=503)
            with pytest.raises(requests.HTTPError):
                fetch_wind_forecasts()

    def test_uses_correct_windfor_url(self):
        """The WINDFOR stream URL must match the official Elexon endpoint."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([])
            fetch_wind_forecasts()

        called_url = mock_get.call_args[0][0]
        assert "WINDFOR/stream" in called_url
        assert "data.elexon.co.uk" in called_url

    def test_uses_publish_datetime_params(self):
        """WINDFOR requests must use publishDateTimeFrom/To parameters."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([])
            fetch_wind_forecasts()

        called_params = mock_get.call_args[1]["params"]
        assert "publishDateTimeFrom" in called_params
        assert "publishDateTimeTo" in called_params


# ===========================================================================
# Tests: select_day_ahead_forecasts
# ===========================================================================

class TestSelectDayAheadForecasts:

    def _make_records(self) -> list[dict]:
        """Return normalised forecast dicts covering the fixture data."""
        from app.services.elexon import fetch_wind_forecasts

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response(
                [WINDFOR_RECORD_1, WINDFOR_RECORD_2, WINDFOR_RECORD_3]
            )
            return fetch_wind_forecasts()

    def test_excludes_forecasts_after_cutoff(self):
        """WINDFOR_RECORD_2 is published at 23:30 D-1 — after the 10:00 cutoff."""
        from app.services.elexon import select_day_ahead_forecasts

        records = self._make_records()
        selected = select_day_ahead_forecasts(records, cutoff_hour_utc=10)

        # For delivery 2026-01-15, only WINDFOR_RECORD_1 (08:30 D-1) qualifies
        jan_15_records = [
            r for r in selected
            if r["start_time"].date().isoformat() == "2026-01-15"
        ]
        # Only the 08:30 publication should survive
        assert all(
            r["publish_time"].hour < 10 for r in jan_15_records
        ), "No record published after 10:00 D-1 should appear for Jan 15"

    def test_selects_latest_eligible_publication(self):
        """When two eligible runs exist, the later one should be chosen."""
        from app.services.elexon import select_day_ahead_forecasts, fetch_wind_forecasts

        # Two day-ahead runs for the same slot: 03:30 and 08:30 on D-1
        early = {**WINDFOR_RECORD_1, "publishTime": "2026-01-14T03:30:00Z", "generation": 4600.0}
        late_ = {**WINDFOR_RECORD_1, "publishTime": "2026-01-14T08:30:00Z", "generation": 4700.0}

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([early, late_])
            records = fetch_wind_forecasts()

        selected = select_day_ahead_forecasts(records, cutoff_hour_utc=10)
        assert len(selected) == 1
        assert selected[0]["generation"] == 4700.0  # the 08:30 run

    def test_no_eligible_forecast_returns_empty(self):
        """If all forecasts post-date the cutoff, no records are returned."""
        from app.services.elexon import select_day_ahead_forecasts, fetch_wind_forecasts

        # publishTime is after the 10:00 cutoff on D-1
        post_cutoff = {**WINDFOR_RECORD_1, "publishTime": "2026-01-14T23:30:00Z"}

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([post_cutoff])
            records = fetch_wind_forecasts()

        selected = select_day_ahead_forecasts(records, cutoff_hour_utc=10)
        assert selected == []

    def test_cutoff_hour_is_configurable(self):
        """Changing the cutoff hour must change which records are included."""
        from app.services.elexon import select_day_ahead_forecasts, fetch_wind_forecasts

        # publishTime = 2026-01-14T23:30 — after 10:00 but before 23:59 cutoff
        post_10 = {**WINDFOR_RECORD_1, "publishTime": "2026-01-14T23:30:00Z"}

        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([post_10])
            records = fetch_wind_forecasts()

        # With cutoff at 10:00, excluded
        assert select_day_ahead_forecasts(records, cutoff_hour_utc=10) == []
        # With cutoff bumped to 24 (next day midnight) it should be included
        # We simulate by using 24 → not valid, so use a very late hour like 23
        # 23:30 is NOT < 23:00 cutoff; adjust: publishTime 22:30 vs cutoff 23
        post_22 = {**WINDFOR_RECORD_1, "publishTime": "2026-01-14T22:30:00Z"}
        with patch("app.services.elexon.requests.get") as mock_get:
            mock_get.return_value = _mock_response([post_22])
            records2 = fetch_wind_forecasts()

        result = select_day_ahead_forecasts(records2, cutoff_hour_utc=23)
        assert len(result) == 1


# ===========================================================================
# Tests: FastAPI endpoints (using TestClient)
# ===========================================================================

class TestAPIEndpoints:

    @pytest.fixture(autouse=True)
    def client(self):
        from fastapi.testclient import TestClient
        import main as app_module
        self._client = TestClient(app_module.app, raise_server_exceptions=False)

    def test_health_returns_ok(self):
        response = self._client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"

    def test_actuals_success(self):
        """Successful actuals call returns correct envelope structure."""
        with patch("main.fetch_actual_generation") as mock_fetch:
            mock_fetch.return_value = [
                {
                    "start_time": datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
                    "generation": 4823.5,
                    "settlement_date": "2026-01-15",
                    "settlement_period": 25,
                }
            ]
            response = self._client.get("/api/v1/wind/actuals")

        assert response.status_code == 200
        body = response.json()
        assert body["dataset"] == "FUELHH"
        assert body["fuel_type"] == "WIND"
        assert body["record_count"] == 1
        assert len(body["records"]) == 1
        assert body["records"][0]["generation"] == 4823.5
        assert "2026-01-15T12:00:00Z" in body["records"][0]["start_time"]

    def test_actuals_timeout_returns_504(self):
        """Elexon timeout must result in HTTP 504."""
        with patch("main.fetch_actual_generation") as mock_fetch:
            mock_fetch.side_effect = requests.Timeout("timed out")
            response = self._client.get("/api/v1/wind/actuals")

        assert response.status_code == 504

    def test_actuals_http_error_returns_502(self):
        """Elexon HTTP error must result in HTTP 502."""
        mock_resp = MagicMock()
        mock_resp.status_code = 503
        with patch("main.fetch_actual_generation") as mock_fetch:
            mock_fetch.side_effect = requests.HTTPError(response=mock_resp)
            response = self._client.get("/api/v1/wind/actuals")

        assert response.status_code == 502

    def test_actuals_invalid_date_returns_422(self):
        """Invalid date parameters must be rejected with HTTP 422."""
        response = self._client.get(
            "/api/v1/wind/actuals?date_from=not-a-date"
        )
        assert response.status_code == 422

    def test_actuals_inverted_range_returns_422(self):
        """date_from > date_to must be rejected."""
        response = self._client.get(
            "/api/v1/wind/actuals?date_from=2026-01-31&date_to=2026-01-01"
        )
        assert response.status_code == 422

    def test_forecasts_success(self):
        """Successful forecasts call returns correct envelope."""
        with patch("main.fetch_wind_forecasts") as mock_fetch:
            mock_fetch.return_value = [
                {
                    "start_time": datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc),
                    "publish_time": datetime(2026, 1, 14, 8, 30, tzinfo=timezone.utc),
                    "generation": 4700.0,
                }
            ]
            response = self._client.get("/api/v1/wind/forecasts")

        assert response.status_code == 200
        body = response.json()
        assert body["dataset"] == "WINDFOR"
        assert body["record_count"] == 1
        assert "publish_time" in body["records"][0]
        assert "2026-01-14T08:30:00Z" in body["records"][0]["publish_time"]

    def test_forecasts_day_ahead_filter_applied(self):
        """When day_ahead_only=true, select_day_ahead_forecasts is called."""
        with patch("main.fetch_wind_forecasts") as mock_fetch, \
             patch("main.select_day_ahead_forecasts") as mock_select:
            mock_fetch.return_value = []
            mock_select.return_value = []
            response = self._client.get(
                "/api/v1/wind/forecasts?day_ahead_only=true"
            )

        assert response.status_code == 200
        mock_select.assert_called_once()

    def test_forecasts_day_ahead_not_applied_by_default(self):
        """select_day_ahead_forecasts must NOT be called unless requested."""
        with patch("main.fetch_wind_forecasts") as mock_fetch, \
             patch("main.select_day_ahead_forecasts") as mock_select:
            mock_fetch.return_value = []
            response = self._client.get("/api/v1/wind/forecasts")

        assert response.status_code == 200
        mock_select.assert_not_called()

    def test_forecasts_cutoff_hour_in_response_when_day_ahead(self):
        """day_ahead_cutoff_hour_utc must appear in response when filtering."""
        with patch("main.fetch_wind_forecasts") as mock_fetch, \
             patch("main.select_day_ahead_forecasts") as mock_select:
            mock_fetch.return_value = []
            mock_select.return_value = []
            response = self._client.get(
                "/api/v1/wind/forecasts?day_ahead_only=true&cutoff_hour_utc=10"
            )

        body = response.json()
        assert body["day_ahead_cutoff_hour_utc"] == 10

    def test_forecasts_timeout_returns_504(self):
        """Elexon timeout on WINDFOR must result in 504."""
        with patch("main.fetch_wind_forecasts") as mock_fetch:
            mock_fetch.side_effect = requests.Timeout("timed out")
            response = self._client.get("/api/v1/wind/forecasts")

        assert response.status_code == 504

    def test_forecasts_http_error_returns_502(self):
        """Elexon HTTP error on WINDFOR must result in 502."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("main.fetch_wind_forecasts") as mock_fetch:
            mock_fetch.side_effect = requests.HTTPError(response=mock_resp)
            response = self._client.get("/api/v1/wind/forecasts")

        assert response.status_code == 502

    def test_forecasts_cutoff_assumption_in_response(self):
        """The assumption note about the cutoff must appear in every response."""
        with patch("main.fetch_wind_forecasts") as mock_fetch:
            mock_fetch.return_value = []
            response = self._client.get("/api/v1/wind/forecasts")

        body = response.json()
        assert "cutoff_assumption" in body
        assert len(body["cutoff_assumption"]) > 10
