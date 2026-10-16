import { useEffect, useState } from 'react';
import { getRieCompany } from '@/lib/intelligenceApi';
import './researchIntelligence.css';

const SECTION_ORDER = [
  ['executive', 'Executive Summary'],
  ['business', 'Business'],
  ['financial_quality', 'Financial Quality'],
  ['growth', 'Growth'],
  ['profitability', 'Profitability'],
  ['capital_allocation', 'Capital Allocation'],
  ['valuation', 'Valuation'],
  ['ownership', 'Ownership'],
  ['risk', 'Risks'],
  ['catalysts', 'Catalysts'],
  ['monitoring', 'Monitoring'],
  ['timeline', 'Timeline'],
  ['confidence', 'Confidence'],
];

function ConfBadge({ conf }) {
  const level = conf?.confidence || conf || '—';
  const cls = String(level).toLowerCase();
  return <span className={`rie-conf rie-conf-${cls}`}>{level}</span>;
}

export default function ResearchDossierPanel({ symbol }) {
  const [pack, setPack] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!symbol) return undefined;
    let cancelled = false;
    setLoading(true);
    getRieCompany(symbol)
      .then((data) => {
        if (!cancelled) {
          setPack(data);
          setError(data?.ok === false ? data.error || 'research unavailable' : null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'research failed');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [symbol]);

  if (!symbol) return null;
  if (loading) return <section className="rie-panel hint">Loading research dossier…</section>;
  if (error && !pack?.sections) {
    return <section className="rie-panel hint">Research dossier unavailable — {error}</section>;
  }
  if (!pack) return null;

  const quality = pack.research_quality || {};
  const sections = pack.sections || {};

  return (
    <section className="rie-panel">
      <header className="rie-head">
        <div>
          <div className="rie-eyebrow">Research Intelligence Engine</div>
          <h3>{pack.company_name || symbol}</h3>
          <p>
            Evidence-backed dossier from warehouse + UVE / HVIE / VARIE / VPAE.
            No recommendations. No UI calculations.
          </p>
        </div>
        <div className="rie-quality">
          <span>Research confidence</span>
          <strong><ConfBadge conf={quality.research_confidence} /></strong>
          <span className="rie-meta">coverage {quality.coverage_pct ?? '—'}%</span>
        </div>
      </header>

      <div className="rie-sections">
        {SECTION_ORDER.map(([id, label]) => {
          const sec = sections[id];
          if (!sec) return null;
          const findings = sec.findings || [];
          const expl = sec.explainability || {};
          return (
            <article key={id} className="rie-section">
              <div className="rie-section-head">
                <h4>{label}</h4>
                <ConfBadge conf={sec.confidence} />
              </div>
              <ul>
                {findings.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              {(expl.observed?.length || expl.derived?.length || expl.inferred?.length) ? (
                <div className="rie-explain">
                  {expl.observed?.length ? <span>Observed: {expl.observed.join(' · ')}</span> : null}
                  {expl.derived?.length ? <span>Derived: {expl.derived.join(' · ')}</span> : null}
                  {expl.inferred?.length ? <span>Inferred: {expl.inferred.join(' · ')}</span> : null}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}
