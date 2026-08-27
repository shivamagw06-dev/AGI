import { Link } from 'react-router-dom';
import { useMarketDataContext } from '@/contexts/MarketDataContext';
import { pickMarketStrip } from './helpers';

const PANELS = [
  { id: 'global', title: 'Global', meta: 'US futures, dollar, risk tone' },
  { id: 'india', title: 'India', meta: 'NIFTY, Bank Nifty, breadth' },
  { id: 'macro', title: 'Macro', meta: 'Growth, inflation, policy path' },
  { id: 'fx', title: 'FX', meta: 'INR, DXY, EM FX impulse' },
  { id: 'rates', title: 'Rates', meta: 'Policy rate, curve, liquidity' },
  { id: 'commodities', title: 'Commodities', meta: 'Brent, gold, industrial metals' },
  { id: 'calendar', title: 'Calendar', meta: 'Data prints and central banks' },
  { id: 'actions', title: 'Corporate Actions', meta: 'Dividends, buybacks, listings' },
];

export default function MarketsWorkspacePage() {
  const { intelligence, loading } = useMarketDataContext();
  const strip = pickMarketStrip(intelligence);

  return (
    <div>
      <h1 className="agi-greeting">Markets</h1>
      <p className="agi-lede">
        Morning dashboard for Global, India, Rates, FX, Commodities, Macro, Calendar, and Corporate Actions — with
        research links into Ask AGI and the Research workspace.
      </p>

      <section className="agi-section">
        <div className="agi-section-head">
          <h2>Live strip</h2>
          <Link to="/agi/ask?q=Summarise%20today%27s%20market">Ask AGI</Link>
        </div>
        <div className="agi-strip">
          {strip.map((m) => (
            <div key={m.label} className="agi-metric">
              <div className="agi-metric-label">{m.label}</div>
              <div className="agi-metric-value">{loading && m.value === '—' ? '…' : String(m.value)}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="agi-section">
        <div className="agi-section-head">
          <h2>Market boards</h2>
          <Link to="/agi/research">Research links</Link>
        </div>
        <ul className="agi-list">
          {PANELS.map((p) => (
            <li key={p.id}>
              <div>
                <div className="agi-list-title">{p.title}</div>
                <div className="agi-list-meta">{p.meta}</div>
              </div>
              <Link className="agi-chip" to={`/agi/ask?q=${encodeURIComponent(`Explain ${p.title} markets today`)}`}>
                Brief
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
