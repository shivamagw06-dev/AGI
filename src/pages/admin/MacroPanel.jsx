import { useEffect, useState } from 'react';
import { getMieCompanyImpact, getMiePack } from '@/lib/intelligenceApi';
import './researchIntelligence.css';

const MODULE_ORDER = [
  ['executive', 'Executive Summary'],
  ['dashboard', 'Macro Dashboard'],
  ['cycle', 'Economic Cycle'],
  ['inflation', 'Inflation'],
  ['rates', 'Interest Rates'],
  ['liquidity', 'Liquidity'],
  ['currency', 'Currency'],
  ['commodities', 'Commodities'],
  ['bonds', 'Bond Market'],
  ['sector_impact', 'Sector Impact'],
  ['industry_impact', 'Industry Impact'],
  ['company_exposure', 'Company Exposure'],
  ['risks', 'Risks'],
  ['forecast', 'Forecast'],
  ['scenarios', 'Scenario Analysis'],
  ['relationships', 'Relationships'],
  ['confidence', 'Confidence'],
];

function ConfBadge({ conf }) {
  const level = conf?.confidence || conf || '—';
  const cls = String(level).toLowerCase();
  return <span className={`rie-conf rie-conf-${cls}`}>{String(level)}</span>;
}

function asLabel(value, fallback = '—') {
  if (value == null || value === '') return fallback;
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (typeof value === 'object') {
    return value.label || value.name || value.regime || value.cycle || fallback;
  }
  return fallback;
}

export default function MacroPanel({ symbol }) {
  const [pack, setPack] = useState(null);
  const [exposure, setExposure] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getMiePack(symbol ? { symbol, country: 'India' } : { country: 'India' }),
      symbol ? getMieCompanyImpact(symbol) : Promise.resolve(null),
    ])
      .then(([data, exp]) => {
        if (cancelled) return;
        setPack(data);
        setExposure(exp);
        setError(data?.ok === false ? data.error || data.status || 'macro unavailable' : null);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'macro failed');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [symbol]);

  if (loading) return <section className="rie-panel hint">Loading macro intelligence…</section>;
  if (error && !pack?.modules) {
    return <section className="rie-panel hint">Macro unavailable — {error}</section>;
  }
  if (!pack) return null;

  const quality = pack.macro_quality || {};
  const modules = pack.modules || pack.sections || {};
  if (exposure && !modules.company_exposure) {
    modules.company_exposure = exposure;
  }
  const probs = pack.probabilities || {};

  return (
    <section className="rie-panel">
      <header className="rie-head">
        <div>
          <div className="rie-eyebrow">Macro Intelligence Engine</div>
          <h3>{pack.country || 'India'}{symbol ? ` · ${symbol}` : ''}</h3>
          <p>
            Top-down macro context from warehouse + CMKP / HMIP / MRI / HMAI / MFI.
            No GDP point predictions. No BUY/SELL.
          </p>
        </div>
        <div className="rie-quality">
          <span>Macro confidence</span>
          <strong><ConfBadge conf={quality.macro_confidence} /></strong>
          <span className="rie-meta">regime {asLabel(pack.regime)} · {asLabel(pack.cycle)}</span>
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
                  {' · '}Inferred: {(sec.explainability.inferred || []).slice(0, 2).join('; ') || '—'}
                </p>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
