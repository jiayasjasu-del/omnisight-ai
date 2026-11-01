import { useEffect } from 'react'
import './AuditFixture.css'

export default function AuditImageFixture() {
  useEffect(() => {
    document.title = 'Image overflow practice page | OmniSight'
  }, [])

  return (
    <main className="fixture-page">
      <header className="fixture-header">
        <a className="fixture-brand" href="/audit">◉ <span>OmniSight</span></a>
        <span className="fixture-label">IMAGE AUDIT PRACTICE PAGE</span>
      </header>

      <section className="fixture-intro">
        <span className="fixture-eyebrow">RESPONSIVE QA EXAMPLE — IMAGE OVERFLOW</span>
        <h1>Product showcase banner</h1>
        <p>This separate sample page includes an unconstrained banner image to test OmniSight's image overflow detection and isolated repair proposal.</p>
      </section>

      <section className="fixture-table-card" aria-labelledby="fixture-image-title">
        <div className="fixture-table-heading">
          <div><h2 id="fixture-image-title">Hero banner asset</h2><p>Sample unconstrained image for responsive layout review.</p></div>
          <span className="fixture-intent-badge">Intentional image overflow</span>
        </div>
        <div className="fixture-image-wrapper">
          <img
            src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1000' height='260' viewBox='0 0 1000 260'%3E%3Crect width='1000' height='260' fill='%230784c5' rx='8'/%3E%3Ctext x='500' y='140' fill='white' font-family='sans-serif' font-size='28' font-weight='bold' text-anchor='middle'%3EOmniStore 1000px Hero Banner%3C/text%3E%3C/svg%3E"
            alt="Wide promo banner asset"
            width="1000"
            height="260"
            style={{ width: '1000px', display: 'block' }}
          />
        </div>
        <p className="fixture-issue-note"><strong>Practice issue:</strong> this image is 1000px wide without a max-width constraint. OmniSight detects horizontal overflow on mobile viewports and generates an isolated repair proposal.</p>
      </section>

      <footer className="fixture-footer">
        <a href="/audit">← Return to OmniSight audit dashboard</a>
        <span>Training fixture · No demo-store changes</span>
      </footer>
    </main>
  )
}
