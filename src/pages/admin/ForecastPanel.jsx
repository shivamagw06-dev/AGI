import { useEffect, useState } from 'react';
import { getFieCompany } from '@/lib/intelligenceApi';
import './researchIntelligence.css';

const MODULE_ORDER = [
  ['executive', 'Executive Outlook'],
  ['business', 'Business Forecast'],
  ['growth', 'Growth Forecast'],
  ['profitability', 'Profitability'],
  ['balance_sheet', 'Balance Sheet'],
  ['valuation', 'Valuation Outlook'],
  ['scenarios', 'Bull / Base / Bear'],
  ['sensitivity', 'Sensitivity'],
  ['risks', 'Risks'],
  ['catalysts', 'Catalysts'],
  ['confidence', 'Confidence'],
  ['history', 'Forecast History'],
  ['accuracy', 'Forecast Accuracy'],
];

function ConfBadge({ conf }) {
  const level = conf?.confidence || conf || '—';
  const cls = String(level).toLowerCase();
  return <span className={`rie-conf rie-conf-${cls}`}>{level}</span>;
}

export default function ForecastPanel({ symbol }) {
  const [pack, setPack] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!symbol) return undefined;
    let cancelled = false;
    setLoading(true);
    getFieCompany(symbol)
      .then((data) => {
        if (!cancelled) {
          setPack(data);
          setError(data?.ok === false ? data.error || data.status || 'forecast unavailable' : null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'forecast failed');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [symbol]);

  if (!symbol) return null;
  if (loading) return <section className="rie-panel hint">Loading forecast pack…</section>;
  if (error && !pack?.modules) {
    return <section className="rie-panel hint">Forecast unavailable — {error}</section>;
  }
  if (!pack) return null;

  const quality = pack.forecast_quality || {};
  const modules = pack.modules || pack.sections || {};
  const probs = pack.probabilities || {};

  return (
    <section className="rie-panel">
      <header className="rie-head">
        <div>
          <div className="rie-eyebrow">Forecast Intelligence Engine</div>
          <h3>{pack.company_name || symbol}</h3>
          <p>
            Evidence-based outlook from warehouse + UVE / HVIE / VARIE / VPAE / RIE.
            No target prices. No recommendations.
          </p>
        </div>
        <div className="rie-quality">
          <span>Forecast confidence</span>
          <strong><ConfBadge conf={quality.forecast_confidence} /></strong>
          <span className="rie-meta">coverage {quality.coverage_pct ?? '—'}%</span>
          {probs.base != null ? (
            <span className="rie-meta">
              B/Base/Bear {probs.bull}/{probs.base}/{probs.bear}
            </span>
          ) : null}
        </div>
      </header>

      <div className="rie-sections">
        {MODULE_ORDER.map(([key, label]) => {
          const sec = modules[key];
          if (!sec) return null;
          return (
            <article key={key} className="rie-section">
              <div className="rie-section-head">
                <h4>{label}</h4>
                <ConfBadge conf={sec.confidence} />
              </div>
              <ul>
                {(sec.findings || []).slice(0, 8).map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              {sec.explainability ? (
                <p className="rie-meta">
                  Observed: {(sec.explainability.observed || []).slice(0, 3).join('; ') || '—'}
                  {' · '}Assumed: {(sec.explainability.assumed || []).slice(0, 2).join('; ') || '—'}
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
