import { useEffect, useMemo, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import API_ORIGIN from '@/config';
import {
  STRATEGIES, LIVE_STRATEGIES, SIZING_MATH, LIMITS, VALIDATION_LABELS,
  DEFAULT_SCREEN, isValidated, caveatOf,
} from '@/lib/hedgeFundStrategies';
import './hedgeFundDesk.css';

/* --------------------------------------------------------------- utilities */

const n = (v) => (v === null || v === undefined || v === '' || !Number.isFinite(Number(v)) ? null : Number(v));

function fmt(value, col) {
  const v = n(value);
  if (col?.type === 'text') return value == null || value === '' ? '—' : String(value).replaceAll('_', ' ');
  if (v === null) return '—';
  if (col?.money) {
    if (Math.abs(v) >= 1e9) return `₹${(v / 1e9).toFixed(1)}bn`;
    if (Math.abs(v) >= 1e7) return `₹${(v / 1e7).toFixed(1)}cr`;
    return `₹${v.toFixed(0)}`;
  }
  const s = v.toFixed(col?.dp ?? 2);
  return `${col?.signed && v > 0 ? '+' : ''}${s}${col?.suffix || ''}`;
}

/** Display equation. Wide formulas scroll inside their container on mobile. */
function Equation({ label, tex, note }) {
  const html = useMemo(
    () => katex.renderToString(tex, { displayMode: true, throwOnError: false, strict: false }),
    [tex],
  );
  return (
    <div className="hd-eq">
      <div className="hd-eq-label">{label}</div>
      <div className="hd-eq-render" role="math" aria-label={label}
           dangerouslySetInnerHTML={{ __html: html }} />
      {note ? <p className="hd-eq-note">{note}</p> : null}
    </div>
  );
}

/**
 * Recomputes the strategy's formula from the raw payload and shows it beside
 * the engine's own number. If the two ever diverge it becomes visible here
 * rather than silently contradicting the maths printed above it.
 */
function ArithmeticCheck({ strategy, row }) {
  const checks = useMemo(() => {
    try { return strategy.verify?.(row) || null; } catch { return null; }
  }, [strategy, row]);
  if (!checks?.length) return null;
  return (
    <div className="hd-check">
      <div className="hd-label" style={{ marginBottom: '0.4rem' }}>
        Recomputed from {row.ticker}
      </div>
      {checks.map((c) => {
        const shown = c.actual === null || c.actual === undefined;
        const agree = !shown && Math.abs(c.expected - c.actual) < 10 ** -(c.dp ?? 2) * 5;
        return (
          <div className="hd-check-row" key={c.label}>
            <span>{c.label}</span>
            <b className={shown ? '' : agree ? 'hd-check-ok' : 'hd-check-bad'}>
              {c.expected.toFixed(c.dp ?? 2)}
              {shown ? '' : ` vs ${c.actual.toFixed(c.dp ?? 2)} ${agree ? '✓' : '✗'}`}
            </b>
          </div>
        );
      })}
    </div>
  );
}

function Stage({ card }) {
  if (!card) return <span className="hd-stage">No data</span>;
  if (card.governance) {
    const mapped = card.governance.mapped !== false;
    return <span className={`hd-stage ${mapped ? 'exp' : 'blocked'}`}>{mapped ? card.governance.stage : 'Unmapped'}</span>;
  }
  return <span className="hd-stage exp">Experimental</span>;
}

/* -------------------------------------------------------------------- page */

export default function HedgeFundDesk() {
  const [data, setData] = useState(null);
  const [live, setLive] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [active, setActive] = useState(DEFAULT_SCREEN);
  const [showFlagged, setShowFlagged] = useState(false);

  const load = async () => {
    setLoading(true); setError('');
    try {
      if (!API_ORIGIN) throw new Error('AGI backend origin is not configured.');
      const json = async (path) => {
        const res = await fetch(`${API_ORIGIN}${path}`, { headers: { Accept: 'application/json' } });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (!(res.headers.get('content-type') || '').includes('application/json')) {
          throw new Error('invalid response');
        }
        return res.json();
      };
      const [snapshot, intraday] = await Promise.allSettled([
        json('/api/intelligence/hedge-fund-lab/terminal?limit=40'),
        json('/api/intelligence/hedge-fund-lab/live-strategies?limit=25'),
      ]);
      if (snapshot.status === 'fulfilled') setData(snapshot.value);
      else throw new Error(`The desk feed is unavailable (${snapshot.reason?.message}).`);
      // The intraday board is additive: if it fails those cards report it and
      // the nine fundamental screens are unaffected.
      setLive(intraday.status === 'fulfilled' ? intraday.value : null);
    } catch (e) {
      setError(e.message || 'The desk feed is unavailable.');
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const cards = useMemo(() => {
    const byId = Object.fromEntries((data?.cards || []).map((c) => [c.id, c]));
    const liveById = Object.fromEntries((live?.cards || []).map((c) => [c.strategy, c]));
    return [
      ...STRATEGIES.map((s) => ({ ...s, card: byId[s.id] || null })),
      ...LIVE_STRATEGIES.map((s) => {
        const c = liveById[s.id];
        return {
          ...s,
          // Shape the intraday payload like a terminal card so one renderer
          // serves both. Intraday screens compute live rather than from the
          // 15-minute snapshot, so they carry no validation_status.
          card: c ? { ...c, id: s.id, count: c.count, results: c.results,
                      suitability_stars: 0 } : null,
        };
      }),
    ];
  }, [data, live]);

  const strategy = useMemo(
    () => cards.find((s) => s.id === active) || cards[0], [cards, active],
  );

  const rows = strategy?.card?.results || [];
  const flagged = rows.filter((r) => !isValidated(r));
  const clean = rows.filter(isValidated);
  const visible = showFlagged ? rows : (clean.length ? clean : []);

  const regime = data?.regime || {};
  const hero = data?.hero || {};
  const queue = data?.research_queue || [];

  return (
    <div className="hd-root">
      <Helmet>
        <title>Hedge Fund Desk | AGI</title>
        <meta name="description" content="Systematic equity research screens with the mathematics, evidence and limitations of each shown in full." />
      </Helmet>

      {/* ---------------------------------------------------- masthead */}
      <header className="hd-masthead">
        <div className="hd-shell hd-masthead-inner">
          <div>
            <div className="hd-label">Agarwal Global Investments</div>
            <h1>Hedge Fund Desk</h1>
            <p>
              Systematic research screens over the listed Indian universe. Each screen shows the
              mathematics it computes, the evidence behind every row, and the reasons it is not
              yet a validated strategy.
            </p>
          </div>
          <div className="hd-asof">
            <b>{data?.as_of || '—'}</b>
            <span>{(data?.cache?.source === 'supabase' ? 'Snapshot' : 'Live')} · {data?.status || '…'}</span>
          </div>
        </div>
      </header>

      {/* ------------------------------------------------------ regime */}
      <section className="hd-regime" aria-label="Market regime">
        <div className="hd-shell">
          <div className="hd-regime-grid">
            <div className="hd-regime-cell accent">
              <b>{regime.stance || '—'}</b><span>Regime stance</span>
            </div>
            <div className="hd-regime-cell">
              <b>{n(regime.breadth_advancing_pct) ?? '—'}%</b><span>Breadth advancing</span>
            </div>
            <div className="hd-regime-cell">
              <b>{n(regime.median_pe)?.toFixed(1) ?? '—'}</b><span>Median P/E</span>
            </div>
            <div className="hd-regime-cell">
              <b>{n(regime.median_return_1y_pct)?.toFixed(1) ?? '—'}%</b><span>Median 1Y return</span>
            </div>
            <div className="hd-regime-cell">
              <b>{(n(regime.universe) ?? n(hero.universe_scanned) ?? 0).toLocaleString('en-IN')}</b>
              <span>Universe scanned</span>
            </div>
            <div className="hd-regime-cell">
              <b>{(n(hero.companies_flagged) ?? 0).toLocaleString('en-IN')}</b><span>Companies flagged</span>
            </div>
          </div>
        </div>
      </section>

      <div className="hd-shell">
        {error ? (
          <div className="hd-section">
            <div className="hd-error">
              <b><AlertTriangle size={14} style={{ verticalAlign: '-2px' }} /> Desk feed unavailable</b>
              {error}
              <div style={{ marginTop: '0.7rem' }}>
                <button type="button" className="hd-stage" onClick={load} style={{ cursor: 'pointer' }}>
                  <RefreshCw size={11} style={{ verticalAlign: '-1px' }} /> Retry
                </button>
              </div>
            </div>
          </div>
        ) : null}

        {/* -------------------------------------------------- screens */}
        <section className="hd-section">
          <div className="hd-section-head">
            <div>
              <h2>Research screens</h2>
              <p>
                Counts are live. A screen showing zero is reported with its reason rather than
                hidden — an empty screen is information about the data, not an absence of it.
              </p>
            </div>
          </div>

          {loading && !data ? (
            <div className="hd-cards">
              {STRATEGIES.map((s) => (
                <div className="hd-card" key={s.id}>
                  <div className="hd-skeleton" style={{ width: '60%' }} />
                  <div className="hd-skeleton" style={{ width: '90%', height: 26 }} />
                  <div className="hd-skeleton" style={{ width: '80%' }} />
                </div>
              ))}
            </div>
          ) : (
            <div className="hd-cards" role="tablist" aria-label="Research screens">
              {cards.map((s) => {
                const count = s.card?.count ?? 0;
                const blocked = Boolean(s.blockedBy);
                return (
                  <button
                    key={s.id}
                    type="button"
                    role="tab"
                    className="hd-card"
                    aria-selected={active === s.id}
                    onClick={() => setActive(s.id)}
                  >
                    <div className="hd-card-top">
                      <span className="hd-card-name">{s.name}</span>
                      <span className={`hd-card-count ${count ? '' : 'zero'}`}>{count}</span>
                    </div>
                    <span className="hd-card-edge">{s.edge}</span>
                    <div className="hd-card-foot">
                      {blocked ? <span className="hd-stage blocked">Blocked</span> : <Stage card={s.card} />}
                      <span className="hd-stars">
                        {'★'.repeat(n(s.card?.suitability_stars) || 0)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* ------------------------------------------------ detail */}
          {strategy ? (
            <div className="hd-detail">
              <div className="hd-detail-head">
                <div className="hd-label">{strategy.family} · {strategy.card?.count ?? 0} candidates</div>
                <h3>{strategy.name}</h3>
                <p className="hd-question">{strategy.question}</p>
                <p className="hd-thesis">{strategy.thesis}</p>
                {strategy.card?.governance ? (
                  <p className="hd-thesis">
                    Governed as <b>{strategy.card.governance.canonical_strategy_id}</b>
                    {' '}· {String(strategy.card.governance.role || '').replaceAll('_', ' ')}
                    {' '}· capital blocked
                  </p>
                ) : null}
              </div>

              <div className="hd-split">
                <div className="hd-pane">
                  <h4>Candidates</h4>

                  {strategy.blockedBy ? (
                    <div className="hd-notice blocked">
                      <b>Screen blocked. </b>{strategy.blockedBy}
                    </div>
                  ) : null}

                  {flagged.length ? (
                    <div className="hd-notice">
                      <b>{flagged.length} of {rows.length} rows are not validated. </b>
                      {VALIDATION_LABELS[flagged[0].validation_status]
                        || 'The engine could not validate these values.'}
                      {' '}
                      <button type="button" className="hd-stage"
                              style={{ cursor: 'pointer', marginLeft: '0.4rem' }}
                              onClick={() => setShowFlagged((v) => !v)}>
                        {showFlagged ? 'Hide flagged' : 'Show anyway'}
                      </button>
                    </div>
                  ) : null}

                  {!visible.length ? (
                    <div className="hd-empty">
                      {strategy.blockedBy
                        ? 'No candidates — the screen cannot run.'
                        : flagged.length
                          ? 'No candidate passed validation. Only flagged rows are available.'
                          : 'No company currently meets this screen.'}
                    </div>
                  ) : (
                    <div className="hd-table-wrap">
                      <table className="hd-table">
                        <thead>
                          <tr>
                            <th>Company</th>
                            {strategy.columns.map((c) => <th key={c.key}>{c.label}</th>)}
                            <th>Conf.</th>
                          </tr>
                        </thead>
                        <tbody>
                          {visible.map((r, i) => {
                            const key = r.ticker || `${r.industry}-${i}`;
                            const legs = strategy.pairLegs && r.long_leg && r.short_leg;
                            return (
                              <tr key={key}>
                                <td className="hd-tick">
                                  {legs ? (
                                    <>
                                      <b>{r.long_leg.ticker} / {r.short_leg.ticker}</b>
                                      <span>long / short</span>
                                    </>
                                  ) : (
                                    <>
                                      <b>{r.ticker}</b>
                                      <span>{r.company_name || r.sector || ''}</span>
                                    </>
                                  )}
                                  {!isValidated(r) ? <span className="hd-flag">unvalidated</span> : null}
                                  {caveatOf(r) ? <span className="hd-flag">{caveatOf(r)}</span> : null}
                                </td>
                                {strategy.columns.map((c) => {
                                  const v = n(r[c.key]);
                                  const cls = c.signed && v !== null ? (v > 0 ? 'hd-pos' : v < 0 ? 'hd-neg' : '') : '';
                                  return <td key={c.key} className={cls}>{fmt(r[c.key], c)}</td>;
                                })}
                                <td>{n(r.confidence) !== null ? n(r.confidence).toFixed(0) : '—'}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {strategy.source === 'live' && visible[0]?.sizing ? (
                    <div className="hd-block">
                      <h4>Position sizing — {visible[0].ticker}</h4>
                      <div className="hd-readout-wrap">
                        <table className="hd-table">
                          <thead>
                            <tr>
                              <th>Company</th><th>σ̂ ann.</th><th>Vol-target w</th>
                              <th>Liquidity cap</th><th>Target w</th><th>Binding</th><th>Notional</th>
                            </tr>
                          </thead>
                          <tbody>
                            {visible.slice(0, 8).map((r) => {
                              const s = r.sizing || {};
                              return (
                                <tr key={`sz-${r.ticker}`}>
                                  <td className="hd-tick"><b>{r.ticker}</b></td>
                                  <td>{s.annualised_vol != null ? `${(s.annualised_vol * 100).toFixed(1)}%` : '—'}</td>
                                  <td>{s.vol_target_weight != null ? `${(s.vol_target_weight * 100).toFixed(2)}%` : '—'}</td>
                                  <td>{s.liquidity_cap_weight != null ? `${(s.liquidity_cap_weight * 100).toFixed(2)}%` : '—'}</td>
                                  <td><b>{s.target_weight != null ? `${(s.target_weight * 100).toFixed(2)}%` : '—'}</b></td>
                                  <td className="hd-why" style={{ whiteSpace: 'nowrap' }}>
                                    {String(s.binding_constraint || '—').replaceAll('_', ' ')}
                                  </td>
                                  <td>{s.notional_inr != null
                                    ? `₹${(s.notional_inr / 1e7).toFixed(2)}cr` : '—'}</td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                      <p className="hd-eq-note" style={{ marginTop: '0.6rem' }}>
                        Target weight is the smallest of the volatility target, the liquidity cap and
                        the per-name maximum. The binding column names which one applied. A row that
                        cannot be sized states the missing input rather than assuming one.
                      </p>
                    </div>
                  ) : null}

                  {visible[0]?.why ? (
                    <div className="hd-block">
                      <h4>Why {visible[0].ticker || 'the top candidate'} surfaced</h4>
                      <p className="hd-eq-note">{visible[0].why}</p>
                    </div>
                  ) : null}
                </div>

                <div className="hd-pane">
                  <h4>The mathematics</h4>
                  {strategy.math.map((eq) => <Equation key={eq.label} {...eq} />)}
                  {visible[0] ? <ArithmeticCheck strategy={strategy} row={visible[0]} /> : null}

                  <div className="hd-block">
                    <h4>Where this breaks</h4>
                    <ul className="hd-risks">
                      {strategy.risks.map((r) => <li key={r}><span>{r}</span></li>)}
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          ) : null}
        </section>

        {/* --------------------------------------------------- sizing */}
        <section className="hd-section">
          <div className="hd-section-head">
            <div>
              <h2>Position sizing</h2>
              <p>
                Applies across every screen. A ranking without sizing is not a portfolio — these
                are the constraints that turn a list of names into positions you could hold.
              </p>
            </div>
          </div>
          <div className="hd-detail">
            <div className="hd-split" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
              {SIZING_MATH.map((eq, i) => (
                <div className="hd-pane" key={eq.label}
                     style={i ? { borderLeft: '1px solid var(--hd-line)' } : undefined}>
                  <Equation {...eq} />
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ---------------------------------------------------- queue */}
        {queue.length ? (
          <section className="hd-section">
            <div className="hd-section-head">
              <div>
                <h2>Research queue</h2>
                <p>Companies surfacing on more than one screen, ranked by combined confidence.</p>
              </div>
            </div>
            <div className="hd-queue">
              {queue.slice(0, 10).map((q) => (
                <div className="hd-queue-row" key={q.ticker}>
                  <i>{String(q.rank).padStart(2, '0')}</i>
                  <div className="hd-queue-name">
                    <b>{q.ticker}</b>
                    <span>
                      {q.company_name}
                      {q.strategies?.length ? ` · ${q.strategies.join(', ')}` : ''}
                    </span>
                  </div>
                  <div className="hd-queue-score">
                    {n(q.unified_score)?.toFixed(1) ?? '—'}
                    <span>{q.confluence_label || 'score'}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {/* --------------------------------------------------- limits */}
        <section className="hd-section">
          <div className="hd-section-head">
            <div>
              <h2>What is not validated</h2>
              <p>
                Read this before the screens above. Nothing on this page has passed a costed
                point-in-time backtest, so none of it constitutes demonstrated alpha.
              </p>
            </div>
          </div>
          <div className="hd-limits">
            {LIMITS.map(([name, status, detail]) => (
              <div className="hd-limit" key={name}>
                <div className="hd-limit-top">
                  <b>{name}</b>
                  <span className={`hd-stage ${status === 'FAILING' ? 'blocked' : 'exp'}`}>{status}</span>
                </div>
                <p>{detail}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <footer className="hd-foot">
        <div className="hd-shell">
          <p>
            Research observations only — no buy, sell, or price target, and no offer or
            solicitation. AGI operates a research platform; it does not manage outside capital,
            execute trades, or act as a broker. Screen output is a research priority, not a
            forecast or a probability of return. Figures are as of{' '}
            {data?.as_of || 'the last completed session'} and are not independently audited.
          </p>
        </div>
      </footer>
    </div>
  );
}
