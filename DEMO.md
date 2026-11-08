# OmniSight — 5-Minute Internship Review Demo Guide

This guide provides a structured, 5-minute walkthrough script and technical runbook for presenting OmniSight at the internship final review.

---

## 1. Project Purpose & Limitations

### Purpose
OmniSight is a **UI audit and human-reviewed repair workflow prototype** designed to bridge automated browser testing with human inspection and reviewable repair suggestions. It does not automatically heal, edit, or modify the audited target website. It automates:
- **Responsive capture**: Headless Playwright capture across standard desktop (1440×1000) and mobile (390×844) viewports.
- **Deterministic DOM audit**: Rule-based detection of horizontal overflow, broken images, unlabelled form controls, unnamed buttons, and console errors.
- **Repair suggestions and isolated verification**: Generating targeted CSS suggestions and trying the supported table and oversized image fixes in disposable Playwright pages, without editing target files.
- **Safe Self-Healing Demonstration**: End-to-end automated verification of an approved allowlisted CSS fix on a temporary copy of the oversized-image sample (`AuditImageFixture.jsx`), verified with Vite SSR compilation and Playwright audits across desktop/mobile viewports, displaying the unified diff and before/after screenshots for human review.
- **Visual regression tracking**: Side-by-side run comparisons classifying findings into resolved, introduced, and unchanged deltas.
- **Optional AI visual analysis**: Inspecting screenshots via vision models for visual clipping and low contrast when configured.
- **Human-approved draft PR workflow**: Presenting reviewers with exact unified diffs and branch targets, strictly creating draft pull requests only after explicit reviewer approval.

### Honest Limitations
- **Prototype scope**: OmniSight is an internship prototype for responsive auditing and human-reviewed repair workflows. Its supported CSS preview runs only in disposable browser pages; it does not change the audited site's source files or persistent state.
- **Local-first focus**: Optimized for local development servers (`127.0.0.1` / `localhost`), not public cloud web crawling.
- **Zero-call default for AI**: When neither `GEMINI_API_KEY` nor `OPENAI_API_KEY` is provided, AI analysis reports `not_configured`. The deterministic audit and browser checks run 100% locally with zero external AI network requests.
- **Draft-only PRs & token requirement**: Without `GITHUB_TOKEN` set on the backend, reviewers can open and inspect the full diff preview, but cannot create a draft PR (the create button is safely disabled and the server reports `not_configured`). When configured, PRs are strictly created as GitHub **Drafts** (`draft: true`). The demo must stop at the preview and must not submit a PR.
- **Self-healing demo scope**: The self-healing demonstration applies only an approved allowlisted CSS rule to a temporary copy of the oversized-image sample. The original fixture file remains cryptographically unchanged (verified via SHA-256 before/after hashes), human review is strictly required, and arbitrary websites are not automatically repaired.

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
| **Self-Healing Demo** | `http://127.0.0.1:5173/audit#self-healing` | Safe isolated repair verification on temporary copy |
| **Audit History & Compare** | `http://127.0.0.1:5173/audit/history` | Timeline of past runs and side-by-side delta analysis |
| **Broken Sample Page** | `http://127.0.0.1:5173/audit-fixture` | Intentional mobile table overflow test fixture |
| **Image Overflow Sample** | `http://127.0.0.1:5173/audit-image-fixture` | Intentional mobile image overflow test fixture |
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
   - Click **Try fix in isolated browser**. Show the verification result and preview screenshot; the original audit and target files remain unchanged.

---

### Minute 3: Repaired Sample Audit & Verification (2:15 – 3:15)
1. On the dashboard, click the shortcut button: **"Use repaired sample"**.
   - The URL input updates to: `http://127.0.0.1:5173/audit-fixture-fixed`.
2. Click **"Run audit"**.
3. Review the completed result:
   - **Status**: `Audit passed — 0 findings detected`.
   - **Mobile screenshot**: The table now scrolls cleanly within its card without overflowing the page width.
4. Optional: Click **"Download Markdown report"** to show the generated audit report with job metadata, evidence, and screenshot links.
   - The isolated repair preview above is a separate demonstration; it does not create another audit-history job.

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

### Minute 5: Safe Self-Healing Demo & Human-Approved Draft PR (4:00 – 5:00)
1. Navigate back to `http://127.0.0.1:5173/audit`.
2. **Safe Self-Healing Demonstration**:
   - Scroll to the **Safe Self-Healing Demonstration** card (or click **"⚡ Self-healing demo"** in the sidebar).
   - Click **"▶ Run Self-Healing Demo"**.
   - Observe the loading state while the backend executes the safe pipeline against an isolated temporary copy (`AuditImageFixture.temp.jsx`).
   - Walk through the verified result:
     - **Result Status**: `Self-Healing Status: VERIFIED` with the `Human Review Required` badge.
     - **Original Fixture Integrity**: Confirms `✓ Unmodified & Intact` with identical SHA-256 before/after hashes for `AuditImageFixture.jsx`.
     - **Build & Audit Outcomes**: Vite SSR build verified with exit code `0`; Playwright audit detected 1 mobile overflow finding before repair and 0 findings after repair.
     - **Unified Diff**: Displays the proposed unified diff for human inspection.
     - **Before & After Screenshots**: Direct links and thumbnails for Desktop and Mobile (served securely from `/repairs/self-healing-demo/screenshots/{phase}/{viewport}`).
   - Emphasize: *"The original fixture file is NEVER edited in place, code is NEVER committed, pushed, or PR'd, and arbitrary websites are not automatically repaired."*
3. **AI Analysis State**:
   - Point out the AI analysis card showing `Status: not_configured`.
   - Explain: *"When neither `GEMINI_API_KEY` nor `OPENAI_API_KEY` is set on the server, OmniSight makes zero external AI requests and runs its deterministic browser checks locally. If enabled, the selected vision model analyzes the captured screenshots for visual clipping and color contrast."*
4. **GitHub Draft PR Review Modal**:
   - On the broken audit's repair proposal card, click **"Review GitHub Draft PR"**.
   - Show the review modal:
     - **Target Repository & Base Branch**: `jiayasjasu-del/omnisight-ai` on base branch `feature/visual-diff-report` (the backend's configured default; changes only if `GITHUB_BASE_BRANCH` is set in the environment).
     - **Proposed Branch**: `omnisight/repair-horizontal-overflow-...`
     - **Exact Unified Diff Viewer**: Highlight the color-coded unified diff showing the exact CSS change.
     - **Security Note**: Point out the banner: *"Human Approval Required: OmniSight will not auto-apply code. A draft pull request will be opened on GitHub for human code review. It will not be merged automatically."*
   - Emphasize: *"Without GITHUB_TOKEN set on the backend, I can show the diff preview but cannot create a draft PR. The demo must stop at the preview and must not submit a PR."*
   - Click **"✕"** or **"Reject Proposal"** to safely close the modal without creating a PR.
5. **Conclusion**:
   > *"OmniSight is a prototype for UI auditing and human-reviewed repairs that pairs automated browser captures with regression tracking, safe isolated self-healing demonstrations, and human-approved repair proposals—without ever altering the target site automatically."*

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
# Full test suite (all 45 automated tests should pass)
.\.venv\Scripts\python.exe -m pytest -v
```
