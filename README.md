# OmniSight AI

OmniSight is an internship project exploring browser automation and visual UI testing. The repository currently includes an OmniStore demo storefront and Playwright tests for its desktop and mobile shopping flow.

## Current status

Implemented:

- React storefront with product categories, search, shopping bag, checkout flow, and demo order confirmation
- Responsive layouts for desktop (1440×1000) and mobile (390×844)
- FastAPI backend with:
  - `GET /health` service health check
  - `POST /webhooks/build` validated endpoint that queues the Playwright browser flow for local storefront URLs
  - `GET /jobs/{job_id}` job status, timestamps, error handling, and screenshot artifact paths
- Playwright checks covering catalog filtering, search, cart tally, checkout form completion, and order confirmation
- Automated desktop and mobile screenshot capture saved in `artifacts/` and per-job in `artifacts/jobs/{job_id}/`

Planned work includes AI-based visual issue detection, suggested self-healing changes, GitHub pull request integration, and a QA dashboard.

## Requirements

- Node.js and npm
- Python 3.11
- Google Chrome or Chromium installed by Playwright

## Set up the frontend

From the repository root, install the frontend dependencies:

```powershell
cd frontend
npm install
```

## Run the storefront

From the `frontend` directory:

```powershell
npm run dev
```

Open the local address printed by Vite (normally `http://127.0.0.1:5173`). Keep this terminal running while using the browser tests and backend webhooks.

## Set up Python environment & backend

In a second PowerShell terminal opened at the repository root, create a Python environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pytest playwright fastapi uvicorn httpx
.\.venv\Scripts\python.exe -m playwright install chromium
```

If `.venv` already exists and has the dependencies installed, skip this section.

## Run the FastAPI backend

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

The interactive OpenAPI documentation will be available at `http://127.0.0.1:8000/docs`.

### Backend API endpoints

1. **Health check**:
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get
   ```

2. **Trigger build webhook** (restricted to local storefront URLs):
   ```powershell
   $body = @{ storefront_url = "http://127.0.0.1:5173"; branch = "feature/visual-qa-mvp" } | ConvertTo-Json
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/webhooks/build" -Method Post -ContentType "application/json" -Body $body
   ```
   Returns `202 Accepted` with a `job_id`.

3. **Check job status and screenshot artifacts**:
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/<job_id>" -Method Get
   ```
   When completed, returns the absolute paths to the desktop and mobile screenshots.

## Run checks & test suites

### Frontend checks

From the `frontend` directory, run lint and create a production build:

```powershell
npm run lint
npm run build
```

### Backend API tests

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_api.py -v
```

### Playwright browser flow tests

From the repository root (ensure the storefront is running at `http://127.0.0.1:5173`):

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_browser_capture.py -v
```

To run all test suites together:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Screenshots are written to `artifacts/omnistore-desktop.png` and `artifacts/omnistore-mobile.png`.

## Project details

- **Internship:** Infotact Solutions
- **Domain:** Generative AI
- **Project:** OmniSight — Multimodal UI Self-Healing and RPA Agent
