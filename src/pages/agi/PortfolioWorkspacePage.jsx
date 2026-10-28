import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  createPortfolioOfficePortfolio,
  getPortfolioDecision,
  getPortfolioGraph,
  getPortfolioOfficeDashboard,
  getPortfolioOfficeHoldings,
  getPortfolioOfficePortfolio,
  getPortfolioPolicy,
  getPortfolioRisk,
  getResearchWorkspacePortfolio,
} from '@/lib/intelligenceApi';

const DEMO_HOLDINGS = [
  { ticker: 'KOTAKBANK', company: 'Kotak Mahindra Bank', sector: 'Banks', weight: '28%' },
  { ticker: 'HDFCBANK', company: 'HDFC Bank', sector: 'Banks', weight: '24%' },
  { ticker: 'TCS', company: 'Tata Consultancy Services', sector: 'IT', weight: '22%' },
  { ticker: 'RELIANCE', company: 'Reliance Industries', sector: 'Energy', weight: '26%' },
];

function formatPct(weight) {
  if (weight == null || Number.isNaN(Number(weight))) return '—';
  const n = Number(weight);
  if (n <= 1) return `${(n * 100).toFixed(0)}%`;
  return `${n.toFixed(0)}%`;
}

export default function PortfolioWorkspacePage() {
  const [portfolioId, setPortfolioId] = useState('agi-desk-demo');
  const [holdings, setHoldings] = useState(DEMO_HOLDINGS);
  const [meta, setMeta] = useState({ name: 'AGI Desk Demo', health: 'Calm', coverage: '—' });
  const [portfolioGraph, setPortfolioGraph] = useState(null);
  const [portfolioDecision, setPortfolioDecision] = useState(null);
  const [portfolioRisk, setPortfolioRisk] = useState(null);
  const [portfolioPolicy, setPortfolioPolicy] = useState(null);
  const [researchWs, setResearchWs] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const dash = await getPortfolioOfficeDashboard().catch(() => null);
        const listed = dash?.portfolios || [];
        let id = listed.find((p) => p.portfolio_id === 'agi-desk-demo')?.portfolio_id;
        if (!id) {
          const created = await createPortfolioOfficePortfolio({
            portfolio_id: 'agi-desk-demo',
            name: 'AGI Desk Demo',
            holdings: DEMO_HOLDINGS.map((h) => ({
              ticker: h.ticker,
              company: h.company,
              sector: h.sector,
              quantity: 100,
              average_cost: 1000,
            })),
          }).catch(() => null);
          id = created?.portfolio_id || created?.portfolio?.portfolio_id || 'agi-desk-demo';
        }
        if (!active) return;
        setPortfolioId(id);
        const pf = await getPortfolioOfficePortfolio(id).catch(() => null);
        const holds =
          (await getPortfolioOfficeHoldings(id).catch(() => null))?.holdings ||
          pf?.holdings ||
          DEMO_HOLDINGS;
        setHoldings(
          (holds.length ? holds : DEMO_HOLDINGS).map((h) => ({
            ticker: h.ticker,
            company: h.company || h.ticker,
            sector: h.sector || '—',
            weight:
              h.weight != null
                ? `${Math.round(Number(h.weight) * (Number(h.weight) <= 1 ? 100 : 1))}%`
                : h.weight_label || '—',
          }))
        );
        setMeta({
          name: pf?.metadata?.name || 'AGI Desk Demo',
          health: 'Calm',
          coverage: `${holds.length || DEMO_HOLDINGS.length} names`,
        });

        const [graph, risk, policy, decision, rw] = await Promise.all([
          getPortfolioGraph('agi-core-equity', { includeCompanyGraphs: true }).catch(() => null),
          getPortfolioRisk('agi-core-equity', { refresh: true }).catch(() => null),
          getPortfolioPolicy('agi-core-equity', {
            refresh: true,
            policy: 'family_office',
          }).catch(() => null),
          getPortfolioDecision('agi-core-equity', { refresh: true }).catch(() => null),
          getResearchWorkspacePortfolio('agi-core-equity').catch(() => null),
        ]);
        if (!active) return;
        setPortfolioGraph(graph && graph.ok !== false ? graph : null);
        setPortfolioRisk(risk && risk.ok !== false ? risk : null);
        setPortfolioPolicy(policy && policy.ok !== false ? policy : null);
        setPortfolioDecision(decision && decision.ok !== false ? decision : null);
        setResearchWs(rw && rw.ok !== false ? rw.workspace || rw : null);
      } catch (err) {
        if (active) setError(err?.message || 'Portfolio unavailable — showing desk demo');
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const concentration = portfolioGraph?.concentration || {};
  const largest = concentration.largest_position || {};
  const sectorExposures = (portfolioGraph?.exposures || []).filter((e) => e.dimension === 'sector');
  const risks = portfolioGraph?.risks || [];
  const decision = portfolioDecision?.decision || null;
  const scorecard = decision?.scorecard || {};
  const monitoring = decision?.monitoring_plan || {};
  const risk = portfolioRisk?.risk || null;
  const riskScorecard = risk?.scorecard || {};
  const riskConc = risk?.concentration || {};
  const policy = portfolioPolicy?.assessment || null;

  return (
    <div>
      <h1 className="agi-greeting">Investment Office</h1>
      <p className="agi-lede">
        Portfolio risk, mandate compliance, and decisioning — what the book may do, what risks it
        carries, and what should change. Company recommendations stay immutable.{' '}
        <Link to="/agi/committee">Investment Committee →</Link>
      </p>

      {error && <div className="agi-error">{error}</div>}

      {researchWs ? (
        <section className="agi-section" style={{ marginBottom: '1rem' }}>
          <div className="agi-section-head">
            <h2>Portfolio workspace · RW-01</h2>
            <Link to={researchWs.ask_deep_link || '/agi/ask?context=portfolio'}>Ask AGI</Link>
          </div>
          <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
            {researchWs.sections?.overview?.headline ||
              'Holdings, risk, policy, decisions, and committee — one navigable investment story.'}
          </p>
          <ul className="agi-list">
            {(researchWs.timeline || []).slice(0, 5).map((e) => (
              <li key={e.event_id || e.title}>
                <div className="agi-list-title">
                  [{e.kind}] {e.title}
                </div>
                <div className="agi-list-meta">{e.summary}</div>
              </li>
            ))}
          </ul>
          <div style={{ marginTop: '0.75rem', display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
            {(researchWs.linked_objects || []).slice(0, 8).map((o) =>
              o.href ? (
                <Link key={`${o.object_type}-${o.object_id}`} className="agi-chip" to={o.href}>
                  {o.object_type}
                </Link>
              ) : (
                <span key={`${o.object_type}-${o.object_id}`} className="agi-chip muted">
                  {o.object_type}
                </span>
              )
            )}
          </div>
        </section>
      ) : null}

      <div className="agi-stat-row">
        <div className="agi-stat">
          <div className="agi-stat-label">Compliance</div>
          <div className="agi-stat-value" style={{ fontSize: '1.05rem' }}>
            {policy?.overall_status || '—'}
          </div>
        </div>
        <div className="agi-stat">
          <div className="agi-stat-label">Overall risk</div>
          <div className="agi-stat-value" style={{ fontSize: '1.05rem' }}>
            {risk?.overall_risk || '—'}
          </div>
        </div>
        <div className="agi-stat">
          <div className="agi-stat-label">Recommendation</div>
          <div className="agi-stat-value" style={{ fontSize: '1.05rem' }}>
            {decision?.recommendation || meta.health}
          </div>
        </div>
        <div className="agi-stat">
          <div className="agi-stat-label">HHI</div>
          <div className="agi-stat-value" style={{ fontSize: '1.15rem' }}>
            {riskConc.hhi != null
              ? Number(riskConc.hhi).toFixed(2)
              : concentration.hhi != null
                ? Number(concentration.hhi).toFixed(2)
                : '—'}
          </div>
        </div>
      </div>

      <section className="agi-section" style={{ marginTop: '1.5rem' }}>
        <div className="agi-section-head">
          <h2>Compliance</h2>
          <span className="agi-list-meta">
            PCE-01 · {policy?.profile_id || 'family_office'} mandate
          </span>
        </div>
        {!policy ? (
          <div className="agi-empty">Policy assessment unavailable.</div>
        ) : (
          <>
            <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
              {(policy.lineage || []).join(' → ')}
              {policy.policy_id ? ` · ${policy.policy_id}` : ''}
            </p>
            <div className="agi-stat-row">
              {[
                ['Status', policy.overall_status],
                ['Score', policy.compliance_score],
                ['Violations', (policy.violations || []).length],
                ['Passed', policy.passed_count],
                ['Failed', policy.failed_count],
              ].map(([label, value]) => (
                <div key={label} className="agi-stat">
                  <div className="agi-stat-label">{label}</div>
                  <div className="agi-stat-value" style={{ fontSize: '1.05rem' }}>
                    {value ?? '—'}
                  </div>
                </div>
              ))}
            </div>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Active violations
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {(policy.violations || []).length ? (
                (policy.violations || []).map((v) => (
                  <li key={v.constraint_id}>
                    <div className="agi-list-title">
                      [{v.severity}] {v.name}
                    </div>
                    <div className="agi-list-meta">
                      {v.detail} · Action: {v.required_action}
                    </div>
                  </li>
                ))
              ) : (
                <li>
                  <div className="agi-list-meta">No active mandate violations.</div>
                </li>
              )}
            </ul>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Required actions
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {(policy.required_actions || []).length ? (
                (policy.required_actions || []).map((a) => (
                  <li key={a}>
                    <div className="agi-list-title">{a}</div>
                  </li>
                ))
              ) : (
                <li>
                  <div className="agi-list-meta">No remediation required.</div>
                </li>
              )}
            </ul>
          </>
        )}
      </section>

      <section className="agi-section" style={{ marginTop: '1.5rem' }}>
        <div className="agi-section-head">
          <h2>Portfolio Risk</h2>
          <span className="agi-list-meta">PRE-01 · authoritative risk object</span>
        </div>
        {!risk ? (
          <div className="agi-empty">Portfolio risk unavailable.</div>
        ) : (
          <>
            <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
              {(risk.lineage || []).join(' → ')}
              {risk.risk_id ? ` · ${risk.risk_id}` : ''}
            </p>
            <div className="agi-stat-row">
              {[
                ['Concentration', riskConc.level],
                ['Liquidity', risk.liquidity?.level],
                ['Correlation', risk.correlations?.level],
                ['Stress resilience', riskScorecard.stress_resilience],
                ['Coverage', riskScorecard.coverage],
              ].map(([label, value]) => (
                <div key={label} className="agi-stat">
                  <div className="agi-stat-label">{label}</div>
                  <div className="agi-stat-value" style={{ fontSize: '1.05rem' }}>
                    {value ?? '—'}
                  </div>
                </div>
              ))}
            </div>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Stress results
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {(risk.stress_results || []).map((s) => (
                <li key={s.scenario}>
                  <div className="agi-list-title">
                    {s.label}: {Number(s.portfolio_impact_pct).toFixed(1)}%
                  </div>
                  <div className="agi-list-meta">
                    [{s.severity}] {(s.affected_holdings || []).slice(0, 4).join(', ')}
                  </div>
                </li>
              ))}
            </ul>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Warnings / recommendations
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {(risk.warnings || []).map((w) => (
                <li key={`w-${w}`}>
                  <div className="agi-list-title">{w}</div>
                </li>
              ))}
              {(risk.recommendations || []).map((rec) => (
                <li key={`r-${rec}`}>
                  <div className="agi-list-meta">{rec}</div>
                </li>
              ))}
              {!(risk.warnings || []).length && !(risk.recommendations || []).length ? (
                <li>
                  <div className="agi-list-meta">No active risk warnings.</div>
                </li>
              ) : null}
            </ul>
          </>
        )}
      </section>

      <section className="agi-section" style={{ marginTop: '1.5rem' }}>
        <div className="agi-section-head">
          <h2>Portfolio Decision</h2>
          <span className="agi-list-meta">
            CIO-01 · consumes PRE-01 + PCE-01 · referential company decisions
          </span>
        </div>
        {!decision ? (
          <div className="agi-empty">Portfolio decision unavailable.</div>
        ) : (
          <>
            <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
              {(decision.lineage || []).join(' → ')}
              {decision.mutates_company_decisions === false
                ? ' · company decisions immutable'
                : ''}
            </p>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem' }}>
              Allocation changes
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {(decision.allocation_actions || []).length ? (
                (decision.allocation_actions || []).map((a) => (
                  <li key={`${a.ticker}-${a.from_weight}-${a.to_weight}`}>
                    <div className="agi-list-title">
                      {a.ticker}: {formatPct(a.from_weight)} → {formatPct(a.to_weight)}
                    </div>
                    <div className="agi-list-meta">{a.reason}</div>
                  </li>
                ))
              ) : (
                <li>
                  <div className="agi-list-meta">No allocation changes required.</div>
                </li>
              )}
            </ul>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Exposure changes
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {(decision.exposure_actions || []).map((a) => (
                <li key={`${a.dimension}-${a.name}-${a.action}`}>
                  <div className="agi-list-title">
                    [{a.action}] {a.dimension}/{a.name}: {formatPct(a.from_weight)} →{' '}
                    {formatPct(a.to_weight)}
                  </div>
                  <div className="agi-list-meta">{a.reason}</div>
                </li>
              ))}
            </ul>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Decision scorecard
            </h3>
            <div className="agi-stat-row" style={{ marginTop: '0.5rem' }}>
              {[
                ['Diversification', scorecard.sector_diversification],
                ['Allocation', scorecard.allocation_balance],
                ['Risk', scorecard.risk],
                ['Agreement', scorecard.decision_agreement],
                ['Coverage', scorecard.coverage],
              ].map(([label, value]) => (
                <div key={label} className="agi-stat">
                  <div className="agi-stat-label">{label}</div>
                  <div className="agi-stat-value" style={{ fontSize: '1.1rem' }}>
                    {value ?? '—'}
                  </div>
                </div>
              ))}
            </div>

            <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
              Monitoring plan
            </h3>
            <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
              {(monitoring.required_reviews || []).map((item) => (
                <li key={`rev-${item}`}>
                  <div className="agi-list-title">{item}</div>
                </li>
              ))}
              {(monitoring.committee_items || []).map((item) => (
                <li key={`com-${item}`}>
                  <div className="agi-list-title">{item}</div>
                  <div className="agi-list-meta">Committee</div>
                </li>
              ))}
              {!(monitoring.required_reviews || []).length &&
              !(monitoring.committee_items || []).length ? (
                <li>
                  <div className="agi-list-meta">No pending reviews.</div>
                </li>
              ) : null}
            </ul>
          </>
        )}
      </section>

      <div className="agi-grid-2" style={{ marginTop: '1.5rem' }}>
        <section className="agi-section">
          <div className="agi-section-head">
            <h2>Holdings</h2>
            <Link
              to={`/agi/ask?context=portfolio&portfolio=${encodeURIComponent(portfolioId)}&q=${encodeURIComponent('Which holding concerns you most?')}`}
            >
              Ask AGI
            </Link>
          </div>
          <ul className="agi-list">
            {holdings.map((h) => (
              <li key={h.ticker}>
                <Link to={`/agi/companies/${h.ticker}`}>
                  <div className="agi-list-title">
                    {h.ticker} · {h.company}
                  </div>
                  <div className="agi-list-meta">
                    {h.sector} · weight {h.weight}
                  </div>
                </Link>
                <span className="agi-chip">Workspace</span>
              </li>
            ))}
          </ul>
        </section>

        <section className="agi-section">
          <div className="agi-section-head">
            <h2>Portfolio Knowledge Graph</h2>
            <span className="agi-list-meta">PKG-01 · AGI Core Equity</span>
          </div>
          {!portfolioGraph ? (
            <div className="agi-empty">Portfolio graph unavailable.</div>
          ) : (
            <>
              <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
                {(portfolioGraph.lineage || []).join(' → ')}
              </p>
              <div className="agi-stat-row">
                <div className="agi-stat">
                  <div className="agi-stat-label">Entities</div>
                  <div className="agi-stat-value">{portfolioGraph.entity_count ?? 0}</div>
                </div>
                <div className="agi-stat">
                  <div className="agi-stat-label">Relationships</div>
                  <div className="agi-stat-value">{portfolioGraph.relationship_count ?? 0}</div>
                </div>
                <div className="agi-stat">
                  <div className="agi-stat-label">Largest</div>
                  <div className="agi-stat-value" style={{ fontSize: '1rem' }}>
                    {largest.ticker || '—'} {formatPct(largest.weight)}
                  </div>
                </div>
              </div>

              <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
                Graph holdings
              </h3>
              <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
                {(portfolioGraph.holdings || []).map((h) => (
                  <li key={`pg-${h.ticker}`}>
                    <Link to={`/agi/companies/${h.ticker}`}>
                      <div className="agi-list-title">
                        {h.ticker} · {formatPct(h.weight)} · {h.recommendation || '—'}
                      </div>
                      <div className="agi-list-meta">
                        conf {h.confidence ?? '—'}
                        {h.company_graph_id ? ` · company graph linked` : ''}
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>

              <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
                Sector exposure
              </h3>
              <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
                {sectorExposures.map((e) => (
                  <li key={e.name}>
                    <div className="agi-list-title">
                      {e.name} <span className="agi-list-meta">{formatPct(e.weight)}</span>
                    </div>
                  </li>
                ))}
              </ul>

              <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.1rem', marginTop: '1rem' }}>
                Concentration risks
              </h3>
              <ul className="agi-list" style={{ marginTop: '0.5rem' }}>
                {risks.length ? (
                  risks.map((r) => (
                    <li key={`${r.kind}-${r.label}`}>
                      <div className="agi-list-title">
                        [{r.severity}] {r.label}
                      </div>
                      <div className="agi-list-meta">{r.detail}</div>
                    </li>
                  ))
                ) : (
                  <li>
                    <div className="agi-list-meta">No concentration risks above threshold.</div>
                  </li>
                )}
              </ul>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
