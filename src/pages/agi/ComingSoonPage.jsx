import { Link } from 'react-router-dom';

const COPY = {
  portfolio: {
    title: 'Portfolio',
    lede: 'Think like a CIO — overall quality, sector exposure, risk, research coverage, watchlist, and ideas. Each holding opens Company Workspace.',
  },
  markets: {
    title: 'Markets',
    lede: 'Morning dashboard for Global, India, Rates, FX, Commodities, Macro, News, Calendar, and Corporate Actions.',
  },
  research: {
    title: 'Research',
    lede: 'Institutional notes across Macro, Company, Sector, Portfolio, Thematic — with executive summary through appendix.',
  },
  watchlists: {
    title: 'Watchlists',
    lede: 'Research queues, not ticker lists — New, Reviewing, Monitoring, Completed, Archived.',
  },
  screeners: {
    title: 'Screeners',
    lede: 'Institutional screens — high ROCE, low debt, improving margins, rising quality, capital allocation.',
  },
  notebook: {
    title: 'Notebook',
    lede: 'Questions, research, evidence, companies, and portfolio — linked like Obsidian meets Bloomberg.',
  },
  alerts: {
    title: 'Alerts',
    lede: 'Intelligence alerts — quality shifts, execution, filings, conference calls, macro, portfolio impact.',
  },
  settings: {
    title: 'Settings',
    lede: 'Workspace preferences, coverage defaults, and notification posture.',
  },
};

export default function ComingSoonPage({ area = 'research' }) {
  const c = COPY[area] || COPY.research;
  return (
    <div>
      <h1 className="agi-greeting">{c.title}</h1>
      <p className="agi-lede">{c.lede}</p>
      <div className="agi-panel">
        <p className="agi-list-meta" style={{ marginBottom: '1rem' }}>
          Phase 2 ships Ask AGI, Company Workspace, and Dashboard first. This surface builds on those foundations.
        </p>
        <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
          <Link className="agi-btn agi-btn-primary" to="/agi/ask">
            Ask AGI
          </Link>
          <Link className="agi-btn" to="/agi/companies">
            Companies
          </Link>
          <Link className="agi-btn" to="/agi">
            Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
