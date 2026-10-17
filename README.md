# OmniSight AI

OmniSight is an internship project exploring browser automation and visual UI testing. The repository currently includes an OmniStore demo storefront and Playwright tests for its desktop and mobile shopping flow.

## Current status

Implemented:

- React storefront with product categories, search, and a shopping bag
- Responsive layouts for desktop and mobile
- Playwright checks for layout, filtering, search, bag quantities, and totals
- Desktop and mobile screenshots saved in `artifacts/` when the browser test runs

Planned work includes AI-based visual issue detection, suggested self-healing changes, GitHub pull request integration, and a QA dashboard. Those features are not implemented yet.

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

Open the local address printed by Vite (normally `http://127.0.0.1:5173`). Keep this terminal running while using the browser tests.

## Set up browser tests

In a second PowerShell terminal opened at the repository root, create a Python environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pytest playwright
.\.venv\Scripts\python.exe -m playwright install chromium
```

If `.venv` already exists and has `pytest` and `playwright` installed, skip this section.

## Run checks

From the `frontend` directory, run lint and create a production build:

```powershell
npm run lint
npm run build
```

From the repository root, run the desktop and mobile browser test:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_browser_capture.py
```

The test expects the storefront at `http://127.0.0.1:5173` by default. Set `OMNISTORE_URL` if it is running at a different address. Test screenshots are written to `artifacts/omnistore-desktop.png` and `artifacts/omnistore-mobile.png`.

## Project details

- **Internship:** Infotact Solutions
- **Domain:** Generative AI
- **Project:** OmniSight — Multimodal UI Self-Healing and RPA Agent
