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
- Initial rule-based UI diagnosis: reports horizontal overflow, failed images, unnamed buttons/links, unlabeled form fields, and browser errors with evidence and repair suggestions; wide-table overflow can include a reviewable CSS proposal
- OmniSight dashboard at `/audit` for submitting audits, tracking completion, viewing findings and desktop/mobile screenshots, and downloading a shareable Markdown report with evidence and screenshot links
- Intentionally broken practice page at `/audit-fixture` with an unconstrained wide data table; mobile audits detect horizontal overflow (706px content vs. 390px viewport) and attach a reviewable CSS repair proposal
- Repaired sample page at `/audit-fixture-fixed` applying `max-width: 100%; overflow-x: auto;` to the table wrapper; mobile audits confirm 0 overflow findings
- Dashboard shortcuts to quickly populate either route ("Use broken sample" and "Use repaired sample") for immediate before/after comparison
- Audit history view at `/audit/history` with side-by-side delta comparisons (resolved, introduced, unchanged findings)
- Human-approved GitHub draft PR preparation workflow with exact unified diff inspection and server-side token safety
- Isolated repair preview: applies the supported table-overflow CSS only in disposable Playwright pages, reruns the audit, and captures before/after screenshots without editing the audited site
- **Safe Self-Healing Demonstration**: Dedicated dashboard section calling `POST /repairs/self-healing-demo`. Applies an approved allowlisted CSS rule (`img { max-width: 100%; height: auto; }`) to an isolated temporary copy (`AuditImageFixture.temp.jsx`) of the oversized-image sample. Verifies compilation with Vite SSR, runs Playwright audits across desktop (1440×1000) and mobile (390×844) viewports (resolving the single mobile overflow finding to 0 findings), and displays the generated unified diff alongside before/after screenshots served via `/repairs/self-healing-demo/screenshots/{phase}/{viewport}`. The original fixture file remains cryptographically unchanged, human review is strictly required, and arbitrary websites are not automatically repaired.
- **5-Minute Presentation Guide**: See [DEMO.md](DEMO.md) for the walkthrough script covering the UI audit, self-healing demonstration, human-reviewed repair prototype, diff preview, and port recovery steps

Optional screenshot-based AI explanations support Gemini (`GEMINI_API_KEY`, recommended) or OpenAI (`OPENAI_API_KEY`). A supported CSS proposal can be tried in a disposable browser page and re-audited; this does not modify the audited site's source files. The OmniStore shopping flow remains a sample target used to exercise automation.

## OmniSight UI audit and repair prototype

OmniSight captures pages at desktop and mobile sizes, detects selected UI issues, compares screenshots with saved baselines, and preserves audit history.

The self-healing demo applies an approved CSS rule to a temporary copy of an oversized-image sample, builds and audits the copy, then displays the proposed diff and before-and-after screenshots. The original fixture remains unchanged, and repairs require human review.

Verified demo result: 1 mobile overflow finding before repair, 0 afterward. The reported tests, frontend lint, and production build passed.

Repairs cover supported sample cases; the system does not automatically repair arbitrary websites. Optional AI vision analysis requires an API key.

### Week 4 progress update — October 26–27, 2026

- Added a dashboard to run local responsive UI audits and review screenshots and findings.
- Added a separate practice page (`/audit-fixture`) with an intentional mobile-width problem. A local browser audit consistently detected horizontal overflow on mobile.
- Improved overflow evidence to include likely affected elements and measurements.
- Added a reviewable CSS repair proposal attached to wide-table overflow findings. The proposal targets the table's scroll wrapper and recommends `overflow-x: auto`; it is displayed in the dashboard and included in downloaded Markdown reports. OmniSight does not apply it automatically.
- Added a separate repaired route (`/audit-fixture-fixed`) with the suggested CSS applied, plus "Use broken sample" and "Use repaired sample" dashboard shortcuts to complete an end-to-end detect → review → fix → re-audit before/after verification workflow.
- Verified: `/audit-fixture` flags horizontal overflow with the repair proposal; `/audit-fixture-fixed` passes with 0 findings. All 8 API tests pass.

## Requirements

- Node.js and npm
- Python 3.11
- Google Chrome or Chromium installed by Playwright
- Optional: a Gemini API key for screenshot-based AI explanations (or an OpenAI API key; provider usage limits and charges depend on the account)

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
# Optional: Gemini visual analysis (recommended). Set before starting backend.
# Never commit API keys or put them in code, logs, or shared config.
$env:GEMINI_API_KEY = "your-gemini-api-key"
# Optional: select provider/model (defaults to Gemini with gemini-3.1-flash-lite; GEMINI_MODEL can override it)
# $env:AI_PROVIDER = "gemini"
# $env:GEMINI_MODEL = "gemini-3.1-flash-lite"

# OpenAI remains supported as an alternative:
# $env:OPENAI_API_KEY = "your-openai-api-key"
# $env:AI_PROVIDER = "openai"
# $env:OPENAI_MODEL = "gpt-4o-mini"

.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

If neither API key is set, UI audits remain fully functional, running all browser checks and returning `ai_analysis.status = "not_configured"`. When configured, the backend sends the captured desktop and mobile screenshots and browser findings to the selected vision model for visual review (clipped content, overlapping elements, and contrast). The model does not edit files or apply repairs. `GEMINI_API_KEY` selects Gemini by default with model `gemini-3.1-flash-lite` (override with `GEMINI_MODEL`); use `AI_PROVIDER` to explicitly choose `gemini` or `openai` when both keys are present. Transient HTTP 429 or 503 errors automatically retry up to 3 times with short backoff.

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

5. **Execute safe self-healing demonstration** (temporary copy verification):
   ```powershell
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/repairs/self-healing-demo" -Method Post -ContentType "application/json" -Body "{}"
   ```
   Applies the approved CSS allowlist repair rule (`img { max-width: 100%; height: auto; }`) to an isolated temporary copy of `frontend/src/AuditImageFixture.jsx`, verifies compilation with Vite SSR, runs Playwright audits across desktop and mobile, asserts file integrity (before/after SHA-256 hashes), and returns the unified diff and verification outcomes. The original fixture file is NEVER modified in place, and code is NEVER committed, pushed, or automatically PR'd.

6. **Serve self-healing demo screenshot artifacts**:
   ```powershell
   # Phase: before | after; Viewport: desktop | mobile
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/repairs/self-healing-demo/screenshots/before/mobile" -Method Get
   ```
   Serves only the known demo artifacts from `artifacts/self_healing_demo/`. Arbitrary filesystem access and path traversals are strictly blocked.

### Before/after audit workflow (testing the repair proposal)

OmniSight includes a paired test fixture to demonstrate a complete detect → review → fix → re-audit cycle:

1. **Broken sample (`/audit-fixture`)**:
   Contains an unconstrained wide table.
   - In the audit dashboard (`http://127.0.0.1:5173/audit`), click **Use broken sample** (fills `http://127.0.0.1:5173/audit-fixture`) and click **Run audit**.
   - Result: Flags horizontal overflow at the mobile viewport (706px content vs. 390px viewport) and generates a reviewable CSS repair proposal:
     ```css
     div.fixture-table-scroll {
       max-width: 100%;
       overflow-x: auto;
     }
     ```
   - The proposed CSS snippet is shown in the dashboard card and included in downloaded Markdown reports.

2. **Repaired sample (`/audit-fixture-fixed`)**:
   Applies the proposed `max-width: 100%; overflow-x: auto;` rule to the table wrapper. The table scrolls cleanly within its card on mobile screens without overflowing the page.
   - In the audit dashboard, click **Use repaired sample** (fills `http://127.0.0.1:5173/audit-fixture-fixed`) and click **Run audit**.
   - Result: 0 findings reported. The horizontal overflow issue is resolved.

3. **Try the proposed fix without changing source files**:
   - After auditing `/audit-fixture`, open its horizontal-overflow finding and click **Try fix in isolated browser**.
   - The backend validates the generated table-wrapper rule, injects it into disposable desktop and mobile Playwright pages, reruns the deterministic checks, and saves preview screenshots under that job's artifacts.
   - The dashboard reports whether the same finding disappeared and links the preview screenshots. The original audit result and target site's files are left unchanged.
   - This preview currently supports only the generated wide-table overflow repair; it does not execute arbitrary model-generated CSS or write changes to the target project.

You can also run both audits directly via PowerShell:

```powershell
# Audit broken sample
$body = @{ storefront_url = "http://127.0.0.1:5173/audit-fixture" } | ConvertTo-Json
$job = Invoke-RestMethod -Uri "http://127.0.0.1:8000/webhooks/audit" -Method Post -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/$($job.job_id)" -Method Get | ConvertTo-Json -Depth 8

# Audit repaired sample
$body = @{ storefront_url = "http://127.0.0.1:5173/audit-fixture-fixed" } | ConvertTo-Json
$job = Invoke-RestMethod -Uri "http://127.0.0.1:8000/webhooks/audit" -Method Post -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri "http://127.0.0.1:8000/jobs/$($job.job_id)" -Method Get | ConvertTo-Json -Depth 8
```

## Optional AI visual analysis (Vision-Language Model)

OmniSight includes an optional visual review step powered by a vision-language model. When configured, it inspects the desktop and mobile screenshots captured during a responsive UI audit to suggest visual improvements.

### Capabilities & Scope

The model identifies visual problems that rule-based DOM checks often miss:
- **Clipped content**: Text or UI cards cut off by container boundaries or screen edges.
- **Overlapping elements**: Colliding buttons, overlapping badges, or z-index stacking issues.
- **Hard-to-read contrast**: Low contrast between text and backgrounds or difficult-to-read badges.
- **Responsive discrepancies**: Unintended visual divergence between desktop (1440×1000) and mobile (390×844) layouts.

### Setup instructions

1. Set `GEMINI_API_KEY` in your terminal session before starting the backend (recommended):
   ```powershell
   # Windows PowerShell
   $env:GEMINI_API_KEY = "your-gemini-api-key-here"

   # Optional: select Gemini and override its default model (defaults to gemini-3.1-flash-lite; GEMINI_MODEL can override it)
   # $env:AI_PROVIDER = "gemini"
   # $env:GEMINI_MODEL = "gemini-3.1-flash-lite"

   # Alternatively, use OpenAI
   # $env:OPENAI_API_KEY = "your-openai-api-key-here"
   # $env:AI_PROVIDER = "openai"
   ```
   ```bash
   # Linux / macOS Bash
   export GEMINI_API_KEY="your-gemini-api-key-here"
   ```
2. Start the backend:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
3. Run an audit from the dashboard at `http://127.0.0.1:5173/audit`. The AI summary and suggestions will appear in a dedicated card below the deterministic findings.

> **Security Note:** Never commit API keys to version control, embed them in client-side code, or include them in logs. OmniSight sanitizes error messages to prevent accidental token exposure.

### Privacy and Data Flow

- **Zero-call default**: When neither `GEMINI_API_KEY` nor `OPENAI_API_KEY` is set, **no external AI requests are made**. The audit runs entirely on your local machine using Playwright.
- **Data transmitted when enabled**:
  - The captured desktop and mobile screenshot images (Base64-encoded over HTTPS).
  - The array of browser-detected findings (evidence strings, selectors, and dimensions) for background context.
- **Data NOT transmitted**: Target website source code, repository files, backend files, environment variables, database contents, or user session credentials are never sent to the model.
- **Review-only guarantee**: The vision model output is strictly advisory. OmniSight never writes files, alters the target website, or opens automated pull requests.

### Limitations & Disclaimers

- AI visual suggestions are **hypotheses for human review**, not confirmed defects.
- Vision models may occasionally hallucinate or overlook subtle styling details.
- Always cross-reference suggested issues against the actual screenshot captures and browser developer tools before making changes.

## Run checks & test suites

### Frontend checks

From the `frontend` directory, run lint and create a production build:

```powershell
npm run lint
npm run build
```

### Backend API & AI analyzer tests

From the repository root:

```powershell
# Run backend API tests
.\.venv\Scripts\python.exe -m pytest tests\test_api.py -v

# Run AI vision analyzer unit tests (uses mocked responses, zero API credits spent)
.\.venv\Scripts\python.exe -m pytest tests\test_ai_analyzer.py -v
```

### Playwright browser flow tests

From the repository root (ensure the storefront is running at `http://127.0.0.1:5173`):

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_browser_capture.py -v
```

### GitHub Draft PR workflow tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_github_pr.py -v
```

### Safe self-healing demonstration tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_self_healing.py -v
```
Verifies original fixture integrity (SHA-256 unchanged), strict CSS allowlist rejection of arbitrary CSS, unified diff generation, Vite SSR temporary-copy compilation, mobile overflow resolution in Playwright, and screenshot artifact serving.

To run all automated tests across test suites (45 passing tests):

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

Screenshots are written to `artifacts/omnistore-desktop.png` and `artifacts/omnistore-mobile.png`.

## Project details

- **Internship:** Infotact Solutions
- **Domain:** Generative AI
- **Project:** OmniSight — UI Audit & Human-Reviewed Repair Workflow Prototype

### October 27 project update

- Added a downloadable Markdown report to completed UI audits. It includes job details, desktop/mobile screenshot links, detected evidence, affected elements, and suggested next steps.
- Reports are generated in the browser and do not require a separate service or API key.
- Verified: an audit of `/audit-fixture` reported horizontal overflow at mobile width (706 px content against a 390 px viewport), listed likely affected elements, and completed with desktop/mobile screenshots.

### October 27 repair proposal update

- Added a reviewable CSS proposal when an overflowing wide table has a parent wrapper without horizontal scrolling. The proposal is displayed with the finding in the dashboard and included in downloaded Markdown reports; OmniSight does not apply it to the audited site.
- Fresh audit of `/audit-fixture` confirmed the proposal targets `div.fixture-table-scroll` with `max-width: 100%; overflow-x: auto;`.
- Fixed a test-suite assertion that was checking for a stale error-message substring; all 8 API tests pass.

### October 27 before/after audit milestone

- Added a separate repaired sample route (`/audit-fixture-fixed`) applying `max-width: 100%; overflow-x: auto;` to the table wrapper while keeping `/audit-fixture` intact as the broken baseline.
- Scoped repaired styles to ensure the repair does not leak into the broken fixture.
- Added "Use broken sample" and "Use repaired sample" shortcut buttons to the audit dashboard for one-click route selection.
- Cross-linked both sample pages so reviewers can switch between them directly in the browser.
- Verified: `/audit-fixture` produces 1 horizontal overflow finding with a reviewable repair proposal; `/audit-fixture-fixed` produces 0 findings. All 8 backend API tests and frontend linting pass.

### October 27 screenshot-based visual analysis milestone

- Added optional Vision-Language Model analysis to UI audits (`backend/ai_analyzer.py`) targeting clipped content, overlapping elements, and contrast issues.
- Implemented robust structured output parsing with Pydantic field normalization and automatic redaction of API key patterns from error messages.
- Added dedicated dashboard UI section (`.ai-analysis-card`) clearly separating AI suggestions from deterministic findings with priority tags, viewport badges, evidence, explanations, review-only suggested fixes, and verification steps.
- Updated Markdown audit reports to export AI visual review suggestions with clear disclaimer notes.
- Added 8 unit tests in `tests/test_ai_analyzer.py` covering no-key, skipped, mocked success, provider exceptions, key scrubbing, and response validation; added mocked audit lifecycle test in `tests/test_api.py`.

### October 28 human-approved GitHub draft PR milestone

- Added GitHub draft PR workflow (`backend/github_service.py`) allowing human reviewers to review proposed repairs, inspect repository targets, base branches, generated branch names, and exact unified diffs.
- Strictly requires explicit approval (`approved: true`) before opening a draft pull request; PRs are strictly opened as **Draft PRs** (`draft: true`).
- Server-side token management via `GITHUB_TOKEN` environment variable; zero credentials or sensitive tokens exposed to client or logs; clean "not configured" status reporting.
- Added 11 unit tests in `tests/test_github_pr.py` covering status endpoints, unapproved submission rejection, missing configuration, unified diff generation, and draft PR creation.

### October 28 audit history & regression tracking milestone

- Added audit history view (`frontend/src/AuditHistory.jsx` and `AuditHistory.css`) accessible via `/audit/history` and the dashboard sidebar.
- Implemented `GET /jobs` and `POST /jobs/compare` backend endpoints for side-by-side run comparisons.
- Classifies findings between two audit runs into `resolved`, `introduced`, and `unchanged` categories with delta summaries and visual screenshot comparisons.
- Verified: all 31 automated backend tests pass; frontend build and oxlint linting pass with 0 errors and 0 warnings.

### October 30 isolated repair preview milestone

- Added **Try fix in isolated browser** for supported wide-table overflow proposals.
- The backend injects only a validated `max-width: 100%; overflow-x: auto;` rule in temporary Playwright pages, reruns the browser audit at desktop and mobile sizes, and captures preview screenshots.
- Original findings and audited source files are not modified. Arbitrary CSS and other repair types are not supported by this preview.

### Safe self-healing demonstration milestone

- Added a dedicated dashboard section and backend endpoint (`POST /repairs/self-healing-demo`) for isolated self-healing verification.
- Applies the approved CSS repair rule (`img { max-width: 100%; height: auto; }`) only to an isolated temporary copy of `frontend/src/AuditImageFixture.jsx` (`AuditImageFixture.temp.jsx`).
- Verified the temporary copy with Vite SSR (`npx vite build --ssr`) and Playwright audits across desktop (1440×1000) and mobile (390×844) viewports.
- Result: Detected 1 mobile horizontal overflow finding before repair, and verified 0 findings after repair.
- Cryptographically verified that the original fixture file remains unchanged (SHA-256 before matches SHA-256 after).
- Displays the generated unified diff, build and browser audit metrics, and links/thumbnails to before/after screenshots via a secure endpoint (`GET /repairs/self-healing-demo/screenshots/{phase}/{viewport}`) that serves only known demo artifacts without exposing arbitrary filesystem paths.
- Guarantees: Human review is strictly required; no code is automatically committed, pushed, or PR'd; arbitrary websites are not automatically repaired.
- Verification results: All 8 self-healing tests in `tests/test_self_healing.py` pass; frontend linter (`oxlint`) passes with 0 errors and 0 warnings; production frontend build (`vite build`) succeeds in ~411ms; all 37 core/PR tests pass (45 total passing automated tests).



## Screenshots

OmniSight dashboard with Gemini AI visual suggestions. AI suggestions are not confirmed defects and need human review.


## Screenshots

OmniSight dashboard with Gemini AI visual suggestions. AI suggestions are not confirmed defects and need human review.

