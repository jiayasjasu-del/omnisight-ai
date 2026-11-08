import { useEffect, useState } from 'react'
import './AuditDashboard.css'

const API = '/api'

async function readJson(response) {
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = typeof payload.detail === 'string' ? payload.detail : 'The request could not be completed.'
    throw new Error(detail)
  }
  return payload
}

function Mark({ children }) {
  return <span className="audit-mark" aria-hidden="true">{children}</span>
}

function StatusPill({ status }) {
  const label = status === 'running' ? 'Audit running' : status === 'queued' ? 'Waiting to start' : 'Ready to audit'
  return <span className={`audit-status audit-status-${status || 'idle'}`}><i />{label}</span>
}

function ScreenshotCard({ jobId, viewport, title, description, visualComparison }) {
  const comp = visualComparison?.[viewport]
  const hasDiff = Boolean(comp?.diff_path)
  const assessment = comp?.assessment
  const changedPct = comp?.changed_percentage

  return (
    <article className="screenshot-card">
      <div className="screenshot-heading">
        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <div className="screenshot-actions">
          {hasDiff && (
            <a href={`${API}/jobs/${jobId}/screenshots/diff-${viewport}`} target="_blank" rel="noreferrer" className="diff-link" aria-label={`Open ${title} visual diff in a new tab`}>
              Diff image ({changedPct}%) ↗
            </a>
          )}
          <a href={`${API}/jobs/${jobId}/screenshots/${viewport}`} target="_blank" rel="noreferrer" aria-label={`Open ${title} screenshot in a new tab`}>
            Open image ↗
          </a>
        </div>
      </div>
      <a className="screenshot-preview" href={`${API}/jobs/${jobId}/screenshots/${viewport}`} target="_blank" rel="noreferrer">
        <img src={`${API}/jobs/${jobId}/screenshots/${viewport}`} alt={`${title} screenshot of the audited website`} />
      </a>
      {comp && (
        <div className="screenshot-comp-footer">
          <span className={`comp-tag comp-${assessment || 'unknown'}`}>
            {assessment === 'baseline_created'
              ? 'Starting baseline created'
              : assessment === 'review_required'
                ? `Visual diff: ${changedPct}% change (review required)`
                : `Visual diff: ${changedPct}% (within threshold)`}
          </span>
        </div>
      )}
    </article>
  )
}

function downloadAuditReport(report) {
  const findings = report.findings || []
  const lines = [
    '# OmniSight UI Audit Report',
    '',
    `- **Job:** ${report.job_id}`,
    `- **Website:** ${report.storefront_url}`,
    `- **Status:** ${report.status}`,
    `- **Completed:** ${report.completed_at || 'Unknown'}`,
    '',
    '## Screenshots',
    '',
    `- [Desktop screenshot](${window.location.origin}${API}/jobs/${report.job_id}/screenshots/desktop)`,
    `- [Mobile screenshot](${window.location.origin}${API}/jobs/${report.job_id}/screenshots/mobile)`,
    '',
  ]

  if (report.visual_comparison && Object.keys(report.visual_comparison).length > 0) {
    lines.push('## Visual baseline comparison', '')
    for (const [vp, comp] of Object.entries(report.visual_comparison)) {
      const label = vp.charAt(0).toUpperCase() + vp.slice(1)
      if (comp.assessment === 'baseline_created') {
        lines.push(`- **${label}:** Starting baseline created`)
      } else {
        const diffLink = comp.diff_path ? ` ([view diff image](${window.location.origin}${API}/jobs/${report.job_id}/screenshots/diff-${vp}))` : ''
        lines.push(`- **${label}:** ${comp.changed_percentage}% pixel difference — assessment: \`${comp.assessment}\`${diffLink}`)
      }
    }
    lines.push('')
  }

  lines.push('## Findings', '')

  if (findings.length === 0) {
    lines.push('No issues were detected by the current rule-based checks.', '')
  } else {
    findings.forEach((finding, index) => {
      lines.push(
        `### ${index + 1}. ${finding.title || finding.code || 'UI finding'} (${finding.viewport || 'page'})`,
        '',
        finding.message || 'A browser check reported an item to review.',
        '',
        `**Evidence:** ${finding.evidence || 'No additional evidence.'}`,
        '',
      )
      if (finding.affected_elements?.length) {
        lines.push('**Affected elements:**', '')
        finding.affected_elements.forEach(element => {
          lines.push(`- \`${element.selector}\` — ${element.width}; overflow ${element.overflowBy}`)
        })
        lines.push('')
      }
      if (finding.suggestion) lines.push(`**Suggested next step:** ${finding.suggestion}`, '')
      if (finding.repair_proposal?.code) {
        lines.push(`**${finding.repair_proposal.title}:** ${finding.repair_proposal.explanation}`, '', '```css', finding.repair_proposal.code, '```', '')
      }
    })
  }

  if (report.ai_analysis) {
    const ai = report.ai_analysis
    if (ai.status === 'completed') {
      lines.push('## AI visual analysis (review suggestions only)', '')
      if (ai.summary) {
        lines.push('### Summary', '', ai.summary, '')
      }
      if (ai.issues?.length > 0) {
        lines.push('### Suggested visual issues to review', '')
        ai.issues.forEach((issue, idx) => {
          lines.push(
            `#### Suggestion ${idx + 1}: ${issue.title} (${issue.viewport || 'unknown'})`,
            `- **Priority:** ${issue.severity || 'medium'}`,
            `- **Confidence:** ${issue.confidence || 'medium'}`,
            `- **Observed evidence:** ${issue.evidence || 'N/A'}`,
            `- **Explanation:** ${issue.explanation || 'N/A'}`,
          )
          if (issue.suggested_fix) {
            lines.push(`- **Suggested fix (review-only):** \`${issue.suggested_fix}\``)
          }
          if (issue.verification_step) {
            lines.push(`- **Verification step:** ${issue.verification_step}`)
          }
          lines.push('')
        })
      }
      if (ai.recommended_next_steps?.length > 0) {
        lines.push('### Recommended next steps', '')
        ai.recommended_next_steps.forEach(step => lines.push(`- ${step}`))
        lines.push('')
      }
      lines.push(
        '> **Note:** AI suggestions are hypotheses for human review and are not confirmed defects.',
        '',
      )
    } else if (ai.status === 'not_configured') {
      lines.push('## AI visual analysis', '', 'Not configured (GEMINI_API_KEY environment variable not set). Browser checks ran normally.', '')
    } else if (ai.status === 'error') {
      lines.push('## AI visual analysis', '', `Unavailable: ${ai.message || 'Provider error'}`, '')
    }
  }
  lines.push('---', 'Generated by OmniSight. Review suggestions before changing the audited website.', '')

  const file = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(file)
  link.download = `omnisight-audit-${report.job_id.slice(0, 8)}.md`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(link.href)
}

export default function AuditDashboard() {
  const [siteUrl, setSiteUrl] = useState('http://127.0.0.1:5173')
  const [serviceStatus, setServiceStatus] = useState('checking')
  const [job, setJob] = useState(null)
  const [report, setReport] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [selfHealing, setSelfHealing] = useState({ loading: false, result: null, error: '' })
  const [repairPreview, setRepairPreview] = useState({ findingIndex: null, loading: false, result: null, error: '' })
  const [prReview, setPrReview] = useState({
    open: false,
    findingIndex: null,
    loading: false,
    preview: null,
    submitting: false,
    result: null,
    error: '',
  })

  useEffect(() => {
    let active = true
    document.title = 'OmniSight | Responsive UI audit'
    fetch(`${API}/health`)
      .then(readJson)
      .then(() => { if (active) setServiceStatus('online') })
      .catch(() => { if (active) setServiceStatus('offline') })
    return () => { active = false }
  }, [])

  async function openPrReview(findingIndex) {
    if (!report?.job_id) return
    setPrReview({
      open: true,
      findingIndex,
      loading: true,
      preview: null,
      submitting: false,
      result: null,
      error: '',
    })

    try {
      const data = await readJson(await fetch(`${API}/repairs/preview-pr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: report.job_id,
          finding_index: findingIndex,
        }),
      }))
      setPrReview(prev => ({ ...prev, loading: false, preview: data }))
    } catch (err) {
      setPrReview(prev => ({
        ...prev,
        loading: false,
        error: err.message || 'Could not load PR preview.',
      }))
    }
  }

  async function previewRepairInBrowser(findingIndex) {
    if (!report?.job_id) return
    setRepairPreview({ findingIndex, loading: true, result: null, error: '' })
    try {
      const result = await readJson(await fetch(`${API}/repairs/preview-fix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: report.job_id, finding_index: findingIndex }),
      }))
      setRepairPreview({ findingIndex, loading: false, result, error: '' })
    } catch (previewError) {
      setRepairPreview({
        findingIndex,
        loading: false,
        result: null,
        error: previewError.message || 'Could not verify the repair in an isolated browser.',
      })
    }
  }

  function closePrReview() {
    setPrReview({
      open: false,
      findingIndex: null,
      loading: false,
      preview: null,
      submitting: false,
      result: null,
      error: '',
    })
  }

  async function handleRejectProposal() {
    if (!report?.job_id || prReview.findingIndex === null) return
    try {
      const data = await readJson(await fetch(`${API}/repairs/create-pr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: report.job_id,
          finding_index: prReview.findingIndex,
          approved: false,
        }),
      }))
      setPrReview(prev => ({ ...prev, result: data }))
    } catch (err) {
      setPrReview(prev => ({
        ...prev,
        error: err.message || 'Failed to record rejection.',
      }))
    }
  }

  async function handleApproveCreatePr() {
    if (!report?.job_id || prReview.findingIndex === null || !prReview.preview) return
    setPrReview(prev => ({ ...prev, submitting: true, error: '' }))
    try {
      const data = await readJson(await fetch(`${API}/repairs/create-pr`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: report.job_id,
          finding_index: prReview.findingIndex,
          approved: true,
          repository: prReview.preview.repository,
          base_branch: prReview.preview.base_branch,
          proposed_branch: prReview.preview.proposed_branch,
          target_file: prReview.preview.target_file,
          pr_title: prReview.preview.title,
          pr_body: prReview.preview.description,
        }),
      }))
      setPrReview(prev => ({ ...prev, submitting: false, result: data }))
    } catch (err) {
      setPrReview(prev => ({
        ...prev,
        submitting: false,
        error: err.message || 'Failed to create pull request on GitHub.',
      }))
    }
  }


  async function handleRunSelfHealingDemo() {
    setSelfHealing({ loading: true, result: null, error: '' })
    try {
      const data = await readJson(await fetch(`${API}/repairs/self-healing-demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      }))
      setSelfHealing({ loading: false, result: data, error: '' })
    } catch (err) {
      setSelfHealing({
        loading: false,
        result: null,
        error: err.message || 'Failed to complete self-healing demonstration.',
      })
    }
  }

  async function runAudit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setReport(null)
    setJob(null)
    setRepairPreview({ findingIndex: null, loading: false, result: null, error: '' })

    try {
      const queued = await readJson(await fetch(`${API}/webhooks/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ storefront_url: siteUrl.trim() }),
      }))
      setJob({ job_id: queued.job_id, status: queued.status })

      for (let attempt = 0; attempt < 120; attempt += 1) {
        await new Promise(resolve => window.setTimeout(resolve, 1500))
        const current = await readJson(await fetch(`${API}/jobs/${queued.job_id}`))
        setJob(current)
        if (current.status === 'completed') {
          setReport(current)
          return
        }
        if (current.status === 'failed') {
          throw new Error(current.error || 'The audit failed. Try again after checking the backend terminal.')
        }
      }
      throw new Error('The audit is taking longer than expected. You can check its status in the API docs.')
    } catch (auditError) {
      setError(auditError.message)
    } finally {
      setBusy(false)
    }
  }

  const findings = report?.findings || []
  const ai = report?.ai_analysis || {}

  return (
    <div className="audit-app">
      <aside className="audit-sidebar">
        <a className="audit-brand" href="/audit" aria-label="OmniSight audit home">
          <Mark>O</Mark><span>omni<span>sight</span></span>
        </a>
        <p className="sidebar-label">WORKSPACE</p>
        <a className="sidebar-link active" href="/audit"><span>◫</span> UI audits</a>
        <a className="sidebar-link" href="/audit/history"><span>⧗</span> Audit history</a>
        <a className="sidebar-link" href="#self-healing"><span>⚡</span> Self-healing demo</a>
        <a className="sidebar-link" href="/"><span>↗</span> Open demo store</a>
        <div className="sidebar-note">
          <span className="note-icon">✦</span>
          <strong>Responsive checks</strong>
          <p>Review the same page at desktop and mobile sizes.</p>
        </div>
        <div className="sidebar-user"><span className="user-avatar">OS</span><span><strong>OmniSight</strong><small>Local workspace</small></span></div>
      </aside>

      <main className="audit-main">
        <header className="audit-topbar">
          <span>Workspace <b>/</b> UI audits</span>
          <span className={`connection-label connection-${serviceStatus}`}><i />{serviceStatus === 'online' ? 'Backend connected' : serviceStatus === 'offline' ? 'Backend offline' : 'Checking backend'}</span>
        </header>

        <div className="audit-content">
          <div className="page-intro">
            <div>
              <p className="page-kicker">QUALITY CHECK</p>
              <h1>Responsive UI audit</h1>
              <p className="page-description">Capture a website at desktop and mobile sizes, then review browser findings.</p>
            </div>
            <StatusPill status={busy ? (job?.status || 'queued') : report ? 'completed' : 'idle'} />
          </div>

          <section className="audit-form-card">
            <div className="form-card-title"><span className="form-icon">⌕</span><div><h2>Start a new audit</h2><p>Enter a local website address to inspect.</p></div></div>
            <form className="audit-form" onSubmit={runAudit}>
              <label htmlFor="site-url">Website address</label>
              <div className="url-row">
                <span className="url-prefix">↗</span>
                <input id="site-url" type="url" required value={siteUrl} onChange={event => setSiteUrl(event.target.value)} placeholder="http://127.0.0.1:5173" />
                <button type="submit" disabled={busy || serviceStatus === 'offline'}>{busy ? <><span className="button-spinner" /> Auditing…</> : <>Run audit <span>→</span></>}</button>
              </div>
              <p className="form-hint">The backend currently accepts local addresses such as localhost and 127.0.0.1.</p>
              <div className="sample-buttons">
                <button className="sample-target-button" type="button" onClick={() => setSiteUrl(`${window.location.origin}/audit-fixture`)}>
                  Use broken sample <span>↗</span>
                </button>
                <button className="sample-target-button" type="button" onClick={() => setSiteUrl(`${window.location.origin}/audit-image-fixture`)}>
                  Use image sample <span>↗</span>
                </button>
                <button className="sample-target-button sample-target-button--fixed" type="button" onClick={() => setSiteUrl(`${window.location.origin}/audit-fixture-fixed`)}>
                  Use repaired sample <span>↗</span>
                </button>
              </div>
            </form>
            {busy && <div className="progress-line"><span /></div>}
            {error && <div className="audit-error" role="alert"><strong>Audit needs attention</strong><span>{error}</span></div>}
          </section>

          <section id="self-healing" className="self-healing-card" aria-labelledby="self-healing-title">
            <div className="self-healing-header">
              <div className="self-healing-title-group">
                <span className="self-healing-icon">⚡</span>
                <div>
                  <h2 id="self-healing-title">Safe Self-Healing Demonstration</h2>
                  <p>Execute an isolated repair verification pipeline on the oversized image fixture with zero file modifications.</p>
                </div>
              </div>
              <button
                type="button"
                className="self-healing-btn"
                disabled={selfHealing.loading || serviceStatus === 'offline'}
                onClick={handleRunSelfHealingDemo}
                aria-busy={selfHealing.loading}
              >
                {selfHealing.loading ? (
                  <>
                    <span className="button-spinner" />
                    Running self-healing demo…
                  </>
                ) : (
                  <>
                    <span>▶</span> Run Self-Healing Demo
                  </>
                )}
              </button>
            </div>

            <div className="self-healing-intro">
              <p>
                Demonstrates safe self-healing using a temporary copy of <code>frontend/src/AuditImageFixture.jsx</code>.
                Applies the approved CSS allowlist repair rule (<code>img &#123; max-width: 100%; height: auto; &#125;</code>),
                compiles with Vite SSR, runs Playwright audits across desktop and mobile, and generates a unified diff for human review.
                <strong> Safety guarantee:</strong> The original fixture file is NEVER modified in place, and code is NEVER committed, pushed, or automatically PR'd.
              </p>
            </div>

            {selfHealing.loading && (
              <div className="self-healing-loading" aria-live="polite">
                <div className="working-spinner" />
                <div>
                  <strong>Executing safe self-healing pipeline…</strong>
                  <p>Validating CSS against strict allowlist → Creating temporary copy → Running Vite build verification → Running Playwright browser audits → Generating unified diff → Verifying fixture integrity.</p>
                </div>
              </div>
            )}

            {selfHealing.error && (
              <div className="audit-error self-healing-error" role="alert">
                <strong>Self-healing demonstration failed</strong>
                <span>{selfHealing.error}</span>
              </div>
            )}

            {selfHealing.result && (
              <div className="self-healing-results" aria-live="polite">
                <div className={`self-healing-status-banner status-${selfHealing.result.status}`}>
                  <div className="status-banner-main">
                    <span className="status-badge-icon">
                      {selfHealing.result.status === 'verified' ? '✓' : 'ℹ'}
                    </span>
                    <div>
                      <div className="status-banner-title">
                        <h3>Self-Healing Status: <span className="status-name">{selfHealing.result.status.toUpperCase()}</span></h3>
                        <span className="human-review-badge">Human Review Required</span>
                      </div>
                      <p>
                        {selfHealing.result.status === 'verified'
                          ? 'Safe self-healing verified cleanly. Temporary copy compiled with Vite, mobile overflow was resolved in Playwright, and original fixture file remained 100% untouched.'
                          : 'The self-healing pipeline completed with partial or rejected status. Inspect details below.'}
                      </p>
                    </div>
                  </div>
                  <div className="safety-guarantee-pills">
                    <span className="safety-pill">✓ Temporary-Copy Isolation</span>
                    <span className="safety-pill">✓ CSS Allowlist Enforced</span>
                    <span className="safety-pill">✓ Human Review Enforced</span>
                    <span className="safety-pill">✓ Zero Git Modifications</span>
                  </div>
                </div>

                <div className="self-healing-metrics-grid">
                  <div className="self-healing-subcard integrity-card">
                    <div className="subcard-header">
                      <span className="subcard-icon">🔒</span>
                      <h4>Original Fixture Integrity</h4>
                      <span className={`integrity-badge ${selfHealing.result.original_fixture_unmodified ? 'is-valid' : 'is-invalid'}`}>
                        {selfHealing.result.original_fixture_unmodified ? '✓ Unmodified & Intact' : '⚠ Modified'}
                      </span>
                    </div>
                    <div className="subcard-body">
                      <div className="metric-row">
                        <span className="metric-label">Target File:</span>
                        <code>{selfHealing.result.original_fixture_path?.split(/[/\\]/).slice(-3).join('/') || 'frontend/src/AuditImageFixture.jsx'}</code>
                      </div>
                      <div className="metric-row">
                        <span className="metric-label">SHA-256 Before:</span>
                        <code className="hash-code">{selfHealing.result.original_fixture_hash_before}</code>
                      </div>
                      <div className="metric-row">
                        <span className="metric-label">SHA-256 After:</span>
                        <code className="hash-code">{selfHealing.result.original_fixture_hash_after}</code>
                      </div>
                      <div className="integrity-check-note">
                        {selfHealing.result.original_fixture_unmodified ? (
                          <span className="integrity-pass">✓ Cryptographic hash matches exactly. Original file was never edited.</span>
                        ) : (
                          <span className="integrity-fail">⚠ Hash mismatch detected!</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="self-healing-subcard build-card">
                    <div className="subcard-header">
                      <span className="subcard-icon">⚙</span>
                      <h4>Frontend Build Outcome</h4>
                      <span className={`outcome-badge ${selfHealing.result.frontend_build?.verified ? 'is-valid' : 'is-invalid'}`}>
                        {selfHealing.result.frontend_build?.verified ? '✓ Build Verified' : '⚠ Build Failed'}
                      </span>
                    </div>
                    <div className="subcard-body">
                      <div className="metric-row">
                        <span className="metric-label">Compiler:</span>
                        <span>Vite SSR Build (Temporary Copy)</span>
                      </div>
                      <div className="metric-row">
                        <span className="metric-label">Exit Code:</span>
                        <code>{selfHealing.result.frontend_build?.returncode ?? 0}</code>
                      </div>
                      <div className="metric-row">
                        <span className="metric-label">Build Duration:</span>
                        <span>{selfHealing.result.frontend_build?.duration_ms} ms</span>
                      </div>
                      <div className="metric-row">
                        <span className="metric-label">Command:</span>
                        <code className="command-code">{selfHealing.result.frontend_build?.command || 'npx vite build --ssr ...'}</code>
                      </div>
                    </div>
                  </div>

                  <div className="self-healing-subcard audit-card">
                    <div className="subcard-header">
                      <span className="subcard-icon">👁</span>
                      <h4>Browser Audit Outcome</h4>
                      <span className={`outcome-badge ${selfHealing.result.browser_audit?.verified ? 'is-valid' : 'is-invalid'}`}>
                        {selfHealing.result.browser_audit?.verified ? '✓ Overflow Resolved' : '⚠ Incomplete'}
                      </span>
                    </div>
                    <div className="subcard-body">
                      <div className="metric-row">
                        <span className="metric-label">Audit Engine:</span>
                        <span>Playwright Chromium (Headless)</span>
                      </div>
                      <div className="metric-row">
                        <span className="metric-label">Before Repair:</span>
                        <span className="finding-flag">
                          {selfHealing.result.browser_audit?.findings_before?.length || 0} findings (overflow on mobile 390px)
                        </span>
                      </div>
                      <div className="metric-row">
                        <span className="metric-label">After Repair:</span>
                        <span className="finding-resolved">
                          {selfHealing.result.browser_audit?.findings_after?.length || 0} findings (0 overflow detected)
                        </span>
                      </div>
                      <div className="metric-row">
                        <span className="metric-label">CSS Allowlist:</span>
                        <span className="css-allowlist-tag">✓ Approved Allowlisted CSS</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="self-healing-css-box">
                  <div className="css-box-header">
                    <strong>Approved CSS Repair Rule Applied to Temporary Copy:</strong>
                    <span className="css-allowlist-pill">✓ CSS Allowlist Verified</span>
                  </div>
                  <pre><code>{selfHealing.result.repair_css}</code></pre>
                </div>

                {selfHealing.result.unified_diff && (
                  <div className="self-healing-diff-viewer">
                    <div className="diff-header">
                      <span>Generated Unified Diff for Human Review:</span>
                      <span className="diff-file-tag">frontend/src/AuditImageFixture.jsx</span>
                    </div>
                    <pre className="diff-code-block">
                      <code>
                        {selfHealing.result.unified_diff.split('\n').map((line, lIdx) => {
                          const isAdd = line.startsWith('+') && !line.startsWith('+++')
                          const isDel = line.startsWith('-') && !line.startsWith('---')
                          const isHunk = line.startsWith('@@')
                          const className = isAdd ? 'diff-line-add' : isDel ? 'diff-line-del' : isHunk ? 'diff-line-hunk' : 'diff-line'
                          return <div key={`sh-diff-${lIdx}`} className={className}>{line || ' '}</div>
                        })}
                      </code>
                    </pre>
                    <div className="diff-review-footer">
                      <span>ℹ Human Review Requirement: This diff demonstrates the exact patch tested on the temporary copy. No branch was created and no PR was submitted.</span>
                    </div>
                  </div>
                )}

                <div className="self-healing-screenshots-section">
                  <div className="section-heading">
                    <div>
                      <h4>Before &amp; After Audit Screenshots</h4>
                      <p>Compare the visual appearance between unconstrained fixture and repaired fixture.</p>
                    </div>
                  </div>

                  <div className="self-healing-screenshot-grid">
                    <div className="sh-screenshot-item">
                      <div className="sh-screenshot-header">
                        <span className="sh-tag sh-tag-before">Before Repair</span>
                        <h5>Desktop (1440 × 1000)</h5>
                        <a
                          href={`${API}/repairs/self-healing-demo/screenshots/before/desktop`}
                          target="_blank"
                          rel="noreferrer"
                          className="sh-shot-link"
                        >
                          Open image ↗
                        </a>
                      </div>
                      <a
                        href={`${API}/repairs/self-healing-demo/screenshots/before/desktop`}
                        target="_blank"
                        rel="noreferrer"
                        className="sh-screenshot-img-wrap"
                      >
                        <img
                          src={`${API}/repairs/self-healing-demo/screenshots/before/desktop`}
                          alt="Desktop view before repair with unconstrained image"
                          loading="lazy"
                        />
                      </a>
                    </div>

                    <div className="sh-screenshot-item">
                      <div className="sh-screenshot-header">
                        <span className="sh-tag sh-tag-after">After Repair</span>
                        <h5>Desktop (1440 × 1000)</h5>
                        <a
                          href={`${API}/repairs/self-healing-demo/screenshots/after/desktop`}
                          target="_blank"
                          rel="noreferrer"
                          className="sh-shot-link"
                        >
                          Open image ↗
                        </a>
                      </div>
                      <a
                        href={`${API}/repairs/self-healing-demo/screenshots/after/desktop`}
                        target="_blank"
                        rel="noreferrer"
                        className="sh-screenshot-img-wrap"
                      >
                        <img
                          src={`${API}/repairs/self-healing-demo/screenshots/after/desktop`}
                          alt="Desktop view after repair with constrained image"
                          loading="lazy"
                        />
                      </a>
                    </div>

                    <div className="sh-screenshot-item">
                      <div className="sh-screenshot-header">
                        <span className="sh-tag sh-tag-before">Before Repair</span>
                        <h5>Mobile (390 × 844) — Overflow</h5>
                        <a
                          href={`${API}/repairs/self-healing-demo/screenshots/before/mobile`}
                          target="_blank"
                          rel="noreferrer"
                          className="sh-shot-link"
                        >
                          Open image ↗
                        </a>
                      </div>
                      <a
                        href={`${API}/repairs/self-healing-demo/screenshots/before/mobile`}
                        target="_blank"
                        rel="noreferrer"
                        className="sh-screenshot-img-wrap"
                      >
                        <img
                          src={`${API}/repairs/self-healing-demo/screenshots/before/mobile`}
                          alt="Mobile view before repair showing horizontal overflow"
                          loading="lazy"
                        />
                      </a>
                    </div>

                    <div className="sh-screenshot-item">
                      <div className="sh-screenshot-header">
                        <span className="sh-tag sh-tag-after">After Repair</span>
                        <h5>Mobile (390 × 844) — Repaired</h5>
                        <a
                          href={`${API}/repairs/self-healing-demo/screenshots/after/mobile`}
                          target="_blank"
                          rel="noreferrer"
                          className="sh-shot-link"
                        >
                          Open image ↗
                        </a>
                      </div>
                      <a
                        href={`${API}/repairs/self-healing-demo/screenshots/after/mobile`}
                        target="_blank"
                        rel="noreferrer"
                        className="sh-screenshot-img-wrap"
                      >
                        <img
                          src={`${API}/repairs/self-healing-demo/screenshots/after/mobile`}
                          alt="Mobile view after repair showing resolved horizontal overflow"
                          loading="lazy"
                        />
                      </a>
                    </div>
                  </div>
                </div>

                {selfHealing.result.explanations?.length > 0 && (
                  <div className="self-healing-explanations">
                    <div className="explanations-header">
                      <span className="info-icon">ℹ</span>
                      <strong>Pipeline Verification Details &amp; Technical Nuances:</strong>
                    </div>
                    <ul>
                      {selfHealing.result.explanations.map((exp, eIdx) => (
                        <li key={`exp-${eIdx}`}>{exp}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </section>

          {!report && !busy && (
            <section className="welcome-card">
              <div className="welcome-art"><div className="art-window"><span /><span /><span /><div className="art-bars"><i /><i /><i /><i /></div></div><div className="art-phone"><span /><i /><i /><i /></div><div className="art-check">✓</div></div>
              <div><p className="page-kicker">YOUR NEXT STEP</p><h2>One audit. Two screen sizes.</h2><p>Run an audit to capture the page and see any browser-detected layout or accessibility checks here.</p><div className="welcome-points"><span>Desktop screenshot</span><span>Mobile screenshot</span><span>Findings and suggestions</span></div></div>
            </section>
          )}

          {busy && <section className="working-card" aria-live="polite"><div className="working-spinner" /><div><strong>Your audit is running</strong><p>Opening the page and capturing desktop and mobile screenshots. This usually takes a few seconds.</p></div></section>}

          {report && (
            <>
              <section className="result-banner">
                <div className="result-icon">✓</div>
                <div><p className="page-kicker">AUDIT COMPLETE</p><h2>{findings.length === 0 ? 'No automatic issues found' : `${findings.length} finding${findings.length === 1 ? '' : 's'} to review`}</h2><p>{ai.summary || `The browser checks completed for ${report.storefront_url}. Review both screenshots below.`}</p></div>
                <button className="download-report-button" type="button" onClick={() => downloadAuditReport(report)}>Download report ↓</button>
              </section>

              <div className="section-heading"><div><h2>Screen captures</h2><p>Compare how the page appears at each viewport.</p></div><span className="job-chip">Job {report.job_id.slice(0, 8)}</span></div>
              <div className="screenshot-grid">
                <ScreenshotCard jobId={report.job_id} viewport="desktop" title="Desktop" description="1440 × 1000 viewport" visualComparison={report.visual_comparison} />
                <ScreenshotCard jobId={report.job_id} viewport="mobile" title="Mobile" description="390 × 844 viewport" visualComparison={report.visual_comparison} />
              </div>

              <section className="findings-card">
                <div className="section-heading"><div><h2>Deterministic findings</h2><p>Rule-based browser checks (DOM measurements, overflow, images, accessibility labels).</p></div><span className={`finding-count ${findings.length ? 'has-findings' : ''}`}>{findings.length} found</span></div>
                {findings.length === 0 ? <div className="empty-findings"><span>✓</span><div><strong>All checked items look good</strong><p>No overflow, image-loading, or basic labeling issues were detected in this run.</p></div></div> : <div className="finding-list">{findings.map((finding, index) => <article className="finding-item" key={`${finding.code || 'finding'}-${index}`}><span className="finding-number">{String(index + 1).padStart(2, '0')}</span><div><h3>{finding.title || finding.code || 'UI finding'}</h3><p>{finding.evidence || finding.message || 'The browser reported an item to review.'}</p>{finding.affected_elements?.length > 0 && <div className="affected-elements"><strong>Elements to inspect</strong>{finding.affected_elements.map((element, elementIndex) => <code key={`${element.selector}-${elementIndex}`}>{element.selector} · {element.width}{element.overflowBy !== '0px' ? ` · ${element.overflowBy} wider than container` : ''}</code>)}</div>}{finding.suggestion && <small>Suggested fix: {finding.suggestion}</small>}{finding.repair_proposal && <div className="repair-proposal"><strong>{finding.repair_proposal.title}</strong><p>{finding.repair_proposal.explanation}</p><pre><code>{finding.repair_proposal.code}</code></pre><div className="proposal-actions"><button type="button" className="prepare-pr-button" onClick={() => previewRepairInBrowser(index)} disabled={repairPreview.loading}><span>✓</span> {repairPreview.loading && repairPreview.findingIndex === index ? 'Checking repair…' : 'Try fix in isolated browser'}</button><button type="button" className="prepare-pr-button" onClick={() => openPrReview(index)}><span>✦</span> Review & Prepare Draft PR ↗</button></div>{repairPreview.findingIndex === index && repairPreview.error && <div className="repair-preview-error" role="alert">{repairPreview.error}</div>}{repairPreview.findingIndex === index && repairPreview.result && <div className={`repair-preview-result repair-preview-${repairPreview.result.status}`}><strong>{repairPreview.result.status === 'verified' ? 'Repair verified in isolated browser' : repairPreview.result.status === 'not_reproduced' ? 'Issue not reproduced in the preview' : 'The issue remains after the preview'}</strong><p>{repairPreview.result.message} Original audit results and website files were not changed.</p><div className="repair-preview-images">{Object.keys(repairPreview.result.before_screenshots).map(viewport => <a key={`before-${viewport}`} href={`${API}/jobs/${report.job_id}/repair-preview-before/${viewport}`} target="_blank" rel="noreferrer">Open {viewport} before screenshot ↗</a>)}{Object.keys(repairPreview.result.screenshots).map(viewport => <a key={`after-${viewport}`} href={`${API}/jobs/${report.job_id}/repair-preview/${viewport}`} target="_blank" rel="noreferrer">Open {viewport} after screenshot ↗</a>)}</div></div>}</div>}</div><span className="viewport-tag">{finding.viewport || 'Page'}</span></article>)}</div>}
              </section>

              <section className="ai-analysis-card">
                <div className="section-heading">
                  <div>
                    <div className="ai-heading-title">
                      <span className="ai-badge-icon">✦</span>
                      <h2>AI visual suggestions</h2>
                      <span className="ai-disclaimer-pill">Review suggestions · Not confirmed defects</span>
                    </div>
                    <p>Optional multimodal vision analysis for clipped content, overlapping elements, and contrast.</p>
                  </div>
                  <span className={`ai-status-pill status-${ai.status || 'not_configured'}`}>
                    {ai.status === 'completed'
                      ? `${ai.issues?.length || 0} suggestion${ai.issues?.length === 1 ? '' : 's'}`
                      : ai.status === 'not_configured'
                        ? 'Not configured'
                        : ai.status === 'error'
                          ? 'Provider error'
                          : (ai.status || 'Inactive')}
                  </span>
                </div>

                {ai.status === 'completed' && (
                  <div className="ai-completed-content">
                    {ai.summary && (
                      <div className="ai-summary-block">
                        <strong>Visual summary:</strong>
                        <p>{ai.summary}</p>
                      </div>
                    )}

                    {ai.issues?.length > 0 ? (
                      <div className="ai-issues-list">
                        {ai.issues.map((issue, idx) => (
                          <article className="ai-issue-card" key={`ai-issue-${idx}`}>
                            <div className="ai-issue-header">
                              <span className="ai-issue-num">S{String(idx + 1).padStart(2, '0')}</span>
                              <div className="ai-issue-title-group">
                                <h3>{issue.title}</h3>
                                <div className="ai-issue-tags">
                                  <span className={`severity-tag severity-${issue.severity}`}>{issue.severity} priority</span>
                                  <span className="viewport-tag">{issue.viewport}</span>
                                  {issue.confidence && <span className="confidence-tag">confidence: {issue.confidence}</span>}
                                </div>
                              </div>
                            </div>
                            <div className="ai-issue-body">
                              <p><strong>Observed evidence:</strong> {issue.evidence}</p>
                              <p><strong>Explanation:</strong> {issue.explanation}</p>
                              {issue.suggested_fix && (
                                <div className="ai-fix-box">
                                  <strong>Suggested fix (review-only):</strong>
                                  <code>{issue.suggested_fix}</code>
                                </div>
                              )}
                              {issue.verification_step && (
                                <p className="ai-verify-step"><strong>Verification step:</strong> {issue.verification_step}</p>
                              )}
                            </div>
                          </article>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-ai-issues">
                        <span>✓</span>
                        <div>
                          <strong>No visual issues flagged by the vision model</strong>
                          <p>The vision model did not identify obvious clipped text, overlapping elements, or contrast problems in these captures.</p>
                        </div>
                      </div>
                    )}

                    {ai.recommended_next_steps?.length > 0 && (
                      <div className="ai-next-steps">
                        <strong>Recommended next steps:</strong>
                        <ul>
                          {ai.recommended_next_steps.map((step, sIdx) => <li key={`step-${sIdx}`}>{step}</li>)}
                        </ul>
                      </div>
                    )}

                    <p className="ai-card-disclaimer">
                      ℹ Note: AI visual analysis generates suggestions from screenshots and is not a deterministic check. Review all suggestions manually before applying changes.
                    </p>
                  </div>
                )}

                {ai.status === 'not_configured' && (
                  <div className="ai-empty-state">
                    <div className="ai-empty-icon">✦</div>
                    <div>
                      <strong>Vision analysis not configured</strong>
                      <p>Set the <code>GEMINI_API_KEY</code> environment variable in your backend terminal to enable optional screenshot-based vision analysis for clipped content, overlapping elements, and contrast issues.</p>
                      <small>The browser audit and rule-based checks above run completely offline without an API key.</small>
                    </div>
                  </div>
                )}

                {ai.status === 'skipped' && (
                  <div className="ai-empty-state">
                    <div className="ai-empty-icon">⤼</div>
                    <div>
                      <strong>Vision analysis skipped</strong>
                      <p>{ai.message || 'No audit screenshots were available for analysis.'}</p>
                    </div>
                  </div>
                )}

                {ai.status === 'error' && (
                  <div className="ai-empty-state ai-state-error">
                    <div className="ai-empty-icon">⚠</div>
                    <div>
                      <strong>Vision analysis unavailable</strong>
                      <p>{ai.message || 'The AI provider returned an error or could not be reached.'}</p>
                      {ai.detail && <p className="ai-error-detail"><code>{ai.detail}</code></p>}
                      <small>Deterministic browser checks and screenshot captures completed normally above.</small>
                    </div>
                  </div>
                )}
              </section>
            </>
          )}

          {prReview.open && (
            <div className="pr-review-backdrop" onClick={closePrReview}>
              <div className="pr-review-modal" onClick={e => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="pr-modal-title">
                <div className="pr-review-header">
                  <div className="pr-review-title">
                    <span className="pr-icon">✦</span>
                    <div>
                      <h3 id="pr-modal-title">Review Proposed GitHub Draft Pull Request</h3>
                      <p>Carefully inspect target branches and exact diff before approving.</p>
                    </div>
                  </div>
                  <button type="button" className="close-review-btn" onClick={closePrReview} aria-label="Close review">✕</button>
                </div>

                {prReview.loading && (
                  <div className="pr-loading-state">
                    <span className="button-spinner" /> Generating unified diff and inspecting branch targets…
                  </div>
                )}

                {prReview.error && !prReview.preview && (
                  <div className="pr-error-box">
                    <strong>Error loading preview:</strong>
                    <p>{prReview.error}</p>
                  </div>
                )}

                {prReview.preview && !prReview.result && (
                  <div className="pr-review-content">
                    <div className="pr-targets-grid">
                      <div className="pr-target-item">
                        <span className="target-label">Target Repository</span>
                        <code>{prReview.preview.repository}</code>
                      </div>
                      <div className="pr-target-item">
                        <span className="target-label">Base Branch</span>
                        <code>{prReview.preview.base_branch}</code>
                      </div>
                      <div className="pr-target-item">
                        <span className="target-label">Proposed New Branch</span>
                        <code>{prReview.preview.proposed_branch}</code>
                      </div>
                      <div className="pr-target-item">
                        <span className="target-label">Target File</span>
                        <code>{prReview.preview.target_file}</code>
                      </div>
                    </div>

                    <div className="pr-diff-viewer">
                      <div className="diff-header">
                        <span>Exact Unified Diff to Commit:</span>
                        <span className="diff-file-tag">{prReview.preview.target_file}</span>
                      </div>
                      <pre className="diff-code-block">
                        <code>
                          {prReview.preview.diff.split('\n').map((line, lIdx) => {
                            const isAdd = line.startsWith('+') && !line.startsWith('+++')
                            const isDel = line.startsWith('-') && !line.startsWith('---')
                            const isHunk = line.startsWith('@@')
                            const className = isAdd ? 'diff-line-add' : isDel ? 'diff-line-del' : isHunk ? 'diff-line-hunk' : 'diff-line'
                            return <div key={`diff-${lIdx}`} className={className}>{line || ' '}</div>
                          })}
                        </code>
                      </pre>
                    </div>

                    {!prReview.preview.github_configured && (
                      <div className="pr-warning-banner">
                        <strong>⚠ GitHub Token Not Configured</strong>
                        <p>The <code>GITHUB_TOKEN</code> environment variable is not set on the backend. You can review the diff and copy the CSS, but submitting a draft PR requires setting GITHUB_TOKEN on the server.</p>
                      </div>
                    )}

                    <div className="pr-notice-box">
                      <p><strong>Human Approval Required:</strong> OmniSight will not auto-apply code. A draft pull request will be opened on GitHub for human code review. It will not be merged automatically.</p>
                    </div>

                    {prReview.error && (
                      <div className="pr-error-box">
                        <strong>Error creating draft PR:</strong>
                        <p>{prReview.error}</p>
                      </div>
                    )}

                    <div className="pr-actions-row">
                      <button
                        type="button"
                        className="pr-reject-btn"
                        disabled={prReview.submitting}
                        onClick={handleRejectProposal}
                      >
                        ✕ Reject Proposal
                      </button>
                      <button
                        type="button"
                        className="pr-approve-btn"
                        disabled={!prReview.preview.github_configured || prReview.submitting}
                        onClick={handleApproveCreatePr}
                      >
                        {prReview.submitting ? (
                          <><span className="button-spinner" /> Creating Draft PR…</>
                        ) : (
                          <>✓ Approve & Create Draft PR ↗</>
                        )}
                      </button>
                    </div>
                  </div>
                )}

                {prReview.result && (
                  <div className={`pr-result-state pr-result-${prReview.result.status}`}>
                    {prReview.result.status === 'created' ? (
                      <div>
                        <div className="pr-result-badge">✓ DRAFT PR CREATED</div>
                        <h4>Draft Pull Request #{prReview.result.pr_number} Created</h4>
                        <p>Branch: <code>{prReview.result.branch}</code> on <code>{prReview.result.repository}</code></p>
                        <p className="pr-disclaimer">This PR is marked as a draft and requires your team's code review before merging.</p>
                        {prReview.result.pr_url && (
                          <a
                            className="pr-link-btn"
                            href={prReview.result.pr_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Open Draft PR on GitHub ↗
                          </a>
                        )}
                      </div>
                    ) : prReview.result.status === 'rejected' ? (
                      <div>
                        <div className="pr-result-badge pr-badge-rejected">✕ REJECTED</div>
                        <h4>Proposal Rejected</h4>
                        <p>{prReview.result.message}</p>
                      </div>
                    ) : (
                      <div>
                        <div className="pr-result-badge pr-badge-error">⚠ FAILED</div>
                        <h4>Could Not Create Draft PR</h4>
                        <p>{prReview.result.message}</p>
                        {prReview.result.detail && <p className="pr-error-detail"><code>{prReview.result.detail}</code></p>}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          <footer className="audit-footer">OmniSight <span>·</span> Local UI quality workspace</footer>
        </div>
      </main>
    </div>
  )
}
