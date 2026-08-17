import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ArrowLeft, Database, RefreshCw, TrendingUp } from 'lucide-react';
import { getMiDashboard, getMiSector } from '@/lib/intelligenceApi';
import { getFeaturedMarketResearchNote, noteAuthor, noteThemes } from '@/lib/marketResearchNote';
import useMarketIntelligence from '@/hooks/useMarketIntelligence';
import useMarketSnapshot from '@/hooks/useMarketSnapshot';
import './marketSectorIntelligence.css';

function fmt(v, d = 2) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(d);
  return String(v);
}

function fmtFlow(buy, sell) {
  if (buy != null) return fmt(buy);
  if (sell != null) return fmt(-sell);
  return '—';
}

function breadthHint(b) {
  const adv = b.advancing ?? 0;
  const dec = b.declining ?? 0;
  const flat = b.unchanged ?? 0;
  let hint = `${adv}↑ ${dec}↓ ${flat}→`;
  if (b.universe_total != null && b.not_tracked > 0) {
    hint += ` · ${b.not_tracked} untracked`;
  }
  return hint;
}

function Stat({ label, value, hint, className = '' }) {
  return (
    <div className={`msi-stat ${className}`}>
      <span className="k">{label}</span>
      <span className="v">{value}</span>
      {hint ? <span className="h">{hint}</span> : null}
    </div>
  );
}

function valuationRegime(percentile) {
  const value = Number(percentile);
  if (!Number.isFinite(value)) return { label: 'Coverage pending', tone: 'coverage' };
  if (value <= 10) return { label: 'Deep discount', tone: 'deep-discount' };
  if (value <= 25) return { label: 'Discount', tone: 'discount' };
  if (value <= 60) return { label: 'Fair', tone: 'fair' };
  if (value <= 80) return { label: 'Premium', tone: 'premium' };
  if (value <= 90) return { label: 'Expensive', tone: 'expensive' };
  return { label: 'Extreme premium', tone: 'extreme-premium' };
}

function signedPercent(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '—';
  return `${n > 0 ? '+' : ''}${fmt(n, 1)}%`;
}

function IndexStrip({ items = [] }) {
  return (
    <div className="msi-index-strip" aria-label="Market index strip">
      {items.map((item) => {
        const change = Number(String(item.hint || '').replace('%', ''));
        const tone = Number.isFinite(change) ? (change > 0 ? 'up' : change < 0 ? 'down' : 'flat') : 'flat';
        return (
          <div className="msi-index-tick" key={item.key}>
            <span>{item.label}</span>
            <strong>{fmt(item.value)}</strong>
            <em className={tone}>{item.hint}</em>
          </div>
        );
      })}
    </div>
  );
}

/** Index cards for MSI overview — prefer live snapshot quotes; else AGI sentiment labels. */
function buildIndexCards(snapshotItems = [], indexSentiments = [], pulseIndices = []) {
  const live = (Array.isArray(snapshotItems) ? snapshotItems : [])
    .filter((row) => row && (row.name || row.symbol) && Number(row.price || row.ltp || row.value) > 0)
    .slice(0, 5)
    .map((row) => {
      const change = row.percentChange ?? row.change_pct ?? row.changePct;
      return {
        key: row.name || row.symbol,
        label: row.name || row.symbol,
        value: row.price ?? row.ltp ?? row.value,
        hint: change != null && change !== '' ? `${fmt(Number(change))}%` : 'Live quote',
      };
    });
  if (live.length) return live;

  const sentiments = (Array.isArray(indexSentiments) && indexSentiments.length
    ? indexSentiments
    : Array.isArray(pulseIndices)
      ? pulseIndices
      : [])
    .filter((row) => row && (row.label || row.name || row.symbol || row.key))
    .slice(0, 5)
    .map((row) => {
      const label = row.label || row.name || row.symbol || row.key;
      const quote = row.value ?? row.ltp ?? row.price;
      if (quote != null && quote !== '') {
        const change = row.change_pct ?? row.percentChange;
        return {
          key: row.key || label,
          label,
          value: quote,
          hint:
            change != null && change !== ''
              ? `${fmt(Number(change))}%`
              : row.sentiment || 'Index',
        };
      }
      return {
        key: row.key || label,
        label,
        value: row.sentiment || 'Pending',
        hint: row.strength || 'AGI index signal',
      };
    });
  return sentiments;
}

function Section({ title, subtitle, children }) {
  return (
    <section className="msi-section">
      <header>
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </header>
      {children}
    </section>
  );
}

function Sparkline({ points = [], current }) {
  const values = points.map((point) => Number(point?.value)).filter(Number.isFinite);
  const all = Number.isFinite(Number(current)) ? [...values, Number(current)] : values;
  if (all.length < 2) return <p className="msi-hint">Verified historical points will appear as coverage develops.</p>;
  const lo = Math.min(...all);
  const hi = Math.max(...all);
  const span = Math.max(hi - lo, 0.0001);
  const coordinates = values.map((value, index) => {
    const x = 4 + (index * 232) / Math.max(values.length - 1, 1);
    const y = 58 - ((value - lo) / span) * 48;
    return `${x},${y}`;
  }).join(' ');
  return (
    <div className="msi-chart" aria-label="Historical valuation series">
      <svg viewBox="0 0 240 64" role="img">
        <line x1="4" x2="236" y1="58" y2="58" />
        <polyline points={coordinates} fill="none" />
      </svg>
      <div className="msi-chart-labels"><span>{points[0]?.period || 'History'}</span><span>{points.at(-1)?.period || 'Current'}</span></div>
    </div>
  );
}

function CoverageBadge({ snapshot = {} }) {
  const confidence = snapshot.confidence || 'Insufficient';
  return <span className={`msi-confidence msi-confidence-${confidence.toLowerCase()}`}>{confidence} confidence</span>;
}

export default function MarketSectorIntelligence() {
  const { indexSentiments = [], pulse } = useMarketIntelligence();
  const { items: snapshotItems = [] } = useMarketSnapshot();
  const [pack, setPack] = useState(null);
  const [sectorPack, setSectorPack] = useState(null);
  const [selectedSector, setSelectedSector] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editorialNote, setEditorialNote] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getMiDashboard();
      setPack(data);
      if (data?.degraded) {
        setError(data.hint || data.error || 'Dashboard is temporarily degraded — showing cached or partial data.');
      } else if (!data?.ok) {
        setError(data?.error || 'Dashboard unavailable');
      }
    } catch (err) {
      setError(err?.message || 'Failed to load market intelligence');
      setPack(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Open a useful research workspace immediately rather than leaving the
  // client at a heatmap with no sector context.
  useEffect(() => {
    if (!selectedSector && pack?.ok && pack?.sectors?.[0]?.sector) openSector(pack.sectors[0].sector);
  // openSector intentionally only changes when a sector is chosen.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pack, selectedSector]);

  useEffect(() => {
    getFeaturedMarketResearchNote().then(setEditorialNote).catch(() => setEditorialNote(null));
  }, []);

  useEffect(() => {
    document.body.classList.add('agi-terminal-route');
    return () => document.body.classList.remove('agi-terminal-route');
  }, []);

  const openSector = async (sector) => {
    setSelectedSector(sector);
    setSectorPack(null);
    try {
      const data = await getMiSector(sector);
      setSectorPack(data);
    } catch {
      setSectorPack(null);
    }
  };

  const overview = pack?.overview || {};
  const regime = pack?.market_regime || {};
  const marketHealth = pack?.market_health || {};
  const drivers = pack?.market_drivers?.drivers || [];
  const breadth = pack?.breadth || {};
  const flows = pack?.flows || {};
  const heatmap = pack?.sector_heatmap || [];
  const sectors = pack?.sectors || [];
  const opps = pack?.opportunities?.cards || [];
  const priorities = pack?.research_priorities || [];
  const rotation = pack?.rotation || {};
  const selectedResearch = sectorPack?.research || {};
  const indexCards = useMemo(
    () => buildIndexCards(snapshotItems, indexSentiments, pulse?.indices || []),
    [snapshotItems, indexSentiments, pulse],
  );
  const breadthTracked = breadth.tracked_universe || breadth.sample_size || 0;
  const breadthUniverse = breadth.universe_total || overview.companies || 0;
  const breadthCoverageLow = Number(breadth.coverage_pct) < 20;
  const valuationRead = Number(marketHealth.market_historical_percentile) <= 25
    ? 'Below historical median'
    : Number(marketHealth.market_historical_percentile) >= 75
      ? 'Above historical median'
      : 'Near historical median';
  const flowRead = flows.available
    ? (flows.latest_values_available === false ? 'Awaiting EOD' : (flows.explanation || 'Mixed'))
    : 'Not yet available';
  const riskRead = Number(marketHealth.overall) >= 70 ? 'Contained' : Number(marketHealth.overall) >= 45 ? 'Moderate' : 'Elevated';

  return (
    <div className="msi-root">
      <header className="msi-header">
        <div className="msi-head-row">
          <div>
            <Link to="/market-intelligence" className="msi-back"><ArrowLeft size={13} /> Market desk</Link>
            <p className="msi-kicker"><Activity size={13} /> Market + Sector Intelligence</p>
            <div className="msi-head-meta">
              <span>India Equities</span><i>·</i><span>{fmt(overview.companies, 0)} Companies</span><i>·</i><span className="history-active">10Y History Active</span>
              <i>·</i><span>As of {overview.valuation_date || '—'}</span><i>·</i><span>P/E Coverage {overview.coverage?.pct != null ? `${fmt(overview.coverage.pct, 1)}%` : '—'}</span>
            </div>
          </div>
          <button type="button" className="msi-btn" onClick={load} disabled={loading}>
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
        {pack?.ok ? (
          <div className="msi-command-bar" aria-label="Sector research controls">
            <div><span>Sector intelligence</span><strong>India equities</strong></div>
            <label>Sector
              <select value={selectedSector || ''} onChange={(event) => openSector(event.target.value)}>
                {sectors.map((sector) => <option key={sector.sector} value={sector.sector}>{sector.sector}</option>)}
              </select>
            </label>
            <div className="msi-command-meta"><span>Metric: {sectorPack?.valuation?.primary_metric_label || 'Primary valuation'}</span><span>Period: 10Y</span><span>As of {overview.valuation_date || '—'}</span></div>
          </div>
        ) : null}
      </header>

      <main className="msi-workbench">
        {pack?.ok ? <aside className="msi-left-rail" aria-label="Sector navigator">
          <span className="msi-rail-label">Sectors</span>
          <div className="msi-rail-sectors">
            {sectors.map((sector) => <button type="button" key={sector.sector} className={selectedSector === sector.sector ? 'on' : ''} onClick={() => openSector(sector.sector)}>
              <span>{sector.sector}</span><b>{sector.historical_percentile != null ? fmt(sector.historical_percentile, 0) : '—'}</b>
            </button>)}
          </div>
          <p>Percentile shown against each sector’s verified valuation history.</p>
        </aside> : null}
        <div className="msi-body">
        {error ? <div className={`msi-error${pack?.degraded ? ' msi-degraded' : ''}`}>{error}</div> : null}
        {loading ? <p className="msi-hint">Loading market intelligence…</p> : null}

        {pack?.ok ? (
          <>
            <Section title="Market state" subtitle={`Constitution v${pack.constitution || '2.0'} · live index snapshot + verified warehouse valuation`}>
              <div className="msi-index-row">
                {indexCards.length ? (
                  <IndexStrip items={indexCards} />
                ) : (
                  <p className="msi-hint">Index quotes unavailable from live gateway for this session.</p>
                )}
              </div>
              <div className="msi-grid msi-intelligence-strip">
                <Stat label="Market regime" value={regime.regime || '—'} hint={regime.drivers?.slice(0, 2).join(' · ')} />
                <Stat label="Market health" value={marketHealth.overall != null ? `${marketHealth.overall}/100` : '—'} />
                <Stat label="Hist %ile" value={marketHealth.market_historical_percentile != null ? `${fmt(marketHealth.market_historical_percentile, 0)}rd` : '—'} hint="Sector median" />
                <Stat label="Median P/E" value={overview.averages?.pe != null ? `${fmt(overview.averages.pe)}x` : '—'} />
                <Stat label="Median P/B" value={overview.averages?.pb != null ? `${fmt(overview.averages.pb)}x` : '—'} />
                <Stat label="EV/EBITDA" value={overview.averages?.ev_ebitda != null ? `${fmt(overview.averages.ev_ebitda)}x` : '—'} />
                <Stat label="Breadth" value={breadth.heatmap || '—'} hint={breadthHint(breadth)} />
                <Stat className={breadthCoverageLow ? 'msi-stat-warning' : ''} label="Breadth coverage" value={breadth.coverage_pct != null ? `${fmt(breadth.coverage_pct, 1)}%` : '—'} hint={`${breadthTracked} / ${breadthUniverse || '—'} · ${breadthCoverageLow ? 'Low coverage' : 'Verified'}`} />
              </div>
              {breadth.universe_definition ? <p className="msi-hint">{breadth.universe_definition}</p> : null}
              {pack.summary ? <p className="msi-market-sentence">{pack.summary}</p> : null}
            </Section>

            {editorialNote ? (
              <section className="msi-editorial-note">
                <div className="msi-editorial-topline"><span>AGI Research Note</span><time>{new Date(editorialNote.published_at || editorialNote.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</time></div>
                <h2>{editorialNote.title}</h2>
                {editorialNote.meta_description ? <p className="msi-editorial-subtitle">{editorialNote.meta_description}</p> : null}
                {editorialNote.excerpt ? <p className="msi-editorial-summary">{editorialNote.excerpt}</p> : null}
                {noteThemes(editorialNote.tags).length ? <div className="msi-editorial-themes"><span>Key themes</span><ul>{noteThemes(editorialNote.tags).map((theme) => <li key={theme}>{theme}</li>)}</ul></div> : null}
                <div className="msi-editorial-footer"><span>{noteAuthor(editorialNote.tags)}</span><Link to={`/article/${editorialNote.slug}`}>Read full note →</Link></div>
              </section>
            ) : null}

            <Section
              title="Sector valuation map"
              subtitle={`Historical valuation percentile · data through ${overview.valuation_date || '—'} · colours describe valuation range, not expected return · click a sector`}
            >
              <div className="msi-sector-nav" aria-label="Sector navigation">
                {sectors.map((s) => (
                  <button type="button" key={`nav-${s.sector}`} onClick={() => openSector(s.sector)} className={selectedSector === s.sector ? 'on' : ''}>
                    {s.sector}<small>{s.historical_percentile != null ? `${fmt(s.historical_percentile, 0)}%ile` : 'coverage'}</small>
                  </button>
                ))}
              </div>
              <div className="msi-heatmap">
                {heatmap.map((s) => {
                  const regimeInfo = valuationRegime(s.historical_percentile);
                  const metric = s.primary_metric_label || 'Metric';
                  return <button
                    type="button"
                    key={s.sector}
                    className={`msi-heat-cell msi-heat-${regimeInfo.tone} ${selectedSector === s.sector ? 'on' : ''}`}
                    onClick={() => openSector(s.sector)}
                  >
                    <div className="msi-heat-top"><strong>{s.sector}</strong><b>
                      {s.historical_percentile != null
                        ? `${fmt(s.historical_percentile, 0)}%ile`
                        : (s.historical_percentile_status === 'DATA_QUALITY_FAIL' ? 'unreliable' : 'coverage developing')}
                    </b></div>
                    <span className="tag">{regimeInfo.label}</span>
                    <div className="msi-heat-values">
                      <span>{metric}<b>{fmt(s.current)}</b></span>
                      <span>10Y median<b>{fmt(s.historical_median)}</b></span>
                      <span>Δ<b>{signedPercent(s.historical_premium_pct ?? s.premium_pct)}</b></span>
                    </div>
                    <span className="msi-obs">{s.historical_years ? `${s.historical_years}Y` : '—'} · <i className={`confidence-dot ${String(s.historical_confidence || 'low').toLowerCase()}`} />{s.historical_confidence || 'Developing'}</span>
                  </button>;
                })}
              </div>
            </Section>

            {selectedSector && sectorPack?.ok ? (
              <>
                <Section title={`${selectedSector} — sector workspace`} subtitle={sectorPack.agi_sector_intelligence}>
                  <div className="msi-sector-workspace">
                  <div className="msi-sector-hero msi-sector-snapshot">
                    <div className="msi-sector-title"><span>AGI Sector View</span><h2>{selectedSector}</h2><CoverageBadge snapshot={selectedResearch.snapshot} /></div>
                    <div className="msi-grid sm">
                      <Stat label="Valuation regime" value={selectedResearch.view?.valuation || '—'} />
                      <Stat label="Historical percentile" value={sectorPack.valuation?.historical_percentile != null ? `${fmt(sectorPack.valuation.historical_percentile, 0)}%ile` : 'Developing'} />
                      <Stat label={sectorPack.valuation?.primary_metric_label || 'Primary metric'} value={fmt(sectorPack.valuation?.current)} />
                      <Stat label="Historical median" value={fmt(sectorPack.valuation?.historical_median)} />
                      <Stat label="Companies" value={fmt(selectedResearch.snapshot?.companies || sectorPack.companies, 0)} />
                      <Stat label="Historical coverage" value={selectedResearch.snapshot?.coverage_pct != null ? `${fmt(selectedResearch.snapshot.coverage_pct, 0)}%` : '—'} hint={`${selectedResearch.snapshot?.historical_years || 0} verified years`} />
                    </div>
                  </div>
                  <div className="msi-workspace-chart">
                    <span className="msi-workspace-label">10Y valuation context</span>
                    <h3>{sectorPack.valuation?.primary_metric_label || 'Primary valuation'} — current vs historical range</h3>
                    <Sparkline points={selectedResearch.valuation_history?.points} current={selectedResearch.valuation_history?.current} />
                    <div className="msi-band-grid">
                      {Object.entries(selectedResearch.valuation_history?.bands || {}).slice(0, 5).map(([label, value]) => <Stat key={label} label={label} value={fmt(value)} />)}
                    </div>
                  </div>
                  <aside className="msi-sector-view">
                    <span className="msi-workspace-label">AGI sector view</span>
                    <Stat label="Valuation" value={selectedResearch.view?.valuation || '—'} />
                    {(selectedResearch.fundamentals || []).slice(0, 4).map((item) => <Stat key={item.key} label={item.label} value={item.interpretation || '—'} hint={item.current != null ? `Current ${fmt(item.current)}` : undefined} />)}
                    <Stat label="Data quality" value={selectedResearch.snapshot?.confidence || '—'} hint={`${selectedResearch.snapshot?.historical_years || 0} verified years`} />
                  </aside>
                  </div>
                </Section>

                <Section title="Valuation intelligence" subtitle={`${selectedResearch.valuation_history?.label || 'Primary valuation metric'} · ${selectedResearch.valuation_history?.source || 'verified warehouse history'}`}>
                  <div className="msi-detail-grid">
                    <div>
                      <Sparkline points={selectedResearch.valuation_history?.points} current={selectedResearch.valuation_history?.current} />
                      <p className="msi-hint">Current value is ranked against valid historical sector observations. Missing constituents reduce coverage; they do not erase the available history.</p>
                    </div>
                    <div className="msi-band-grid">
                      {Object.entries(selectedResearch.valuation_history?.bands || {}).map(([label, value]) => <Stat key={label} label={label} value={fmt(value)} />)}
                    </div>
                  </div>
                </Section>

                <Section title="Fundamental intelligence" subtitle="Current sector medians from the verified company universe; coverage is shown per metric.">
                  <div className="msi-fundamentals">
                    {(selectedResearch.fundamentals || []).map((item) => <Stat key={item.key} label={item.label} value={fmt(item.current)} hint={`${item.interpretation} · ${fmt(item.coverage_pct, 0)}% coverage`} />)}
                  </div>
                </Section>

                <Section title="Industry breakdown" subtitle="Constituent industries ranked by covered company count.">
                  <div className="msi-table-wrap"><table className="msi-table"><thead><tr><th>Industry</th><th>Companies</th><th>Median P/E</th><th>Median P/B</th><th>Median ROE</th></tr></thead><tbody>
                    {(selectedResearch.industries || []).map((row) => <tr key={row.industry}><td><strong>{row.industry}</strong></td><td>{row.companies}</td><td>{fmt(row.median_pe)}</td><td>{fmt(row.median_pb)}</td><td>{fmt(row.median_roe)}</td></tr>)}
                  </tbody></table></div>
                </Section>

                <Section title="Company leaders and valuation context" subtitle="Largest constituents first. This is a research starting point, not a security recommendation.">
                  <div className="msi-table-wrap"><table className="msi-table"><thead><tr><th>Company</th><th>Industry</th><th>P/E</th><th>P/B</th><th>ROE</th><th>Hist. %ile</th></tr></thead><tbody>
                    {(selectedResearch.companies || []).slice(0, 15).map((row) => <tr key={row.symbol}><td><Link to={`/valuation-terminal?symbol=${encodeURIComponent(row.symbol || '')}`}>{row.company_name || row.symbol}</Link></td><td>{row.industry || '—'}</td><td>{fmt(row.pe)}</td><td>{fmt(row.pb)}</td><td>{fmt(row.roe)}</td><td>{row.historical_percentile != null ? `${fmt(row.historical_percentile, 0)}%ile` : '—'}</td></tr>)}
                  </tbody></table></div>
                </Section>
              </>
            ) : null}

            <Section
              title="Sector intelligence"
              subtitle={
                sectors.some((s) => (s.upstox_coverage_pct || 0) > 0)
                  ? 'Primary metric · current · AGI sector benchmark · premium · opportunity'
                  : 'Primary metric · current · sector benchmark awaits AGI key-ratio coverage'
              }
            >
              <div className="msi-table-wrap">
                <table className="msi-table">
                  <thead>
                    <tr>
                      <th>Sector</th>
                      <th>Metric</th>
                      <th>Current</th>
                      <th>Sector</th>
                      <th>Premium</th>
                      <th>History</th>
                      <th>Hist range</th>
                      <th>AGI Coverage</th>
                      <th>Cos</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sectors.map((s) => (
                      <tr key={s.sector} onClick={() => openSector(s.sector)} className="click">
                        <td><strong>{s.sector}</strong></td>
                        <td>{s.primary_metric_label}</td>
                        <td>{fmt(s.current)}</td>
                        <td>
                          {(s.upstox_coverage_pct || 0) > 0
                            ? fmt(s.sector_benchmark ?? s.historical_median)
                            : '—'}
                        </td>
                        <td>
                          {(s.upstox_coverage_pct || 0) > 0 && s.premium_pct != null
                            ? `${fmt(s.premium_pct, 1)}%`
                            : '—'}
                        </td>
                        <td title={s.historical_percentile_reason || ''}>
                          {s.historical_percentile != null
                            ? `${fmt(s.historical_percentile, 0)}%ile`
                            : (s.historical_percentile_status === 'INSUFFICIENT_HISTORY'
                              ? `Limited (${s.historical_observations || 0})`
                              : s.historical_percentile_status === 'DATA_QUALITY_FAIL'
                                ? 'unreliable'
                                : '—')}
                        </td>
                        <td>{s.historical_range_status || s.opportunity}</td>
                        <td>{s.upstox_coverage_pct != null ? `${fmt(s.upstox_coverage_pct, 0)}%` : '—'}</td>
                        <td>{fmt(s.companies, 0)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>

            <Section
              title="Institutional flow (FII / DII)"
              subtitle={
                flows.available
                  ? flows.latest_values_available === false
                    ? `History through ${flows.latest_date} · latest session unavailable`
                    : `Latest ${flows.latest_date}`
                  : 'Warehouse institutional_flow'
              }
            >
              {flows.available ? (
                <>
                  <div className="msi-grid">
                    <Stat
                      label="FII net"
                      value={
                        flows.latest_values_available === false
                          ? 'Awaiting EOD print'
                          : fmtFlow(flows.fii_net_buy ?? flows.fii_net, flows.fii_net_sell)
                      }
                    />
                    <Stat
                      label="DII net"
                      value={
                        flows.latest_values_available === false
                          ? 'Awaiting EOD print'
                          : fmtFlow(flows.dii_net_buy ?? flows.dii_net, flows.dii_net_sell)
                      }
                    />
                    <Stat
                      label="Combined"
                      value={flows.latest_values_available === false ? '—' : fmt(flows.net_institutional_flow)}
                    />
                    <Stat label="5D trend" value={fmt(flows.trend_5d)} />
                    <Stat label="20D trend" value={fmt(flows.trend_20d)} />
                  </div>
                  {flows.latest_values_available === false ? (
                    <p className="msi-hint">
                      Flow history exists through {flows.latest_date || 'recent sessions'}, but net FII/DII
                      values are still null in the AGI warehouse and may arrive after the end-of-day processing window.
                    </p>
                  ) : null}
                  {flows.explanation ? <p className="msi-note">{flows.explanation}</p> : null}
                </>
              ) : (
                <div className="msi-empty-flow">
                  <p className="msi-hint"><strong>No data collected yet</strong></p>
                  <p className="msi-hint">Last successful refresh: Never</p>
                  <p className="msi-hint">
                    Daily EOD ingest runs automatically at 18:05 IST after market close
                    (AGI collection → quality validation → warehouse). Admin may also trigger refresh from Mission Control.
                  </p>
                </div>
              )}
            </Section>

            <Section title="Today’s research candidates" subtitle="Evidence-backed starting points for research — not recommendations">
              <div className="msi-opp-grid">
                {opps.slice(0, 12).map((c) => (
                  <article key={`${c.kind}-${c.symbol}`} className="msi-opp-card">
                    <span className="kind">{c.kind.replace(/_/g, ' ')}</span>
                    <h3>{c.company_name || c.symbol}</h3>
                    <p>{c.why}</p>
                    <Link to={`/valuation-terminal?symbol=${encodeURIComponent(c.symbol)}`}>Open valuation →</Link>
                  </article>
                ))}
              </div>
            </Section>

            <Section title="Research priorities" subtitle="Ranked for analyst attention today">
              <div className="msi-table-wrap">
                <table className="msi-table">
                  <thead>
                    <tr><th>Rank</th><th>Company</th><th>Reason</th><th>Confidence</th></tr>
                  </thead>
                  <tbody>
                    {priorities.map((p) => (
                      <tr key={p.rank}>
                        <td>{p.rank}</td>
                        <td><Link to={`/valuation-terminal?symbol=${p.symbol}`}>{p.company_name || p.symbol}</Link></td>
                        <td>{p.reason}</td>
                        <td>{fmt(p.confidence, 0)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>

            {drivers.length ? (
              <Section title="Market drivers" subtitle="Top institutional drivers today — magnitude and affected sectors">
                <ul className="msi-explain">
                  {drivers.map((d) => (
                    <li key={d.driver}>
                      <strong>{d.driver}</strong> ({d.direction}) — {d.detail}
                      {d.affected_sectors?.length ? ` · Sectors: ${d.affected_sectors.join(', ')}` : ''}
                    </li>
                  ))}
                </ul>
              </Section>
            ) : null}

            {pack.rotation?.explanation ? (
              <Section title="Market rotation" subtitle="Valuation rotation — compression → expansion; this is not a measured fund-flow claim.">
                <p className="msi-note">{pack.rotation.explanation}</p>
                <div className="msi-grid sm">
                  {(pack.rotation.leaving || []).length ? (
                    <Stat
                      label="Leaving"
                      value={(rotation.leaving || []).map((r) => r.sector).join(', ')}
                      hint={(rotation.leaving || []).map((r) => `${r.median_pe_change_pct ?? r.avg_pe_change_pct}%`).join(', ')}
                    />
                  ) : null}
                  {(pack.rotation.entering || []).length ? (
                    <Stat
                      label="Entering"
                      value={(rotation.entering || []).map((r) => r.sector).join(', ')}
                      hint={(rotation.entering || []).map((r) => `${r.median_pe_change_pct ?? r.avg_pe_change_pct}%`).join(', ')}
                    />
                  ) : null}
                </div>
              </Section>
            ) : null}

            {pack.explainability?.length ? (
              <Section title="Market explainability" subtitle="Dependency-graph attribution">
                <ul className="msi-explain">
                  {pack.explainability.map((e) => (
                    <li key={e.sector}><strong>{e.sector}</strong> — {e.summary}</li>
                  ))}
                </ul>
              </Section>
            ) : null}

            <Section title="Provenance & validation" subtitle="Constitution v2.0 — auditable warehouse-backed intelligence">
              <div className="msi-prov">
                <div><span>Valuation</span><strong>{pack.provenance?.valuation}</strong></div>
                <div><span>Price / breadth</span><strong>{pack.provenance?.price}</strong></div>
                <div><span>Fresh through</span><strong>{overview.valuation_date || '—'}</strong></div>
                <div><span>Engine</span><strong>{pack.engine} v{pack.version}</strong></div>
                <div><span>Coverage</span><strong>{fmt(pack.coverage?.companies, 0)} cos</strong></div>
                <div><span>Validation</span><strong>{pack.validation?.publishable ? 'Passed' : `${pack.validation?.checks_passed || 0}/${pack.validation?.checks_total || 0} checks`}</strong></div>
                <div><span>Confidence</span><strong className="msi-hint-inline">{pack.confidence?.methodology?.slice(0, 80)}…</strong></div>
                <div><span>Historical hierarchy</span><strong><Database size={13} /> AGI source records → normalized warehouse → HVIE → verified ratios</strong></div>
              </div>
            </Section>
          </>
        ) : null}

        {!loading && !pack?.ok && !error ? (
          <p className="msi-hint"><TrendingUp size={14} /> Waiting for warehouse valuation coverage.</p>
        ) : null}
        </div>
        {pack?.ok ? <aside className="msi-right-rail" aria-label="AGI research intelligence">
          <section className="msi-rail-panel">
            <span className="msi-rail-label">AGI Market View</span>
            <dl><div><dt>Regime</dt><dd>{regime.regime || '—'}</dd></div><div><dt>Valuation</dt><dd>{valuationRead}</dd></div><div><dt>Breadth</dt><dd>{breadth.heatmap || '—'}</dd></div><div><dt>Flows</dt><dd>{flowRead}</dd></div><div><dt>Risk</dt><dd>{riskRead}</dd></div></dl>
          </section>
          {editorialNote ? <section className="msi-rail-panel msi-rail-note"><span className="msi-rail-label">AGI Research Note</span><time>{new Date(editorialNote.published_at || editorialNote.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}</time><h2>{editorialNote.title}</h2><p>{editorialNote.excerpt || editorialNote.meta_description}</p>{noteThemes(editorialNote.tags).length ? <ul>{noteThemes(editorialNote.tags).slice(0, 4).map((theme) => <li key={theme}>{theme}</li>)}</ul> : null}<Link to={`/article/${editorialNote.slug}`}>Read note →</Link></section> : null}
          <section className="msi-rail-panel"><span className="msi-rail-label">Market risks</span><ul><li>{breadthCoverageLow ? 'Breadth coverage remains low' : 'Breadth conditions require monitoring'}</li><li>{riskRead} market-risk regime</li><li>{flows.latest_values_available === false ? 'Institutional flow update awaiting EOD' : 'Earnings and valuation dispersion'}</li></ul></section>
          {drivers[0] ? <section className="msi-rail-panel"><span className="msi-rail-label">Latest intelligence</span><strong>{drivers[0].driver}</strong><p>{drivers[0].detail}</p></section> : null}
          <Link className="msi-rail-ask" to="/ask-agi">Ask AGI about this market →</Link>
        </aside> : null}
      </main>
    </div>
  );
}
