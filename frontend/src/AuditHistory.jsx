import { useEffect, useState } from 'react'
import './AuditDashboard.css'
import './AuditHistory.css'

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

function formatTime(isoString) {
  if (!isoString) return '—'
  try {
    const date = new Date(isoString)
    return date.toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch { return isoString }
}

function extractPath(url) {
  try {
    const u = new URL(url)
    return u.pathname === '/' ? u.host : u.pathname
  } catch { return url }
}

export default function AuditHistory() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState([])
  const [comparison, setComparison] = useState(null)
  const [comparing, setComparing] = useState(false)
  const [error, setError] = useState('')

  async function fetchJobs() {
    setLoading(true)
    try {
      const data = await readJson(await fetch(`${API}/jobs`))
      setJobs(data.jobs || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    document.title = 'OmniSight | Audit history'
    let ignore = false

    fetch(`${API}/jobs`)
      .then(res => res.json())
      .then(data => {
        if (!ignore) {
          setJobs(data.jobs || [])
          setLoading(false)
        }
      })
      .catch(err => {
        if (!ignore) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => {
      ignore = true
    }
  }, [])

  function toggleSelection(jobId) {
    setSelected(prev => {
      if (prev.includes(jobId)) return prev.filter(id => id !== jobId)
      if (prev.length >= 2) return [prev[1], jobId]
      return [...prev, jobId]
    })
    setComparison(null)
  }

  async function runComparison() {
    if (selected.length !== 2) return
    setComparing(true)
    setError('')
    setComparison(null)
    try {
      const data = await readJson(await fetch(`${API}/jobs/compare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_a: selected[0], job_b: selected[1] }),
      }))
      setComparison(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setComparing(false)
    }
  }

  function clearSelection() {
    setSelected([])
    setComparison(null)
  }

  return (
    <div className="audit-app">
      <aside className="audit-sidebar">
        <a className="audit-brand" href="/audit" aria-label="OmniSight audit home">
          <Mark>O</Mark><span>omni<span>sight</span></span>
        </a>
        <p className="sidebar-label">WORKSPACE</p>
        <a className="sidebar-link" href="/audit"><span>◫</span> UI audits</a>
        <a className="sidebar-link active" href="/audit/history"><span>⧗</span> Audit history</a>
        <a className="sidebar-link" href="/"><span>↗</span> Open demo store</a>
        <div className="sidebar-note">
          <span className="note-icon">✦</span>
          <strong>Regression tracking</strong>
          <p>Compare two audits to see what improved or regressed.</p>
        </div>
        <div className="sidebar-user"><span className="user-avatar">OS</span><span><strong>OmniSight</strong><small>Local workspace</small></span></div>
      </aside>

      <main className="audit-main">
        <header className="audit-topbar">
          <span>Workspace <b>/</b> Audit history</span>
          <a href="/audit" className="back-link">← Back to audits</a>
        </header>

        <div className="audit-content history-content">
          <div className="history-intro">
            <div>
              <p className="page-kicker">REGRESSION TRACKING</p>
              <h1>Audit history</h1>
              <p className="page-description">Browse past audit runs and compare two side-by-side to track regressions or verify fixes.</p>
            </div>
            <button className="compare-btn compare-btn-secondary" onClick={fetchJobs} disabled={loading} style={{ alignSelf: 'flex-start' }}>
              ↻ Refresh
            </button>
          </div>

          {loading && (
            <div className="history-loading">
              <span>Loading audit history</span><span className="loading-dots"></span>
            </div>
          )}

          {error && (
            <div className="audit-error" role="alert">
              <strong>Error</strong><span>{error}</span>
            </div>
          )}

          {!loading && jobs.length === 0 && (
            <div className="history-empty">
              <span className="empty-icon">⧗</span>
              <strong>No audits yet</strong>
              <p>Run your first audit from the dashboard to start building history.</p>
              <a href="/audit" className="run-audit-link">Open audit dashboard →</a>
            </div>
          )}

          {!loading && jobs.length > 0 && (
            <>
              {selected.length > 0 && (
                <div className="compare-toolbar">
                  <span className="compare-label">
                    <strong>{selected.length}</strong> of 2 selected for comparison
                  </span>
                  <div className="compare-actions">
                    <button className="compare-btn compare-btn-secondary" onClick={clearSelection}>
                      Clear
                    </button>
                    <button
                      className="compare-btn compare-btn-primary"
                      disabled={selected.length !== 2 || comparing}
                      onClick={runComparison}
                    >
                      {comparing ? 'Comparing…' : 'Compare selected →'}
                    </button>
                  </div>
                </div>
              )}

              <div className="job-timeline">
                {jobs.map(job => {
                  const isSelected = selected.includes(job.job_id)
                  return (
                    <div
                      key={job.job_id}
                      className={`job-row${isSelected ? ' selected' : ''}`}
                      onClick={() => toggleSelection(job.job_id)}
                    >
                      <input
                        type="checkbox"
                        className="job-row-checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelection(job.job_id)}
                        onClick={e => e.stopPropagation()}
                        aria-label={`Select job ${job.job_id.slice(0, 8)}`}
                      />
                      <div className="job-row-meta">
                        <span className="job-row-url">{extractPath(job.storefront_url)}</span>
                        <span className="job-row-time">
                          {formatTime(job.created_at)} — {job.job_id.slice(0, 8)}
                        </span>
                      </div>
                      <div className="job-row-tags">
                        <span className={`job-tag tag-status-${job.status}`}>{job.status}</span>
                        <span className={`job-tag ${job.finding_count === 0 ? 'tag-findings-0' : 'tag-findings-n'}`}>
                          {job.finding_count} finding{job.finding_count !== 1 ? 's' : ''}
                        </span>
                        {job.has_ai_analysis && <span className="job-tag tag-ai">AI</span>}
                      </div>
                      <div className="job-row-actions">
                        <a
                          className="job-action-btn"
                          href={`/audit?view=${job.job_id}`}
                          onClick={e => e.stopPropagation()}
                        >
                          View ↗
                        </a>
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}

          {comparison && (
            <div className="comparison-panel">
              <div className="comparison-header">
                <h2><span className="comp-icon">⧗</span> Comparison result</h2>
                <span className="comparison-summary">{comparison.summary}</span>
              </div>
              <div className="comparison-body">
                <div className="comp-stats-row">
                  <div className="comp-stat">
                    <span className="comp-stat-value stat-total">{comparison.findings_a_count}</span>
                    <span className="comp-stat-label">Run A findings</span>
                  </div>
                  <div className="comp-stat">
                    <span className="comp-stat-value stat-total">{comparison.findings_b_count}</span>
                    <span className="comp-stat-label">Run B findings</span>
                  </div>
                  <div className="comp-stat">
                    <span className="comp-stat-value stat-resolved">{comparison.resolved.length}</span>
                    <span className="comp-stat-label">Resolved</span>
                  </div>
                  <div className="comp-stat">
                    <span className="comp-stat-value stat-introduced">{comparison.introduced.length}</span>
                    <span className="comp-stat-label">Introduced</span>
                  </div>
                </div>

                {comparison.resolved.length > 0 && (
                  <div className="delta-section delta-resolved">
                    <p className="delta-section-title">✓ Resolved findings</p>
                    <div className="delta-list">
                      {comparison.resolved.map((d, i) => (
                        <div className="delta-item" key={`r-${i}`}>
                          <span className="delta-badge badge-resolved">Resolved</span>
                          <span className="delta-code">{d.code}</span>
                          <span className="delta-viewport">{d.viewport}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {comparison.introduced.length > 0 && (
                  <div className="delta-section delta-introduced">
                    <p className="delta-section-title">⚠ New findings</p>
                    <div className="delta-list">
                      {comparison.introduced.map((d, i) => (
                        <div className="delta-item" key={`i-${i}`}>
                          <span className="delta-badge badge-introduced">New</span>
                          <span className="delta-code">{d.code}</span>
                          <span className="delta-viewport">{d.viewport}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {comparison.unchanged.length > 0 && (
                  <div className="delta-section delta-unchanged">
                    <p className="delta-section-title">— Unchanged</p>
                    <div className="delta-list">
                      {comparison.unchanged.map((d, i) => (
                        <div className="delta-item" key={`u-${i}`}>
                          <span className="delta-badge badge-unchanged">Same</span>
                          <span className="delta-code">{d.code}</span>
                          <span className="delta-viewport">{d.viewport}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="comp-screenshots">
                  <div className="comp-screenshot-card">
                    <h4>Run A — {extractPath(comparison.job_a.storefront_url)}</h4>
                    <img
                      src={`${API}/jobs/${comparison.job_a.job_id}/screenshots/mobile`}
                      alt={`Mobile screenshot from audit ${comparison.job_a.job_id.slice(0, 8)}`}
                      onError={e => { e.target.style.display = 'none' }}
                    />
                  </div>
                  <div className="comp-screenshot-card">
                    <h4>Run B — {extractPath(comparison.job_b.storefront_url)}</h4>
                    <img
                      src={`${API}/jobs/${comparison.job_b.job_id}/screenshots/mobile`}
                      alt={`Mobile screenshot from audit ${comparison.job_b.job_id.slice(0, 8)}`}
                      onError={e => { e.target.style.display = 'none' }}
                    />
                  </div>
                </div>
              </div>
            </div>
          )}

          <footer className="audit-footer">OmniSight <span>·</span> Local UI quality workspace</footer>
        </div>
      </main>
    </div>
  )
}
