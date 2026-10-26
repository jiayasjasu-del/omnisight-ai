import { useEffect } from 'react'
import './AuditFixture.css'

export default function AuditFixture() {
  useEffect(() => {
    document.title = 'Audit practice page | OmniSight'
  }, [])

  return (
    <main className="fixture-page">
      <header className="fixture-header">
        <a className="fixture-brand" href="/audit">◉ <span>OmniSight</span></a>
        <span className="fixture-label">AUDIT PRACTICE PAGE</span>
      </header>

      <section className="fixture-intro">
        <span className="fixture-eyebrow">RESPONSIVE QA EXAMPLE</span>
        <h1>Weekly activity report</h1>
        <p>This separate sample page includes one intentional layout issue for the OmniSight audit to find.</p>
      </section>

      <section className="fixture-summary" aria-label="Weekly summary">
        <article><span>Sessions</span><strong>1,284</strong><small>↑ 8.2% this week</small></article>
        <article><span>Conversion</span><strong>4.8%</strong><small>↑ 0.6% this week</small></article>
        <article><span>Avg. order</span><strong>₹3,420</strong><small>↑ 2.1% this week</small></article>
      </section>

      <section className="fixture-table-card" aria-labelledby="fixture-table-title">
        <div className="fixture-table-heading">
          <div><h2 id="fixture-table-title">Recent activity</h2><p>Sample data for a responsive layout review.</p></div>
          <span className="fixture-intent-badge">Intentional mobile overflow</span>
        </div>
        <div className="fixture-table-scroll">
          <table className="fixture-data-table">
            <thead><tr><th>Page</th><th>Visitors</th><th>Conversions</th><th>Change</th></tr></thead>
            <tbody>
              <tr><td>Home</td><td>4,820</td><td>238</td><td className="fixture-positive">+12.4%</td></tr>
              <tr><td>Product details</td><td>3,160</td><td>192</td><td className="fixture-positive">+6.8%</td></tr>
              <tr><td>Search results</td><td>2,740</td><td>116</td><td className="fixture-negative">−1.3%</td></tr>
            </tbody>
          </table>
        </div>
        <p className="fixture-issue-note"><strong>Practice issue:</strong> this table is deliberately too wide for a phone screen. OmniSight should report horizontal overflow at the mobile viewport.</p>
      </section>

      <footer className="fixture-footer"><a href="/audit">← Return to OmniSight audit dashboard</a><span>Training fixture · No demo-store changes</span></footer>
    </main>
  )
}
