import { useEffect } from 'react'
import './AuditFixture.css'
import './AuditFixtureFixed.css'

/**
 * /audit-fixture-fixed
 *
 * The same sample page as /audit-fixture, but with the repair proposal applied:
 *   .fixture-table-scroll { max-width: 100%; overflow-x: auto; }
 *
 * The table now scrolls inside its card on mobile instead of widening the page,
 * so an OmniSight audit of this route should find no horizontal overflow.
 * Compare with /audit-fixture to see the before/after difference.
 */
export default function AuditFixtureFixed() {
  useEffect(() => {
    document.title = 'Repaired sample page | OmniSight'
  }, [])

  return (
    <main className="fixture-page fixture-page--fixed">
      <header className="fixture-header">
        <a className="fixture-brand" href="/audit">◉ <span>OmniSight</span></a>
        <span className="fixture-label">REPAIRED SAMPLE PAGE</span>
      </header>

      <section className="fixture-intro">
        <span className="fixture-eyebrow">RESPONSIVE QA EXAMPLE — REPAIRED</span>
        <h1>Weekly activity report</h1>
        <p>
          This is the repaired version of the audit practice page. The CSS repair
          proposal has been applied so the table scrolls inside its card on mobile
          instead of overflowing the page.
        </p>
        <div className="fixture-fixed-header-bar">
          <strong>Repair applied:</strong>
          <code>.fixture-table-scroll &#123; max-width: 100%; overflow-x: auto; &#125;</code>
          &nbsp;·&nbsp;
          <a href="/audit-fixture">View broken version →</a>
        </div>
      </section>

      <section className="fixture-summary" aria-label="Weekly summary">
        <article><span>Sessions</span><strong>1,284</strong><small>↑ 8.2% this week</small></article>
        <article><span>Conversion</span><strong>4.8%</strong><small>↑ 0.6% this week</small></article>
        <article><span>Avg. order</span><strong>₹3,420</strong><small>↑ 2.1% this week</small></article>
      </section>

      <section className="fixture-table-card" aria-labelledby="fixture-table-title">
        <div className="fixture-table-heading">
          <div><h2 id="fixture-table-title">Recent activity</h2><p>Sample data for a responsive layout review.</p></div>
          <span className="fixture-fixed-badge">Overflow fixed</span>
        </div>
        {/* .fixture-table-scroll now has max-width:100%; overflow-x:auto via AuditFixtureFixed.css */}
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
        <p className="fixture-issue-note">
          <strong>Repair verified:</strong> the table scrolls horizontally inside this card. The page itself
          should have no horizontal overflow at any viewport width.
        </p>
      </section>

      <footer className="fixture-footer">
        <a href="/audit">← Return to OmniSight audit dashboard</a>
        <span>
          <a href="/audit-fixture">View broken version</a>
          &nbsp;·&nbsp;Repaired sample · No demo-store changes
        </span>
      </footer>
    </main>
  )
}
