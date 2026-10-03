import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  exportPublication,
  generatePublication,
  getCompanyRelationships,
  getPublication,
  getResearchWorkspaceCompany,
  getResearchWorkspacePortfolio,
  listPlatformPortfolios,
  listPublications,
  resolvePlatformWorkspace,
  searchResearchWorkspace,
} from '@/lib/intelligenceApi';

const NAV = [
  'Overview',
  'Timeline',
  'Evidence',
  'Decisions',
  'Risk',
  'Policy',
  'Committee',
  'Forecast',
  'Knowledge Graph',
  'Relationship Map',
  'Publications',
  'Notes',
  'Ask AGI',
];

const CONTEXTS = [
  { id: 'company', label: 'Company' },
  { id: 'portfolio', label: 'Portfolio' },
];

export default function ResearchWorkspacePage() {
  const [params, setParams] = useSearchParams();
  const context = (params.get('context') || 'company').toLowerCase();
  const ticker = (params.get('ticker') || 'AXISBANK').toUpperCase();
  const portfolioId = params.get('portfolio') || 'agi-core-equity';
  const clientId = params.get('client') || '';
  const tab = (params.get('tab') || 'Overview').replace(/_/g, ' ');
  const [workspace, setWorkspace] = useState(null);
  const [relationships, setRelationships] = useState(null);
  const [publications, setPublications] = useState([]);
  const [activePub, setActivePub] = useState(null);
  const [pubBusy, setPubBusy] = useState(false);
  const [platformPortfolios, setPlatformPortfolios] = useState([]);
  const [platformWorkspace, setPlatformWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState([]);

  const refreshPublications = () =>
    listPublications({ limit: 12 })
      .then((res) => setPublications(res?.publications || []))
      .catch(() => setPublications([]));

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    const load =
      context === 'portfolio'
        ? getResearchWorkspacePortfolio(portfolioId, { focus: 'overview' })
        : getResearchWorkspaceCompany(ticker, { focus: 'overview' });
    const relLoad =
      context === 'company'
        ? getCompanyRelationships(ticker).catch(() => null)
        : Promise.resolve(null);
    const platformLoad = Promise.all([
      listPlatformPortfolios().catch(() => null),
      context === 'portfolio'
        ? resolvePlatformWorkspace({
            portfolio_id: portfolioId,
            role_id: 'portfolio_manager',
            client_id: clientId,
          }).catch(() => null)
        : Promise.resolve(null),
    ]);
    Promise.all([load, relLoad, listPublications({ limit: 12 }).catch(() => null), platformLoad])
      .then(([res, rel, pubs, platform]) => {
        if (!active) return;
        if (!res || res.ok === false) {
          setError(res?.error || 'Workspace unavailable');
          setWorkspace(null);
        } else {
          setWorkspace(res.workspace || res);
        }
        setRelationships(rel && rel.ok !== false ? rel : null);
        setPublications(pubs?.publications || []);
        const [plist, pws] = platform || [];
        setPlatformPortfolios(plist?.portfolios || []);
        setPlatformWorkspace(pws && pws.ok !== false ? pws.workspace || pws : null);
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        setError(err?.message || 'Unable to load research workspace');
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [context, ticker, portfolioId, clientId]);

  const onGeneratePublication = async (publicationType) => {
    setPubBusy(true);
    try {
      const res = await generatePublication({
        publication_type: publicationType,
        ticker: context === 'company' ? ticker : undefined,
        portfolio_id: portfolioId,
        renderer: 'markdown',
        distribute_to: 'workspace',
        scope: clientId ? 'client' : 'portfolio',
        client_id: clientId || undefined,
        execution_context: platformWorkspace?.execution_context || {
          portfolio_id: portfolioId,
          client_id: clientId,
          role_id: 'portfolio_manager',
        },
      });
      if (res?.ok) {
        setActivePub(res.publication || null);
        await refreshPublications();
      }
    } finally {
      setPubBusy(false);
    }
  };

  const setContext = (id) => {
    const next = new URLSearchParams(params);
    next.set('context', id);
    setParams(next, { replace: true });
  };

  const setTab = (label) => {
    const next = new URLSearchParams(params);
    next.set('tab', label);
    setParams(next, { replace: true });
  };

  const onSearch = async (e) => {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    const res = await searchResearchWorkspace(q, {
      contextType: context === 'portfolio' ? 'portfolio' : 'company',
      contextId: context === 'portfolio' ? portfolioId : ticker,
    }).catch(() => null);
    setHits(res?.hits || []);
  };

  const activeNav = useMemo(() => {
    const match = NAV.find((n) => n.toLowerCase() === tab.toLowerCase());
    return match || 'Overview';
  }, [tab]);

  const askHref =
    workspace?.ask_deep_link ||
    (context === 'portfolio'
      ? `/agi/ask?context=portfolio&portfolio=${encodeURIComponent(portfolioId)}`
      : `/agi/ask?ticker=${encodeURIComponent(ticker)}`);

  return (
    <div>
      <h1 className="agi-greeting">Research Workspace</h1>
      <p className="agi-lede">
        The complete investment story — timeline, evidence, decisions, risk, policy, and committee —
        linked for reconstruction. Ask AGI points here; this is where analysts spend the day.
      </p>

      <div className="agi-tabs" role="tablist" aria-label="Workspace context">
        {CONTEXTS.map((c) => (
          <button
            key={c.id}
            type="button"
            className={context === c.id ? 'active' : undefined}
            onClick={() => setContext(c.id)}
          >
            {c.label}
          </button>
        ))}
      </div>

      {context === 'portfolio' && platformPortfolios.length ? (
        <div className="agi-tabs" role="tablist" aria-label="Platform portfolios">
          {platformPortfolios.slice(0, 8).map((p) => (
            <button
              key={p.portfolio_id}
              type="button"
              className={portfolioId === p.portfolio_id ? 'active' : undefined}
              onClick={() => {
                const next = new URLSearchParams(params);
                next.set('context', 'portfolio');
                next.set('portfolio', p.portfolio_id);
                setParams(next, { replace: true });
              }}
            >
              {p.name || p.portfolio_id}
            </button>
          ))}
        </div>
      ) : null}

      {platformWorkspace ? (
        <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
          MPC-01 · mandate {platformWorkspace.mandate} · policy {platformWorkspace.policy_profile} ·
          role {platformWorkspace.role_id || '—'} · intelligence global
          {platformWorkspace.ask_deep_link ? (
            <>
              {' · '}
              <Link to={platformWorkspace.ask_deep_link}>Ask in context</Link>
            </>
          ) : null}
        </p>
      ) : null}

      <div className="agi-meta-row" style={{ marginBottom: '0.75rem' }}>
        <span className="agi-chip">{context === 'portfolio' ? portfolioId : ticker}</span>
        <span className="agi-chip muted">RW-01</span>
        {workspace?.workspace_id ? (
          <span className="agi-chip muted">{workspace.workspace_id}</span>
        ) : null}
        <Link className="agi-chip ok" to={askHref}>
          Ask AGI
        </Link>
        {context === 'company' ? (
          <Link className="agi-chip" to={`/agi/companies/${ticker}?rw=1`}>
            Company page
          </Link>
        ) : (
          <Link className="agi-chip" to="/agi/portfolio?rw=1">
            Portfolio page
          </Link>
        )}
      </div>

      <div className="agi-tabs" role="tablist" aria-label="Workspace navigation">
        {NAV.map((n) => (
          <button
            key={n}
            type="button"
            className={activeNav === n ? 'active' : undefined}
            onClick={() => (n === 'Ask AGI' ? null : setTab(n))}
          >
            {n === 'Ask AGI' ? (
              <Link to={askHref} style={{ color: 'inherit', textDecoration: 'none' }}>
                Ask AGI
              </Link>
            ) : (
              n
            )}
          </button>
        ))}
      </div>

      <form className="agi-ask-input-wrap" style={{ margin: '1rem 0' }} onSubmit={onSearch}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search within workspace — capital allocation, CEO, buyback, risk…"
          aria-label="Search workspace"
        />
        <button type="submit" className="agi-btn agi-btn-primary">
          Search
        </button>
      </form>

      {hits.length ? (
        <section className="agi-section" style={{ marginBottom: '1rem' }}>
          <div className="agi-section-head">
            <h2>Search results</h2>
          </div>
          <ul className="agi-list">
            {hits.map((h, i) => (
              <li key={`${h.kind}-${h.title}-${i}`}>
                <div className="agi-list-title">
                  [{h.kind}] {h.title}
                </div>
                <div className="agi-list-meta">
                  {h.object_type}
                  {h.href ? (
                    <>
                      {' · '}
                      <Link to={h.href}>Open</Link>
                    </>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {loading && <div className="agi-empty">Loading research workspace…</div>}
      {error && <div className="agi-error">{error}</div>}

      {!loading && !error && workspace ? (
        <div className="agi-grid-2">
          <section className="agi-section">
            <div className="agi-section-head">
              <h2>{activeNav}</h2>
              <span className="agi-list-meta">{workspace.title}</span>
            </div>

            {(activeNav === 'Overview' || activeNav === 'Timeline') && (
              <ul className="agi-list">
                {(workspace.timeline || []).map((e) => (
                  <li key={e.event_id || e.title}>
                    <div className="agi-list-title">
                      [{e.kind}] {e.title}
                    </div>
                    <div className="agi-list-meta">
                      {e.object_type} · {e.summary}
                    </div>
                  </li>
                ))}
                {!(workspace.timeline || []).length ? (
                  <li>
                    <div className="agi-list-meta">Timeline will fill as objects link.</div>
                  </li>
                ) : null}
              </ul>
            )}

            {activeNav === 'Evidence' && (
              <ul className="agi-list">
                {(workspace.evidence || []).map((e) => (
                  <li key={e.evidence_id || e.title}>
                    <div className="agi-list-title">{e.title}</div>
                    <div className="agi-list-meta">
                      {e.source_type} · {(e.linked_object_ids || []).join(', ') || 'unlinked'}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {(activeNav === 'Decisions' ||
              activeNav === 'Risk' ||
              activeNav === 'Policy' ||
              activeNav === 'Committee' ||
              activeNav === 'Forecast' ||
              activeNav === 'Knowledge Graph') && (
              <ul className="agi-list">
                {(workspace.linked_objects || [])
                  .filter((o) => {
                    const t = (o.object_type || '').toLowerCase();
                    if (activeNav === 'Decisions') return t.includes('decision');
                    if (activeNav === 'Risk') return t.includes('risk');
                    if (activeNav === 'Policy') return t.includes('policy');
                    if (activeNav === 'Committee') return t.includes('committee');
                    if (activeNav === 'Forecast') return t.includes('forecast') || t.includes('scenario');
                    return true;
                  })
                  .map((o) => (
                    <li key={`${o.object_type}-${o.object_id}`}>
                      <div className="agi-list-title">{o.label}</div>
                      <div className="agi-list-meta">
                        {o.object_type} · {o.relation}
                        {o.href ? (
                          <>
                            {' · '}
                            <Link to={o.href}>Open</Link>
                          </>
                        ) : null}
                      </div>
                      {o.summary ? <div className="agi-list-meta">{o.summary}</div> : null}
                    </li>
                  ))}
              </ul>
            )}

            {activeNav === 'Relationship Map' && (
              <div>
                <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
                  CCI-01 · Company → Competitors → Sector → Portfolio → Macro Drivers. KG-01 remains
                  the graph system of record; CCI reasons over it.
                </p>
                {!relationships ? (
                  <div className="agi-empty">Relationship map unavailable for this context.</div>
                ) : (
                  <>
                    <div className="agi-stat-row" style={{ marginBottom: '0.75rem' }}>
                      <div className="agi-stat">
                        <div className="agi-stat-label">Competitors</div>
                        <div className="agi-stat-value">
                          {(relationships.competitors || []).length}
                        </div>
                      </div>
                      <div className="agi-stat">
                        <div className="agi-stat-label">Macro</div>
                        <div className="agi-stat-value">
                          {(relationships.macro_drivers || []).length}
                        </div>
                      </div>
                      <div className="agi-stat">
                        <div className="agi-stat-label">KG-01</div>
                        <div className="agi-stat-value" style={{ fontSize: '1rem' }}>
                          {relationships.kg_ref?.ok ? 'linked' : 'soft'}
                        </div>
                      </div>
                    </div>
                    <ul className="agi-list">
                      {(relationships.competitors || []).slice(0, 8).map((c) => (
                        <li key={c}>
                          <div className="agi-list-title">Competitor · {c}</div>
                          <div className="agi-list-meta">
                            <Link to={`/agi/companies/${c}?rw=1`}>Open</Link>
                            {' · '}
                            <Link to={`/agi/research?ticker=${c}&tab=Relationship%20Map`}>Map</Link>
                          </div>
                        </li>
                      ))}
                      {(relationships.macro_drivers || []).map((m) => (
                        <li key={m}>
                          <div className="agi-list-title">Macro · {m}</div>
                          <div className="agi-list-meta">Dependency propagation — not a forecast</div>
                        </li>
                      ))}
                      {(relationships.similar || []).slice(0, 5).map((s) => (
                        <li key={s.ticker}>
                          <div className="agi-list-title">
                            Similar · {s.ticker} ({Number(s.score).toFixed(2)})
                          </div>
                          <div className="agi-list-meta">{(s.reasons || []).join(' · ')}</div>
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}

            {activeNav === 'Publications' && (
              <div>
                <p className="agi-list-meta" style={{ marginBottom: '0.75rem' }}>
                  PUB-01 · Compose-only institutional deliverables. Templates format; manifests
                  audit. No new analysis.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginBottom: '0.85rem' }}>
                  {(context === 'portfolio'
                    ? ['PortfolioReview', 'RiskSummary', 'InvestmentCommitteePack', 'WeeklyClientReport']
                    : ['CompanyResearchNote', 'InvestmentSnapshot', 'DecisionUpdate', 'MorningBrief']
                  ).map((t) => (
                    <button
                      key={t}
                      type="button"
                      className="agi-btn"
                      disabled={pubBusy}
                      onClick={() => onGeneratePublication(t)}
                    >
                      Generate {t}
                    </button>
                  ))}
                </div>
                <ul className="agi-list">
                  {publications.map((p) => (
                    <li key={p.publication_id}>
                      <button
                        type="button"
                        onClick={() =>
                          getPublication(p.publication_id)
                            .then((res) => setActivePub(res?.publication || p))
                            .catch(() => setActivePub(p))
                        }
                        style={{ all: 'unset', cursor: 'pointer' }}
                      >
                        <div className="agi-list-title">{p.title || p.publication_type}</div>
                        <div className="agi-list-meta">
                          {p.publication_type} · v{p.version || '1'} · {p.status} ·{' '}
                          {(p.lineage_hash || '').slice(0, 10) || 'no hash'}
                        </div>
                      </button>
                    </li>
                  ))}
                  {!publications.length ? (
                    <li>
                      <div className="agi-list-meta">No publications yet — generate one above.</div>
                    </li>
                  ) : null}
                </ul>
                {activePub ? (
                  <div className="agi-panel" style={{ marginTop: '1rem' }}>
                    <div className="agi-section-head">
                      <h2>{activePub.title || activePub.publication_type}</h2>
                      <button
                        type="button"
                        className="agi-btn"
                        onClick={() =>
                          exportPublication({
                            publication_id: activePub.publication_id,
                            renderer: 'markdown',
                            target: 'export',
                          }).then(() => refreshPublications())
                        }
                      >
                        Export
                      </button>
                    </div>
                    <p className="agi-list-meta">
                      Sources: {activePub.source_count ?? (activePub.source_objects || []).length} ·
                      Manifest lineage:{' '}
                      {(activePub.lineage_hash || activePub.manifest?.lineage_hash || '—').slice(0, 16)}
                    </p>
                    {activePub.body_markdown ? (
                      <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', marginTop: '0.75rem' }}>
                        {String(activePub.body_markdown).slice(0, 1800)}
                      </pre>
                    ) : null}
                  </div>
                ) : null}
              </div>
            )}

            {activeNav === 'Notes' && (
              <ul className="agi-list">
                {(workspace.notes || []).map((n) => (
                  <li key={n.note_id}>
                    <div className="agi-list-title">{n.title}</div>
                    <div className="agi-list-meta">
                      Analyst note · {(n.tags || []).join(', ') || 'untagged'} · never mutates system
                      intelligence
                    </div>
                    <p className="agi-list-meta" style={{ marginTop: '0.35rem' }}>
                      {n.body}
                    </p>
                  </li>
                ))}
                {!(workspace.notes || []).length ? (
                  <li>
                    <div className="agi-list-meta">No analyst notes yet.</div>
                  </li>
                ) : null}
              </ul>
            )}
          </section>

          <section className="agi-section">
            <div className="agi-section-head">
              <h2>Linked objects</h2>
            </div>
            <ul className="agi-list">
              {(workspace.linked_objects || []).map((o) => (
                <li key={`${o.object_type}-${o.object_id}`}>
                  <div className="agi-list-title">{o.label}</div>
                  <div className="agi-list-meta">
                    {o.object_type}
                    {o.href ? (
                      <>
                        {' · '}
                        <Link to={o.href}>Navigate</Link>
                      </>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
            <div className="agi-panel" style={{ marginTop: '1rem' }}>
              <div className="agi-section-head">
                <h2>Diagnostics</h2>
              </div>
              <p className="agi-list-meta" style={{ margin: 0 }}>
                Missing links: {(workspace.diagnostics?.missing_links || []).length} · Timeline gaps:{' '}
                {workspace.diagnostics?.timeline_gaps ?? '—'} · Orphaned notes:{' '}
                {workspace.diagnostics?.orphaned_notes ?? '—'} · Presentation only
              </p>
            </div>
          </section>
        </div>
      ) : null}
    </div>
  );
}
