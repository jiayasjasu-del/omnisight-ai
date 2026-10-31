import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './App.css'
import App from './App.jsx'
import AuditDashboard from './AuditDashboard.jsx'
import AuditFixture from './AuditFixture.jsx'
import AuditFixtureFixed from './AuditFixtureFixed.jsx'
import AuditHistory from './AuditHistory.jsx'

const currentPage = window.location.pathname.replace(/\/$/, '')
const Page = currentPage === '/audit'
  ? AuditDashboard
  : currentPage === '/audit-fixture'
    ? AuditFixture
    : currentPage === '/audit-fixture-fixed'
      ? AuditFixtureFixed
      : currentPage === '/audit/history'
        ? AuditHistory
        : App

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Page />
  </StrictMode>,
)

