# OmniSight AI

OmniSight is an internship project exploring browser automation and visual UI testing. The repository currently includes an OmniStore demo storefront and Playwright tests for its desktop and mobile shopping flow.

## Current status

Implemented:

- React storefront with product categories, search, shopping bag, checkout flow, and demo order confirmation
- Responsive layouts for desktop (1440×1000) and mobile (390×844)
- FastAPI backend with:
  - `GET /health` service health check
  - `POST /webhooks/build` validated endpoint that queues the Playwright browser flow for local storefront URLs
  - `POST /webhooks/audit` general responsive UI audit for any local web page, without OmniStore-specific interactions
  - `GET /jobs/{job_id}` job status, timestamps, error handling, and screenshot artifact paths
- Playwright checks covering catalog filtering, search, cart tally, checkout form completion, and order confirmation
- Automated desktop and mobile screenshot capture saved in `artifacts/` and per-job in `artifacts/jobs/{job_id}/`
- Pixel-based visual comparison of stable desktop/mobile storefront screenshots, with local baselines in `artifacts/baselines/` and highlighted diff images for later runs
- Readable per-viewport visual assessment: changes at or above 0.5% are marked `review_required`; smaller changes are `within_threshold`; first captures are marked `baseline_created`
- Initial rule-based UI diagnosis: reports horizontal overflow, failed images, unnamed buttons/links, unlabeled form fields, and browser errors with evidence and repair suggestions
- OmniSight dashboard at `/audit` for submitting audits, tracking completion, viewing findings and desktop/mobile screenshots, and downloading a shareable Markdown report with evidence and screenshot links
- Separate `/audit-fixture` practice page with a known mobile overflow issue; a local audit flagged its mobile content width (706px) against the 390px viewport
- Overflow findings include likely element selectors and dimensions; a fresh sample audit verified the detector reports 706px of content in a 390px mobile viewport and identifies the table wrapper and card

Optional screenshot-based AI explanations are implemented but require an `OPENAI_API_KEY`; the backend does not automatically edit target websites. The OmniStore shopping flow remains a sample target used to exercise automation.

### Week 4 progress update — October 26, 2026

- Added a dashboard to run local responsive UI audits and review screenshots and findings.
- Added a separate practice page with an intentional mobile-width problem. A local browser audit detected horizontal overflow on mobile.
- Improved overflow evidence to include likely affected elements and measurements. The updated detail still needs a fresh audit after restarting the backend.
- Next: verify the richer finding, then build a reviewable repair proposal before attempting any automatic fix.

## Requirements

- Node.js and npm
- Python 3.11
- Google Chrome or Chromium installed by Playwright
- Optional: an OpenAI API key for screenshot-based AI explanations (API usage may incur charges)

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
.\.venv\Scripts\python.exe -m pip install pytest playwright fastapi uvicorn httpx pillow openai
.\.venv\Scripts\python.exe -m playwright install chromium
```

If `.venv` already exists and has the dependencies installed, skip this section.
If the environment already existed before visual comparison was added, install Pillow with:

```powershell
.\.venv\Scripts\python.exe -m pip install pillow
```

## Run the FastAPI backend

From the repository root:

```powershell
# Optional: enable vision-model analysis for UI audit jobs.
# Set this in the same terminal before starting the backend; do not commit the key.
$env:OPENAI_API_KEY = "your-api-key"

.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

If `OPENAI_API_KEY` is not set, UI audits still run their browser checks and return `ai_analysis.status = "not_configured"`. When configured, the backend sends the audit screenshots and browser findings to the OpenAI Responses API for structured explanations and suggested repairs. The model does not edit files or apply repairs.

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
   When completed, returns the absolute paths to the desktop and mobile checkout screenshots. The response also includes `visual_comparison` results for each viewport. The first run creates local baselines; later runs report changed-pixel percentages, an assessment (`within_threshold` or `review_required`), and red-highlighted diff images in that job's artifact folder. The initial review threshold is 0.5% of pixels. Baselines are local files under `artifacts/baselines/`; remove a baseline image to establish a new one on the next run.

4. **Run the general OmniSight UI audit** (does not run the OmniStore shopping flow):
   ```powershell
   $body = @{ storefront_url = "http://127.0.0.1:5173" } | ConvertTo-Json
   $job = Invoke-RestMethod -Uri "http://127.0.0.1:8000/webhooks/audit" -Method Post -ContentType "application/json" -Body $body
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/$($job.job_id)" -Method Get | ConvertTo-Json -Depth 8
   ```
   The job response includes `findings`, with a finding code, viewport, evidence, and repair suggestion, plus desktop and mobile audit screenshots under `artifacts/jobs/{job_id}/`. It also includes `ai_analysis`, with status `completed`, `not_configured`, `skipped`, or `error`.

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

### October 27 project update

- Added a downloadable Markdown report to completed UI audits. It includes job details, desktop/mobile screenshot links, detected evidence, affected elements, and suggested next steps.
- Reports are generated in the browser and do not require a separate service or API key.
- Verified: an audit of `/audit-fixture` reported horizontal overflow at mobile width (706px content against a 390px viewport), listed likely affected elements, and completed with desktop/mobile screenshots. The dashboard report download is available for saving this evidence.
- Next: make the suggested repair more actionable, then rerun the fixture audit to show the before/after result.
