import { Link } from 'react-router-dom';

export default function PeFirmRankings({ firms = [] }) {
  return (
    <aside className="pe-col-rank">
      <div className="pe-glass p-4 sticky top-[72px]">
        <h2 className="pe-title text-base mb-1">Top Global Private Equity Firms</h2>
        <p className="text-xs text-[var(--pe-text-muted)] mb-4">By assets under management</p>
        {firms.map((firm, i) => (
          <Link
            key={firm.slug}
            to={`/private-equity/firms/${firm.slug}`}
            className="pe-glass pe-firm-card"
          >
            <span className="text-xs pe-gold font-bold w-5">{i + 1}</span>
            <img src={firm.logo} alt="" className="pe-firm-logo" />
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold truncate">{firm.name}</div>
              <div className="text-xs text-[var(--pe-text-muted)]">{firm.aum}</div>
            </div>
          </Link>
        ))}
      </div>
    </aside>
  );
}
