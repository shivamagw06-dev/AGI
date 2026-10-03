import { useEffect, useState } from 'react';
import {
  getVarieCompany,
  getVarieSector,
  getVarieTimeline,
} from '@/lib/intelligenceApi';
import './valuationAttribution.css';

function fmt(v, digits = 2) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') {
    return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  }
  return String(v);
}

function copyText(text) {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return Promise.resolve();
}

export function CompanyAttributionPanel({ symbol }) {
  const [pack, setPack] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFactor, setSelectedFactor] = useState(null);
  const [selectedTransition, setSelectedTransition] = useState(null);

  useEffect(() => {
    if (!symbol) return undefined;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      getVarieCompany(symbol),
      getVarieTimeline(symbol, { window: 'max' }),
    ])
      .then(([a, t]) => {
        if (cancelled) return;
        setPack(a);
        setTimeline(t);
        setError(a?.ok === false ? a.error : null);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'attribution_failed');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [symbol]);

  if (!symbol) return null;
  if (loading) return <section className="varie-panel hint">Loading valuation attribution…</section>;
  if (error) return <section className="varie-panel varie-error">{error}</section>;
  if (!pack?.ok) return null;

  const snap = pack.snapshot || {};
  const daily = pack.daily_change || {};
  const note = pack.research_note || {};
  const premiumRows = pack.premium_attribution || [];

  return (
    <section className="varie-panel">
      <div className="varie-head">
        <div>
          <h3>Why valuation?</h3>
          <p className="hint">
            {pack.symbol} · as of {pack.as_of || '—'} · VARIE v{pack.version} · warehouse / UVE / HVIE
          </p>
        </div>
        <div className="varie-actions">
          <button
            type="button"
            onClick={() => copyText(note.export?.markdown || note.body || '')}
          >
            Copy research note
          </button>
          <button
            type="button"
            onClick={() => copyText(note.export?.summary || (pack.why || []).join('\n'))}
          >
            Copy summary
          </button>
        </div>
      </div>

      <div className="varie-snap">
        <div><span className="k">Current</span><span className="v">{fmt(snap.current)}</span></div>
        <div><span className="k">Historical median</span><span className="v">{fmt(snap.historical_median)}</span></div>
        <div><span className="k">Premium</span><span className="v">{snap.premium_pct != null ? `${fmt(snap.premium_pct, 1)}%` : '—'}</span></div>
        <div><span className="k">Historical %</span><span className="v">{fmt(snap.historical_percentile, 0)}</span></div>
        <div><span className="k">Regime</span><span className="v">{snap.regime || '—'}</span></div>
        <div><span className="k">Confidence</span><span className="v">{pack.confidence != null ? `${fmt(pack.confidence, 0)}%` : '—'}</span></div>
      </div>

      <div className="varie-two">
        <div>
          <h4>Why?</h4>
          <ul className="varie-why">
            {(pack.why || []).map((w, i) => (
              <li key={i}>✓ {w}</li>
            ))}
          </ul>
          {pack.largest_contributor ? (
            <p className="varie-largest">
              Largest contributor · <strong>{pack.largest_contributor.label}</strong>
              <span className="hint"> · {pack.largest_contributor.evidence_kind}</span>
            </p>
          ) : null}
        </div>
        <div>
          <h4>{(snap.premium_pct || 0) >= 0 ? 'Premium' : 'Discount'} attribution</h4>
          {!premiumRows.length ? (
            <p className="hint">Primary driver cannot be determined from available data.</p>
          ) : (
            <ul className="varie-breakdown">
              {premiumRows.map((r) => (
                <li key={r.key || r.label}>
                  <button type="button" onClick={() => setSelectedFactor(r)}>
                    <span>{r.label}</span>
                    <strong>{r.contribution_pct != null ? `${fmt(r.contribution_pct, 1)}%` : '—'}</strong>
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="hint">Derived relative evidence weights — not invented causes.</p>
        </div>
      </div>

      {selectedFactor ? (
        <div className="varie-driver-detail">
          <strong>{selectedFactor.label}</strong>
          <p>{selectedFactor.statement}</p>
          <div className="varie-driver-meta">
            <span>Current · {fmt(selectedFactor.current)}</span>
            <span>Previous · {fmt(selectedFactor.previous)}</span>
            <span>Kind · {selectedFactor.evidence_kind}</span>
            <span>Source · {selectedFactor.source}</span>
          </div>
          <button type="button" className="varie-linkish" onClick={() => setSelectedFactor(null)}>Close</button>
        </div>
      ) : null}

      <div className="varie-two">
        <div>
          <h4>Daily valuation change</h4>
          {daily.material === false && daily.yesterday == null ? (
            <p className="hint">{daily.note || 'No daily comparison available.'}</p>
          ) : (
            <>
              <div className="varie-daily">
                <span>Prior · {fmt(daily.yesterday)}</span>
                <span>Current · {fmt(daily.today)}</span>
                <span>
                  Change · {daily.change_pct != null ? `${daily.change_pct > 0 ? '+' : ''}${fmt(daily.change_pct, 1)}%` : '—'}
                </span>
              </div>
              <p>{daily.reason}</p>
              <p className="hint">Materiality threshold {daily.material_pct ?? 0.5}% · UVE attribution graph</p>
            </>
          )}
        </div>
        <div>
          <h4>Opportunity & risk</h4>
          <p><strong>{pack.opportunity?.label || '—'}</strong></p>
          <ul className="varie-why">
            {(pack.opportunity?.reason || []).map((r, i) => <li key={i}>{r}</li>)}
          </ul>
          <p className="hint">{pack.risk?.statement}</p>
          <ul className="varie-why">
            {(pack.risk?.risks || []).map((r, i) => <li key={`risk-${i}`}>{r}</li>)}
          </ul>
        </div>
      </div>

      <div className="varie-two">
        <div>
          <h4>Research note</h4>
          <p className="varie-note">{note.body}</p>
          <p className="hint">Confidence {fmt(note.confidence, 0)}% · analysis only — never BUY / SELL / target</p>
        </div>
        <div>
          <h4>Historical regime timeline</h4>
          <ul className="varie-timeline">
            {(timeline?.regime_timeline || []).slice(-8).map((t) => (
              <li key={`${t.year}-${t.regime}`}>
                <button type="button" onClick={() => setSelectedTransition(t)}>
                  <strong>{t.year}</strong>
                  <span>{t.label || t.regime}</span>
                  {t.transition_from ? <span className="hint">{t.transition_from} →</span> : null}
                </button>
              </li>
            ))}
            {!timeline?.regime_timeline?.length ? (
              <li className="hint">Insufficient HVIE history for regime timeline.</li>
            ) : null}
          </ul>
          {selectedTransition ? (
            <div className="varie-driver-detail">
              <strong>{selectedTransition.year} · {selectedTransition.label}</strong>
              <p>{selectedTransition.why}</p>
              <div className="varie-driver-meta">
                <span>Value · {fmt(selectedTransition.value)}</span>
                <span>Hist % · {fmt(selectedTransition.percentile, 0)}</span>
                <span>Median · {fmt(selectedTransition.median)}</span>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {(pack.factors || []).length ? (
        <div>
          <h4>All drivers</h4>
          <div className="varie-factors">
            {pack.factors.map((f) => (
              <button key={f.key} type="button" className="varie-factor" onClick={() => setSelectedFactor(f)}>
                <strong>{f.label}</strong>
                <span>{f.statement}</span>
                <em>{f.evidence_kind}</em>
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function SectorAttributionPanel({ sector }) {
  const [pack, setPack] = useState(null);
  useEffect(() => {
    if (!sector) return undefined;
    let cancelled = false;
    getVarieSector(sector)
      .then((r) => { if (!cancelled) setPack(r); })
      .catch(() => { if (!cancelled) setPack(null); });
    return () => { cancelled = true; };
  }, [sector]);
  if (!pack?.ok) return null;
  const snap = pack.snapshot || {};
  return (
    <section className="varie-panel varie-sector">
      <h3>Sector attribution · {pack.sector}</h3>
      <div className="varie-snap">
        <div><span className="k">Current PE</span><span className="v">{fmt(snap.current_pe)}</span></div>
        <div><span className="k">Current PB</span><span className="v">{fmt(snap.current_pb)}</span></div>
        <div><span className="k">Premium</span><span className="v">{snap.premium_pct != null ? `${fmt(snap.premium_pct, 1)}%` : '—'}</span></div>
        <div><span className="k">Hist %</span><span className="v">{fmt(snap.historical_percentile, 0)}</span></div>
        <div><span className="k">Median ROE</span><span className="v">{fmt(snap.median_roe)}</span></div>
        <div><span className="k">Confidence</span><span className="v">{fmt(pack.confidence, 0)}%</span></div>
      </div>
      <ul className="varie-why">
        {(pack.why || []).map((w, i) => <li key={i}>✓ {w}</li>)}
      </ul>
      <p className="hint">Analysis only — not a recommendation.</p>
    </section>
  );
}

export default CompanyAttributionPanel;
