import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Search } from 'lucide-react';
import {
  getValuationPolicyHealth,
  getValuationPolicyUniverse,
  getValuationApplicability,
} from '@/lib/intelligenceApi';
import './valuationPolicy.css';

function pillClass(status) {
  const s = String(status || '').toUpperCase();
  if (['VALID', 'BANKING_MODEL', 'NBFC_MODEL', 'INSURANCE_MODEL', 'OK'].includes(s)) return 'ok';
  if (['LOSS_MAKING', 'EXTREME_VALUATION', 'ETF', 'REIT', 'INVIT', 'WARN'].includes(s)) return 'warn';
  if (['INSUFFICIENT_DATA', 'NOT_APPLICABLE', 'FAIL', 'UNDER_REVIEW'].includes(s)) return 'bad';
  return '';
}

function Stat({ label, value, hint }) {
  return (
    <div className="vp-stat">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      {hint ? <span className="vp-muted" style={{ fontSize: '0.75rem' }}>{hint}</span> : null}
    </div>
  );
}

export default function ValuationPolicy() {
  const [health, setHealth] = useState(null);
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [detail, setDetail] = useState(null);
  const [filters, setFilters] = useState({
    sector: '',
    instrument_type: '',
    primary_model: '',
    status: '',
    confidence: '',
    symbol: '',
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = {
        limit: 150,
        offset: 0,
      };
      for (const key of ['sector', 'instrument_type', 'primary_model', 'status', 'confidence']) {
        if (filters[key]) params[key] = filters[key];
      }
      const [h, u] = await Promise.all([
        getValuationPolicyHealth(),
        getValuationPolicyUniverse(params),
      ]);
      setHealth(h);
      setRows(u?.rows || []);
      setMeta(u || {});
      setError(null);
    } catch (err) {
      setError(err.message || 'valuation_policy_failed');
    } finally {
      setLoading(false);
    }
  }, [filters.sector, filters.instrument_type, filters.primary_model, filters.status, filters.confidence]);

  useEffect(() => {
    load();
  }, [load]);

  const counts = useMemo(() => {
    const byStatus = {};
    const byModel = {};
    for (const r of rows) {
      byStatus[r.status || '—'] = (byStatus[r.status || '—'] || 0) + 1;
      byModel[r.primary_model || '—'] = (byModel[r.primary_model || '—'] || 0) + 1;
    }
    return { byStatus, byModel };
  }, [rows]);

  const onLookup = async () => {
    const sym = String(filters.symbol || '').trim().toUpperCase();
    if (!sym) return;
    try {
      const payload = await getValuationApplicability(sym);
      setDetail(payload);
      setError(null);
    } catch (err) {
      setError(err.message || 'lookup_failed');
    }
  };

  return (
    <div className="vp-root">
      <div className="vp-shell">
        <Link to="/admin" className="vp-back">
          <ArrowLeft size={14} /> Admin
        </Link>
        <p className="vp-kicker">Phase 8.2A · Valuation Policy & Applicability Engine</p>
        <h1 className="vp-title">Valuation Policy</h1>
        <p className="vp-sub">
          Institutional decision layer in front of the Unified Valuation Engine.
          Every company gets a primary model, supporting metrics, hidden metrics,
          status, confidence, and explanation before any multiple is displayed.
        </p>

        <div className="vp-stats">
          <Stat label="Engine" value={health?.version || '8.2A'} hint={health?.engine || 'VPAE'} />
          <Stat label="Matched" value={meta.total_matched ?? '—'} hint={`scanned ${meta.total_scanned ?? '—'}`} />
          <Stat label="Page rows" value={rows.length} />
          <Stat
            label="Top status"
            value={Object.entries(counts.byStatus).sort((a, b) => b[1] - a[1])[0]?.[0] || '—'}
          />
        </div>

        <div className="vp-filters">
          <input
            placeholder="Symbol lookup"
            value={filters.symbol}
            onChange={(e) => setFilters((f) => ({ ...f, symbol: e.target.value }))}
            onKeyDown={(e) => e.key === 'Enter' && onLookup()}
          />
          <button type="button" onClick={onLookup}><Search size={14} style={{ marginRight: 6 }} />Lookup</button>
          <select
            value={filters.instrument_type}
            onChange={(e) => setFilters((f) => ({ ...f, instrument_type: e.target.value }))}
          >
            <option value="">Instrument</option>
            <option value="EQUITY">EQUITY</option>
            <option value="ETF">ETF</option>
            <option value="REIT">REIT</option>
            <option value="INVIT">INVIT</option>
          </select>
          <select
            value={filters.primary_model}
            onChange={(e) => setFilters((f) => ({ ...f, primary_model: e.target.value }))}
          >
            <option value="">Primary model</option>
            <option value="PRICE_TO_BOOK">PRICE_TO_BOOK</option>
            <option value="PE">PE</option>
            <option value="EV_EBITDA">EV_EBITDA</option>
            <option value="EV_SALES">EV_SALES</option>
            <option value="NAV">NAV</option>
            <option value="PRICE_TO_NAV">PRICE_TO_NAV</option>
            <option value="PRICE_TO_EMBEDDED_VALUE">PRICE_TO_EMBEDDED_VALUE</option>
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value }))}
          >
            <option value="">Status</option>
            <option value="VALID">VALID</option>
            <option value="LOSS_MAKING">LOSS_MAKING</option>
            <option value="EXTREME_VALUATION">EXTREME_VALUATION</option>
            <option value="BANKING_MODEL">BANKING_MODEL</option>
            <option value="INSURANCE_MODEL">INSURANCE_MODEL</option>
            <option value="ETF">ETF</option>
            <option value="INSUFFICIENT_DATA">INSUFFICIENT_DATA</option>
          </select>
          <select
            value={filters.confidence}
            onChange={(e) => setFilters((f) => ({ ...f, confidence: e.target.value }))}
          >
            <option value="">Confidence</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>
          <input
            placeholder="Sector"
            value={filters.sector}
            onChange={(e) => setFilters((f) => ({ ...f, sector: e.target.value }))}
          />
          <button type="button" className="ghost" onClick={load}>
            <RefreshCw size={14} style={{ marginRight: 6 }} />
            {loading ? 'Loading…' : 'Refresh'}
          </button>
        </div>

        {error ? <div className="vp-error">{error}</div> : null}

        {detail?.ok ? (
          <div className="vp-table-wrap" style={{ marginBottom: '1.25rem', padding: '1rem' }}>
            <p className="vp-kicker">{detail.symbol} · Policy detail</p>
            <h2 style={{ margin: '0.35rem 0', fontFamily: '"IBM Plex Serif", Georgia, serif' }}>
              {detail.primary_model}
            </h2>
            <p className="vp-sub" style={{ margin: 0 }}>{detail.reason}</p>
            <p style={{ marginTop: '0.75rem' }}>
              <span className={`vp-pill ${pillClass(detail.status)}`}>{detail.status}</span>{' '}
              <span className={`vp-pill ${pillClass(detail.confidence)}`}>{detail.confidence}</span>{' '}
              <span className="vp-pill">{detail.coverage}</span>
            </p>
            <p className="vp-muted" style={{ marginTop: '0.75rem' }}>
              Supporting: {(detail.supporting_models || []).join(', ') || '—'}
            </p>
            <p className="vp-muted">
              Hidden: {(detail.hidden_models || []).join(', ') || '—'}
            </p>
          </div>
        ) : null}

        <div className="vp-table-wrap">
          <table className="vp-table">
            <thead>
              <tr>
                <th>Company</th>
                <th>Instrument</th>
                <th>Primary</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Coverage</th>
                <th>DQIV</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.symbol}
                  style={{ cursor: 'pointer' }}
                  onClick={async () => {
                    setFilters((f) => ({ ...f, symbol: r.symbol }));
                    try {
                      setDetail(await getValuationApplicability(r.symbol));
                      setError(null);
                    } catch (err) {
                      setError(err.message || 'lookup_failed');
                    }
                  }}
                >
                  <td>
                    <strong>{r.symbol}</strong>
                    <div className="vp-muted">{r.company || r.sector || '—'}</div>
                  </td>
                  <td>{r.instrument_type || '—'}</td>
                  <td>{r.primary_model || '—'}</td>
                  <td><span className={`vp-pill ${pillClass(r.status)}`}>{r.status || '—'}</span></td>
                  <td>{r.confidence || '—'}</td>
                  <td>{r.coverage || '—'}</td>
                  <td><span className={`vp-pill ${pillClass(r.dqiv)}`}>{r.dqiv || '—'}</span></td>
                  <td className="vp-reason">{r.reason || '—'}</td>
                </tr>
              ))}
              {!loading && !rows.length ? (
                <tr>
                  <td colSpan={8} className="vp-muted">No rows matched these filters.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
