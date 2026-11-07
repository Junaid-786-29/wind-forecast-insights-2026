# WindForecast Analytics — UK National Wind Generation Platform

A full-stack analytics platform built for UK energy trading and purchasing teams to compare **Actual National Wind Generation** against **Day-Ahead Wind Generation Forecasts** for January 2026.

Data is sourced directly from the official **Elexon BMRS API** (`FUELHH` actuals and `WINDFOR` forecasts) without external databases or fabricated records.

---

## Architecture Overview

```
                      ┌──────────────────────────────────────────┐
                      │              Host Machine                │
                      │  Browser: http://localhost:3000 (UI)     │
                      │  API:     http://localhost:8000 (Docs)   │
                      └───────────────────┬──────────────────────┘
                                          │
                     Docker Network (windforecast-network)
                     ─────────────────────────────────────
                                          │
                   ┌──────────────────────┴──────────────────────┐
                   │                                             │
                   ▼ :3000                                       ▼ :8000
    ┌───────────────────────────────┐             ┌───────────────────────────────┐
    │      windforecast-frontend    │             │      windforecast-backend     │
    │  Nginx 1.25 Alpine (Port 80)  │             │  FastAPI + Python 3.13 Slim   │
    │  - Serves React Production App│  /api/*     │  - Elexon Ingestion Service   │
    │  - Reverse proxies /api/ ─────┼────────────►│  - Day-Ahead Cutoff Engine    │
    │  - Static Asset Caching & Gzip│  proxy_pass │  - Accuracy Metrics Pipeline  │
    └───────────────────────────────┘             └───────────────┬───────────────┘
                                                                  │ HTTPS
                                                                  ▼
                                                      ┌───────────────────────┐
                                                      │    Elexon BMRS API    │
                                                      │  data.elexon.co.uk    │
                                                      │  - FUELHH (Actuals)   │
                                                      │  - WINDFOR (Forecasts)│
                                                      └───────────────────────┘
```

---

## Technology Stack

- **Backend**: Python 3.13, FastAPI, Pydantic v2, Uvicorn, Requests.
- **Frontend**: React 19, Vite, Native SVG Time-Series Visualizations, CSS Custom Properties.
- **Production Server**: Nginx Alpine (multi-stage build, reverse proxy, SPA fallback).
- **Containerization**: Docker & Docker Compose.

---

## Analytical Methodology: Forecast Resolution & Granularity Mapping

To ensure accurate, domain-compliant analytics for UK energy purchasing teams, the platform implements an explicit data-granularity mapping between actual generation outturn and forecast publications:

1. **FUELHH Actuals (Half-Hourly Cadence)**:
   - Sourced from Elexon BMRS `FUELHH` (`fuelType = WIND`).
   - Represents measured national wind generation across Great Britain for each of the 48 half-hour **Settlement Periods** per day (:00 and :30 intervals).
   - All 48 half-hourly actual intervals are preserved without downsampling or truncation.

2. **WINDFOR Forecasts (Hourly Cadence)**:
   - Sourced from Elexon BMRS `WINDFOR` (stream endpoint).
   - Produced and published by National Grid ESO (NESO) on an **hourly profile** (60-minute delivery periods, :00 intervals) with updates up to 8 times daily.
   - Values represent average forecasted active power in **Megawatts (MW)** across visible Power Park Modules on the transmission network.

3. **Settlement Period Mapping Convention**:
   - Each hourly WINDFOR forecast for hour $H$ (e.g., `14:00:00Z`) is mapped to both constituent 30-minute Settlement Periods within that hour:
     - Settlement Period $2H-1$ (`14:00:00Z` to `14:30:00Z`) maps to the `14:00:00Z` forecast.
     - Settlement Period $2H$ (`14:30:00Z` to `15:00:00Z`) maps to the same `14:00:00Z` forecast.
   - The original half-hourly `startTime` and the forecast's original `forecastPublishTime` are preserved on every matched record.
   - The same hourly forecast value is used twice in the half-hourly comparison.

4. **Analytical Transparency & Variance Notice**:
   - Because actual generation can fluctuate or ramp within an hour, sub-hourly variations between the :00 and :30 actual values contribute to the calculated forecast errors (MAE, RMSE, Bias).
   - This mapping is an **analytical evaluation convention** designed to benchmark against GB half-hourly settlement periods; it is not a claim that WINDFOR supplies independently modeled 30-minute forecast values.

5. **Day-Ahead Gate Closure Cutoff Policy**:
   - Day-ahead forecast selection enforces a gate closure cutoff of **10:00 UTC on D-1** (the day prior to delivery), aligning with the GB Day-Ahead power auction gate closure (EPEX SPOT / N2EX).
   - For all intervals on delivery date $D$, only forecast runs published at or before `10:00:00 UTC` on $D-1$ are eligible. The latest eligible run is selected independently per delivery slot.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (v24.0+ recommended)
- [Docker Compose](https://docs.docker.com/compose/) (v2.20+ / Docker Compose V2)
- Network access to `data.elexon.co.uk` (Elexon BMRS is a public API, no key required).

---

## Quick Start with Docker

### 1. Clone & Configure Environment

```bash
# Clone the repository
git clone https://github.com/Junaid-786-29/wind-forecast-insights-2026.git
cd wind-forecast-insights-2026

# (Optional) Copy example environment configuration
cp .env.example .env
```

### 2. Build & Start the Application

Build container images and start both frontend and backend services:

```bash
docker compose up --build -d
```

### 3. Verify Container Status & Health

```bash
docker compose ps
```

Expected output:
```text
NAME                    IMAGE                           STATUS                   PORTS
windforecast-backend    windforecast-analytics-backend   Up (healthy)             0.0.0.0:8000->8000/tcp
windforecast-frontend   windforecast-analytics-frontend  Up                       0.0.0.0:3000->80/tcp
```

---

## Accessing the Application

| Service | URL | Description |
|---|---|---|
| **Dashboard UI** | [http://localhost:3000](http://localhost:3000) | React production dashboard with KPIs, time-series charts, and data tables. |
| **API Interactive Docs** | [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger UI for exploring and testing API v1 endpoints. |
| **API ReDoc** | [http://localhost:8000/redoc](http://localhost:8000/redoc) | Alternative OpenAPI specification view. |
| **Backend Health Check** | [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) | Service alive signal (`{"status": "ok"}`). |
| **Analysis Endpoint** | [http://localhost:8000/api/v1/wind/analysis](http://localhost:8000/api/v1/wind/analysis) | Primary dataset comparison endpoint for January 2026. |

---

## Managing the Containers

### Viewing Logs

Stream unified logs from all services:
```bash
docker compose logs -f
```

Stream logs from a specific container:
```bash
# Backend logs
docker compose logs -f backend

# Frontend Nginx logs
docker compose logs -f frontend
```

### Rebuilding After Code Changes

When source files in `backend/` or `frontend/` are updated:
```bash
docker compose up --build -d
```

### Stopping the Application

Stop and remove running containers and networks:
```bash
docker compose down
```

To also remove named volumes:
```bash
docker compose down -v
```

---

## Local Development (Without Docker)

You can also run backend and frontend independently on your host machine:

### Backend (Terminal 1)
```bash
cd backend

# Create & activate virtual environment (optional)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (Terminal 2)
```bash
cd frontend

# Install Node modules
npm install

# Start Vite dev server with Hot Module Replacement
npm run dev
```
Visit Vite development UI at [http://localhost:5173](http://localhost:5173).

---

## Running Automated Tests

Run the backend test suite (65 tests across Phase 1 Elexon integration and Phase 2 Analysis):

```bash
# From project root
python -m pytest backend/tests/ -v --tb=short

# Or inside running backend container
docker compose exec backend pytest tests/ -v --tb=short
```

---

## Environment Variables Reference

Configurable via `.env` or system environment:

| Variable | Default | Service | Description |
|---|---|---|---|
| `BACKEND_PORT` | `8000` | Host / Compose | Host port mapped to the FastAPI container. |
| `FRONTEND_PORT` | `3000` | Host / Compose | Host port mapped to the React Nginx container. |
| `DAY_AHEAD_CUTOFF_HOUR_UTC` | `10` | Backend | Cutoff hour (UTC) on D-1 for Day-Ahead forecast selection (GB auction close). |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Backend | Comma-separated allowed HTTP origins for browser requests. |
| `VITE_API_BASE_URL` | `""` (empty) | Frontend | Custom public API base URL (empty uses Nginx reverse proxy). |

---

## Cloud Deployment

This section provides a step-by-step guide to deploying **WindForecast Analytics** to production in the cloud:
- **Backend**: Hosted on **Render** as a Docker Web Service.
- **Frontend**: Hosted on **Vercel** as a static Vite Single Page Application.
- **No external databases or Redis instances are required.**

```
   ┌─────────────────────────────────────────────────────────┐
   │                    Vercel Frontend                      │
   │       https://wind-forecast-insights-2026.vercel.app/   │
   │               (React 19 + Vite SPA)                     │
   └───────────────────────────┬─────────────────────────────┘
                               │
                               │ HTTPS API Calls (VITE_API_BASE_URL)
                               │ (Headers: origin, content-type)
                               ▼
   ┌─────────────────────────────────────────────────────────┐
   │                     Render Backend                      │
   │    https://wind-forecast-insights-2026.onrender.com     │
   │      (FastAPI Docker Container on 0.0.0.0:$PORT)        │
   │            CORS_ORIGINS=<your-vercel-url>               │
   └───────────────────────────┬─────────────────────────────┘
                               │
                               │ Outbound HTTPS Requests
                               ▼
   ┌─────────────────────────────────────────────────────────┐
   │                 Official Elexon BMRS API                │
   │                  data.elexon.co.uk                      │
   └─────────────────────────────────────────────────────────┘
```

---

### Step 1: Deploy Backend to Render

Deploy the FastAPI backend first so you have its public URL ready before configuring the frontend.

#### Option A: Using Render Blueprint (`render.yaml` — Recommended)

1. Push your code to your GitHub repository.
2. Log in to your [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** and select **Blueprint**.
4. Connect your GitHub repository. Render will automatically detect the [`render.yaml`](./render.yaml) specification in the root directory.
5. Review the plan settings and click **Apply**.

#### Option B: Manual Web Service Creation

1. In the Render Dashboard, click **New +** and select **Web Service**.
2. Select your repository.
3. Configure the following service settings:
   - **Name**: `windforecast-backend` (or your preferred name)
   - **Region**: Choose a region closest to the UK (e.g. Frankfurt)
   - **Language / Runtime**: **Docker**
   - **Dockerfile Path**: `./backend/Dockerfile`
   - **Docker Context**: `./backend`
   - **Instance Type**: Free
4. Under **Advanced** $\to$ **Health Check Path**, enter:
   ```text
   /api/v1/health
   ```
5. Under **Environment Variables**, add:
   - `PORT`: `10000` (Render's dynamic port; Dockerfile binds to `0.0.0.0:$PORT`)
   - `PYTHONUNBUFFERED`: `1`
   - `DAY_AHEAD_CUTOFF_HOUR_UTC`: `10`
   - `CORS_ORIGINS`: `http://localhost:3000` (You will update this with your Vercel URL in Step 3)
6. Click **Create Web Service** and wait for the initial build to complete.
7. Once deployed, note down your backend URL:
   `https://<your-backend-app>.onrender.com`

---

### Step 2: Deploy Frontend to Vercel

1. Log in to your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** $\to$ **Project**.
3. Import your GitHub repository.
4. In the **Configure Project** screen:
   - **Framework Preset**: **Vite**
   - **Root Directory**: Click *Edit* and select `frontend` (or leave as root if using the root `vercel.json`)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
5. Expand the **Environment Variables** section and configure:
   - **Name**: `VITE_API_BASE_URL`
   - **Value**: Your Render backend URL from Step 1 (e.g. `https://<your-backend-app>.onrender.com` — *omit any trailing slash*)
6. Click **Deploy**.
7. Once deployed, note down your production Vercel URL:
   `https://<your-frontend-app>.vercel.app`

---

### Step 3: Connect Frontend and Backend (Configure CORS)

Now that you have your Vercel URL, update the CORS configuration on Render so the browser allows API requests from your Vercel domain:

1. In the **Render Dashboard**, navigate to your `windforecast-backend` Web Service.
2. Go to **Environment** tab.
3. Locate `CORS_ORIGINS` and set its value to your Vercel frontend URL:
   ```text
   https://<your-frontend-app>.vercel.app,http://localhost:3000,http://localhost:5173
   ```
   *(Multiple comma-separated origins are supported for local testing).*
4. *(Optional)* If you want Vercel branch preview URLs to work, add:
   - `CORS_ORIGIN_REGEX`: `https:\/\/.*\.vercel\.app`
5. Click **Save Changes**. Render will automatically trigger a rolling redeploy.

---

### Step 4: Verification Commands

After both services are deployed, verify connectivity from your local terminal:

#### 1. Verify Backend Health Endpoint
```bash
curl -i https://<your-backend-app>.onrender.com/api/v1/health
```
**Expected Response (`200 OK`):**
```json
{"status":"ok","version":"1.0.0","service":"wind-forecast-analytics"}
```

#### 2. Verify Backend Analysis Endpoint
```bash
curl -i "https://<your-backend-app>.onrender.com/api/v1/wind/analysis?date_from=2026-01-01&date_to=2026-01-02"
```
**Expected Response (`200 OK`):**
HTTP 200 JSON payload containing `matched_interval_count`, `mae`, `rmse`, `bias`, `mape`, and `intervals`.

#### 3. Verify CORS Response Headers
```bash
curl -i -X OPTIONS "https://<your-backend-app>.onrender.com/api/v1/wind/analysis" \
  -H "Origin: https://<your-frontend-app>.vercel.app" \
  -H "Access-Control-Request-Method: GET"
```
**Expected Response:**
`HTTP/1.1 200 OK` with header `access-control-allow-origin: https://<your-frontend-app>.vercel.app`.

#### 4. Verify Frontend Application in Browser
1. Open `https://<your-frontend-app>.vercel.app` in your web browser.
2. Confirm the **KPI Overview**, **Actual vs Forecast Chart**, **Forecast Error Chart**, and **Data Table** populate with January 2026 data.
3. Open browser DevTools (`F12` $\to$ **Network** tab) to verify API requests resolve directly to your Render URL with HTTP 200.

---

### Common Deployment Errors & Troubleshooting

| Symptom | Root Cause | Solution |
|---|---|---|
| **CORS error in browser console** (`Access-Control-Allow-Origin missing`) | Frontend origin does not match `CORS_ORIGINS` on Render. | In Render Web Service settings, update `CORS_ORIGINS` to include your exact Vercel URL (`https://<your-app>.vercel.app` without trailing slash) and redeploy. |
| **Backend port binding error** (`Port scan timeout / service failed to bind`) | FastAPI is listening on `127.0.0.1` or a hardcoded port instead of `0.0.0.0:$PORT`. | Verify [`backend/Dockerfile`](./backend/Dockerfile) starts with `uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`. Render dynamically assigns the port via `$PORT`. |
| **Frontend displays "Unable to Load Wind Forecast Analysis"** | `VITE_API_BASE_URL` is missing or points to `localhost`. | In Vercel Project Settings $\to$ **Environment Variables**, verify `VITE_API_BASE_URL` is set to `https://<your-backend>.onrender.com`. Redeploy the frontend after editing. |
| **Render cold start delay (50–90 seconds on Free Tier)** | Render spins down free web services after 15 minutes of inactivity. | Wait ~60 seconds on initial load while Render restarts the container. Once awake, subsequent requests respond immediately. |
| **404 Not Found on browser page refresh on Vercel** | SPA routing not rewrote to `/index.html`. | Ensure [`frontend/vercel.json`](./frontend/vercel.json) or [`vercel.json`](./vercel.json) contains the `"rewrites": [{"source": "/(.*)", "destination": "/index.html"}]` rule. |


