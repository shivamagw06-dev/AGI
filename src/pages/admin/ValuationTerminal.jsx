import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  RefreshCw,
  Star,
  Clock,
  Search,
  Info,
  X,
} from 'lucide-react';
import {
  Line,
  LineChart as RLineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  getSveMarket,
  getSveSectors,
  getVtCompany,
  getVtExplain,
  getVtHealth,
  getVtInsights,
  getVtSeries,
  searchVtCompanies,
} from '@/lib/intelligenceApi';
import SectorValuationWorkspace, {
  MarketSnapshot,
  ResearchBoards,
  SectorDirectory,
} from '@/pages/admin/SectorValuationWorkspace';
import CoverageHealthPanel from '@/pages/admin/CoverageHealthPanel';
import { CompanyAttributionPanel } from '@/pages/admin/ValuationAttributionPanel';
import ResearchDossierPanel from '@/pages/admin/ResearchDossierPanel';
import ForecastPanel from '@/pages/admin/ForecastPanel';
import MacroPanel from '@/pages/admin/MacroPanel';
import './valuationIntelligence.css';
import './valuationTerminal.css';
import './sectorValuationExplorer.css';
import './valuationAttribution.css';
import './coverageHealth.css';
import './researchIntelligence.css';

const METRIC_LABELS = {
  pe: 'P/E',
  forward_pe: 'Fwd P/E',
  pb: 'P/B',
  ev_ebitda: 'EV/EBITDA',
  ev_sales: 'EV/Sales',
  ps: 'P/S',
  roe: 'ROE %',
  eps: 'EPS',
  dividend_yield: 'Div Yield %',
  market_cap: 'Market Cap',
  price: 'Price',
  revenue: 'Revenue',
};

const CHART_METRICS = ['price', 'pe', 'pb', 'ev_ebitda', 'revenue', 'eps', 'roe', 'dividend_yield'];
const WINDOWS = ['1Y', '3Y', '5Y', '10Y', 'MAX'];
const RECENT_KEY = 'agi.vt.recent';
const FAV_KEY = 'agi.vt.favorites';
const NOTES_KEY = 'agi.vt.research-notes';

function fmt(v, digits = 2) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1e11) return `${(v / 1e10).toFixed(1)}k cr`;
    if (Math.abs(v) >= 1e7) return `${(v / 1e7).toFixed(0)} cr`;
    if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  }
  return String(v);
}

function readList(key) {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || '[]');
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

function writeList(key, items) {
  try {
    localStorage.setItem(key, JSON.stringify(items.slice(0, 12)));
  } catch {
    /* ignore */
  }
}

function readObject(key) {
  try {
    const raw = JSON.parse(localStorage.getItem(key) || '{}');
    return raw && typeof raw === 'object' && !Array.isArray(raw) ? raw : {};
  } catch {
    return {};
  }
}

function writeObject(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* Notes remain local-only when browser storage is unavailable. */
  }
}

function positionClass(pos) {
  if (!pos) return '';
  if (pos === 'Premium' || pos === 'Above') return 'vt-pos-up';
  if (pos === 'Discount' || pos === 'Below') return 'vt-pos-down';
  return 'vt-pos-flat';
}

function MetricModal({ metric, onClose }) {
  const [body, setBody] = useState(null);
  useEffect(() => {
    if (!metric) return;
    getVtExplain(metric).then(setBody).catch(() => setBody(null));
  }, [metric]);
  if (!metric) return null;
  return (
    <div className="vi-modal-backdrop" onClick={onClose}>
      <div className="vi-modal" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="vt-close" onClick={onClose} aria-label="Close">
          <X size={16} />
        </button>
        <h2>{body?.label || METRIC_LABELS[metric] || metric}</h2>
        {body?.ok ? (
          <div className="vt-explain">
            <p><strong>What it is.</strong> {body.what}</p>
            <p><strong>Why it matters.</strong> {body.why}</p>
            <p><strong>Where it applies.</strong> {body.where}</p>
            <p><strong>How to read it.</strong> {body.interpret}</p>
          </div>
        ) : (
          <p className="hint">No explanation available for this metric.</p>
        )}
      </div>
    </div>
  );
}

function CompanySearch({ onSelect, recent, favorites, onToggleFavorite }) {
  const [q, setQ] = useState('');
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const boxRef = useRef(null);

  useEffect(() => {
    if (!q.trim()) {
      setItems([]);
      setSearching(false);
      setSearchError('');
      return undefined;
    }
    setSearching(true);
    setSearchError('');
    const t = setTimeout(() => {
      searchVtCompanies(q.trim(), 10)
        .then((r) => {
          setItems(r?.suggestions || []);
          setSearchError('');
        })
        .catch((err) => {
          setItems([]);
          const msg = String(err?.message || '');
          setSearchError(
            /recovering|502|503|504|timed out|timeout|unavailable/i.test(msg)
              ? 'Search is temporarily unavailable — the intelligence engine is busy. Retry in a moment.'
              : (msg || 'Company search failed.'),
          );
        })
        .finally(() => setSearching(false));
    }, 180);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    const onDoc = (e) => {
      if (!boxRef.current?.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const pick = (symbol, name) => {
    onSelect(symbol, name);
    setQ('');
    setOpen(false);
  };

  return (
    <div className="vt-search" ref={boxRef}>
      <div className="vt-search-bar">
        <Search size={16} />
        <input
          value={q}
          placeholder="Search Axis Bank, ICICI Bank, Infosys, TCS…"
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
        />
      </div>
      {open ? (
        <div className="vt-search-panel">
          {q.trim() && items.length ? (
            <ul>
              {items.map((s) => (
                <li key={s.symbol}>
                  <button type="button" onClick={() => pick(s.symbol, s.name)}>
                    <strong>{s.symbol}</strong>
                    <span>{s.name}</span>
                  </button>
                  <button
                    type="button"
                    className={`vt-fav ${favorites.some((f) => f.symbol === s.symbol) ? 'on' : ''}`}
                    onClick={() => onToggleFavorite(s.symbol, s.name)}
                    aria-label="Favorite"
                  >
                    <Star size={14} />
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {!q.trim() && favorites.length ? (
            <div className="vt-search-block">
              <div className="k"><Star size={12} /> Favorites</div>
              <ul>
                {favorites.map((s) => (
                  <li key={s.symbol}>
                    <button type="button" onClick={() => pick(s.symbol, s.name)}>
                      <strong>{s.symbol}</strong>
                      <span>{s.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {!q.trim() && recent.length ? (
            <div className="vt-search-block">
              <div className="k"><Clock size={12} /> Recent</div>
              <ul>
                {recent.map((s) => (
                  <li key={s.symbol}>
                    <button type="button" onClick={() => pick(s.symbol, s.name)}>
                      <strong>{s.symbol}</strong>
                      <span>{s.name}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {q.trim() && searching ? (
            <p className="hint">Searching warehouse…</p>
          ) : null}
          {q.trim() && !searching && searchError ? (
            <p className="hint">{searchError}</p>
          ) : null}
          {q.trim() && !searching && !searchError && !items.length ? (
            <p className="hint">No warehouse matches for “{q}”.</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function OverviewStrip({ overview, healthScore, table = [], packMeta = null }) {
  if (!overview) return null;
  const metric = (id) => table.find((row) => row.metric === id) || {};
  const pe = metric('pe');
  const pb = metric('pb');
  const evEbitda = metric('ev_ebitda');
  const keyMetrics = [
    { label: 'Market price', value: fmt(overview.cmp), note: 'Latest warehouse price' },
    { label: 'P/E', value: fmt(pe.company), note: pe.position ? `${pe.position} vs reference` : 'Reference unavailable', tone: positionClass(pe.position) },
    { label: 'P/B', value: fmt(pb.company), note: pb.position ? `${pb.position} vs reference` : 'Reference unavailable', tone: positionClass(pb.position) },
    { label: 'EV / EBITDA', value: fmt(evEbitda.company), note: evEbitda.position ? `${evEbitda.position} vs reference` : 'Reference unavailable', tone: positionClass(evEbitda.position) },
  ];
  return (
    <section className="vt-company-hero">
      <div className="vt-company-hero-top">
        <div>
          <div className="vt-company-kicker">Company valuation snapshot</div>
          <div className="vt-company-title">
            <h2>{overview.name || overview.symbol}</h2>
            <span className="vt-ticker">{overview.symbol}</span>
          </div>
          <p className="vt-company-context">
            {[overview.sector, overview.industry].filter(Boolean).join(' · ') || 'Classification unavailable'}
          </p>
          {packMeta?.generated_at || packMeta?.freshness ? (
            <p className="vt-pack-freshness" data-freshness={packMeta.freshness || 'unknown'}>
              Pack{' '}
              {packMeta.generated_at
                ? new Date(packMeta.generated_at).toLocaleString('en-IN', {
                    timeZone: 'Asia/Kolkata',
                    day: '2-digit',
                    month: 'short',
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : '—'}
              {packMeta.freshness ? ` · ${packMeta.freshness}` : ''}
              {packMeta.source_as_of ? ` · source ${packMeta.source_as_of}` : ''}
              {packMeta.cache?.stale || packMeta.freshness === 'stale' ? ' · serving stored result' : ''}
            </p>
          ) : null}
        </div>
        <div className="vt-hero-quality">
          <span>Evidence confidence</span>
          <strong>{healthScore?.score != null ? `${healthScore.score}%` : '—'}</strong>
          <small className={`vt-band-${overview.data_quality || 'low'}`}>{overview.data_quality || 'Data status unavailable'}</small>
        </div>
      </div>
      <div className="vt-hero-metrics">
        {keyMetrics.map((item) => (
          <div key={item.label} className="vt-hero-metric">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
            <small className={item.tone}>{item.note}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

function InstitutionalTable({ rows, onExplain }) {
  return (
    <section className="vt-panel">
      <div className="vt-panel-head">
        <h3>Institutional valuation</h3>
        <p className="hint">Company · Industry · Historical · Position · Source</p>
      </div>
      <div className="vi-table-wrap">
        <table className="vi-table vt-inst-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Company</th>
              <th>Industry</th>
              <th>Historical</th>
              <th>Position</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            {(rows || []).map((r) => (
              <tr key={r.metric} className={!r.meaningful ? 'vt-na-row' : ''}>
                <td>
                  <button type="button" className="vt-metric-btn" onClick={() => onExplain(r.metric)}>
                    {METRIC_LABELS[r.metric] || r.metric}
                    <Info size={11} />
                  </button>
                </td>
                <td>{!r.meaningful ? 'n/a' : fmt(r.company)}</td>
                <td>{!r.meaningful ? '—' : fmt(r.industry)}</td>
                <td>
                  {!r.meaningful ? '—' : fmt(r.historical)}
                  {r.coverage?.observations ? <small className="hint"> n={r.coverage.observations}</small> : null}
                </td>
                <td className={positionClass(r.position)}>{r.position || (r.note ? '—' : '—')}</td>
                <td className="vt-source">{r.source || (r.available ? 'Engine' : '—')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function ChartPanel({ symbol, window, onWindow, coverage }) {
  const [metric, setMetric] = useState('pe');
  const [series, setSeries] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!symbol || !metric) return;
    setLoading(true);
    getVtSeries(symbol, metric, window)
      .then(setSeries)
      .catch(() => setSeries(null))
      .finally(() => setLoading(false));
  }, [symbol, metric, window]);

  const data = useMemo(
    () => (series?.points || []).map((p) => ({ period: p.period, value: p.value })),
    [series],
  );
  const cov = series?.coverage || coverage?.series?.[metric] || {};

  return (
    <section className="vt-panel">
      <div className="vt-panel-head">
        <h3>Historical charts</h3>
        <div className="vt-window-row">
          {WINDOWS.map((w) => (
            <button
              key={w}
              type="button"
              className={`vt-chip ${window === w ? 'on' : ''}`}
              onClick={() => onWindow(w)}
            >
              {w}
            </button>
          ))}
        </div>
      </div>
      <div className="vt-metric-row">
        {CHART_METRICS.map((m) => (
          <button
            key={m}
            type="button"
            className={`vt-chip ${metric === m ? 'on' : ''}`}
            onClick={() => setMetric(m)}
          >
            {METRIC_LABELS[m] || m}
          </button>
        ))}
      </div>
      <div className="vt-cov-line">
        Coverage {fmt(cov.history ?? cov.count, 0)}
        {' · '}History {cov.confidence || '—'}
        {' · '}Span {cov.observed_span != null ? `${cov.observed_span}y` : '—'}
        {cov.first && cov.last ? ` · ${cov.first} → ${cov.last}` : ''}
        {!cov.sufficient_for_window && cov.count ? ` · Insufficient history for ${window}` : ''}
      </div>
      <div className="vt-chart">
        {loading ? (
          <p className="hint">Loading series…</p>
        ) : !data.length ? (
          <p className="hint">No history for {METRIC_LABELS[metric] || metric} in this window.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <RLineChart data={data}>
              <XAxis dataKey="period" hide />
              <YAxis width={48} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line type="monotone" dataKey="value" stroke="#0f6e6a" strokeWidth={2} dot={false} />
            </RLineChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  );
}

function SectorContext({ ctx }) {
  if (!ctx?.sector) return null;
  const dist = ctx.distribution || {};
  return (
    <section className="vt-panel">
      <div className="vt-panel-head">
        <h3>Sector context</h3>
        <p className="hint">{ctx.sector}</p>
      </div>
      <div className="vt-ov-grid vt-sector-grid">
        <div><span className="k">Current Median</span><span className="v">{fmt(ctx.current_median)}</span></div>
        <div><span className="k">Historical Median</span><span className="v">{fmt(ctx.historical_median)}</span></div>
        <div>
          <span className="k">Current Rank</span>
          <span className="v">
            {ctx.current_rank != null ? `${ctx.current_rank} / ${ctx.universe || '—'}` : '—'}
          </span>
        </div>
        <div>
          <span className="k">Distribution</span>
          <span className="v">
            {dist.low != null ? `${fmt(dist.low)} – ${fmt(dist.high)}` : '—'}
          </span>
        </div>
        <div><span className="k">Peer Percentile</span><span className="v">{fmt(ctx.peer_percentile, 1)}</span></div>
        <div><span className="k">Primary Metric</span><span className="v">{METRIC_LABELS[ctx.primary_metric] || ctx.primary_metric}</span></div>
      </div>
    </section>
  );
}

function PeerTable({ peers }) {
  const rows = peers?.rows || [];
  if (!rows.length) return null;
  return (
    <section className="vt-panel">
      <div className="vt-panel-head">
        <h3>Peer comparison</h3>
        <p className="hint">Current multiple · Historical · ROE · Consensus · Relative score</p>
      </div>
      <div className="vi-table-wrap">
        <table className="vi-table vt-peers">
          <thead>
            <tr>
              <th>Company</th>
              <th>P/E</th>
              <th>P/B</th>
              <th>Historical P/E</th>
              <th>ROE</th>
              <th>Consensus upside</th>
              <th>Relative score</th>
              <th>Peer basis</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((p) => (
              <tr key={p.symbol} className={p.is_self ? 'vt-self' : ''}>
                <td>{p.company_name || p.symbol}</td>
                <td>{fmt(p.pe)}</td>
                <td>{fmt(p.pb)}</td>
                <td>{fmt(p.historical_pe)}</td>
                <td>{fmt(p.roe)}</td>
                <td>{fmt(p.consensus_upside)}</td>
                <td>{fmt(p.relative_score, 1)}</td>
                <td>{p.is_self ? 'Selected company' : (p.selection_reason || 'Sector match')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Explanation({ explanation }) {
  if (!explanation?.sections?.length) return null;
  return (
    <section className="vt-panel vt-explain-panel">
      <div className="vt-panel-head"><h3>Valuation explanation</h3></div>
      <ol className="vt-explain-flow">
        {explanation.sections.map((s) => (
          <li key={s.title}>
            <strong>{s.title}</strong>
            <p>{s.text}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

function ChangeLog({ log }) {
  if (!log) return null;
  const entries = log.entries || [];
  return (
    <section className="vt-panel">
      <div className="vt-panel-head">
        <h3>Valuation change log</h3>
        <p className="hint">
          {log.before_date || 'Prior'} → {log.after_date || 'Today'}
          {log.note ? ` · ${log.note}` : ''}
        </p>
      </div>
      {!entries.length ? (
        <p className="hint">No material multiple moves between the two observations.</p>
      ) : (
        <ul className="vt-changelog">
          {entries.map((e) => (
            <li key={e.metric}>
              <div className="vt-change-head">
                <strong>{METRIC_LABELS[e.metric] || e.metric}</strong>
                <span>{fmt(e.from)} → {fmt(e.to)}</span>
                <span className={e.change_pct < 0 ? 'vt-pos-down' : 'vt-pos-up'}>
                  {e.change_pct != null ? `${e.change_pct > 0 ? '+' : ''}${e.change_pct.toFixed(1)}%` : ''}
                </span>
              </div>
              <p>{e.summary}</p>
              {e.drivers?.length ? (
                <div className="vt-drivers">
                  {e.drivers.map((d) => (
                    <span key={d.input}>
                      {d.input.replace(/_/g, ' ')} {d.change_pct > 0 ? 'rose' : 'declined'} {Math.abs(d.change_pct).toFixed(1)}%
                    </span>
                  ))}
                  {(e.unchanged || []).map((u) => (
                    <span key={u} className="flat">{u.replace(/_/g, ' ')} unchanged</span>
                  ))}
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ProvenancePanel({ provenance, version }) {
  if (!provenance) return null;
  const blocks = [
    ['Price', provenance.price],
    ['Statements', provenance.financials],
    ['Consensus', provenance.consensus],
  ];
  return (
    <section className="vt-panel">
      <div className="vt-panel-head"><h3>Provenance</h3></div>
      <div className="vt-prov-grid">
        {blocks.map(([label, block]) => (
          <div key={label}>
            <span className="k">{label}</span>
            <span className="v">{block?.source || '—'}</span>
            <span className="hint">
              {block?.updated_at ? new Date(block.updated_at).toLocaleString() : '—'}
              {block?.reported_unit ? ` · ${block.reported_unit}` : ''}
            </span>
          </div>
        ))}
        <div>
          <span className="k">Formula</span>
          <span className="v">{provenance.formula || 'unified_valuation_engine'}</span>
          <span className="hint">Version {provenance.formula_version || version || '3.0'}</span>
        </div>
        <div>
          <span className="k">Freshness</span>
          <span className="v">
            {provenance.freshness?.price_age_hours != null ? `Price ${provenance.freshness.price_age_hours}h` : 'Price timestamp unavailable'}
          </span>
          <span className="hint">
            {provenance.freshness?.ratio_age_hours != null ? `Ratios ${provenance.freshness.ratio_age_hours}h` : 'Ratio timestamp unavailable'}
          </span>
        </div>
      </div>
    </section>
  );
}

function DataQualityPanel({ dq, healthScore }) {
  if (!dq && !healthScore) return null;
  return (
    <section className="vt-panel">
      <div className="vt-panel-head">
        <h3>Data quality · Valuation confidence</h3>
      </div>
      <div className="vt-dq-grid">
        <div><span className="k">Validated</span><span className="v">{dq?.validated ? 'Yes' : 'No'}</span></div>
        <div><span className="k">Warnings</span><span className="v">{dq?.warnings?.length || 0}</span></div>
        <div><span className="k">Freshness</span><span className="v">{dq?.freshness?.warnings?.length ? 'Review' : 'Current'}</span></div>
        <div><span className="k">Missing</span><span className="v">{(dq?.missing || []).join(', ') || 'None'}</span></div>
        <div><span className="k">Conflicts</span><span className="v">{dq?.conflicts ?? 0}</span></div>
        <div><span className="k">Overrides</span><span className="v">{dq?.overrides ?? 0}</span></div>
        <div><span className="k">Confidence</span><span className="v vt-health">{healthScore?.score != null ? `${healthScore.score}%` : '—'}</span></div>
      </div>
      {healthScore ? (
        <div className="vt-reasons">
          <ul className="ok">
            {(healthScore.reasons_ok || []).map((r) => <li key={r}>✓ {r}</li>)}
          </ul>
          <ul className="miss">
            {(healthScore.reasons_missing || []).map((r) => <li key={r}>Missing — {r}</li>)}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function labelForMetric(metric) {
  return METRIC_LABELS[metric] || String(metric || '').replace(/_/g, ' ').toUpperCase();
}

function ResearchGuide({ pack }) {
  const table = pack?.table || [];
  const overview = pack?.overview || {};
  const health = pack?.health_score || {};
  const meaningful = table.filter((row) => row.meaningful && row.company != null);
  const valuationRows = meaningful.filter((row) => ['pe', 'pb', 'ev_ebitda', 'ev_sales'].includes(row.metric));
  const below = valuationRows.filter((row) => ['Discount', 'Below'].includes(row.position));
  const above = valuationRows.filter((row) => ['Premium', 'Above'].includes(row.position));
  const qualityRow = meaningful.find((row) => row.metric === 'roe');
  const debtRow = meaningful.find((row) => ['debt_to_equity', 'net_debt_ebitda'].includes(row.metric));
  const coverage = pack?.coverage || {};
  const reliable = health.score != null && health.score >= 70 && (coverage.pct == null || coverage.pct >= 60);
  const stance = !reliable
    ? { label: 'Build evidence', tone: 'review', text: 'Coverage is not yet strong enough for a reliable valuation conclusion.' }
    : below.length >= 2
      ? { label: 'Investigate valuation gap', tone: 'investigate', text: 'More than one applicable multiple screens below its historical or peer reference. Confirm that fundamentals support the discount.' }
      : above.length >= 2
        ? { label: 'Test expectations', tone: 'caution', text: 'More than one applicable multiple carries a premium. Check whether growth, returns and cash generation justify it.' }
        : { label: 'Monitor', tone: 'monitor', text: 'The available valuation evidence is mixed. Track the next result, estimate revision and price move.' };

  const questions = [
    below.length
      ? `Why is ${below.map((row) => labelForMetric(row.metric)).join(' and ')} below its reference range?`
      : above.length
        ? `What must improve for the ${above.map((row) => labelForMetric(row.metric)).join(' and ')} premium to be sustained?`
        : 'Which operating KPI is most likely to change the valuation range?',
    qualityRow?.company != null
      ? `Is the reported ${labelForMetric(qualityRow.metric)} of ${fmt(qualityRow.company)} durable through the cycle?`
      : 'Validate profitability and cash conversion before using valuation multiples.',
    debtRow?.company != null
      ? `Does leverage (${labelForMetric(debtRow.metric)}: ${fmt(debtRow.company)}) constrain capital allocation or downside resilience?`
      : 'Review balance-sheet resilience and any refinancing or dilution risk.',
  ];

  return (
    <section className="vt-panel vt-research-guide">
      <div className="vt-panel-head">
        <div>
          <h3>Research guidance</h3>
          <p className="hint">Evidence-led questions for your next research step — not a recommendation.</p>
        </div>
        <span className={`vt-stance vt-stance-${stance.tone}`}>{stance.label}</span>
      </div>
      <p className="vt-stance-copy">{stance.text}</p>
      <div className="vt-signal-grid">
        <div>
          <span className="k">Valuation signals</span>
          <strong>{below.length ? `${below.length} below reference` : above.length ? `${above.length} at premium` : 'Mixed / limited'}</strong>
          <small>{meaningful.length ? `${meaningful.length} applicable metrics available` : 'No applicable metrics'}</small>
        </div>
        <div>
          <span className="k">Financial quality</span>
          <strong>{qualityRow?.company != null ? `${labelForMetric(qualityRow.metric)} ${fmt(qualityRow.company)}` : 'Needs validation'}</strong>
          <small>{overview.sector || 'Sector unavailable'} · {overview.industry || 'Industry unavailable'}</small>
        </div>
        <div>
          <span className="k">Evidence confidence</span>
          <strong>{health.score != null ? `${health.score}%` : '—'}</strong>
          <small>{coverage.pct != null ? `${coverage.pct}% metric coverage` : 'Coverage not reported'}</small>
        </div>
      </div>
      <div className="vt-next-questions">
        <span className="k">Suggested questions to answer</span>
        <ol>
          {questions.map((question) => <li key={question}>{question}</li>)}
        </ol>
      </div>
    </section>
  );
}

function ResearchNotes({ symbol, companyName }) {
  const [notes, setNotes] = useState(() => readObject(NOTES_KEY));
  const [saved, setSaved] = useState(false);
  const value = notes[symbol] || '';

  useEffect(() => { setSaved(false); }, [symbol]);

  const save = () => {
    const next = { ...notes, [symbol]: value.trim() };
    setNotes(next);
    writeObject(NOTES_KEY, next);
    setSaved(true);
  };

  return (
    <section className="vt-panel vt-notes-panel">
      <div className="vt-panel-head">
        <div>
          <h3>Your research notes</h3>
          <p className="hint">Private to this browser · use for thesis, risks, catalysts and open questions.</p>
        </div>
        <button type="button" className="vi-btn" onClick={save}>{saved ? 'Saved' : 'Save notes'}</button>
      </div>
      <textarea
        value={value}
        onChange={(e) => { setNotes((prev) => ({ ...prev, [symbol]: e.target.value })); setSaved(false); }}
        placeholder={`Write your ${companyName || symbol} research notes…`}
        aria-label={`Research notes for ${companyName || symbol}`}
      />
    </section>
  );
}

function WorkspaceBriefing({ onSelectCompany }) {
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    getVtInsights()
      .then((result) => { if (!cancelled) setInsights(result?.insights || []); })
      .catch(() => { if (!cancelled) setInsights([]); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  return (
    <section className="vt-workspace-briefing">
      <div>
        <span className="vt-brief-eyebrow">Start here</span>
        <h2>What deserves research today?</h2>
        <p>Use the screens to find ideas, then test the evidence in the company workspace. Nothing here is a buy or sell call.</p>
      </div>
      <div className="vt-brief-actions">
        <button type="button" className="vt-brief-link" onClick={() => onSelectCompany?.('ICICIBANK', 'ICICI Bank')}>Research ICICI Bank</button>
        <button type="button" className="vt-brief-link" onClick={() => onSelectCompany?.('HDFCBANK', 'HDFC Bank')}>Compare bank quality</button>
      </div>
      <div className="vt-insight-list">
        {loading ? <p className="hint">Loading verified market observations…</p> : null}
        {!loading && !insights?.length ? <p className="hint">Market observations will appear once the valuation engine has sufficient coverage.</p> : null}
        {insights?.map((insight) => <p key={insight}>• {insight}</p>)}
      </div>
    </section>
  );
}

function LandingWorkspace({ market, marketLoading, sectors, sectorsLoading, onSelectCompany, onSelectSector }) {
  const [showHealth, setShowHealth] = useState(false);

  return (
    <>
      <section className="vt-landing-hero">
        <div>
          <span className="vt-brief-eyebrow">AGI valuation intelligence</span>
          <h2>Find valuation gaps worth explaining.</h2>
          <p>
            Start with the market, identify sectors at a historical discount or premium, then test the company-level evidence.
          </p>
        </div>
        <div className="vt-landing-actions">
          <button type="button" className="vi-btn primary" onClick={() => onSelectCompany('ICICIBANK', 'ICICI Bank')}>
            Research a company
          </button>
          <button type="button" className="vi-btn" onClick={() => onSelectSector(sectors?.[0]?.sector || 'Financials')}>
            Explore sectors
          </button>
        </div>
        <div className="vt-landing-steps" aria-label="Research workflow">
          <span><b>1</b> Market context</span>
          <span><b>2</b> Sector valuation</span>
          <span><b>3</b> Company evidence</span>
          <span><b>4</b> Thesis &amp; risks</span>
        </div>
      </section>

      <MarketSnapshot market={market} loading={marketLoading} />
      <WorkspaceBriefing onSelectCompany={onSelectCompany} />
      <SectorDirectory sectors={sectors} loading={sectorsLoading} onSelect={onSelectSector} />
      <ResearchBoards onSelectCompany={onSelectCompany} />

      <section className="vt-data-health-drawer">
        <button
          type="button"
          className="vt-data-health-toggle"
          onClick={() => setShowHealth((value) => !value)}
          aria-expanded={showHealth}
        >
          <span>
            <b>Data health &amp; coverage</b>
            <small>Operational diagnostics for the valuation warehouse</small>
          </span>
          <span aria-hidden="true">{showHealth ? '−' : '+'}</span>
        </button>
        {showHealth ? <CoverageHealthPanel /> : null}
      </section>
    </>
  );
}

const COMPANY_TABS = [
  { id: 'overview', label: 'Snapshot' },
  { id: 'valuation', label: 'Multiples' },
  { id: 'historical', label: 'History' },
  { id: 'research', label: 'Thesis' },
  { id: 'forecast', label: 'Forecast' },
  { id: 'macro', label: 'Macro' },
  { id: 'peers', label: 'Peers' },
  { id: 'risks', label: 'Data & risks' },
];

function CompanyDetailWorkspace({
  pack,
  symbol,
  window,
  onWindow,
  isFavorite,
  onToggleFavorite,
  onExplain,
}) {
  const [tab, setTab] = useState('overview');
  const overview = pack.overview || {};
  const healthScore = pack.health_score || {};

  return (
    <div className="vt-company-shell">
      <div className="vt-company-main">
        <div className="vt-title-actions">
          <OverviewStrip
            overview={overview}
            healthScore={healthScore}
            table={pack.table}
            packMeta={{
              generated_at: pack.generated_at,
              freshness: pack.freshness,
              source_as_of: pack.source_as_of,
              cache: pack.cache,
            }}
          />
          <button
            type="button"
            className={`vt-fav-btn ${isFavorite ? 'on' : ''}`}
            onClick={onToggleFavorite}
          >
            <Star size={14} /> {isFavorite ? 'Favorited' : 'Favorite'}
          </button>
        </div>

        <nav className="vt-tabs" aria-label="Company sections">
          {COMPANY_TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={tab === t.id ? 'on' : ''}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        {tab === 'overview' ? <ResearchGuide pack={pack} /> : null}

        {tab === 'overview' ? (
          <div className="vt-main-grid">
            <InstitutionalTable rows={pack.table} onExplain={onExplain} />
            <ChartPanel
              symbol={symbol}
              window={window}
              onWindow={onWindow}
              coverage={pack.charts}
            />
          </div>
        ) : null}

        {tab === 'overview' ? (
          <div className="vt-main-grid">
            <SectorContext ctx={pack.sector_context} />
            <Explanation explanation={pack.explanation} />
          </div>
        ) : null}

        {tab === 'valuation' ? (
          <>
            <InstitutionalTable rows={pack.table} onExplain={onExplain} />
            <div className="vt-main-grid">
              <SectorContext ctx={pack.sector_context} />
              <PeerTable peers={pack.peers} />
            </div>
          </>
        ) : null}

        {tab === 'research' ? (
          <>
            <ResearchGuide pack={pack} />
            <ResearchNotes symbol={symbol} companyName={overview.name} />
            <ResearchDossierPanel symbol={symbol} />
            <CompanyAttributionPanel symbol={symbol} />
          </>
        ) : null}

        {tab === 'forecast' ? (
          <ForecastPanel symbol={symbol} />
        ) : null}

        {tab === 'macro' ? (
          <MacroPanel symbol={symbol} />
        ) : null}

        {tab === 'historical' ? (
          <>
            <ChartPanel
              symbol={symbol}
              window={window}
              onWindow={onWindow}
              coverage={pack.charts}
            />
            <ChangeLog log={pack.change_log} />
          </>
        ) : null}

        {tab === 'peers' ? <PeerTable peers={pack.peers} /> : null}

        {tab === 'risks' || tab === 'valuation' ? (
          <div className="vt-main-grid">
            <ProvenancePanel provenance={pack.provenance} version={pack.version} />
            <DataQualityPanel dq={pack.data_quality} healthScore={healthScore} />
          </div>
        ) : null}

        {pack.coverage ? (
          <p className="vt-cov-foot">
            Metric coverage {pack.coverage.pct}%
            ({pack.coverage.available}/{pack.coverage.applicable} applicable)
            · Engine {pack.engine} v{pack.version}
          </p>
        ) : null}
      </div>

      <aside className="vt-side-rail" aria-label="Institutional summary">
        <div className="vt-side-card">
          <div className="vt-side-label">Research checklist</div>
          <h3>Before forming a view</h3>
          <div className="vt-side-metric">
            <span>Historical evidence</span>
            <strong>{pack.coverage?.pct != null ? `${pack.coverage.pct}%` : '—'}</strong>
          </div>
          <div className="vt-side-metric">
            <span>Data confidence</span>
            <strong className="vt-health">{healthScore.score != null ? `${healthScore.score}%` : '—'}</strong>
          </div>
          <div className="vt-side-metric">
            <span>Peer context</span>
            <strong>{pack.peers?.rows?.length ? `${pack.peers.rows.length} companies` : '—'}</strong>
          </div>
          <div className="vt-side-metric">
            <span>Consensus</span>
            <strong>{overview.consensus_coverage ? 'Available' : 'Missing'}</strong>
          </div>
          <div className="vt-side-metric">
            <span>Last update</span>
            <strong>{overview.updated ? new Date(overview.updated).toLocaleDateString() : '—'}</strong>
          </div>
          <p className="hint">Test the multiple against earnings quality, balance-sheet resilience and the next catalyst. This is research context, not a recommendation.</p>
        </div>
      </aside>
    </div>
  );
}

export default function ValuationTerminal() {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const [symbol, setSymbol] = useState(params.get('symbol') || '');
  const [sector, setSector] = useState(params.get('sector') || '');
  const [industry, setIndustry] = useState(params.get('industry') || '');
  const [window, setWindow] = useState('5Y');
  const [pack, setPack] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [metric, setMetric] = useState(null);
  const [recent, setRecent] = useState(() => readList(RECENT_KEY));
  const [favorites, setFavorites] = useState(() => readList(FAV_KEY));
  const [sectors, setSectors] = useState([]);
  const [sectorsLoading, setSectorsLoading] = useState(true);
  const [market, setMarket] = useState(null);
  const [marketLoading, setMarketLoading] = useState(true);
  const [compare, setCompare] = useState([]);

  const home = location.pathname.startsWith('/admin') ? '/admin' : '/';

  const loadHealth = useCallback(() => {
    getVtHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  const selectSector = useCallback((name) => {
    setSector(name);
    setIndustry('');
    setSymbol('');
    setPack(null);
    setCompare([]);
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('symbol');
      next.delete('industry');
      next.set('sector', name);
      return next;
    });
  }, [setParams]);

  const selectIndustry = useCallback((name) => {
    setIndustry(name || '');
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      if (name) next.set('industry', name);
      else next.delete('industry');
      return next;
    });
  }, [setParams]);

  const clearSector = useCallback(() => {
    setSector('');
    setIndustry('');
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete('sector');
      next.delete('industry');
      return next;
    });
  }, [setParams]);

  const selectCompany = useCallback((sym, name) => {
    const ticker = String(sym || '').toUpperCase();
    setSymbol(ticker);
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set('symbol', ticker);
      // Keep sector context when drilling down from sector workspace.
      return next;
    });
    const entry = { symbol: ticker, name: name || ticker };
    setRecent((prev) => {
      const next = [entry, ...prev.filter((r) => r.symbol !== ticker)];
      writeList(RECENT_KEY, next);
      return next;
    });
  }, [setParams]);

  const toggleFavorite = useCallback((sym, name) => {
    const ticker = String(sym || '').toUpperCase();
    setFavorites((prev) => {
      const exists = prev.some((f) => f.symbol === ticker);
      const next = exists
        ? prev.filter((f) => f.symbol !== ticker)
        : [{ symbol: ticker, name: name || ticker }, ...prev];
      writeList(FAV_KEY, next);
      return next;
    });
  }, []);

  const loadPack = useCallback(async ({ force = false } = {}) => {
    if (!symbol) {
      setPack(null);
      return;
    }
    setLoading(true);
    setError('');
    try {
      const params = { window, peer_limit: 12 };
      if (force) params.refresh = 1;
      const out = await getVtCompany(symbol, params);
      setPack(out);
      if (!out?.ok) setError(out?.error || 'Company not in warehouse');
    } catch (err) {
      setError(err?.message || 'Failed to load valuation');
      setPack(null);
    } finally {
      setLoading(false);
    }
  }, [symbol, window]);

  useEffect(() => { loadHealth(); }, [loadHealth]);
  useEffect(() => { loadPack(); }, [loadPack]);
  useEffect(() => {
    setSectorsLoading(true);
    setMarketLoading(true);
    getSveSectors()
      .then((r) => setSectors(r?.sectors || []))
      .catch(() => setSectors([]))
      .finally(() => setSectorsLoading(false));
    getSveMarket()
      .then(setMarket)
      .catch(() => setMarket(null))
      .finally(() => setMarketLoading(false));
  }, []);

  useEffect(() => {
    const fromUrl = params.get('symbol');
    const sectorUrl = params.get('sector') || '';
    const industryUrl = params.get('industry') || '';
    if (fromUrl && fromUrl.toUpperCase() !== symbol) setSymbol(fromUrl.toUpperCase());
    if (sectorUrl !== sector) setSector(sectorUrl);
    if (industryUrl !== industry) setIndustry(industryUrl);
  }, [params, symbol, sector, industry]);

  const isFavorite = favorites.some((f) => f.symbol === symbol);
  const showSectorHome = !symbol && !sector;
  const showSectorWorkspace = !symbol && !!sector;

  return (
    <div className="vi-root vt-root">
      <header className="vi-header">
        <div className="vi-brand-row">
          <div className="vi-brand">
            <Link to={home} className="vt-back"><ArrowLeft size={14} /> Back</Link>
            <h1>Valuation Research Workspace</h1>
            <p>Market → Sector → Industry → Company → Research</p>
          </div>
          <div className="vi-actions">
            <button
              type="button"
              className="vi-btn"
              onClick={() => {
                loadHealth();
                loadPack({ force: true });
                getSveSectors().then((r) => setSectors(r?.sectors || []));
                getSveMarket().then(setMarket).catch(() => setMarket(null));
              }}
              disabled={loading}
            >
              <RefreshCw size={14} /> Refresh
            </button>
            <div className="vi-updated">
              Engine {health?.version || pack?.version || '3.0'}
              <div style={{ color: 'var(--vi-ink)', fontWeight: 600 }}>
                {health?.companies != null ? `${health.companies} companies` : 'Warehouse'}
              </div>
            </div>
          </div>
        </div>
        <CompanySearch
          onSelect={selectCompany}
          recent={recent}
          favorites={favorites}
          onToggleFavorite={toggleFavorite}
        />
      </header>

      <main className="vi-body">
        {error ? <div className="vi-error">{error}</div> : null}

        {showSectorHome ? (
          <LandingWorkspace
            market={market}
            marketLoading={marketLoading}
            sectors={sectors}
            sectorsLoading={sectorsLoading}
            onSelectCompany={selectCompany}
            onSelectSector={selectSector}
          />
        ) : null}

        {showSectorWorkspace ? (
          <SectorValuationWorkspace
            sector={sector}
            industry={industry}
            onBack={clearSector}
            onSelectIndustry={selectIndustry}
            onClearIndustry={() => selectIndustry('')}
            onSelectCompany={selectCompany}
            compare={compare}
            onToggleCompare={(sym) => {
              setCompare((prev) => (
                prev.includes(sym) ? prev.filter((x) => x !== sym) : [...prev, sym].slice(0, 5)
              ));
            }}
          />
        ) : null}

        {symbol && sector ? (
          <div className="sve-context-bar">
            <button type="button" onClick={() => { setSymbol(''); setParams((p) => { const n = new URLSearchParams(p); n.delete('symbol'); return n; }); }}>
              ← Back to {sector}
            </button>
            <span className="hint">Company drill-down from sector workspace</span>
          </div>
        ) : null}

        {loading ? <p className="hint">Loading valuation pack…</p> : null}

        {pack?.ok ? (
          <CompanyDetailWorkspace
            pack={pack}
            symbol={symbol}
            window={window}
            onWindow={setWindow}
            isFavorite={isFavorite}
            onToggleFavorite={() => toggleFavorite(symbol, pack.overview?.name)}
            onExplain={setMetric}
          />
        ) : null}
      </main>

      <MetricModal metric={metric} onClose={() => setMetric(null)} />
    </div>
  );
}
