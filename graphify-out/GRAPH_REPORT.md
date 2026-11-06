# Graph Report - WindForecast-Analytics  (2026-11-06)

## Corpus Check
- 27 files · ~19,089 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 385 nodes · 656 edges · 23 communities
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 44 edges (avg confidence: 0.86)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- fetch_actual_generation
- test_analysis.py
- patch
- TestAPIEndpoints
- React + Vite
- devDependencies
- App.jsx
- _make_utc_dt
- TestTimezoneHandling
- WindForecast Analytics — UK National Wind Generation Platform
- calculate_interval_errors
- TestAnalysisEndpoint
- .test_excludes_forecasts_published_after_cutoff
- match_actuals_and_forecasts
- schemas.py
- .test_duplicate_actuals_deduplicated
- .test_negative_generation_actual_excluded
- .test_selection_ignores_error_value

## God Nodes (most connected - your core abstractions)
1. `_mock_response()` - 31 edges
2. `fetch_actual_generation()` - 29 edges
3. `fetch_wind_forecasts()` - 29 edges
4. `match_actuals_and_forecasts()` - 23 edges
5. `_make_utc_dt()` - 22 edges
6. `TestFetchActualGeneration` - 16 edges
7. `TestAPIEndpoints` - 15 edges
8. `calculate_accuracy_metrics()` - 14 edges
9. `select_day_ahead_forecasts()` - 13 edges
10. `TestFetchWindForecasts` - 13 edges

## Surprising Connections (you probably didn't know these)
- `get_wind_actuals()` --uses--> `ActualRecord`  [INFERRED]
  backend/main.py → backend/schemas.py
- `get_wind_forecasts()` --uses--> `ForecastRecord`  [INFERRED]
  backend/main.py → backend/schemas.py
- `get_wind_analysis()` --uses--> `AnalysisIntervalRecord`  [INFERRED]
  backend/main.py → backend/schemas.py
- `run_forecast_accuracy_analysis()` --calls--> `fetch_actual_generation()`  [EXTRACTED]
  backend/app/services/analysis.py → backend/app/services/elexon.py
- `run_forecast_accuracy_analysis()` --calls--> `fetch_wind_forecasts()`  [EXTRACTED]
  backend/app/services/analysis.py → backend/app/services/elexon.py

## Import Cycles
- None detected.

## Communities (23 total, 0 thin omitted)

### Community 0 - "fetch_actual_generation"
Cohesion: 0.07
Nodes (52): _chunk_date_range(), fetch_actual_generation(), _fetch_fuelhh_chunk(), fetch_wind_forecasts(), _fetch_windfor_chunk(), _get(), _parse_generation(), _parse_utc_timestamp() (+44 more)

### Community 1 - "test_analysis.py"
Cohesion: 0.11
Nodes (15): calculate_accuracy_metrics(), Calculate overall aggregate forecast accuracy metrics across all matched…, Phase 2 Test Suite: Wind Forecast Selection and Accuracy Analysis. Covers all…, Actual interval with all forecasts post-cutoff is recorded as unmatched actual., Errors: [20, -20, 50] Absolute errors: [20, 20, 50] MAE = (20 + 20 + 50) / 3 =…, Squared errors: [400, 400, 2500] -> sum = 3300, mean = 1100 RMSE = sqrt(1100) =…, Errors: [20, -20, 50] -> sum = 50, mean = 50 / 3 = 16.666... -> rounded to…, Under-forecasting produces negative bias. (+7 more)

### Community 2 - "patch"
Cohesion: 0.06
Nodes (33): Upstream HTTP error propagates as 502., _mock_response(), Duplicate records (same startTime + settlementPeriod) are collapsed., Records with null generation must be skipped, not substituted., Negative generation values are invalid and must be excluded., Non-numeric generation strings must be excluded., Records missing startTime must be skipped., Records with unparseable timestamps must be skipped, not crash. (+25 more)

### Community 3 - "TestAPIEndpoints"
Cohesion: 0.07
Nodes (14): Successful actuals call returns correct envelope structure., Elexon timeout must result in HTTP 504., Elexon HTTP error must result in HTTP 502., Invalid date parameters must be rejected with HTTP 422., date_from > date_to must be rejected., Successful forecasts call returns correct envelope., When day_ahead_only=true, select_day_ahead_forecasts is called., select_day_ahead_forecasts must NOT be called unless requested. (+6 more)

### Community 4 - "React + Vite"
Cohesion: 0.50
Nodes (3): Expanding the ESLint configuration, React Compiler, React + Vite

### Community 5 - "devDependencies"
Cohesion: 0.06
Nodes (33): eslint, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, dependencies, react, react-dom, devDependencies (+25 more)

### Community 6 - "App.jsx"
Cohesion: 0.10
Nodes (17): App(), DashboardHeader(), DataTable(), formatDateTime(), DateFilter(), ErrorState(), ForecastErrorChart(), formatDateShort() (+9 more)

### Community 7 - "_make_utc_dt"
Cohesion: 0.14
Nodes (11): _make_utc_dt(), :00 actual interval maps to the corresponding :00 hourly forecast., :30 actual interval maps to the :00 hourly forecast of the same hour., Both :00 and :30 intervals in the same hour map to the same hourly forecast., Matched records must retain their exact original 30-minute timestamps., When an hourly forecast is missing, both constituent half-hours remain…, Forecast published after D-1 gate closure (10:00 UTC) is excluded., Verify counts across multiple hours and extra forecast horizons. (+3 more)

### Community 9 - "TestTimezoneHandling"
Cohesion: 0.25
Nodes (5): datetime, Naive datetime strings/objects are normalized to UTC without dropping., ISO strings with offsets (+02:00) are converted to UTC., Actual with 'Z' and forecast with '+00:00' match cleanly., TestTimezoneHandling

### Community 10 - "WindForecast Analytics — UK National Wind Generation Platform"
Cohesion: 0.06
Nodes (31): 1. Clone & Configure Environment, 1. Verify Backend Health Endpoint, 2. Build & Start the Application, 2. Verify Backend Analysis Endpoint, 3. Verify Container Status & Health, 3. Verify CORS Response Headers, 4. Verify Frontend Application in Browser, Accessing the Application (+23 more)

### Community 14 - "calculate_interval_errors"
Cohesion: 0.18
Nodes (9): calculate_interval_errors(), Calculate forecast errors for a single matched interval. Formulas: -…, Actuals: [100.0, 200.0] Forecasts: [110.0, 180.0] APE: [10.0%, 10.0%] MAPE:…, When actual == 0, absolutePercentageError is None and not a division-by-zero…, Actual below ZERO_ACTUAL_THRESHOLD (0.001 MW) sets APE to None., Zero actual is excluded from MAPE; mape_excluded_count is incremented., If all intervals have zero actual generation, MAPE is None without error., TestMAPECalculation (+1 more)

### Community 15 - "TestAnalysisEndpoint"
Cohesion: 0.29
Nodes (4): Invalid date format returns 422., date_from > date_to returns 422., Upstream timeout propagates as 504., TestAnalysisEndpoint

### Community 16 - ".test_excludes_forecasts_published_after_cutoff"
Cohesion: 0.40
Nodes (3): Forecasts published strictly after the cutoff timestamp must be excluded., A forecast published at or before the cutoff is eligible., TestCutoffExclusion

### Community 17 - "match_actuals_and_forecasts"
Cohesion: 0.23
Nodes (14): ensure_utc_datetime(), get_day_ahead_decision_cutoff(), match_actuals_and_forecasts(), Any, date, datetime, Wind Forecast Accuracy Analysis Service. Responsibilities: 1. Day-ahead…, Select the latest eligible forecast for a specific delivery interval. Rules: 1.… (+6 more)

### Community 18 - "schemas.py"
Cohesion: 0.12
Nodes (20): ActualRecord, ActualsResponse, AnalysisIntervalRecord, AnalysisResponse, _DatetimeAsUTCStr, ErrorResponse, ForecastRecord, HealthResponse (+12 more)

### Community 19 - ".test_duplicate_actuals_deduplicated"
Cohesion: 0.40
Nodes (3): Duplicate actual records for the same interval are collapsed., Duplicate forecast records with identical (startTime, publishTime) are…, TestDuplicateHandling

### Community 22 - ".test_negative_generation_actual_excluded"
Cohesion: 0.40
Nodes (3): Actual record with null generation is excluded from matching., Actual record with negative generation is treated as invalid and excluded., TestMissingActuals

### Community 24 - ".test_selection_ignores_error_value"
Cohesion: 0.40
Nodes (3): Among multiple runs published prior to cutoff, select the one with the latest…, Selection must NEVER pick a forecast because it is closer to actual., TestForecastSelection

## Knowledge Gaps
- **46 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+41 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 182 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `fetch_actual_generation()` connect `fetch_actual_generation` to `match_actuals_and_forecasts`, `patch`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `fetch_wind_forecasts()` connect `fetch_actual_generation` to `match_actuals_and_forecasts`, `patch`?**
  _High betweenness centrality (0.107) - this node is a cross-community bridge._
- **Why does `run_forecast_accuracy_analysis()` connect `match_actuals_and_forecasts` to `fetch_actual_generation`, `test_analysis.py`?**
  _High betweenness centrality (0.078) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `patch` (e.g. with `.test_actuals_http_error_returns_502()` and `.test_actuals_success()`) actually correct?**
  _`patch` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _46 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `fetch_actual_generation` be split into smaller, more focused modules?**
  _Cohesion score 0.06502732240437159 - nodes in this community are weakly interconnected._
- **Should `test_analysis.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1067193675889328 - nodes in this community are weakly interconnected._