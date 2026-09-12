import { useEffect, useMemo, useState } from 'react';
import { ArrowUpRight, BookOpen, Globe2, Layers3, ShieldCheck, WalletCards } from 'lucide-react';
import { getFounderPortfolioPublic } from '@/lib/founderPortfolio';
import './founderPortfolio.css';
import './founderPortfolioIntelligence.css';
import './founderPortfolioAttribution.css';

const TYPE_LABELS = {
  indian_stock: 'Indian stocks',
  us_stock: 'US stocks',
  mutual_fund: 'Mutual funds',
  etf: 'ETFs',
  cash: 'Cash',
};

function pct(value, digits = 1) {
  const n = Number(value);
  return Number.isFinite(n) ? `${n.toFixed(digits)}%` : '—';
}

function month(value) {
  if (!value) return '—';
  return new Date(`${value}T00:00:00`).toLocaleDateString('en-IN', {
    month: 'short',
    year: 'numeric',
  });
}

export default function FounderPortfolio() {
  const [data, setData] = useState({ settings: null, holdings: [], performance: [], attribution: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    getFounderPortfolioPublic()
      .then((result) => active && setData(result))
      .catch((err) => active && setError(err?.message || 'Portfolio disclosure is unavailable.'))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const allocations = useMemo(() => {
    const totals = data.holdings.reduce((acc, row) => {
      const key = row.asset_type || 'other';
      acc[key] = (acc[key] || 0) + Number(row.public_weight || 0);
      return acc;
    }, {});
    return Object.entries(totals)
      .map(([key, value]) => ({ key, label: TYPE_LABELS[key] || key, value }))
      .sort((a, b) => b.value - a.value);
  }, [data.holdings]);

  const settings = data.settings || {};
  const attributionDate = data.attribution[0]?.valuation_date;
  const latestAttribution = data.attribution.filter((row) => row.valuation_date === attributionDate);
  const publishedWeight = data.holdings.reduce((sum, row) => sum + Number(row.public_weight || 0), 0);
  const lastUpdated = settings.last_published_at
    ? new Date(settings.last_published_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
    : 'Not published yet';

  return (
    <main className="founder-portfolio">
      <section className="founder-hero">
        <div>
          <div className="founder-kicker">AGI DISCLOSED INVESTMENT BOOK</div>
          <h1>Founder&apos;s Portfolio</h1>
          <p>
            A transparent, multi-asset view of the founder&apos;s investment thinking across Indian
            equities, US equities, mutual funds and ETFs.
          </p>
        </div>
        <div className="founder-aside">
          <ShieldCheck size={22} />
          <div>
            <strong>Public weights only</strong>
            <span>Quantities and personal capital remain private.</span>
          </div>
        </div>
      </section>

      {loading ? <div className="founder-notice">Loading portfolio disclosure…</div> : null}
      {error ? <div className="founder-notice founder-error">{error}</div> : null}

      {!loading && !error && !data.holdings.length ? (
        <section className="founder-empty">
          <BookOpen size={30} />
          <h2>Disclosure is being prepared</h2>
          <p>The first holdings and launch benchmark will appear here after the founder publishes them.</p>
        </section>
      ) : null}

      {data.holdings.length ? (
        <>
          <section className="founder-stats">
            <article>
              <span>Published allocation</span>
              <strong>{pct(publishedWeight, 0)}</strong>
            </article>
            <article>
              <span>Time-weighted return</span>
              <strong className={Number(settings.twr_pct) >= 0 ? 'positive' : 'negative'}>
                {pct(settings.twr_pct ?? settings.portfolio_return_pct)}
              </strong>
            </article>
            <article>
              <span>{settings.benchmark || 'Blended benchmark'}</span>
              <strong>{pct(settings.benchmark_return_pct)}</strong>
            </article>
            <article>
              <span>Last disclosed</span>
              <strong className="date-value">{lastUpdated}</strong>
            </article>
          </section>

          <section className="founder-intelligence-grid">
            <article className="founder-panel performance-panel">
              <div className="panel-heading"><ArrowUpRight size={20} /><div><span>PERFORMANCE</span><h2>Growth of ₹100</h2></div></div>
              {data.performance.length > 1 ? (
                <div className="performance-lines">
                  {data.performance.map((row, index) => {
                    const width = Math.max(data.performance.length - 1, 1);
                    const p = Number(row.portfolio_index || 100);
                    const b = Number(row.benchmark_index || 100);
                    return <i key={row.snapshot_date} style={{ left: `${(index / width) * 100}%`, height: `${Math.max(4, Math.min(100, p - 70))}%` }} title={`${row.snapshot_date}: ${p.toFixed(2)}`}><b style={{ height: `${Math.max(3, Math.min(100, b - 70))}%` }} /></i>;
                  })}
                </div>
              ) : <p className="panel-empty">Performance history will build from the first verified daily snapshot.</p>}
              <div className="performance-legend"><span><i /> Portfolio</span><span><i /> Benchmark</span></div>
            </article>
            <article className="founder-panel risk-panel">
              <div className="panel-heading"><ShieldCheck size={20} /><div><span>RISK INTELLIGENCE</span><h2>Portfolio risk</h2></div></div>
              <dl>
                <div><dt>Annualised volatility</dt><dd>{pct(settings.volatility_pct)}</dd></div>
                <div><dt>Maximum drawdown</dt><dd>{pct(settings.max_drawdown_pct)}</dd></div>
                <div><dt>One-day VaR (95%)</dt><dd>{pct(settings.var_95_pct)}</dd></div>
                <div><dt>Portfolio beta</dt><dd>{settings.beta == null ? '—' : Number(settings.beta).toFixed(2)}</dd></div>
                <div><dt>Largest position</dt><dd>{pct(settings.largest_position_pct)}</dd></div>
                <div><dt>Top five concentration</dt><dd>{pct(settings.top_five_pct)}</dd></div>
                <div><dt>Money-weighted return</dt><dd>{pct(settings.xirr_pct)}</dd></div>
              </dl>
            </article>
          </section>

          <section className="founder-grid">
            <article className="founder-panel allocation-panel">
              <div className="panel-heading">
                <Layers3 size={20} />
                <div>
                  <span>ALLOCATION</span>
                  <h2>Portfolio architecture</h2>
                </div>
              </div>
              <div className="allocation-list">
                {allocations.map((row) => (
                  <div key={row.key} className="allocation-row">
                    <div><span>{row.label}</span><strong>{pct(row.value)}</strong></div>
                    <div className="allocation-track"><i style={{ width: `${Math.min(row.value, 100)}%` }} /></div>
                  </div>
                ))}
              </div>
            </article>

            <article className="founder-panel mandate-panel">
              <div className="panel-heading">
                <Globe2 size={20} />
                <div>
                  <span>MANDATE</span>
                  <h2>Global, long-term, evidence-led</h2>
                </div>
              </div>
              <p>
                Positions are disclosed as a record of the founder&apos;s investment decisions. The
                portfolio combines concentrated business ownership with diversified funds and ETFs.
              </p>
              <dl>
                <div><dt>Base currency</dt><dd>{settings.base_currency || 'INR'}</dd></div>
                <div><dt>Public launch</dt><dd>{month(settings.launch_date)}</dd></div>
                <div><dt>Disclosure timing</dt><dd>{settings.disclosure_delay || 'After market close'}</dd></div>
              </dl>
            </article>
          </section>

          <section className="founder-holdings">
            <div className="holdings-title">
              <div>
                <span>DISCLOSED HOLDINGS</span>
                <h2>Current portfolio</h2>
              </div>
              <WalletCards size={24} />
            </div>
            <div className="holdings-table-wrap">
              <table>
                <thead><tr><th>Holding</th><th>Asset class</th><th>Market</th><th>Last price</th><th>Weight</th><th>Return</th><th>Conviction</th><th>Status</th></tr></thead>
                <tbody>
                  {data.holdings.map((row) => (
                    <tr key={row.id}>
                      <td><strong>{row.asset_name}</strong><span>{row.symbol}</span></td>
                      <td>{TYPE_LABELS[row.asset_type] || row.asset_type}</td>
                      <td>{row.market || row.country || '—'}</td>
                      <td>{row.latest_price == null ? '—' : `${row.currency === 'USD' ? '$' : '₹'}${Number(row.latest_price).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`}<span>{row.price_source || ''}</span></td>
                      <td><strong>{pct(row.public_weight)}</strong></td>
                      <td className={Number(row.return_pct) >= 0 ? 'positive' : 'negative'}>{pct(row.return_pct)}</td>
                      <td>{row.conviction || '—'}</td>
                      <td><span className="status-pill">{row.status || 'Holding'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="founder-journal">
            <div className="holdings-title">
              <div><span>FOUNDER&apos;S JOURNAL</span><h2>Investment reasoning</h2></div>
              <BookOpen size={24} />
            </div>
            <div className="journal-grid">
              {data.holdings.filter((row) => row.thesis || row.change_note).map((row) => (
                <article key={row.id}>
                  <div><strong>{row.symbol}</strong><span>{row.conviction || 'Core'}</span></div>
                  <p>{row.thesis || row.change_note}</p>
                  <footer><span>Entered {month(row.entry_month)}</span><ArrowUpRight size={16} /></footer>
                </article>
              ))}
            </div>
          </section>

          {latestAttribution.length ? (
            <section className="founder-attribution founder-panel">
              <div className="holdings-title">
                <div><span>DAILY ATTRIBUTION</span><h2>What moved the portfolio</h2></div>
                <strong>{new Date(`${attributionDate}T00:00:00`).toLocaleDateString('en-IN', { dateStyle: 'medium' })}</strong>
              </div>
              <div className="attribution-grid">
                {latestAttribution.map((row) => (
                  <article key={`${row.symbol}-${row.asset_type}-${row.market}`}>
                    <div><strong>{row.symbol}</strong><span>{TYPE_LABELS[row.asset_type] || row.asset_type}</span></div>
                    <b className={Number(row.contribution_pct) >= 0 ? 'positive' : 'negative'}>{pct(row.contribution_pct, 2)}</b>
                    <dl><div><dt>Asset move</dt><dd>{pct(row.asset_contribution_pct, 2)}</dd></div><div><dt>FX move</dt><dd>{pct(row.fx_contribution_pct, 2)}</dd></div></dl>
                  </article>
                ))}
              </div>
            </section>
          ) : null}
        </>
      ) : null}

      <footer className="founder-disclaimer">
        This is a delayed disclosure of the founder&apos;s investment decisions for transparency and
        education. It is not investment advice, a recommendation, or a managed portfolio service.
      </footer>
    </main>
  );
}
