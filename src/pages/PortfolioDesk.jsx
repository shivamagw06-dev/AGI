import { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { getUiPortfolio } from '@/lib/uiApi';

function Card({ title, children }) {
  return (
    <article className="border border-[#dddddd] bg-white p-5">
      <h2 className="text-xs font-bold uppercase tracking-wide text-[#767676]">{title}</h2>
      <div className="mt-3 text-sm text-[#333333]">{children}</div>
    </article>
  );
}

export default function PortfolioDesk() {
  const [state, setState] = useState({ loading: true, data: null, error: null });

  useEffect(() => {
    let active = true;
    getUiPortfolio()
      .then((data) => active && setState({ loading: false, data, error: null }))
      .catch((error) => active && setState({ loading: false, data: null, error }));
    return () => {
      active = false;
    };
  }, []);

  const data = state.data;
  const book = Object.entries(data?.composite_book || {}).slice(0, 12);

  return (
    <div className="bg-white min-h-screen">
      <Helmet>
        <title>Portfolio Desk | AGI</title>
      </Helmet>
      <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-8">
        <p className="text-[11px] font-bold uppercase tracking-wider text-[#ff6600]">Model Portfolio</p>
        <h1 className="mt-2 text-3xl font-bold text-[#111111]">Portfolio Desk</h1>
        <p className="mt-2 text-sm text-[#767676]">
          Current book, risk, performance and attribution from the Investment Office — no engine names exposed.
        </p>

        {state.loading ? (
          <div className="mt-8 h-48 bg-[#eee] animate-pulse" />
        ) : state.error ? (
          <p className="mt-8 text-sm text-[#767676]">Portfolio intelligence temporarily unavailable.</p>
        ) : (
          <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card title="Current Portfolio">
              <pre className="text-xs whitespace-pre-wrap text-[#444] overflow-auto max-h-64">
                {JSON.stringify(data?.current_portfolio || {}, null, 2)}
              </pre>
            </Card>
            <Card title="Sector Allocation">
              <pre className="text-xs whitespace-pre-wrap text-[#444] overflow-auto max-h-64">
                {JSON.stringify(data?.sector_allocation || {}, null, 2)}
              </pre>
            </Card>
            <Card title="Risk">
              <pre className="text-xs whitespace-pre-wrap text-[#444] overflow-auto max-h-48">
                {JSON.stringify(data?.risk || {}, null, 2)}
              </pre>
            </Card>
            <Card title="Performance & Attribution">
              <p className="text-xs text-[#767676] mb-2">
                Confidence: {data?.confidence != null ? data.confidence : '—'}
              </p>
              <pre className="text-xs whitespace-pre-wrap text-[#444] overflow-auto max-h-48">
                {JSON.stringify({ performance: data?.performance, attribution: data?.attribution }, null, 2)}
              </pre>
            </Card>
            <Card title="Composite Book">
              {book.length === 0 ? (
                <p className="text-xs text-[#767676]">No composite opinions loaded yet.</p>
              ) : (
                <ul className="space-y-2">
                  {book.map(([ticker, opinion]) => (
                    <li key={ticker} className="flex items-center justify-between border-b border-[#eee] pb-2">
                      <Link to={`/research/stocks/${encodeURIComponent(ticker)}`} className="text-sm font-bold text-[#111] hover:text-[#ff6600]">
                        {ticker}
                      </Link>
                      <span className="text-xs text-[#767676]">
                        {opinion?.label || opinion?.side || '—'}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
            <Card title="Historical Portfolio">
              <p className="text-xs text-[#767676]">{(data?.historical_portfolio || []).length} snapshots</p>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
