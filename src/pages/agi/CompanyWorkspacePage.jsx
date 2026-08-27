import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  getCompanyWorkspace,
  getCompanyWorkspaceEvidence,
  getCompanyWorkspaceTimeline,
  getInstitutionalDecision,
  getInstitutionalGraph,
  getInstitutionalObservations,
  getInstitutionalScenarios,
  getResearchWorkspaceCompany,
} from '@/lib/intelligenceApi';
import {
  COMPANY_TABS,
  boardOf,
  coverageLabel,
  eventLabel,
  firstBlockText,
  formatConfidence,
  formatPct,
  productizeText,
  researchStatusTone,
  sectionByKey,
} from './helpers';

function MetricGrid({ payload }) {
  if (!payload || typeof payload !== 'object') return null;
  const keys = [
    ['revenue', 'Revenue'],
    ['ebit', 'EBIT'],
    ['margins', 'Margins'],
    ['gross_margin', 'Gross margin'],
    ['ebit_margin', 'EBIT margin'],
    ['roe', 'ROE'],
    ['roce', 'ROCE'],
    ['cash_flow', 'Cash flow'],
    ['fcf', 'FCF'],
    ['debt', 'Debt'],
  ];
  const rows = keys
    .map(([k, label]) => {
      const v = payload[k] ?? payload[label] ?? payload[label.toLowerCase()];
      if (v == null || (typeof v === 'object' && !Array.isArray(v))) return null;
      return { label, value: typeof v === 'number' ? String(v) : String(v) };
    })
    .filter(Boolean)
    .slice(0, 8);
  if (!rows.length) return null;
  return (
    <div className="agi-stat-row" style={{ marginTop: '1rem' }}>
      {rows.map((r) => (
        <div key={r.label} className="agi-stat">
          <div className="agi-stat-label">{r.label}</div>
          <div className="agi-stat-value" style={{ fontSize: '1.15rem' }}>
            {r.value}
          </div>
        </div>
      ))}
    </div>
  );
}

function DriversList({ payload }) {
  const drivers =
    payload?.drivers ||
    payload?.quality_drivers ||
    payload?.key_drivers ||
    payload?.factors ||
    [];
  const list = Array.isArray(drivers) ? drivers : [];
  if (!list.length) return null;
  return (
    <ul className="agi-list" style={{ marginTop: '1rem' }}>
      {list.slice(0, 8).map((d, i) => {
        const title = typeof d === 'string' ? d : d?.name || d?.driver || d?.label || `Driver ${i + 1}`;
        const meta = typeof d === 'object' ? d?.detail || d?.trend || d?.note || '' : '';
        return (
          <li key={`${title}-${i}`}>
            <div>
              <div className="agi-list-title">{productizeText(title)}</div>
              {meta ? <div className="agi-list-meta">{productizeText(String(meta))}</div> : null}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export default function CompanyWorkspacePage() {
  const { ticker: rawTicker } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const ticker = String(rawTicker || '').trim().toUpperCase();
  const tab = searchParams.get('tab') || 'overview';

  const [workspace, setWorkspace] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [decisionPack, setDecisionPack] = useState(null);
  const [knowledgeGraph, setKnowledgeGraph] = useState(null);
  const [observationsPack, setObservationsPack] = useState(null);
  const [forecastPack, setForecastPack] = useState(null);
  const [researchWs, setResearchWs] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState('base');
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!ticker) return;
    let active = true;
    setLoading(true);
    setError(null);
    Promise.all([
      getCompanyWorkspace(ticker),
      getCompanyWorkspaceTimeline(ticker).catch(() => null),
      getCompanyWorkspaceEvidence(ticker).catch(() => null),
      getInstitutionalDecision(ticker, {
        includeCalibration: true,
        includeDrift: true,
      }).catch(() => null),
      getInstitutionalGraph(ticker, { includePaths: true, includeInference: true }).catch(() => null),
      getInstitutionalScenarios(ticker, {
        includeGraph: true,
        includePropagation: true,
      }).catch(() => null),
      getInstitutionalObservations(ticker, {
        includeDecisionChanges: true,
      }).catch(() => null),
      getResearchWorkspaceCompany(ticker, { focus: 'overview' }).catch(() => null),
    ])
      .then(([ws, tl, ev, decision, graph, forecast, observations, rw]) => {
        if (!active) return;
        setWorkspace(ws);
        const events =
          tl?.events ||
          tl?.board?.events ||
          sectionByKey(ws, 'historical_timeline')?.board?.events ||
          [];
        setTimeline(Array.isArray(events) ? events : []);
        const refs =
          ev?.references ||
          ev?.board?.references ||
          sectionByKey(ws, 'evidence_references')?.board?.references ||
          [];
        setEvidence(Array.isArray(refs) ? refs : []);
        setDecisionPack(decision && decision.ok !== false ? decision : null);
        setKnowledgeGraph(graph && graph.ok !== false ? graph : null);
        setForecastPack(forecast && forecast.ok !== false ? forecast : null);
        setResearchWs(rw && rw.ok !== false ? rw.workspace || rw : null);
        setSelectedScenario('base');
        setObservationsPack(observations && observations.ok !== false ? observations : null);
        setSelectedNodeId(null);
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        setError(err?.message || 'Unable to load company workspace');
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [ticker]);

  const overview = useMemo(() => boardOf(sectionByKey(workspace, 'overview')), [workspace]);
  const profile = useMemo(() => boardOf(sectionByKey(workspace, 'company_profile')), [workspace]);
  const activeSection = useMemo(() => sectionByKey(workspace, tab), [workspace, tab]);
  const activeBoard = boardOf(activeSection);

  const companyName = overview.company || profile.company || ticker;
  const exchange = overview.exchange || profile.exchange || 'NSE';
  const sector = overview.sector || profile.sector || '—';
  const industry = overview.industry || profile.industry || '';
  const coverage = overview.coverage || {};
  const confidence = overview.confidence;
  const researchStatus = overview.current_research_status || '—';
  const lastUpdated = overview.last_updated || workspace?.metadata?.generated_at || '—';
  const watchCount = boardOf(sectionByKey(workspace, 'watchlist_status')).count || 0;
  const portCount = boardOf(sectionByKey(workspace, 'portfolio_references')).count || 0;

  const qualityPayload = boardOf(sectionByKey(workspace, 'business_quality')).payload || {};
  const qualityScore =
    qualityPayload.score ??
    qualityPayload.quality_score ??
    qualityPayload.business_quality_score ??
    confidence;

  const setTab = (id) => {
    const next = new URLSearchParams(searchParams);
    next.set('tab', id);
    setSearchParams(next, { replace: true });
  };

  if (!ticker) {
    return <div className="agi-empty">Choose a company to open its workspace.</div>;
  }

  return (
    <div>
      <div className="agi-company-header">
        <div className="agi-company-title-row">
          <h1>{companyName}</h1>
          <span className="agi-chip">{ticker}</span>
          <span className="agi-chip muted">{exchange}</span>
          {industry ? <span className="agi-chip muted">{industry}</span> : null}
          {sector && sector !== '—' ? <span className="agi-chip muted">{sector}</span> : null}
        </div>
        <div className="agi-meta-row">
          <span>{coverageLabel(coverage)}</span>
          <span>Confidence {formatConfidence(confidence)}</span>
          <span>Updated {String(lastUpdated).slice(0, 19) || '—'}</span>
          <span className={`agi-chip ${researchStatusTone(researchStatus)}`}>
            {productizeText(researchStatus)}
          </span>
          {watchCount > 0 ? <span className="agi-chip ok">Watchlisted</span> : <span className="agi-chip muted">Not watchlisted</span>}
          {portCount > 0 ? <span className="agi-chip ok">In portfolio</span> : <span className="agi-chip muted">Not in portfolio</span>}
        </div>
        <div className="agi-stat-row">
          <div className="agi-stat">
            <div className="agi-stat-label">Coverage</div>
            <div className="agi-stat-value">{formatPct(coverage.ratio, 0)}</div>
          </div>
          <div className="agi-stat">
            <div className="agi-stat-label">Confidence</div>
            <div className="agi-stat-value">{formatConfidence(confidence)}</div>
          </div>
          <div className="agi-stat">
            <div className="agi-stat-label">Research</div>
            <div className="agi-stat-value" style={{ fontSize: '1.05rem' }}>
              {productizeText(String(researchStatus).slice(0, 28))}
            </div>
          </div>
          <div className="agi-stat">
            <div className="agi-stat-label">Ask</div>
            <div className="agi-stat-value" style={{ fontSize: '1.05rem' }}>
              <Link to={`/agi/ask?ticker=${encodeURIComponent(ticker)}&q=${encodeURIComponent('Explain margins.')}`}>
                Open Ask AGI
              </Link>
            </div>
          </div>
        </div>
      </div>

      <div className="agi-tabs" role="tablist" aria-label="Company sections">
        {COMPANY_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? 'active' : undefined}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div className="agi-empty">Loading company workspace…</div>}
      {error && <div className="agi-error">{error}</div>}

      {!loading && researchWs ? (
        <section className="agi-section" style={{ marginBottom: '1rem' }}>
          <div className="agi-section-head">
            <h2>Investment story · RW-01</h2>
            <Link to={researchWs.ask_deep_link || `/agi/ask?ticker=${ticker}`}>Ask AGI</Link>
          </div>
          <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
            {researchWs.sections?.overview?.story ||
              'Linked decisions, evidence, risk, policy, and committee — living workspace, not a static report.'}
          </p>
          <div className="agi-stat-row">
            <div className="agi-stat">
              <div className="agi-stat-label">Timeline</div>
              <div className="agi-stat-value">{researchWs.timeline_count ?? (researchWs.timeline || []).length}</div>
            </div>
            <div className="agi-stat">
              <div className="agi-stat-label">Linked</div>
              <div className="agi-stat-value">{researchWs.linked_count ?? (researchWs.linked_objects || []).length}</div>
            </div>
            <div className="agi-stat">
              <div className="agi-stat-label">Evidence</div>
              <div className="agi-stat-value">{researchWs.evidence_count ?? (researchWs.evidence || []).length}</div>
            </div>
            <div className="agi-stat">
              <div className="agi-stat-label">Notes</div>
              <div className="agi-stat-value">{researchWs.note_count ?? (researchWs.notes || []).length}</div>
            </div>
          </div>
          <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
            {(researchWs.timeline || []).slice(0, 5).map((e) => (
              <li key={e.event_id || e.title}>
                <div className="agi-list-title">[{e.kind}] {e.title}</div>
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

      {!loading && !error && tab === 'overview' && (
        <div>
          <p className="agi-lede" style={{ marginBottom: '1rem' }}>
            {productizeText(firstBlockText(sectionByKey(workspace, 'overview'))) ||
              `${companyName} research workspace — quality, financials, evidence, and timeline.`}
          </p>
          <div className="agi-grid-2">
            <section className="agi-panel">
              <div className="agi-section-head">
                <h2>Business quality</h2>
                <button type="button" className="agi-btn" onClick={() => setTab('business_quality')}>
                  Open
                </button>
              </div>
              <div className="agi-score-block">
                <div className="agi-score-ring">
                  <strong>{formatConfidence(qualityScore)}</strong>
                  <span>Score</span>
                </div>
                <div>
                  <div className="agi-list-title">Institutional quality view</div>
                  <div className="agi-list-meta" style={{ marginTop: '0.35rem' }}>
                    Trend, drivers, and historical context live in the Business Quality section — not a spreadsheet.
                  </div>
                </div>
              </div>
            </section>
            <section className="agi-panel">
              <div className="agi-section-head">
                <h2>Outstanding questions</h2>
              </div>
              <ul className="agi-list">
                {(boardOf(sectionByKey(workspace, 'outstanding_questions')).questions || []).length ? (
                  (boardOf(sectionByKey(workspace, 'outstanding_questions')).questions || []).map((q) => (
                    <li key={q}>
                      <div className="agi-list-title">{productizeText(q)}</div>
                    </li>
                  ))
                ) : (
                  <li>
                    <div className="agi-list-meta">No open coverage gaps recorded.</div>
                  </li>
                )}
              </ul>
            </section>
          </div>
          {decisionPack?.decision ? (
            <section className="agi-panel" style={{ marginTop: '1.25rem' }}>
              <div className="agi-section-head">
                <h2>Institutional decision</h2>
                <button type="button" className="agi-btn" onClick={() => setTab('decision')}>
                  Calibration
                </button>
              </div>
              <div className="agi-stat-row">
                <div className="agi-stat">
                  <div className="agi-stat-label">Recommendation</div>
                  <div className="agi-stat-value" style={{ fontSize: '1.35rem' }}>
                    {decisionPack.decision.recommendation}
                  </div>
                </div>
                <div className="agi-stat">
                  <div className="agi-stat-label">Calibrated confidence</div>
                  <div className="agi-stat-value">
                    {formatConfidence(decisionPack.decision.confidence)}
                  </div>
                </div>
              </div>
            </section>
          ) : null}
        </div>
      )}

      {!loading && !error && tab === 'decision' && (
        <div>
          <h2 style={{ margin: '0 0 0.5rem', fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
            Decision calibration
          </h2>
          <p className="agi-list-meta" style={{ marginBottom: '1rem' }}>
            Confidence is computed from evidence quality, reasoning strength, and penalties — not assigned.
          </p>
          {!decisionPack?.decision ? (
            <div className="agi-empty">Decision calibration unavailable for this ticker.</div>
          ) : (
            <>
              <div className="agi-stat-row">
                <div className="agi-stat">
                  <div className="agi-stat-label">Recommendation</div>
                  <div className="agi-stat-value" style={{ fontSize: '1.35rem' }}>
                    {decisionPack.decision.recommendation}
                  </div>
                </div>
                <div className="agi-stat">
                  <div className="agi-stat-label">Confidence</div>
                  <div className="agi-stat-value">
                    {formatConfidence(decisionPack.decision.confidence)}
                  </div>
                </div>
              </div>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Confidence breakdown
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {(decisionPack.calibration?.positive || []).slice(0, 6).map((c) => (
                    <li key={`p-${c.key || c.label}`}>
                      <div className="agi-list-title">+ {productizeText(c.label || c.key)}</div>
                    </li>
                  ))}
                  {(decisionPack.calibration?.negative || []).slice(0, 6).map((c) => (
                    <li key={`n-${c.key || c.label}`}>
                      <div className="agi-list-title">− {productizeText(c.label || c.key)}</div>
                    </li>
                  ))}
                </ul>
              </section>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Decision scorecard
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {(decisionPack.scorecard?.lines || []).map((line) => (
                    <li key={line.dimension}>
                      <div className="agi-list-title">
                        {line.dimension}{' '}
                        <span className="agi-list-meta">
                          {line.points > 0 ? `+${line.points}` : String(line.points)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Decision drift
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {(decisionPack.drift?.explanation_chain || ['No prior decision']).map((step) => (
                    <li key={step}>
                      <div className="agi-list-title">{productizeText(step)}</div>
                    </li>
                  ))}
                </ul>
              </section>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>Lineage</h3>
                <p className="agi-list-meta" style={{ marginTop: '0.5rem' }}>
                  {(decisionPack.lineage?.chain || []).join(' → ') ||
                    'Evidence → Reasons → Decision → Calibration → Report'}
                </p>
              </section>
            </>
          )}
        </div>
      )}

      {!loading && !error && tab === 'observations' && (
        <div>
          <h2 style={{ margin: '0 0 0.5rem', fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
            Observations
          </h2>
          <p className="agi-list-meta" style={{ marginBottom: '1rem' }}>
            Proactive institutional monitoring — material changes, severity, evidence lineage, and
            recommended actions. Small moves stay silent via hysteresis.
          </p>
          {!observationsPack ? (
            <div className="agi-empty">Observations unavailable for this ticker.</div>
          ) : (
            <>
              <div className="agi-stat-row">
                <div className="agi-stat">
                  <div className="agi-stat-label">Observations</div>
                  <div className="agi-stat-value">
                    {(observationsPack.observations || []).length}
                  </div>
                </div>
                <div className="agi-stat">
                  <div className="agi-stat-label">Critical / high</div>
                  <div className="agi-stat-value">
                    {
                      (observationsPack.observations || []).filter((o) =>
                        ['critical', 'high'].includes(o.severity)
                      ).length
                    }
                  </div>
                </div>
                <div className="agi-stat">
                  <div className="agi-stat-label">Pending review</div>
                  <div className="agi-stat-value">
                    {(observationsPack.observations || []).filter((o) => o.requires_review).length}
                  </div>
                </div>
              </div>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>Timeline</h3>
                {!(observationsPack.observations || []).length ? (
                  <div className="agi-empty" style={{ marginTop: '0.75rem' }}>
                    No material observations yet — graph updates may remain silent below hysteresis
                    thresholds.
                  </div>
                ) : (
                  <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                    {[...(observationsPack.observations || [])]
                      .reverse()
                      .map((o) => (
                        <li key={o.observation_id}>
                          <div className="agi-list-title">
                            {o.category}{' '}
                            <span className="agi-list-meta">[{o.severity}]</span>
                          </div>
                          <div className="agi-list-meta" style={{ marginTop: '0.35rem' }}>
                            {productizeText(o.summary)}
                          </div>
                          <div className="agi-list-meta" style={{ marginTop: '0.35rem' }}>
                            Evidence {o.evidence_snapshot_id || '—'}
                            {o.decision_changed
                              ? ` · Decision ${o.previous_decision || '—'} → ${o.current_decision || '—'}`
                              : ''}
                            {o.recommended_action ? ` · ${o.recommended_action}` : ''}
                          </div>
                        </li>
                      ))}
                  </ul>
                )}
              </section>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Decision changes
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {(observationsPack.decision_changes || [])
                    .filter((d) => d.changed)
                    .map((d, idx) => (
                      <li key={`dc-${idx}`}>
                        <div className="agi-list-title">
                          {d.previous || '—'} → {d.current || '—'}
                        </div>
                        <div className="agi-list-meta">
                          Confidence {d.previous_confidence ?? '—'} → {d.current_confidence ?? '—'}
                          {d.re_evaluated ? ' · re-evaluated' : ''}
                        </div>
                      </li>
                    ))}
                  {!(observationsPack.decision_changes || []).some((d) => d.changed) ? (
                    <li>
                      <div className="agi-list-meta">No recommendation changes in this cycle.</div>
                    </li>
                  ) : null}
                </ul>
              </section>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Recommended actions
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {(observationsPack.observations || []).map((o) => (
                    <li key={`act-${o.observation_id}`}>
                      <div className="agi-list-title">{o.recommended_action || 'Monitor'}</div>
                      <div className="agi-list-meta">
                        {(o.lineage || []).join(' → ') ||
                          'Evidence → Observation → Knowledge Graph → Reason → Decision → Calibration → Forecast → Report'}
                      </div>
                    </li>
                  ))}
                  {!(observationsPack.observations || []).length ? (
                    <li>
                      <div className="agi-list-meta">
                        {(observationsPack.plan || {}).recommended_action || 'No action'}
                      </div>
                    </li>
                  ) : null}
                </ul>
              </section>
            </>
          )}
        </div>
      )}

      {!loading && !error && tab === 'knowledge_graph' && (
        <div>
          <h2 style={{ margin: '0 0 0.5rem', fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
            Knowledge graph
          </h2>
          <p className="agi-list-meta" style={{ marginBottom: '1rem' }}>
            Evidence → relationships → reasons → decision → calibration → report — one company at a time.
          </p>
          {!knowledgeGraph ? (
            <div className="agi-empty">Knowledge graph unavailable for this ticker.</div>
          ) : (
            <>
              <div className="agi-stat-row">
                <div className="agi-stat">
                  <div className="agi-stat-label">Entities</div>
                  <div className="agi-stat-value">{knowledgeGraph.entity_count ?? 0}</div>
                </div>
                <div className="agi-stat">
                  <div className="agi-stat-label">Relationships</div>
                  <div className="agi-stat-value">{knowledgeGraph.relationship_count ?? 0}</div>
                </div>
                <div className="agi-stat">
                  <div className="agi-stat-label">Inferences</div>
                  <div className="agi-stat-value">{knowledgeGraph.inference_count ?? 0}</div>
                </div>
              </div>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>Lineage</h3>
                <p className="agi-list-meta" style={{ marginTop: '0.5rem' }}>
                  {(knowledgeGraph.lineage || []).join(' → ')}
                </p>
              </section>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Impact scores
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {Object.entries(knowledgeGraph.impact || {})
                    .filter(([k]) => k !== 'total')
                    .map(([label, pts]) => (
                      <li key={label}>
                        <div className="agi-list-title">
                          {label}{' '}
                          <span className="agi-list-meta">
                            {pts > 0 ? `+${pts}` : String(pts)}
                          </span>
                        </div>
                      </li>
                    ))}
                </ul>
              </section>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>Nodes</h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {(knowledgeGraph.nodes || [])
                    .filter((n) =>
                      ['Evidence', 'Reason', 'Decision', 'Calibration', 'FinancialMetric', 'Risk', 'ValuationMetric', 'MacroVariable'].includes(
                        n.type
                      )
                    )
                    .slice(0, 24)
                    .map((n) => (
                      <li key={n.id}>
                        <button
                          type="button"
                          className="agi-btn"
                          style={{
                            width: '100%',
                            textAlign: 'left',
                            opacity: selectedNodeId && selectedNodeId !== n.id ? 0.7 : 1,
                          }}
                          onClick={() => setSelectedNodeId(n.id)}
                        >
                          <div className="agi-list-title">
                            {n.type}: {productizeText(n.label)}
                          </div>
                          <div className="agi-list-meta">
                            confidence {formatConfidence(n.confidence)}
                            {n.impact_score
                              ? ` · impact ${n.impact_score > 0 ? `+${n.impact_score}` : n.impact_score}`
                              : ''}
                          </div>
                        </button>
                      </li>
                    ))}
                </ul>
              </section>

              {selectedNodeId ? (
                <section style={{ marginTop: '1.25rem' }}>
                  <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                    Selected node
                  </h3>
                  {(() => {
                    const node = (knowledgeGraph.nodes || []).find((n) => n.id === selectedNodeId);
                    if (!node) return null;
                    const rels = (knowledgeGraph.relationships || []).filter(
                      (r) => r.source_id === node.id || r.target_id === node.id
                    );
                    return (
                      <div style={{ marginTop: '0.75rem' }}>
                        <div className="agi-list-title">
                          {node.type}: {productizeText(node.label)}
                        </div>
                        <div className="agi-list-meta" style={{ marginTop: '0.35rem' }}>
                          Confidence {formatConfidence(node.confidence)}
                          {node.impact_score != null
                            ? ` · impact ${node.impact_score > 0 ? `+${node.impact_score}` : node.impact_score}`
                            : ''}
                        </div>
                        <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                          {rels.slice(0, 8).map((r) => (
                            <li key={r.id}>
                              <div className="agi-list-title">
                                {r.kind}: {productizeText(r.label || r.id)}
                              </div>
                            </li>
                          ))}
                        </ul>
                      </div>
                    );
                  })()}
                </section>
              ) : null}

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Decision path
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {(knowledgeGraph.paths?.decision_chain ||
                    knowledgeGraph.diagnostics?.decision_chain ||
                    []).map((nid) => {
                    const node = (knowledgeGraph.nodes || []).find((n) => n.id === nid);
                    return (
                      <li key={nid}>
                        <div className="agi-list-title">
                          {node ? `${node.type}: ${productizeText(node.label)}` : nid}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            </>
          )}
        </div>
      )}

      {!loading && !error && tab === 'forecast' && (
        <div>
          <h2 style={{ margin: '0 0 0.5rem', fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
            Forecast scenarios
          </h2>
          <p className="agi-list-meta" style={{ marginBottom: '1rem' }}>
            Explicit assumptions propagate through the knowledge graph — not price prediction.
          </p>
          {!forecastPack?.scenarios?.length ? (
            <div className="agi-empty">Forecast scenarios unavailable for this ticker.</div>
          ) : (
            <>
              <div className="agi-tabs" role="tablist" aria-label="Scenario cases">
                {(forecastPack.scenarios || []).map((s) => (
                  <button
                    key={s.scenario_name}
                    type="button"
                    role="tab"
                    aria-selected={selectedScenario === s.scenario_name}
                    className={selectedScenario === s.scenario_name ? 'active' : undefined}
                    onClick={() => setSelectedScenario(s.scenario_name)}
                  >
                    {String(s.scenario_name || '').toUpperCase()}
                  </button>
                ))}
              </div>

              {(() => {
                const active =
                  (forecastPack.scenarios || []).find((s) => s.scenario_name === selectedScenario) ||
                  forecastPack.scenarios[0];
                if (!active) return null;
                return (
                  <>
                    <div className="agi-stat-row" style={{ marginTop: '1rem' }}>
                      <div className="agi-stat">
                        <div className="agi-stat-label">Decision</div>
                        <div className="agi-stat-value" style={{ fontSize: '1.35rem' }}>
                          {active.resulting_decision}
                        </div>
                      </div>
                      <div className="agi-stat">
                        <div className="agi-stat-label">Confidence</div>
                        <div className="agi-stat-value">
                          {formatConfidence(active.resulting_confidence)}
                        </div>
                      </div>
                      <div className="agi-stat">
                        <div className="agi-stat-label">Probability</div>
                        <div className="agi-stat-value" style={{ fontSize: '1.15rem' }}>
                          {Math.round(Number(active.probability || 0) * 100)}%
                        </div>
                      </div>
                    </div>

                    <section style={{ marginTop: '1.25rem' }}>
                      <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                        Propagation
                      </h3>
                      <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                        {(active.graph_changes || []).slice(0, 10).map((step) => (
                          <li key={step}>
                            <div className="agi-list-title">{productizeText(step)}</div>
                          </li>
                        ))}
                      </ul>
                    </section>

                    <section style={{ marginTop: '1.25rem' }}>
                      <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                        Decision evolution
                      </h3>
                      <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                        {(active.reason_changes || [
                          `${active.base_decision || '—'} → ${active.resulting_decision}`,
                        ]).map((step) => (
                          <li key={step}>
                            <div className="agi-list-title">{productizeText(step)}</div>
                          </li>
                        ))}
                      </ul>
                    </section>
                  </>
                );
              })()}

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Scenario comparison
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {(forecastPack.comparison || []).map((c) => (
                    <li key={c.scenario}>
                      <div className="agi-list-title">
                        {String(c.scenario || '').toUpperCase()}: {c.decision}{' '}
                        <span className="agi-list-meta">
                          {formatConfidence(c.confidence)} · p={Math.round(Number(c.probability || 0) * 100)}%
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>

              <section style={{ marginTop: '1.25rem' }}>
                <h3 style={{ fontFamily: 'var(--agi-display)', fontSize: '1.15rem' }}>
                  Sensitivity
                </h3>
                <ul className="agi-list" style={{ marginTop: '0.75rem' }}>
                  {Object.entries(
                    forecastPack.sensitivity?.scorecard ||
                      forecastPack.scenarios?.[0]?.sensitivity?.scorecard ||
                      {}
                  ).map(([label, pts]) => (
                    <li key={label}>
                      <div className="agi-list-title">
                        {label}{' '}
                        <span className="agi-list-meta">
                          {pts > 0 ? `+${pts}` : String(pts)}
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </section>
            </>
          )}
        </div>
      )}

      {!loading && !error && tab === 'business_quality' && (
        <div>
          <div className="agi-score-block">
            <div className="agi-score-ring">
              <strong>{formatConfidence(qualityScore)}</strong>
              <span>Quality</span>
            </div>
            <div>
              <h2 style={{ margin: 0, fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
                Business Quality
              </h2>
              <p className="agi-list-meta" style={{ marginTop: '0.45rem' }}>
                {productizeText(firstBlockText(activeSection)) ||
                  'Large visual score with drivers and trend context.'}
              </p>
            </div>
          </div>
          <DriversList payload={qualityPayload} />
          {!Object.keys(qualityPayload).length && (
            <div className="agi-empty">Quality intelligence will appear when research layers are available.</div>
          )}
        </div>
      )}

      {!loading && !error && tab === 'financial_trends' && (
        <div>
          <h2 style={{ margin: '0 0 0.5rem', fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
            Financials
          </h2>
          <p className="agi-list-meta">
            Revenue, EBIT, margins, ROE, ROCE, cash flow, debt — institutional charts, not spreadsheets.
          </p>
          <MetricGrid payload={activeBoard.payload || activeBoard} />
          <p style={{ marginTop: '1rem' }}>{productizeText(firstBlockText(activeSection))}</p>
          {!activeBoard.available && !activeBoard.payload && (
            <div className="agi-empty">Financial intelligence pending for this company.</div>
          )}
        </div>
      )}

      {!loading && !error && tab === 'historical_timeline' && (
        <div>
          <h2 style={{ margin: '0 0 0.75rem', fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
            Timeline
          </h2>
          {timeline.length ? (
            <div className="agi-timeline">
              {[...timeline]
                .slice()
                .reverse()
                .slice(0, 24)
                .map((ev, i) => (
                  <div key={`${ev.at || i}-${ev.event_type || i}`} className="agi-timeline-item">
                    <div className="agi-timeline-when">{String(ev.at || '—').slice(0, 19)}</div>
                    <div className="agi-timeline-title">{eventLabel(ev)}</div>
                    <div className="agi-timeline-body">{productizeText(ev.summary || '')}</div>
                  </div>
                ))}
            </div>
          ) : (
            <div className="agi-empty">Timeline will fill as filings, calls, and research updates arrive.</div>
          )}
        </div>
      )}

      {!loading && !error && tab === 'evidence_references' && (
        <div>
          <h2 style={{ margin: '0 0 0.5rem', fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
            Evidence
          </h2>
          <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
            Every statement drills to original evidence — click through to the source trail.
          </p>
          <ul className="agi-list">
            {(evidence.length ? evidence : activeBoard.references || []).map((ref, i) => {
              const id = ref.evidence_id || ref.id || `ref-${i}`;
              const conf = ref.confidence;
              return (
                <li key={id}>
                  <div>
                    <div className="agi-list-title">{id}</div>
                    <div className="agi-list-meta">
                      {ref.source ? productizeText(String(ref.source)) : 'Evidence reference'}
                      {conf != null ? ` · confidence ${formatConfidence(conf)}` : ''}
                    </div>
                  </div>
                  <span className="agi-chip">Filing</span>
                </li>
              );
            })}
          </ul>
          {!evidence.length && !(activeBoard.references || []).length && (
            <div className="agi-empty">No evidence references on file yet.</div>
          )}
        </div>
      )}

      {!loading &&
        !error &&
        !['overview', 'business_quality', 'financial_trends', 'historical_timeline', 'evidence_references'].includes(
          tab
        ) && (
          <div>
            <h2 style={{ margin: '0 0 0.5rem', fontFamily: 'var(--agi-display)', fontSize: '1.5rem' }}>
              {COMPANY_TABS.find((t) => t.id === tab)?.label || 'Section'}
            </h2>
            <p style={{ marginBottom: '1rem' }}>
              {productizeText(firstBlockText(activeSection)) || 'Section assembled from institutional research.'}
            </p>
            {tab === 'research_notes' && (
              <ul className="agi-list">
                {(activeBoard.research_history || []).length ? (
                  (activeBoard.research_history || []).slice(0, 12).map((note, i) => (
                    <li key={note.id || i}>
                      <div>
                        <div className="agi-list-title">
                          {note.package_type || note.title || 'Research note'}
                        </div>
                        <div className="agi-list-meta">
                          {String(note.recorded_at || note.status || '').slice(0, 32)}
                        </div>
                      </div>
                    </li>
                  ))
                ) : (
                  <li>
                    <div className="agi-list-meta">No research notes on file.</div>
                  </li>
                )}
              </ul>
            )}
            {tab === 'watchlist_status' && (
              <ul className="agi-list">
                {(activeBoard.watchlists || []).length ? (
                  (activeBoard.watchlists || []).map((w, i) => (
                    <li key={w.id || i}>
                      <div className="agi-list-title">{w.name || w.list || 'Watchlist'}</div>
                      <div className="agi-list-meta">{w.status || 'Monitoring'}</div>
                    </li>
                  ))
                ) : (
                  <li>
                    <div className="agi-list-meta">Not on a research queue yet.</div>
                  </li>
                )}
              </ul>
            )}
            {tab === 'portfolio_references' && (
              <ul className="agi-list">
                {(activeBoard.memberships || []).length ? (
                  (activeBoard.memberships || []).map((m, i) => (
                    <li key={m.id || i}>
                      <div className="agi-list-title">{m.portfolio || m.name || 'Portfolio'}</div>
                      <div className="agi-list-meta">{m.weight != null ? `Weight ${m.weight}` : 'Holding'}</div>
                    </li>
                  ))
                ) : (
                  <li>
                    <div className="agi-list-meta">Not referenced in a portfolio.</div>
                  </li>
                )}
              </ul>
            )}
            {['business_strategy', 'management_execution'].includes(tab) && !activeBoard.available && (
              <div className="agi-empty">Intelligence for this section is not cached yet.</div>
            )}
          </div>
        )}
    </div>
  );
}
