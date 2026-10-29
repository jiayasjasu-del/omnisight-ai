# OmniSight — 5-Minute Internship Review Demo Guide

This guide provides a structured, 5-minute walkthrough script and technical runbook for presenting OmniSight at the internship final review.

---

## 1. Project Purpose & Limitations

### Purpose
OmniSight is a **UI audit and human-reviewed repair workflow prototype** designed to bridge automated browser testing with human inspection and reviewable repair suggestions. It does not automatically heal, edit, or modify the audited target website. It automates:
- **Responsive capture**: Headless Playwright capture across standard desktop (1440×1000) and mobile (390×844) viewports.
- **Deterministic DOM audit**: Rule-based detection of horizontal overflow, broken images, unlabelled form controls, unnamed buttons, and console errors.
- **Review-only repair proposals**: Generating targeted CSS suggestions (e.g., container scroll wrappers for overflowing wide tables) without editing target files.
- **Visual regression tracking**: Side-by-side run comparisons classifying findings into resolved, introduced, and unchanged deltas.
- **Optional AI visual analysis**: Inspecting screenshots via vision models for visual clipping and low contrast when configured.
- **Human-approved draft PR workflow**: Presenting reviewers with exact unified diffs and branch targets, strictly creating draft pull requests only after explicit reviewer approval.

### Honest Limitations
- **Prototype scope**: OmniSight is an internship prototype for responsive auditing and human-in-the-loop repair workflows; it never automatically heals, applies code to, or mutates the audited site.
- **Local-first focus**: Optimized for local development servers (`127.0.0.1` / `localhost`), not public cloud web crawling.
- **Zero-call default for AI**: When `OPENAI_API_KEY` is not provided, AI analysis reports `not_configured`. The deterministic audit and browser checks run 100% locally with zero external network dependencies.
- **Draft-only PRs & token requirement**: Without `GITHUB_TOKEN` set on the backend, reviewers can open and inspect the full diff preview, but cannot create a draft PR (the create button is safely disabled and the server reports `not_configured`). When configured, PRs are strictly created as GitHub **Drafts** (`draft: true`). The demo must stop at the preview and must not submit a PR.

---

## 2. Local Startup Steps (Before the Presentation)

Open two separate PowerShell terminal windows from the repository root:

### Terminal 1: Frontend Storefront & Dashboard
```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```
*Wait until Vite outputs: `Local: http://127.0.0.1:5173/`*

### Terminal 2: FastAPI Backend Server
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
*Wait for Uvicorn’s “Uvicorn running on http://127.0.0.1:8000” message before opening the dashboard.*

---

## 3. Quick Reference URLs

| Page / Resource | Local URL | Purpose |
| :--- | :--- | :--- |
| **OmniSight Dashboard** | `http://127.0.0.1:5173/audit` | Run audits, review screenshots, inspect findings |
| **Audit History & Compare** | `http://127.0.0.1:5173/audit/history` | Timeline of past runs and side-by-side delta analysis |
| **Broken Sample Page** | `http://127.0.0.1:5173/audit-fixture` | Intentional mobile table overflow test fixture |
| **Repaired Sample Page** | `http://127.0.0.1:5173/audit-fixture-fixed` | Corrected layout with CSS scroll wrapper applied |
| **Demo Storefront** | `http://127.0.0.1:5173/` | OmniStore sample e-commerce application |
| **FastAPI Swagger Docs** | `http://127.0.0.1:8000/docs` | Interactive backend API endpoints |

---

## 4. The 5-Minute Demo Walkthrough Script

### Minute 1: Introduction & Problem Statement (0:00 – 1:00)
1. Open browser to **`http://127.0.0.1:5173/audit`**.
2. **Talking points**:
   > *"Modern responsive web development often suffers from subtle layout breakage on mobile devices—such as unconstrained tables forcing horizontal scrolling across the whole screen. OmniSight is a prototype UI audit and human-reviewed repair workflow that pairs headless Playwright testing with deterministic rule engines, side-by-side run regression tracking, and reviewable repair suggestions—without automatically modifying or healing the target website."*
3. Briefly show the clean dark-mode dashboard interface and the sidebar links (**UI audits**, **Audit history**, and **Demo store**).

---

### Minute 2: Broken Sample Audit & Repair Proposal (1:00 – 2:15)
1. On the dashboard, click the shortcut button: **"Use broken sample"**.
   - Notice the URL input automatically fills: `http://127.0.0.1:5173/audit-fixture`.
2. Click **"Run audit"**.
3. Watch the progress status change from `queued` → `running` → `completed` (~3–4 seconds).
4. Review the results:
   - **Screenshot previews**: Desktop (1440px) shows a readable table; Mobile (390px) shows the table extending past screen bounds. Click *"Open image ↗"* to show the raw capture if desired.
   - **Finding Card**: Point out the finding:
     - **Issue**: `Horizontal overflow`
     - **Viewport**: `mobile (390×844)`
     - **Evidence**: `Content width 706px exceeds viewport 390px by 316px.`
   - **Repair Proposal**: Point out the reviewable CSS suggestion attached directly to the finding:
     ```css
     div.fixture-table-scroll {
       max-width: 100%;
       overflow-x: auto;
     }
     ```
   - Mention: *"OmniSight does not automatically edit user code. The proposal is review-only."*

---

### Minute 3: Repaired Sample Audit & Verification (2:15 – 3:15)
1. On the dashboard, click the shortcut button: **"Use repaired sample"**.
   - The URL input updates to: `http://127.0.0.1:5173/audit-fixture-fixed`.
2. Click **"Run audit"**.
3. Review the completed result:
   - **Status**: `Audit passed — 0 findings detected`.
   - **Mobile screenshot**: The table now scrolls cleanly within its card without overflowing the page width.
4. Optional: Click **"Download Markdown report"** to show the generated audit report with job metadata, evidence, and screenshot links.

---

### Minute 4: Audit History & Side-by-Side Comparison (3:15 – 4:00)
1. Click **"Audit history"** in the sidebar (or navigate to `http://127.0.0.1:5173/audit/history`).
2. Show the run timeline listing recent audit jobs with timestamps, URLs, and finding counts.
3. Select the checkboxes for both runs:
   - Select the **broken fixture run** (1 finding).
   - Select the **repaired fixture run** (0 findings).
4. Click **"Compare 2 runs (delta analysis) →"**.
5. Highlight the regression delta view:
   - **Summary banner**: *"1 finding(s) resolved between these runs."*
   - **Resolved tab (green)**: Shows `horizontal_overflow` marked as `Resolved` in Run B.
   - **Introduced tab**: Confirms 0 new defects introduced.
   - **Screenshots side-by-side**: Visual desktop and mobile comparisons between Run A and Run B.

---

### Minute 5: AI Analysis State & Human-Approved Draft PR (4:00 – 5:00)
1. Navigate back to `http://127.0.0.1:5173/audit` (or view the broken audit card).
2. **AI Analysis State**:
   - Point out the AI analysis card showing `Status: not_configured`.
   - Explain: *"When `OPENAI_API_KEY` is not set on the server, OmniSight executes zero external API calls, preserves data privacy, and runs 100% locally. If enabled, it analyzes the captured screenshots for visual clipping and color contrast."*
3. **GitHub Draft PR Review Modal**:
   - On the broken audit's repair proposal card, click **"Review GitHub Draft PR"**.
   - Show the review modal:
     - **Target Repository & Base Branch**: `jiayasjasu-del/omnisight-ai` on base branch `feature/visual-diff-report` (the backend's configured default; changes only if `GITHUB_BASE_BRANCH` is set in the environment).
     - **Proposed Branch**: `omnisight/repair-horizontal-overflow-...`
     - **Exact Unified Diff Viewer**: Highlight the color-coded unified diff showing the exact CSS change.
     - **Security Note**: Point out the banner: *"Human Approval Required: OmniSight will not auto-apply code. A draft pull request will be opened on GitHub for human code review. It will not be merged automatically."*
   - Emphasize: *"Without GITHUB_TOKEN set on the backend, I can show the diff preview but cannot create a draft PR. The demo must stop at the preview and must not submit a PR."*
   - Click **"✕"** or **"Reject Proposal"** to safely close the modal without creating a PR.
4. **Conclusion**:
   > *"OmniSight is a prototype for UI auditing and human-reviewed repairs that pairs automated browser captures with regression tracking and human-approved repair proposals—without ever altering the target site automatically."*

---

## 5. Troubleshooting & Port Recovery

### Issue: Port 8000 already in use
```powershell
# Identify process using port 8000
Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -Property OwningProcess

# Stop the process if needed (replace <PID> with process ID)
Stop-Process -Id <PID> -Force
```

### Issue: Port 5173 already in use
```powershell
Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | Select-Object -Property OwningProcess
Stop-Process -Id <PID> -Force
```

### Issue: Playwright browser missing
```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
```

### Issue: Running backend tests before demo
```powershell
# Full test suite (all 30 tests should pass)
.\.venv\Scripts\python.exe -m pytest -v
```
