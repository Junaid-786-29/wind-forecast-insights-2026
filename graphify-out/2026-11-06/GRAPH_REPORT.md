# Graph Report - WindForecast-Analytics  (2026-11-06)

## Corpus Check
- 27 files · ~17,884 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 372 nodes · 630 edges · 23 communities
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
- WindForecast Analytics — UK National Wind Generation Platform
- calculate_interval_errors
- TestAnalysisEndpoint
- .test_excludes_forecasts_published_after_cutoff
- match_actuals_and_forecasts
- main.py
- .test_duplicate_actuals_deduplicated
- .test_negative_generation_actual_excluded
- TestEmptyDatasets
- .test_selection_ignores_error_value

## God Nodes (most connected - your core abstractions)
1. `_mock_response()` - 31 edges
2. `fetch_actual_generation()` - 29 edges
3. `fetch_wind_forecasts()` - 29 edges
4. `match_actuals_and_forecasts()` - 17 edges
5. `_make_utc_dt()` - 16 edges
6. `TestFetchActualGeneration` - 16 edges
7. `TestAPIEndpoints` - 15 edges
8. `calculate_accuracy_metrics()` - 13 edges
9. `select_day_ahead_forecasts()` - 13 edges
10. `TestFetchWindForecasts` - 13 edges

## Surprising Connections (you probably didn't know these)
- `run_forecast_accuracy_analysis()` --calls--> `fetch_actual_generation()`  [EXTRACTED]
  backend/app/services/analysis.py → backend/app/services/elexon.py
- `run_forecast_accuracy_analysis()` --calls--> `fetch_wind_forecasts()`  [EXTRACTED]
  backend/app/services/analysis.py → backend/app/services/elexon.py
- `get_wind_analysis()` --calls--> `run_forecast_accuracy_analysis()`  [EXTRACTED]
  backend/main.py → backend/app/services/analysis.py
- `get_wind_actuals()` --calls--> `fetch_actual_generation()`  [EXTRACTED]
  backend/main.py → backend/app/services/elexon.py
- `get_wind_forecasts()` --calls--> `fetch_wind_forecasts()`  [EXTRACTED]
  backend/main.py → backend/app/services/elexon.py

## Import Cycles
- None detected.

## Communities (23 total, 0 thin omitted)

### Community 0 - "fetch_actual_generation"
Cohesion: 0.10
Nodes (31): _chunk_date_range(), fetch_actual_generation(), _fetch_fuelhh_chunk(), fetch_wind_forecasts(), _fetch_windfor_chunk(), _parse_generation(), _parse_utc_timestamp(), Any (+23 more)

### Community 1 - "test_analysis.py"
Cohesion: 0.12
Nodes (14): calculate_accuracy_metrics(), Calculate overall aggregate forecast accuracy metrics across all matched…, Phase 2 Test Suite: Wind Forecast Selection and Accuracy Analysis. Covers all…, Actual interval with all forecasts post-cutoff is recorded as unmatched actual., Errors: [20, -20, 50] Absolute errors: [20, 20, 50] MAE = (20 + 20 + 50) / 3 =…, Squared errors: [400, 400, 2500] -> sum = 3300, mean = 1100 RMSE = sqrt(1100) =…, Errors: [20, -20, 50] -> sum = 50, mean = 50 / 3 = 16.666... -> rounded to…, Under-forecasting produces negative bias. (+6 more)

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

### Community 9 - "_make_utc_dt"
Cohesion: 0.15
Nodes (10): _make_utc_dt(), datetime, Actual and forecast records must match by exact startTime., Records with non-matching intervals must remain unmatched., Naive datetime strings/objects are normalized to UTC without dropping., ISO strings with offsets (+02:00) are converted to UTC., Actual with 'Z' and forecast with '+00:00' match cleanly., GET /api/v1/wind/analysis returns 200 with complete envelope structure. (+2 more)

### Community 10 - "WindForecast Analytics — UK National Wind Generation Platform"
Cohesion: 0.06
Nodes (30): 1. Clone & Configure Environment, 1. Verify Backend Health Endpoint, 2. Build & Start the Application, 2. Verify Backend Analysis Endpoint, 3. Verify Container Status & Health, 3. Verify CORS Response Headers, 4. Verify Frontend Application in Browser, Accessing the Application (+22 more)

### Community 14 - "calculate_interval_errors"
Cohesion: 0.24
Nodes (7): calculate_interval_errors(), Calculate forecast errors for a single matched interval. Formulas: -…, When actual == 0, absolutePercentageError is None and not a division-by-zero…, Actual below ZERO_ACTUAL_THRESHOLD (0.001 MW) sets APE to None., Zero actual is excluded from MAPE; mape_excluded_count is incremented., If all intervals have zero actual generation, MAPE is None without error., TestZeroActualHandling

### Community 15 - "TestAnalysisEndpoint"
Cohesion: 0.29
Nodes (4): Invalid date format returns 422., date_from > date_to returns 422., Upstream timeout propagates as 504., TestAnalysisEndpoint

### Community 16 - ".test_excludes_forecasts_published_after_cutoff"
Cohesion: 0.40
Nodes (3): Forecasts published strictly after the cutoff timestamp must be excluded., A forecast published at or before the cutoff is eligible., TestCutoffExclusion

### Community 17 - "match_actuals_and_forecasts"
Cohesion: 0.23
Nodes (14): ensure_utc_datetime(), get_day_ahead_decision_cutoff(), match_actuals_and_forecasts(), Any, date, datetime, Wind Forecast Accuracy Analysis Service. Responsibilities: 1. Day-ahead…, Select the latest eligible forecast for a specific delivery interval. Rules: 1.… (+6 more)

### Community 18 - "main.py"
Cohesion: 0.08
Nodes (41): _get(), Perform a GET request and return the parsed JSON list. The Elexon BMRS stream…, get_wind_actuals(), get_wind_analysis(), get_wind_forecasts(), _handle_elexon_error(), health(), Wind Forecast Analytics — FastAPI application entry point. API v1 endpoints… (+33 more)

### Community 19 - ".test_duplicate_actuals_deduplicated"
Cohesion: 0.40
Nodes (3): Duplicate actual records for the same interval are collapsed., Duplicate forecast records with identical (startTime, publishTime) are…, TestDuplicateHandling

### Community 22 - ".test_negative_generation_actual_excluded"
Cohesion: 0.40
Nodes (3): Actual record with null generation is excluded from matching., Actual record with negative generation is treated as invalid and excluded., TestMissingActuals

### Community 23 - "TestEmptyDatasets"
Cohesion: 0.40
Nodes (3): When no matched intervals exist, metrics are safely None., End-to-end pipeline handles empty lists without crashing., TestEmptyDatasets

### Community 24 - ".test_selection_ignores_error_value"
Cohesion: 0.40
Nodes (3): Among multiple runs published prior to cutoff, select the one with the latest…, Selection must NEVER pick a forecast because it is closer to actual., TestForecastSelection

## Knowledge Gaps
- **45 isolated node(s):** `name`, `private`, `version`, `type`, `dev` (+40 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 175 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `fetch_actual_generation()` connect `fetch_actual_generation` to `match_actuals_and_forecasts`, `main.py`, `patch`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Why does `fetch_wind_forecasts()` connect `fetch_actual_generation` to `match_actuals_and_forecasts`, `main.py`, `patch`?**
  _High betweenness centrality (0.108) - this node is a cross-community bridge._
- **Why does `run_forecast_accuracy_analysis()` connect `match_actuals_and_forecasts` to `fetch_actual_generation`, `test_analysis.py`, `main.py`, `TestEmptyDatasets`?**
  _High betweenness centrality (0.072) - this node is a cross-community bridge._
- **Are the 41 inferred relationships involving `patch` (e.g. with `.test_actuals_http_error_returns_502()` and `.test_actuals_success()`) actually correct?**
  _`patch` has 41 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `private`, `version` to the rest of the system?**
  _45 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `fetch_actual_generation` be split into smaller, more focused modules?**
  _Cohesion score 0.09851551956815115 - nodes in this community are weakly interconnected._
- **Should `test_analysis.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11904761904761904 - nodes in this community are weakly interconnected._