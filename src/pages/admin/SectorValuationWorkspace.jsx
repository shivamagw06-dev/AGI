import { useEffect, useMemo, useState } from 'react';
import {
  getSveOpportunities,
  getSvePremium,
  getSveRerating,
  getSveSector,
  getSveSectorLeaders,
  getSveSectorResearch,
  getSveSectorRotation,
} from '@/lib/intelligenceApi';
import { SectorAttributionPanel } from '@/pages/admin/ValuationAttributionPanel';

function fmt(v, digits = 2) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1e12) return `₹${(v / 1e12).toFixed(1)}T`;
    if (Math.abs(v) >= 1e7) return `₹${(v / 1e7).toFixed(0)} cr`;
    if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  }
  return String(v);
}

function toneFromStatus(status) {
  const s = String(status || '').toLowerCase();
  if (s.includes('cheap') || s.includes('attractive') || s.includes('undervalued')) return 'cheap';
  if (s.includes('premium') || s.includes('expensive')) return 'premium';
  if (s.includes('fair')) return 'fair';
  return 'neutral';
}

function KpiChip({ label, tone = 'neutral' }) {
  return <span className={`kpi-chip kpi-${tone}`}>{label}</span>;
}

function HistBar({ pct }) {
  const width = pct == null ? 0 : Math.max(4, Math.min(100, Number(pct)));
  const tone = pct == null ? 'neutral' : pct <= 35 ? 'cheap' : pct >= 65 ? 'premium' : 'fair';
  return (
    <div className={`hist-bar hist-${tone}`} title={pct == null ? '—' : `${pct}`}>
      <div style={{ width: `${width}%` }} />
    </div>
  );
}

function SparkDir({ changePct }) {
  // Visual direction from server-provided change — not a UI valuation calc.
  const v = changePct == null ? 0 : Number(changePct);
  const cls = v > 0.5 ? 'up' : v < -0.5 ? 'down' : 'flat';
  return <span className={`spark-dir spark-${cls}`} aria-hidden="true" />;
}

function DistBars({ dist, label }) {
  const bins = dist?.bins || [];
  const max = Math.max(1, ...bins.map((b) => b.count || 0));
  if (!bins.length) return <p className="hint">No {label} distribution.</p>;
  return (
    <div className="sve-dist">
      <div className="sve-dist-label">{label}</div>
      <div className="sve-dist-bars">
        {bins.map((b, i) => (
          <div key={i} className="sve-dist-col" title={`${fmt(b.start)}–${fmt(b.end)}: ${b.count}`}>
            <div className="sve-dist-bar" style={{ height: `${Math.max(6, (100 * b.count) / max)}%` }} />
          </div>
        ))}
      </div>
      <div className="sve-dist-meta">
        <span>n={dist.count}</span>
        <span>med {fmt(dist.median)}</span>
      </div>
    </div>
  );
}

function MetricTip({ label, value, sector, industry, hist, pct, source, confidence }) {
  return (
    <span className="sve-tip" tabIndex={0}>
      {value}
      <span className="sve-tip-pop" role="tooltip">
        <strong>{label}</strong>
        <div>Current · {value}</div>
        {sector != null ? <div>Sector · {fmt(sector)}</div> : null}
        {industry != null ? <div>Industry · {fmt(industry)}</div> : null}
        {hist != null ? <div>Historical median · {fmt(hist)}</div> : null}
        {pct != null ? <div>Historical % · {fmt(pct, 0)}</div> : null}
        <div className="hint">Source · {source || 'Warehouse / HVIE'}</div>
        {confidence != null ? <div className="hint">Confidence · {fmt(confidence, 0)}%</div> : null}
      </span>
    </span>
  );
}

const QUICK = [
  { id: 'cheap', label: 'Historically Cheap', apply: (r) => String(r.valuation_status || '').toLowerCase().includes('cheap') },
  { id: 'expensive', label: 'Historically Expensive', apply: (r) => String(r.valuation_status || '').toLowerCase().includes('expensive') },
  { id: 'premium', label: 'Premium', apply: (r) => String(r.valuation_status || '').toLowerCase().includes('premium') || String(r.valuation_status || '').includes('Expensive') },
  { id: 'fair', label: 'Fair', apply: (r) => String(r.valuation_status || '').toLowerCase().includes('fair') },
  { id: 'deep', label: 'Deep Value', apply: (r) => (r.historical_percentile != null && r.historical_percentile <= 15) },
  { id: 'growth', label: 'Growth Premium', apply: (r) => (r.premium_pct != null && r.premium_pct >= 25 && (r.roe || 0) >= 18) },
  { id: 'roe', label: 'Highest ROE', sort: 'roe' },
  { id: 'roce', label: 'Highest ROCE', sort: 'roce' },
  { id: 'discount', label: 'Largest Discount', sort: 'premium_pct', order: 'asc' },
  { id: 'low_pct', label: 'Lowest Hist %', sort: 'historical_percentile', order: 'asc' },
  { id: 'high_pct', label: 'Highest Hist %', sort: 'historical_percentile' },
  { id: 'large', label: 'Large Cap', bucket: 'large' },
  { id: 'mid', label: 'Mid Cap', bucket: 'mid' },
  { id: 'small', label: 'Small Cap', bucket: 'small' },
  { id: 'hi_conf', label: 'High Confidence', apply: (r) => (r.confidence || 0) >= 0.85 || (r.coverage?.provider || 0) >= 3 },
  { id: 'low_cov', label: 'Low Coverage', apply: (r) => !(r.coverage?.provider) },
];

function copyText(text) {
  if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
    return navigator.clipboard.writeText(text);
  }
  return Promise.resolve();
}

function rowsToCsv(rows) {
  const cols = [
    'symbol', 'company_name', 'cmp', 'market_cap', 'sector', 'industry',
    'pe', 'sector_pe', 'industry_pe', 'premium_pct', 'historical_percentile',
    'pb', 'sector_pb', 'roe', 'roce', 'ev_ebitda', 'historical_regime',
    'valuation_status',
  ];
  const header = cols.join(',');
  const body = rows.map((r) => cols.map((c) => {
    const v = r[c];
    if (v == null) return '';
    const s = String(v).replace(/"/g, '""');
    return s.includes(',') ? `"${s}"` : s;
  }).join(',')).join('\n');
  return `${header}\n${body}`;
}

export function MarketSnapshot({ market, loading }) {
  if (loading) return <section className="sve-hero hint">Loading Indian market…</section>;
  if (!market?.ok) return null;
  const tone = toneFromStatus(market.regime || market.opportunity);
  return (
    <section className="sve-hero">
      <div className="sve-hero-top">
        <div>
          <div className="sve-hero-eyebrow">Indian Market</div>
          <h2 className="sve-hero-title">Market valuation</h2>
        </div>
        <div className="sve-hero-chips">
          <KpiChip label={market.regime || market.opportunity || '—'} tone={tone} />
          <KpiChip
            label={market.confidence != null ? `${fmt(market.confidence, 0)}% Confidence` : 'Confidence —'}
            tone="confidence"
          />
        </div>
      </div>
      <div className="sve-hero-metrics">
        <div>
          <span className="k">Valuation coverage</span>
          <span className="v">{(market.valuation_coverage_pct ?? market.coverage_pct) != null ? `${fmt(market.valuation_coverage_pct ?? market.coverage_pct, 0)}%` : '—'}</span>
        </div>
        <div>
          <span className="k">Median PE</span>
          <span className="v">{fmt(market.median_pe)}</span>
        </div>
        <div>
          <span className="k">Historical %</span>
          <span className="v">{fmt(market.historical_percentile, 0)}</span>
        </div>
        <div>
          <span className="k">Premium</span>
          <span className="v">{market.premium_pct != null ? `${fmt(market.premium_pct, 1)}%` : '—'}</span>
        </div>
        <div>
          <span className="k">Median PB</span>
          <span className="v">{fmt(market.median_pb)}</span>
        </div>
        <div>
          <span className="k">EV/EBITDA</span>
          <span className="v">{fmt(market.median_ev_ebitda)}</span>
        </div>
        <div>
          <span className="k">ROE</span>
          <span className="v">{fmt(market.median_roe)}</span>
        </div>
        <div>
          <span className="k">Companies</span>
          <span className="v">{fmt(market.companies_covered, 0)}</span>
        </div>
      </div>
      <div className="sve-hero-focus">
        <span className="k">Research focus</span>
        <p>{market.research_focus || '—'}</p>
      </div>
    </section>
  );
}

function heatTone(status, pct) {
  const fromStatus = toneFromStatus(status);
  if (fromStatus !== 'neutral') return fromStatus;
  if (pct == null) return 'neutral';
  if (pct <= 35) return 'cheap';
  if (pct >= 65) return 'premium';
  return 'fair';
}

function SectorHeatmap({ sectors, onSelect }) {
  const rows = [...(sectors || [])].sort((a, b) => {
    const ap = a.historical_percentile;
    const bp = b.historical_percentile;
    if (ap == null && bp == null) return String(a.sector).localeCompare(String(b.sector));
    if (ap == null) return 1;
    if (bp == null) return -1;
    return bp - ap;
  });
  if (!rows.length) return null;
  return (
    <section className="sve-heatmap">
      <div className="sve-directory-head">
        <h3>Sector valuation heatmap</h3>
        <p className="hint">
          Sector median vs its own history (HVIE) — green cheap · blue fair · red premium.
          Unavailable when history is insufficient (never defaults to 50).
        </p>
      </div>
      <div className="sve-heatmap-grid">
        {rows.map((s) => {
          const pct = s.historical_percentile;
          const unavailable = pct == null;
          const tone = unavailable ? 'neutral' : heatTone(s.status || s.opportunity, pct);
          const obs = s.historical_observations;
          const reason = s.historical_percentile_reason
            || (obs != null ? `Insufficient history (${obs} obs; need ≥24)` : 'Insufficient history');
          const label = unavailable ? 'n/a' : fmt(pct, 0);
          return (
            <button
              key={s.sector}
              type="button"
              className={`sve-heat-cell heat-${tone}`}
              onClick={() => onSelect(s.sector)}
              title={
                unavailable
                  ? `${s.sector} · Historical % unavailable — ${reason}`
                  : `${s.sector} · hist% ${label}`
              }
            >
              <strong>{s.sector}</strong>
              <span>{label}</span>
              {unavailable && obs != null ? (
                <em className="sve-heat-meta">{obs} obs</em>
              ) : null}
              <HistBar pct={pct} />
            </button>
          );
        })}
      </div>
    </section>
  );
}

export default function SectorValuationWorkspace({
  sector,
  industry: industryProp = '',
  onBack,
  onSelectIndustry,
  onClearIndustry,
  onSelectCompany,
  compare = [],
  onToggleCompare,
}) {
  const [pack, setPack] = useState(null);
  const [leaders, setLeaders] = useState(null);
  const [research, setResearch] = useState(null);
  const [rotation, setRotation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [industry, setIndustry] = useState(industryProp || '');
  const [quick, setQuick] = useState(null);
  const [sort, setSort] = useState('market_cap');
  const [order, setOrder] = useState('desc');
  const [dashTab, setDashTab] = useState('leaders');

  useEffect(() => {
    setIndustry(industryProp || '');
  }, [industryProp]);

  useEffect(() => {
    if (!sector) return undefined;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getSveSector(sector),
      getSveSectorLeaders(sector),
      getSveSectorResearch(sector),
      getSveSectorRotation(sector),
    ])
      .then(([p, l, r, rot]) => {
        if (cancelled) return;
        setPack(p);
        setLeaders(l);
        setResearch(r);
        setRotation(rot);
        setError(p?.ok === false ? p.error : null);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || 'sector_load_failed');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [sector]);

  const industryCards = useMemo(() => {
    const list = pack?.industries || [];
    return list.map((ind) => (typeof ind === 'string' ? { industry: ind } : ind));
  }, [pack]);

  const rows = useMemo(() => {
    let list = [...(pack?.company_rows || [])];
    if (industry) list = list.filter((r) => r.industry === industry);
    const q = QUICK.find((x) => x.id === quick);
    if (q?.apply) list = list.filter(q.apply);
    if (q?.bucket) list = list.filter((r) => r.market_cap_bucket === q.bucket);
    const sortKey = q?.sort || sort;
    const sortOrder = q?.order || order;
    const reverse = sortOrder !== 'asc';
    list.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      if (typeof av === 'number' && typeof bv === 'number') {
        return reverse ? bv - av : av - bv;
      }
      return reverse
        ? String(bv).localeCompare(String(av))
        : String(av).localeCompare(String(bv));
    });
    return list;
  }, [pack, industry, quick, sort, order]);

  const selectIndustry = (name) => {
    setIndustry(name);
    onSelectIndustry?.(name);
  };

  const clearIndustry = () => {
    setIndustry('');
    onClearIndustry?.();
  };

  const exportCsv = () => {
    const csv = rowsToCsv(rows);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${sector.replace(/\s+/g, '_')}_valuation.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyTable = () => copyText(rowsToCsv(rows));
  const copySummary = () => {
    const o = pack?.outcome || {};
    const text = [
      pack?.sector,
      o.conclusion,
      `Overall: ${o.overall || '—'}`,
      `Confidence: ${o.confidence ?? '—'}%`,
      'Analysis only — not a recommendation.',
    ].filter(Boolean).join('\n');
    return copyText(text);
  };

  if (loading) return <div className="sve-workspace hint">Loading sector workspace…</div>;
  if (error) return <div className="sve-workspace sve-error">{error}</div>;
  if (!pack?.ok) return <div className="sve-workspace hint">Sector unavailable.</div>;

  const summary = pack.summary || {};
  const explanation = pack.explanation || {};
  const outcome = pack.outcome || {};
  const dists = pack.distributions || {};
  const activeIndustry = industryCards.find((c) => c.industry === industry);

  const currentPe = activeIndustry?.median_pe ?? summary.current_median;
  const premiumVal = activeIndustry?.premium_pct ?? summary.premium_pct;
  const histPct = activeIndustry?.historical_percentile ?? summary.historical_percentile;
  const overallTone = heatTone(outcome.overall || summary.overall, histPct);

  return (
    <div className="sve-workspace">
      <div className="sve-workspace-head">
        <button type="button" className="sve-back" onClick={onBack}>← All sectors</button>
        <div>
          <h2>{pack.sector}{industry ? ` · ${industry}` : ''}</h2>
          <p className="hint">{fmt(industry ? rows.length : pack.companies, 0)} companies</p>
        </div>
        <div className="sve-hero-chips">
          <KpiChip label={outcome.overall || summary.overall || '—'} tone={overallTone} />
          <KpiChip
            label={`${fmt(activeIndustry?.confidence ?? outcome.confidence, 0)}% Conf`}
            tone="confidence"
          />
        </div>
        <div className="sve-export">
          <button type="button" onClick={exportCsv}>Export CSV</button>
          <button type="button" onClick={copyTable}>Copy Table</button>
          <button type="button" onClick={copySummary}>Copy Research Summary</button>
        </div>
      </div>

      <section className="sve-sector-hero">
        <div className="sve-sector-summary">
          <h3>Sector summary</h3>
          <div className="sve-sector-metrics">
            <div><span className="k">Current PE</span><span className="v">{fmt(currentPe)}</span></div>
            <div><span className="k">Historical median</span><span className="v">{fmt(summary.historical_median)}</span></div>
            <div><span className="k">Premium</span><span className="v">{premiumVal != null ? `${fmt(premiumVal, 1)}%` : '—'}</span></div>
            <div><span className="k">Historical %</span><span className="v">{fmt(histPct, 0)}</span></div>
            <div><span className="k">Market cap</span><span className="v">{fmt(activeIndustry?.market_cap ?? summary.market_cap)}</span></div>
            <div><span className="k">Coverage</span><span className="v">{(activeIndustry?.coverage_pct ?? summary.coverage_pct) != null ? `${fmt(activeIndustry?.coverage_pct ?? summary.coverage_pct, 0)}%` : '—'}</span></div>
          </div>
          <HistBar pct={histPct} />
          <p className="hint">Primary metric · {explanation.primary_metric_label || summary.primary_metric_label || '—'}</p>
        </div>
        <div className="sve-sector-chart">
          <h3>Distribution charts</h3>
          <div className="sve-dist-grid">
            <DistBars dist={dists.pe} label="P/E" />
            <DistBars dist={dists.pb} label="P/B" />
            <DistBars dist={dists.historical_percentile} label="Historical %" />
            <DistBars dist={dists.ev_ebitda || dists.premium_pct} label={dists.ev_ebitda ? 'EV/EBITDA' : 'Premium %'} />
          </div>
        </div>
        <div className="sve-sector-why">
          <h3>Why?</h3>
          <p className="sve-conclusion">{outcome.conclusion}</p>
          <ul className="varie-why">
            {(outcome.evidence || []).slice(0, 5).map((e, i) => <li key={i}>✓ {e}</li>)}
          </ul>
          <p className="hint">{explanation.rationale || explanation.why}</p>
          <SectorAttributionPanel sector={pack.sector} />
        </div>
      </section>

      <section className="sve-panel">
        <div className="sve-panel-head">
          <h3>Industry workspace</h3>
          {industry ? (
            <button type="button" className="sve-back" onClick={clearIndustry}>Clear industry</button>
          ) : null}
        </div>
        <div className="sve-cards sve-cards-modern sve-industry-cards">
          {industryCards.map((ind) => {
            const tone = heatTone(ind.opportunity, ind.historical_percentile);
            return (
              <button
                key={ind.industry}
                type="button"
                className={`sve-card-modern heat-${tone} ${industry === ind.industry ? 'sve-card-on' : ''}`}
                onClick={() => selectIndustry(ind.industry)}
              >
                <div className="sve-card-modern-top">
                  <div>
                    <div className="sve-card-title">{ind.industry}</div>
                    <div className="sve-card-meta">{fmt(ind.companies, 0)} companies</div>
                  </div>
                  <div className="sve-card-premium">
                    <span>Premium</span>
                    <strong>{ind.premium_pct != null ? `${fmt(ind.premium_pct, 1)}%` : '—'}</strong>
                  </div>
                </div>
                <HistBar pct={ind.historical_percentile} />
                <div className="sve-card-modern-grid">
                  <div><span>PE</span><strong>{fmt(ind.median_pe)}</strong></div>
                  <div><span>PB</span><strong>{fmt(ind.median_pb)}</strong></div>
                  <div><span>Hist %</span><strong>{fmt(ind.historical_percentile, 0)}</strong></div>
                  <div><span>ROE</span><strong>{fmt(ind.median_roe)}</strong></div>
                </div>
                <div className="sve-card-modern-foot">
                  <KpiChip label={ind.opportunity || '—'} tone={tone} />
                  <span className="sve-open">Filter →</span>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      <section className="sve-panel sve-table-panel">
        <div className="sve-sticky-filters">
          <h3>Company table{industry ? ` · ${industry}` : ''}</h3>
          <div className="sve-filters">
            <select
              value={industry}
              onChange={(e) => (e.target.value ? selectIndustry(e.target.value) : clearIndustry())}
            >
              <option value="">All industries</option>
              {industryCards.map((ind) => (
                <option key={ind.industry} value={ind.industry}>{ind.industry}</option>
              ))}
            </select>
            <select value={sort} onChange={(e) => setSort(e.target.value)}>
              <option value="market_cap">Market cap</option>
              <option value="pe">P/E</option>
              <option value="pb">P/B</option>
              <option value="roe">ROE</option>
              <option value="roce">ROCE</option>
              <option value="ev_ebitda">EV/EBITDA</option>
              <option value="premium_pct">Premium %</option>
              <option value="historical_percentile">Historical %</option>
            </select>
            <select value={order} onChange={(e) => setOrder(e.target.value)}>
              <option value="desc">Desc</option>
              <option value="asc">Asc</option>
            </select>
          </div>
          <div className="sve-quick">
            {QUICK.map((q) => (
              <button
                key={q.id}
                type="button"
                className={quick === q.id ? 'on' : ''}
                onClick={() => setQuick(quick === q.id ? null : q.id)}
              >
                {q.label}
              </button>
            ))}
          </div>
        </div>
        <div className="vi-table-wrap sve-table-dominant">
          <table className="vi-table sve-table">
            <thead>
              <tr>
                <th className="pin" />
                <th className="pin">Company</th>
                <th>CMP</th>
                <th>PE</th>
                <th>PB</th>
                <th>EV/EBITDA</th>
                <th>Sector PE</th>
                <th>Industry PE</th>
                <th>Hist %</th>
                <th>Premium</th>
                <th>ROE</th>
                <th>ROCE</th>
                <th>Status</th>
                <th>Conf</th>
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 250).map((r) => (
                <tr key={r.symbol}>
                  <td className="pin">
                    <input
                      type="checkbox"
                      checked={compare.includes(r.symbol)}
                      disabled={!compare.includes(r.symbol) && compare.length >= 5}
                      onChange={() => onToggleCompare?.(r.symbol)}
                      aria-label={`Compare ${r.symbol}`}
                    />
                  </td>
                  <td className="pin">
                    <button type="button" className="sve-link" onClick={() => onSelectCompany(r.symbol, r.company_name)}>
                      <strong>{r.symbol}</strong>
                      <span>{r.company_name}</span>
                    </button>
                    <SparkDir changePct={r.pe_change_pct} />
                  </td>
                  <td>{fmt(r.cmp)}</td>
                  <td>
                    <MetricTip
                      label="P/E"
                      value={fmt(r.pe)}
                      sector={r.sector_pe}
                      industry={r.industry_pe}
                      pct={r.historical_percentile}
                      source={r.source || r.coverage?.source}
                      confidence={(r.confidence || 0) * 100}
                    />
                  </td>
                  <td>{fmt(r.pb)}</td>
                  <td>{fmt(r.ev_ebitda)}</td>
                  <td>{fmt(r.sector_pe)}</td>
                  <td>{fmt(r.industry_pe)}</td>
                  <td>
                    <div className="cell-hist">
                      <span>{fmt(r.historical_percentile, 0)}</span>
                      <HistBar pct={r.historical_percentile} />
                    </div>
                  </td>
                  <td>{r.premium_pct != null ? `${fmt(r.premium_pct, 1)}%` : '—'}</td>
                  <td>{fmt(r.roe)}</td>
                  <td>{fmt(r.roce)}</td>
                  <td>
                    <KpiChip
                      label={r.valuation_status || '—'}
                      tone={toneFromStatus(r.valuation_status)}
                    />
                  </td>
                  <td>
                    <KpiChip
                      label={r.confidence != null ? `${Math.round((r.confidence > 1 ? r.confidence : r.confidence * 100))}%` : '—'}
                      tone="confidence"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="hint">Showing {Math.min(rows.length, 250)} of {rows.length}. Warehouse → UVE / HVIE — no UI calculations.</p>
      </section>

      {compare.length >= 2 ? (
        <section className="sve-panel">
          <h3>Peer comparison ({compare.length})</h3>
          <div className="vi-table-wrap">
            <table className="vi-table sve-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>P/E</th>
                  <th>P/B</th>
                  <th>EV/EBITDA</th>
                  <th>ROE</th>
                  <th>ROCE</th>
                  <th>Hist %</th>
                  <th>Premium %</th>
                  <th>Industry PE</th>
                  <th>Sector PE</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.filter((r) => compare.includes(r.symbol)).map((r) => (
                  <tr key={r.symbol}>
                    <td>{r.symbol}</td>
                    <td>{fmt(r.pe)}</td>
                    <td>{fmt(r.pb)}</td>
                    <td>{fmt(r.ev_ebitda)}</td>
                    <td>{fmt(r.roe)}</td>
                    <td>{fmt(r.roce)}</td>
                    <td>{fmt(r.historical_percentile, 0)}</td>
                    <td>{r.premium_pct != null ? `${fmt(r.premium_pct, 1)}%` : '—'}</td>
                    <td>{fmt(r.industry_pe)}</td>
                    <td>{fmt(r.sector_pe)}</td>
                    <td>{r.valuation_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <section className="sve-panel">
        <div className="sve-panel-head">
          <h3>Leaders & research</h3>
          <div className="sve-quick">
            {['leaders', 'rotation', 'research'].map((t) => (
              <button key={t} type="button" className={dashTab === t ? 'on' : ''} onClick={() => setDashTab(t)}>
                {t}
              </button>
            ))}
          </div>
        </div>
        {dashTab === 'leaders' ? (
          <div className="sve-leaders-grid">
            {leaders?.leaders ? Object.entries(leaders.leaders).map(([key, list]) => (
              <div key={key} className="sve-leader-block">
                <div className="k">{key.replace(/_/g, ' ')}</div>
                <ul>
                  {(list || []).slice(0, 5).map((item) => (
                    <li key={`${key}-${item.symbol}`}>
                      <button type="button" className="sve-link" onClick={() => onSelectCompany(item.symbol, item.company_name)}>
                        {item.symbol}
                      </button>
                      <span>{fmt(item.value)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )) : <p className="hint">No leaders yet.</p>}
          </div>
        ) : null}
        {dashTab === 'rotation' ? (
          <div className="sve-rotation">
            <p>{rotation?.rotation?.explanation || rotation?.note || 'Rotation context loading…'}</p>
            <ul>
              {(rotation?.rotation?.rows || rotation?.sectors || []).slice(0, 8).map((s) => (
                <li key={s.sector}>
                  <strong>{s.sector}</strong>
                  <span> hist% {fmt(s.historical_percentile, 0)}</span>
                  <span> PE chg {s.avg_pe_change_pct != null ? `${fmt(s.avg_pe_change_pct, 1)}%` : '—'}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        {dashTab === 'research' ? (
          <ul className="sve-research">
            {(research?.priorities || []).map((p) => (
              <li key={p.symbol}>
                <button type="button" className="sve-link" onClick={() => onSelectCompany(p.symbol, p.company_name)}>
                  <strong>{p.symbol}</strong>
                </button>
                <span>{p.reason}</span>
                <span className="hint">→ {p.action}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </div>
  );
}

export function SectorDirectory({ sectors, onSelect, loading }) {
  const [q, setQ] = useState('');
  const [sort, setSort] = useState('pct');

  const list = useMemo(() => {
    let rows = [...(sectors || [])];
    if (q.trim()) {
      const needle = q.trim().toLowerCase();
      rows = rows.filter((s) => String(s.sector || '').toLowerCase().includes(needle));
    }
    rows.sort((a, b) => {
      if (sort === 'name') return String(a.sector).localeCompare(String(b.sector));
      if (sort === 'pe') return (b.median_pe || b.current || 0) - (a.median_pe || a.current || 0);
      if (sort === 'pct') return (b.historical_percentile || 0) - (a.historical_percentile || 0);
      if (sort === 'premium') return (b.premium_pct || 0) - (a.premium_pct || 0);
      return (b.companies || 0) - (a.companies || 0);
    });
    return rows;
  }, [sectors, q, sort]);

  if (loading) return <section className="sve-directory hint">Loading sectors…</section>;
  return (
    <>
      <SectorHeatmap sectors={sectors} onSelect={onSelect} />
      <section className="sve-directory">
        <div className="sve-directory-head">
          <h3>All sectors</h3>
          <p className="hint">Open a sector for industry drill-down and the company table</p>
        </div>
        <div className="sve-directory-tools">
          <input
            type="search"
            placeholder="Search sectors…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search sectors"
          />
          <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort sectors">
            <option value="pct">Historical %</option>
            <option value="premium">Premium</option>
            <option value="pe">Median PE</option>
            <option value="companies">Companies</option>
            <option value="name">Name</option>
          </select>
        </div>
        <div className="sve-cards sve-cards-modern">
          {list.map((s) => {
            const status = s.status || s.opportunity || 'Unknown';
            const tone = heatTone(status, s.historical_percentile);
            return (
              <button
                key={s.sector}
                type="button"
                className={`sve-card-modern heat-${tone}`}
                onClick={() => onSelect(s.sector)}
              >
                <div className="sve-card-modern-top">
                  <div>
                    <div className="sve-card-title">{s.sector}</div>
                    <div className="sve-card-meta">{fmt(s.companies, 0)} companies</div>
                  </div>
                  <div className="sve-card-premium">
                    <span>Premium</span>
                    <strong>{s.premium_pct != null ? `${fmt(s.premium_pct, 1)}%` : '—'}</strong>
                  </div>
                </div>
                <HistBar pct={s.historical_percentile} />
                <div className="sve-card-modern-grid">
                  <div><span>Historical %</span><strong>{fmt(s.historical_percentile, 0)}</strong></div>
                  <div><span>Current PE</span><strong>{fmt(s.current || s.median_pe)}</strong></div>
                  <div><span>Median PB</span><strong>{fmt(s.median_pb)}</strong></div>
                  <div><span>ROE</span><strong>{fmt(s.median_roe)}</strong></div>
                  <div><span>Coverage</span><strong>{s.coverage_pct != null ? `${fmt(s.coverage_pct, 0)}%` : '—'}</strong></div>
                  <div><span>EV/EBITDA</span><strong>{fmt(s.median_ev_ebitda)}</strong></div>
                </div>
                <div className="sve-card-modern-foot">
                  <KpiChip label={status} tone={tone} />
                  <KpiChip
                    label={s.confidence != null ? `${fmt(s.confidence, 0)}% Conf` : 'Conf —'}
                    tone="confidence"
                  />
                  <span className="sve-open">Open →</span>
                </div>
              </button>
            );
          })}
        </div>
      </section>
    </>
  );
}

function OppRail({ title, accent, rows, onSelectCompany }) {
  return (
    <div className={`opp-rail accent-${accent}`}>
      <h4>{title}</h4>
      <ul>
        {(rows || []).slice(0, 6).map((r) => (
          <li key={`${title}-${r.symbol}`}>
            <button type="button" className="sve-link" onClick={() => onSelectCompany?.(r.symbol, r.company_name)}>
              <strong>{r.symbol}</strong>
              <span>{r.company_name || r.sector || r.transition || r.why || ''}</span>
            </button>
          </li>
        ))}
        {!rows?.length ? <li className="hint">No rows yet</li> : null}
      </ul>
    </div>
  );
}

export function ResearchBoards({ onSelectCompany }) {
  const [opps, setOpps] = useState(null);
  const [premium, setPremium] = useState(null);
  const [rerating, setRerating] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    Promise.all([
      getSveOpportunities({ limit: 10 }),
      getSvePremium({ limit: 10 }),
      getSveRerating({ limit: 15 }),
    ])
      .then(([o, p, r]) => {
        if (cancelled) return;
        setOpps(o);
        setPremium(p);
        setRerating(r);
      })
      .catch(() => {
        if (!cancelled) {
          setOpps(null);
          setPremium(null);
          setRerating(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  if (loading) return <section className="sve-boards hint">Loading opportunity dashboard…</section>;

  const boards = opps?.boards || {};
  const researchBullets = [
    ...(boards.most_attractive || []).slice(0, 1).map((r) => `${r.symbol} screens historically attractive`),
    ...(premium?.rows || []).slice(0, 1).map((r) => `${r.sector || r.symbol} carrying elevated premium`),
    ...(rerating?.rows || []).slice(0, 1).map((r) => `${r.symbol}: ${r.transition}`),
    ...(boards.highest_roe || []).slice(0, 1).map((r) => `${r.symbol} among highest ROE names`),
  ].filter(Boolean);

  return (
    <>
      <section className="sve-boards sve-opp-dash">
        <div className="sve-directory-head">
          <h3>Opportunity dashboard</h3>
          <p className="hint">Warehouse screens for research focus — not recommendations</p>
        </div>
        <div className="opp-rails">
          <OppRail title="Deep value" accent="cheap" rows={boards.most_undervalued || boards.most_attractive} onSelectCompany={onSelectCompany} />
          <OppRail title="Highest premium" accent="premium" rows={premium?.rows || boards.largest_premiums} onSelectCompany={onSelectCompany} />
          <OppRail title="Strongest ROE" accent="quality" rows={boards.highest_roe} onSelectCompany={onSelectCompany} />
          <OppRail title="Research priority" accent="alert" rows={rerating?.rows || boards.most_overvalued} onSelectCompany={onSelectCompany} />
        </div>
      </section>
      <section className="sve-today-research">
        <h3>Today&apos;s research</h3>
        <ul>
          {researchBullets.length
            ? researchBullets.map((b) => <li key={b}>{b}</li>)
            : <li className="hint">Research bullets appear when warehouse screens populate.</li>}
        </ul>
      </section>
    </>
  );
}
