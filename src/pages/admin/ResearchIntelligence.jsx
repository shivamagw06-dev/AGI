import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Search } from 'lucide-react';
import {
  getRieCompany,
  getRieCoverage,
  getRieDashboard,
  getRieHealth,
} from '@/lib/intelligenceApi';
import ResearchDossierPanel from '@/pages/admin/ResearchDossierPanel';
import './valuationPolicy.css';
import './researchIntelligence.css';

function fmt(n, d = 0) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
}

function Stat({ label, value }) {
  return (
    <div className="vp-stat">
      <span className="label">{label}</span>
      <span className="value">{value ?? '—'}</span>
    </div>
  );
}

export default function ResearchIntelligence() {
  const [health, setHealth] = useState(null);
  const [dash, setDash] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [symbol, setSymbol] = useState('INFY');
  const [lookup, setLookup] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [h, d, c] = await Promise.all([
        getRieHealth(),
        getRieDashboard(),
        getRieCoverage({ limit: 80 }),
      ]);
      setHealth(h);
      setDash(d);
      setCoverage(c);
      setError(null);
    } catch (err) {
      setError(err.message || 'rie_dashboard_failed');
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 20000);
    return () => clearInterval(id);
  }, [refresh]);

  const runLookup = async () => {
    const sym = String(symbol || '').trim().toUpperCase();
    if (!sym) return;
    setLoading(true);
    try {
      const pack = await getRieCompany(sym);
      setLookup(pack);
      setError(pack?.ok === false ? pack.error : null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const cov = coverage || dash?.coverage || {};
  const dist = cov.confidence_distribution || {};

  return (
    <div className="vp-page">
      <header className="vp-header">
        <Link to="/admin" className="vp-back"><ArrowLeft size={16} /> Admin</Link>
        <div>
          <div className="vp-eyebrow">Phase 8.4</div>
          <h1>Research Intelligence Engine</h1>
          <p className="vp-muted">
            Institutional research dossiers from warehouse + UVE / HVIE / VARIE / VPAE.
            Consumer only — no vendor calls, no BUY/SELL language.
          </p>
        </div>
        <button type="button" onClick={refresh}><RefreshCw size={14} /> Refresh</button>
      </header>

      {error ? <p className="hint">Error — {error}</p> : null}

      <section className="vp-stats">
        <Stat label="Engine" value={health?.version || '—'} />
        <Stat label="Universe" value={fmt(cov.universe)} />
        <Stat label="Analyzed" value={fmt(cov.companies_analyzed)} />
        <Stat label="Coverage" value={cov.coverage_pct != null ? `${fmt(cov.coverage_pct, 1)}%` : '—'} />
        <Stat label="High conf" value={fmt(dist.High)} />
        <Stat label="Medium conf" value={fmt(dist.Medium)} />
        <Stat label="Low conf" value={fmt(dist.Low)} />
        <Stat label="Runtime" value={dash?.runtime?.status || 'on_demand'} />
      </section>

      <section className="vp-card">
        <h2>Company research lookup</h2>
        <div className="vp-actions" style={{ justifyContent: 'flex-start' }}>
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="Symbol"
            aria-label="Symbol"
          />
          <button type="button" disabled={loading} onClick={runLookup}>
            <Search size={14} /> {loading ? 'Loading…' : 'Load dossier'}
          </button>
        </div>
        {lookup ? <ResearchDossierPanel symbol={lookup.symbol || symbol} /> : null}
      </section>

      <section className="vp-card">
        <h2>Recent dossier summaries</h2>
        <div className="vp-table-wrap">
          <table className="vp-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Confidence</th>
                <th>Score</th>
                <th>Coverage</th>
                <th>Status</th>
                <th>As of</th>
              </tr>
            </thead>
            <tbody>
              {(coverage?.rows || []).slice(0, 40).map((r) => (
                <tr key={`${r.symbol}-${r.as_of}`}>
                  <td>{r.symbol}</td>
                  <td>{r.research_confidence || '—'}</td>
                  <td>{fmt(r.score, 2)}</td>
                  <td>{fmt(r.coverage_pct, 1)}%</td>
                  <td>{r.status || '—'}</td>
                  <td>{r.as_of || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
