import { Link } from 'react-router-dom';
import { useMarketDataContext } from '@/contexts/MarketDataContext';
import { greetingForNow, pickMarketStrip } from './helpers';

const INTEL_TODAY = [
  { title: 'Macro Brief', meta: 'Rates, liquidity, and overnight policy signals', to: '/agi/markets' },
  { title: 'Overnight Events', meta: 'Global moves that matter for India open', to: '/agi/markets' },
  { title: 'Earnings Today', meta: 'Companies reporting — jump into workspace', to: '/agi/companies' },
  { title: 'Corporate Actions', meta: 'Dividends, buybacks, and capital events', to: '/agi/markets' },
];

const WATCHLIST = [
  { ticker: 'TCS', change: 'Research refresh due', tone: 'warn' },
  { ticker: 'KOTAKBANK', change: 'New evidence available', tone: 'ok' },
  { ticker: 'RELIANCE', change: 'Monitoring execution', tone: 'muted' },
];

const RESEARCH = [
  { title: 'Banking quality screen — deposit franchise focus', meta: 'Sector · Saved' },
  { title: 'IT services margins — what changed this quarter', meta: 'Company · Draft' },
  { title: 'RBI liquidity — portfolio implications', meta: 'Macro · Published' },
];

const ALERTS = [
  { title: 'Business quality shift detected', meta: 'Company intelligence' },
  { title: 'New filing ingested', meta: 'Evidence' },
  { title: 'Portfolio coverage gap', meta: 'Research queue' },
];

function deltaClass(direction, delta) {
  const d = String(direction || delta || '').toLowerCase();
  if (d.includes('up') || d.includes('bull') || d.startsWith('+')) return 'up';
  if (d.includes('down') || d.includes('bear') || d.startsWith('-')) return 'down';
  return '';
}

export default function DashboardPage() {
  const { intelligence, loading } = useMarketDataContext();
  const strip = pickMarketStrip(intelligence);
  const greeting = greetingForNow();

  return (
    <div>
      <h1 className="agi-greeting">{greeting}</h1>
      <p className="agi-lede">
        Your institutional command centre — markets, intelligence, watchlists, and research in one continuous
        workflow.
      </p>

      <section className="agi-section">
        <div className="agi-section-head">
          <h2>Global Markets</h2>
          <Link to="/agi/markets">Open Markets</Link>
        </div>
        <div className="agi-strip">
          {strip.map((m) => (
            <div key={m.label} className="agi-metric">
              <div className="agi-metric-label">{m.label}</div>
              <div className="agi-metric-value">
                {loading && m.value === '—' ? '…' : String(m.value)}
              </div>
              {m.delta !== '' && m.delta != null && (
                <div className={`agi-metric-delta ${deltaClass(m.direction, m.delta)}`}>
                  {String(m.delta)}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      <div className="agi-grid-2">
        <section className="agi-section">
          <div className="agi-section-head">
            <h2>Today&apos;s Intelligence</h2>
            <Link to="/agi/ask">Ask AGI</Link>
          </div>
          <ul className="agi-list">
            {INTEL_TODAY.map((item) => (
              <li key={item.title}>
                <Link to={item.to}>
                  <div className="agi-list-title">{item.title}</div>
                  <div className="agi-list-meta">{item.meta}</div>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <section className="agi-section">
          <div className="agi-section-head">
            <h2>Watchlist Changes</h2>
            <Link to="/agi/watchlists">Queue</Link>
          </div>
          <ul className="agi-list">
            {WATCHLIST.map((w) => (
              <li key={w.ticker}>
                <Link to={`/agi/companies/${w.ticker}`}>
                  <div className="agi-list-title">{w.ticker}</div>
                  <div className="agi-list-meta">{w.change}</div>
                </Link>
                <span className={`agi-chip ${w.tone}`}>{w.tone === 'ok' ? 'New' : w.tone === 'warn' ? 'Review' : 'Watch'}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="agi-grid-2">
        <section className="agi-section">
          <div className="agi-section-head">
            <h2>Portfolio Summary</h2>
            <Link to="/agi/portfolio">Workspace</Link>
          </div>
          <div className="agi-panel">
            <div className="agi-stat-row">
              <div className="agi-stat">
                <div className="agi-stat-label">Overall quality</div>
                <div className="agi-stat-value">—</div>
              </div>
              <div className="agi-stat">
                <div className="agi-stat-label">Research coverage</div>
                <div className="agi-stat-value">—</div>
              </div>
              <div className="agi-stat">
                <div className="agi-stat-label">Risk posture</div>
                <div className="agi-stat-value">Calm</div>
              </div>
              <div className="agi-stat">
                <div className="agi-stat-label">Ideas</div>
                <div className="agi-stat-value">3</div>
              </div>
            </div>
            <p className="agi-list-meta" style={{ marginTop: '0.85rem' }}>
              Think like a CIO — quality, exposure, coverage, and ideas. Holdings open into Company Workspace.
            </p>
          </div>
        </section>

        <section className="agi-section">
          <div className="agi-section-head">
            <h2>Research Feed</h2>
            <Link to="/agi/research">All notes</Link>
          </div>
          <ul className="agi-list">
            {RESEARCH.map((r) => (
              <li key={r.title}>
                <div>
                  <div className="agi-list-title">{r.title}</div>
                  <div className="agi-list-meta">{r.meta}</div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <section className="agi-section">
        <div className="agi-section-head">
          <h2>Alerts</h2>
          <Link to="/agi/alerts">Centre</Link>
        </div>
        <ul className="agi-list">
          {ALERTS.map((a) => (
            <li key={a.title}>
              <div>
                <div className="agi-list-title">{a.title}</div>
                <div className="agi-list-meta">{a.meta}</div>
              </div>
              <span className="agi-chip">Intel</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
