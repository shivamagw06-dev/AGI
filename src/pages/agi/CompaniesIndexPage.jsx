import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

const FEATURED = [
  { ticker: 'TCS', name: 'Tata Consultancy Services', sector: 'IT Services' },
  { ticker: 'INFY', name: 'Infosys', sector: 'IT Services' },
  { ticker: 'HDFCBANK', name: 'HDFC Bank', sector: 'Banks' },
  { ticker: 'ICICIBANK', name: 'ICICI Bank', sector: 'Banks' },
  { ticker: 'KOTAKBANK', name: 'Kotak Mahindra Bank', sector: 'Banks' },
  { ticker: 'RELIANCE', name: 'Reliance Industries', sector: 'Energy' },
  { ticker: 'ASIANPAINT', name: 'Asian Paints', sector: 'Consumer' },
  { ticker: 'SUNPHARMA', name: 'Sun Pharmaceutical', sector: 'Pharma' },
];

export default function CompaniesIndexPage() {
  const [q, setQ] = useState('');
  const navigate = useNavigate();

  const open = (ticker) => {
    const t = String(ticker || '').trim().toUpperCase();
    if (!t) return;
    navigate(`/agi/companies/${encodeURIComponent(t)}`);
  };

  return (
    <div>
      <h1 className="agi-greeting">Companies</h1>
      <p className="agi-lede">
        Open any company into the research workspace — coverage, quality, financials, evidence, and timeline.
      </p>

      <form
        className="agi-search-bar"
        onSubmit={(e) => {
          e.preventDefault();
          open(q);
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ticker — e.g. TCS"
          aria-label="Company ticker"
        />
        <button type="submit" className="agi-btn agi-btn-primary">
          Open
        </button>
      </form>

      <section className="agi-section">
        <div className="agi-section-head">
          <h2>Coverage universe</h2>
        </div>
        <ul className="agi-list">
          {FEATURED.map((c) => (
            <li key={c.ticker}>
              <Link to={`/agi/companies/${c.ticker}`}>
                <div className="agi-list-title">
                  {c.ticker} · {c.name}
                </div>
                <div className="agi-list-meta">{c.sector}</div>
              </Link>
              <span className="agi-chip">Workspace</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
