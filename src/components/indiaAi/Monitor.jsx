import React from 'react';
import { fetchExitability } from '@/lib/indiaAiApi';
import { ALL_SUBS, LAYER_LABEL, SUB_LABEL, rupeesCr } from '@/lib/indiaAiSummary';
import { impliedGrowth, runModel, valueOf } from '@/lib/indiaAiEstimates';
import {
  aiMateriality, capitalQuality, earningsMomentum, evidenceConfidence, expectationLoad,
} from '@/lib/indiaAiFactors';
import { MATERIALITY_TIER, TEST_LABEL, classifyMateriality } from '@/lib/indiaAiMateriality';
import {
  FIVE_METRICS, NON_MEMBER_FILED, OUTSIDE, STRATEGY_ASOF, STRATEGY_FACTORS, STRATEGY_ROWS, STRUCTURES,
} from './strategyContent';

/**
 * India AI Infrastructure Monitor: the dashboard view of the page.
 *
 * Built only from AGI's own data: the evidence record, filed figures, AGI's
 * market value and AGI's estimate models. Every figure carries a provenance
 * tag - D disclosed by the company, I AGI arithmetic on disclosed figures,
 * A an AGI estimate - so fact and analysis cannot be confused. There is no
 * consensus tag because AGI has no consensus source, and no broker figure
 * appears anywhere in this view.
 *
 * Colour carries one meaning each: blue is disclosed, green is strong,
 * amber is an AGI estimate, grey is low confidence. The brand orange is for
 * focus and the active control only.
 */

const TAGS = {
  D: ['Disclosed', 'Stated by the company in its own filing, release, presentation or call.', 'text-[#6cb2f0] border-[#2a4a66]'],
  I: ['AGI arithmetic', 'Calculated by AGI from disclosed figures (for example close x filed shares, or order book / quarterly revenue). No assumption involved.', 'text-[#b6c2d1] border-[#3a4453]'],
  A: ['AGI estimate', 'Depends on AGI assumptions (growth, margin, exit multiple). See the Estimates tab for every input.', 'text-[#f0a060] border-[#7a5a2e]'],
};
function Tag({ t }) {
  const [label, why, tone] = TAGS[t];
  return (
    <abbr title={`${label}: ${why}`} className={`ml-1.5 inline-block rounded border px-1 align-middle text-[10px] font-semibold leading-[15px] no-underline ${tone}`}>
      {t}
    </abbr>
  );
}

// Bands read differently by factor: a high materiality is strong (green),
// a high expectation load is a caution (amber), never a green light.
const TONE = {
  strong: 'bg-[#0f2419] text-[#4ade80]',
  neutral: 'bg-[#18202c] text-[#c7cfda]',
  disclosed: 'bg-[#0f1b2a] text-[#6cb2f0]',
  caution: 'bg-[#261c0e] text-[#f0a060]',
  weak: 'bg-[#2a1515] text-[#f28b8b]',
  low: 'bg-[#141a23] text-[#8b95a3]',
  none: 'bg-transparent text-[#5b6675]',
};
const BAND_TONE = {
  default: { high: 'strong', strong: 'strong', medium: 'neutral', moderate: 'neutral', low: 'low', weak: 'weak', 'capital-hungry': 'caution', 'stated only': 'disclosed', 'not measurable': 'none' },
  expectation: { low: 'neutral', moderate: 'neutral', high: 'caution', 'very high': 'weak', 'not measurable': 'none' },
};
function Band({ b, scale = 'default' }) {
  const tone = TONE[BAND_TONE[scale][b] || BAND_TONE.default[b] || 'neutral'];
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-[1px] text-[12px] ${tone}`}>{b}</span>;
}

const TIER = {
  SEGMENT_REPORTED: ['Audited segment', '#4ade80'],
  MANAGEMENT_DISCLOSED: ['Company-stated', '#6cb2f0'],
  NOT_ATTRIBUTABLE: ['Linked, not sized', '#7d8894'],
};
function TierMark({ tier }) {
  const [label, color] = TIER[tier] || ['Not recorded', '#5b6675'];
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
      <span aria-hidden="true" className="inline-block h-2 w-2 rounded-full" style={{ background: color }} />
      <span style={{ color }}>{label}</span>
    </span>
  );
}

const TIER_CHIP = {
  material: 'bg-[#0f2419] text-[#4ade80]',
  'material-estimate': 'bg-[#261c0e] text-[#f0a060]',
  exception: 'border border-dashed border-[#7a5a2e] text-[#f0a060]',
  'not-yet': 'bg-[#141a23] text-[#8b95a3]',
};
const TIER_RANK = { material: 4, 'material-estimate': 3, exception: 2, 'not-yet': 1 };
function MaterialityChip({ mat, long = false }) {
  if (!mat) return <span className="text-[#5b6675]">—</span>;
  const t = MATERIALITY_TIER[mat.tier];
  return <span className={`inline-block whitespace-nowrap rounded-full px-2 py-[1px] text-[12px] ${TIER_CHIP[mat.tier]}`}>{long ? t.label : t.short}</span>;
}

const HARD = new Set(['order', 'capex', 'operating']);
const IMPACT = { order: 'Orders', capex: 'Capacity', operating: 'AI exposure' };
const EV_COLOR = { high: '#4ade80', medium: '#6cb2f0', low: '#7d8894' };
const FOCUS = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e8833a]';

const median = (xs) => {
  const v = xs.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const m = Math.floor(v.length / 2);
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
};
const pct = (v, d = 0) => (Number.isFinite(v) ? `${v >= 0 ? '' : '−'}${Math.abs(v * 100).toFixed(d)}%` : '—');
const signedPct = (v, d = 0) => (Number.isFinite(v) ? `${v >= 0 ? '+' : '−'}${Math.abs(v * 100).toFixed(d)}%` : '—');
const cr = (v) => (Number.isFinite(v) ? rupeesCr(v) : '—');
const dateLabel = (d) => {
  if (!d) return '';
  const t = new Date(`${d}T00:00:00Z`);
  return Number.isNaN(t.getTime()) ? d : t.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
};

/** Everything AGI holds about one member, in one record. */
function buildRecords({ universe, operating, estimates, marketValue, stage3, scoring, exit, materiality }) {
  const mv = Object.fromEntries((marketValue?.rows || []).map((r) => [r.symbol, r.marketValueCr]));
  const s3 = Object.fromEntries((stage3?.rows || []).map((r) => [r.symbol, r.verdict]));
  const models = Object.fromEntries((estimates?.models || []).map((m) => [m.symbol, m]));
  const sc = Object.fromEntries((scoring?.rows || []).map((r) => [r.symbol, r]));
  const books = Object.fromEntries((operating?.orderBooks || []).map((r) => [r.symbol, r]));
  const caps = Object.fromEntries((operating?.dataCentreCapacity || []).map((r) => [r.symbol, r]));
  const liq = Object.fromEntries((exit?.sized || []).map((r) => [r.symbol, r]));
  const shares = {};
  for (const r of operating?.statedShares || []) (shares[r.symbol] ||= []).push(r);
  const targets = {};
  for (const r of operating?.targets || []) (targets[r.symbol] ||= []).push(r);
  const exitMultiple = estimates?.exitMultiple ? valueOf(estimates.exitMultiple, 'base') : null;
  const years = estimates?.horizonYears || 3;
  const matExceptions = Object.fromEntries((materiality?.exceptions || []).map((e) => [e.symbol, e]));
  return (universe?.members || []).map((m) => {
    const model = models[m.symbol];
    const runs = model ? Object.fromEntries(['low', 'base', 'high'].map((s) => [s, runModel(model, { scenario: s })])) : null;
    const row = sc[m.symbol] || {};
    const pat = model ? valueOf(model.params?.patFY26Cr, 'base') : row.patFY26 ?? null;
    const ebitda = model ? valueOf(model.params?.totalEbitdaFY26Cr, 'base') : null;
    const book = books[m.symbol];
    const evidence = [...(m.admittedOn || []), ...(m.supportingEvidence || [])].filter((e) => HARD.has(e.kind));
    const q1 = row.revenueQ1FY27 && row.revenueQ1FY26 ? row.revenueQ1FY27 / row.revenueQ1FY26 - 1 : null;
    const fcf = row.revenueFY26 && Number.isFinite(row.cfoFY26) && Number.isFinite(row.capexFY26)
      ? (row.cfoFY26 - row.capexFY26 - (row.capexIntangiblesFY26 || 0)) / row.revenueFY26 : null;
    const roce = row.statedRoceFY26 ?? (row.ebitFY26 && row.capitalEmployedFY26 ? row.ebitFY26 / row.capitalEmployedFY26 : null);
    const cover = book?.backlogCr && book?.quarterRevenueCr ? book.backlogCr / book.quarterRevenueCr : null;
    const evidenceF = evidenceConfidence(m);
    const mat = materiality?.members && materiality.rules ? classifyMateriality({
      entry: materiality.members[m.symbol] || {},
      rules: materiality.rules,
      evidenceBand: evidenceF.band,
      hardItems: evidence.length,
      fy29Materiality: runs?.base.ok ? runs.base.materiality : null,
      orderCover: cover,
      exception: matExceptions[m.symbol] || null,
    }) : null;
    return {
      mat, vehicle: materiality?.vehicles?.[m.symbol] || null,
      m, model, runs, row, pat, ebitda, book, cap: caps[m.symbol], liq: liq[m.symbol],
      shares: shares[m.symbol] || [], targets: targets[m.symbol] || [], evidence, fcf, roce,
      latest: evidence.map((e) => e.date).filter(Boolean).sort().at(-1) || null,
      mv: mv[m.symbol] ?? null, stage3: s3[m.symbol] || null, q1,
      cover,
      implied: impliedGrowth({ marketValueCr: mv[m.symbol], patCr: pat, exitMultiple, years }),
      factors: {
        materiality: aiMateriality({ model, statedShare: shares[m.symbol]?.[0]?.value }),
        evidence: evidenceF,
        momentum: earningsMomentum(row),
        capital: capitalQuality(row),
        expectation: expectationLoad({ marketValueCr: mv[m.symbol], patCr: pat, exitMultiple, years }),
      },
    };
  });
}

/** Every dated evidence item, newest first. Undated sources carry a read date, not a change date. */
function evidenceFeed(records) {
  const items = [];
  for (const r of records) {
    for (const e of r.m.admittedOn || []) if (e.date) items.push({ r, e, since: false });
    for (const e of r.m.supportingEvidence || []) if (e.date && !e.undated) items.push({ r, e, since: true });
  }
  return items.sort((a, b) => (a.e.date < b.e.date ? 1 : a.e.date > b.e.date ? -1 : 0));
}

function Panel({ id, title, sub, action, children, className = '' }) {
  return (
    <section aria-labelledby={id} className={`min-w-0 rounded-xl bg-[#0e131b] p-5 sm:p-6 ${className}`}>
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <div className="min-w-0">
          <h2 id={id} className="text-[20px] font-semibold tracking-tight text-[#f1f5f9]">{title}</h2>
          {sub ? <p className="mt-1 max-w-[70ch] text-[14px] leading-relaxed text-[#8b95a3]">{sub}</p> : null}
        </div>
        {action ? <div className="ml-auto">{action}</div> : null}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function Segmented({ label, options, value, onChange }) {
  return (
    <div role="group" aria-label={label} className="inline-flex flex-wrap rounded-lg bg-[#151c27] p-1">
      {options.map(([k, text]) => (
        <button
          key={k}
          type="button"
          onClick={() => onChange(k)}
          aria-pressed={value === k}
          className={`rounded-md px-3 py-1.5 text-[13px] ${FOCUS} ${value === k ? 'bg-[#26303f] font-medium text-[#f1f5f9]' : 'text-[#8b95a3] hover:text-[#e3e8ef]'}`}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

/* ── header and KPIs ─────────────────────────────────────────────────── */

/** The monitor's title block; the page renders it above its tab bar. */
export function MonitorHeader({ universe, marketValue }) {
  const n = universe?.members?.length || 0;
  const read = n + (universe?.candidates?.length || 0) + (universe?.excluded?.length || 0);
  return (
    <header className="pb-5 pt-2">
      <p className="text-[12px] font-semibold uppercase tracking-[0.22em] text-[#e8833a]">AGI Investment Intelligence</p>
      <h1 className="mt-2 text-[32px] font-semibold leading-[1.1] tracking-tight text-[#f5f7fa] sm:text-[40px]">India AI Infrastructure Monitor</h1>
      <p className="mt-2 max-w-[70ch] text-[17px] leading-relaxed text-[#9aa5b3]">
        The listed Indian companies whose own filings tie them to AI data-centre build-out, from power to packaging.
      </p>
      <p className="mt-3 flex flex-wrap gap-2 text-[13px] text-[#8b95a3]">
        {n ? <span className="rounded-full bg-[#121823] px-3 py-1">{n} admitted of {read} read</span> : null}
        {marketValue?.closeDate ? <span className="rounded-full bg-[#121823] px-3 py-1">Prices to {dateLabel(marketValue.closeDate)}</span> : null}
        {universe?.version ? <span className="rounded-full bg-[#121823] px-3 py-1">Evidence read {universe.version}</span> : null}
        <span className="rounded-full bg-[#121823] px-3 py-1">No broker or consensus figures</span>
      </p>
    </header>
  );
}

function Kpi({ label, value, sub, tag }) {
  return (
    <div className="min-w-0 rounded-xl bg-[#0e131b] px-5 py-4">
      <p className="text-[13px] text-[#8b95a3]">{label}{tag ? <Tag t={tag} /> : null}</p>
      <p className="mt-1.5 text-[30px] font-semibold leading-none tracking-tight tabular-nums text-[#f5f7fa]">{value}</p>
      <p className="mt-2 text-[13px] leading-snug text-[#6b7684]">{sub}</p>
    </div>
  );
}

function KpiRow({ records, others, marketValue, live }) {
  const read = records.length + others.held.length + others.excluded.length;
  const sized = records.filter((r) => r.m.attribution && r.m.attribution !== 'NOT_ATTRIBUTABLE').length;
  const segment = records.filter((r) => r.m.attribution === 'SEGMENT_REPORTED').length;
  const material = records.filter((r) => r.mat && (r.mat.tier === 'material' || r.mat.tier === 'material-estimate'));
  const onEstimate = material.filter((r) => r.mat.tier === 'material-estimate').length;
  const growth = median(records.map((r) => r.q1));
  const withGrowth = records.filter((r) => r.q1 !== null).length;
  const index = live?.index;
  const lastTrade = live?.quality?.closed && live?.quality?.session_last;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      <Kpi label="Companies admitted" value={records.length} sub={`of ${read} read, each on its own filings`} />
      <Kpi label="Combined market value" value={marketValue?.byLayer ? rupeesCr(marketValue.byLayer.totalCr) : '—'} sub="last close × filed shares, whole companies" tag="I" />
      {records.some((r) => r.mat) ? (
        <Kpi
          label="Economically material"
          value={`${material.length} / ${records.length}`}
          sub={`${material.length - onEstimate} on filed figures · ${onEstimate} on AGI estimate · ${sized} with the AI business sized`}
        />
      ) : <Kpi label="AI business sized" value={`${sized} / ${records.length}`} sub={`${segment} audited segment · ${sized - segment} company-stated`} tag="D" />}
      <Kpi
        label={lastTrade ? 'Basket, last session' : 'Basket today'}
        value={index?.status === 'ok' ? signedPct(index.return_pp / 100, 2) : '—'}
        sub={index?.relative ? `${signedPct(index.relative.excess_pp / 100, 2)} against the Nifty 50 · equal weight` : 'waiting for prices'}
        tag="I"
      />
      <Kpi label="Revenue growth, median" value={growth !== null ? signedPct(growth) : '—'} sub={`latest quarter y/y · ${withGrowth} companies`} tag="I" />
    </div>
  );
}

/* ── the chart ───────────────────────────────────────────────────────── */

/**
 * AI materiality (AGI base case) against expectation load (profit growth the
 * price needs). Both axes are AGI figures; bubble size is market value and
 * colour is evidence confidence. Only the ten largest are labelled; the rest
 * name themselves on hover. Quadrant names describe position, not advice.
 */
function MaterialityScatter({ records, open }) {
  const [hover, setHover] = React.useState(null);
  const W = 760; const H = 440; const pad = { l: 56, r: 20, t: 20, b: 52 };
  const pts = records.map((r) => ({ r, x: r.implied?.cagr ?? null, y: r.runs?.base.ok ? r.runs.base.materiality : null }));
  const plotted = pts.filter((p) => p.x !== null && p.y !== null);
  const notPlotted = pts.filter((p) => !(p.x !== null && p.y !== null)).map((p) => p.r.m.symbol);
  // Points clamp at yMax; the axis runs to yTop so the top quadrant names sit in clear space.
  const xMin = -0.2; const xMax = 0.9; const yMax = 1.2; const yTop = 1.34;
  const sx = (v) => pad.l + ((Math.max(xMin, Math.min(xMax, v)) - xMin) / (xMax - xMin)) * (W - pad.l - pad.r);
  const sy = (v) => H - pad.b - (Math.max(0, Math.min(yMax, v)) / yTop) * (H - pad.t - pad.b);
  // Log scale: market values run from about Rs 7,000 cr to Rs 11 lakh cr.
  const rad = (mv) => (mv > 0 ? Math.max(6, 6 + 7.5 * (Math.log10(mv) - 3.8)) : 6);
  const x25 = sx(0.25); const y25 = sy(0.25);
  const bySize = [...plotted].sort((a, b) => (b.r.mv || 0) - (a.r.mv || 0));
  const labelled = new Set(bySize.slice(0, 10).map((p) => p.r.m.symbol));
  const placed = [];
  const fits = (b) => placed.every((q) => b.x2 < q.x1 || b.x1 > q.x2 || b.y2 < q.y1 || b.y1 > q.y2);
  const bubbles = bySize.map((p) => {
    const cx = sx(p.x); const cy = sy(p.y); const rr = rad(p.r.mv);
    placed.push({ x1: cx - rr, x2: cx + rr, y1: cy - rr, y2: cy + rr });
    return { p, cx, cy, rr };
  });
  // Each quadrant name takes the first of its candidate spots that no bubble covers.
  const L = pad.l + 10; const R = W - pad.r - 10; const T = pad.t + 16; const B = H - pad.b - 10;
  const quad = [
    ['High AI impact · lower hurdle', [[L, T, 'start'], [L, y25 - 10, 'start']]],
    ['High AI impact · high hurdle', [[R, T, 'end'], [x25 + 10, T, 'start'], [R, y25 - 10, 'end']]],
    ['Early · lower hurdle', [[L, B, 'start'], [L, y25 + 20, 'start'], [x25 - 10, y25 + 20, 'end']]],
    ['Early · high hurdle', [[R, B, 'end'], [R, y25 + 20, 'end'], [x25 + 10, B, 'start']]],
  ].map(([text, spots]) => {
    const w = text.length * 6.6;
    for (const [x, y, anchor] of spots) {
      const x1 = anchor === 'start' ? x : x - w;
      const box = { x1, x2: x1 + w, y1: y - 12, y2: y + 3 };
      if (fits(box)) { placed.push(box); return { text, x, y, anchor }; }
    }
    return null;
  }).filter(Boolean);
  const marks = bubbles.map((mk) => {
    if (!labelled.has(mk.p.r.m.symbol)) return { ...mk, ly: null };
    const text = `${mk.p.r.m.symbol}${mk.p.y > yMax ? ' ↑' : ''}${mk.p.x > xMax ? ' →' : ''}`;
    const w = text.length * 7;
    for (const y of [mk.cy - mk.rr - 5, mk.cy + mk.rr + 14]) {
      const box = { x1: mk.cx - w / 2, x2: mk.cx + w / 2, y1: y - 11, y2: y + 2 };
      if (box.y1 > pad.t && box.y2 < H - pad.b && fits(box)) { placed.push(box); return { ...mk, text, ly: y }; }
    }
    return { ...mk, ly: null };
  });
  const hp = hover ? marks.find((mk) => mk.p.r.m.symbol === hover) : null;
  return (
    <Panel
      id="scatter-h"
      title="AI Materiality vs Expectation Load"
      sub="How much AI could add to each company's earnings (AGI base case), against how much profit growth today's price already needs."
      action={(
        <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-[#8b95a3]">
          {['high', 'medium', 'low'].map((b) => (
            <span key={b} className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: EV_COLOR[b] }} />{b} evidence
            </span>
          ))}
          <span>size = market value</span>
        </p>
      )}
    >
      <div className="relative overflow-x-auto">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full min-w-[600px]" role="img" aria-label="Scatter of AI materiality against expectation load">
          {[0, 0.25, 0.5, 0.75, 1].map((v) => (
            <g key={`y${v}`}>
              <line x1={pad.l} x2={W - pad.r} y1={sy(v)} y2={sy(v)} stroke="#18202b" />
              <text x={pad.l - 10} y={sy(v) + 4} textAnchor="end" fontSize="12" fill="#6b7684">{Math.round(v * 100)}%</text>
            </g>
          ))}
          {[-0.2, 0, 0.25, 0.5, 0.75].map((v) => (
            <text key={`x${v}`} x={sx(v)} y={H - pad.b + 20} textAnchor="middle" fontSize="12" fill="#6b7684">{v < 0 ? 'none' : `${Math.round(v * 100)}%`}</text>
          ))}
          <line x1={x25} x2={x25} y1={pad.t} y2={H - pad.b} stroke="#3a4453" strokeDasharray="3 5" />
          <line x1={pad.l} x2={W - pad.r} y1={y25} y2={y25} stroke="#3a4453" strokeDasharray="3 5" />
          {quad.map(({ x, y, anchor, text }) => (
            <text key={text} x={x} y={y} textAnchor={anchor} fontSize="12" fill="#56616f" letterSpacing="0.02em">{text}</text>
          ))}
          <text x={(W + pad.l) / 2} y={H - 8} textAnchor="middle" fontSize="13" fill="#9aa5b3">Expectation load: profit growth a year the price needs →</text>
          <text x={16} y={(H - pad.b + pad.t) / 2} textAnchor="middle" fontSize="13" fill="#9aa5b3" transform={`rotate(-90 16 ${(H - pad.b + pad.t) / 2})`}>AI materiality →</text>
          {marks.map(({ p, cx, cy, rr, text, ly }) => {
            const color = EV_COLOR[p.r.factors.evidence.band] || '#7d8894';
            const active = hover === p.r.m.symbol;
            return (
              <g
                key={p.r.m.symbol}
                role="button"
                tabIndex={0}
                aria-label={`${p.r.m.symbol}: AI materiality ${Math.round(p.y * 100)}%, price needs ${p.x <= 0 ? 'no growth' : `${Math.round(p.x * 100)}% a year`}`}
                onClick={() => open(p.r.m.symbol)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(p.r.m.symbol); } }}
                onMouseEnter={() => setHover(p.r.m.symbol)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(p.r.m.symbol)}
                onBlur={() => setHover(null)}
                className="cursor-pointer focus-visible:outline-none"
              >
                <circle cx={cx} cy={cy} r={rr} fill={color} fillOpacity={active ? 0.55 : 0.28} stroke={color} strokeWidth={active ? 2.5 : 1.5} />
                {ly !== null ? <text x={cx} y={ly} textAnchor="middle" fontSize="12" fontWeight="600" fill="#dbe2ea">{text}</text> : null}
              </g>
            );
          })}
        </svg>
        {hp ? (
          <div
            className="pointer-events-none absolute z-10 w-[240px] rounded-lg bg-[#1a2230] px-3.5 py-3 text-[13px] shadow-xl"
            style={{
              left: `${Math.min(88, Math.max(0, (hp.cx / W) * 100 - (hp.cx / W > 0.6 ? 32 : 0)))}%`,
              top: `${Math.min(70, (hp.cy / H) * 100 + 4)}%`,
            }}
          >
            <p className="font-semibold text-[#f1f5f9]">{hp.p.r.m.symbol} <span className="font-normal text-[#8b95a3]">{hp.p.r.m.name}</span></p>
            <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 text-[#c7cfda]">
              <dt className="text-[#8b95a3]">AI materiality</dt><dd className="tabular-nums">{Math.round(hp.p.y * 100)}%</dd>
              <dt className="text-[#8b95a3]">Price needs</dt><dd className="tabular-nums">{hp.p.x <= 0 ? 'no growth' : `${Math.round(hp.p.x * 100)}% a year`}</dd>
              <dt className="text-[#8b95a3]">Market value</dt><dd className="tabular-nums">{cr(hp.p.r.mv)}</dd>
              <dt className="text-[#8b95a3]">Evidence</dt><dd>{hp.p.r.factors.evidence.band}</dd>
            </dl>
          </div>
        ) : null}
      </div>
      <p className="mt-3 text-[13px] leading-relaxed text-[#6b7684]">
        AI materiality is AGI&rsquo;s FY29 AI/data-centre EBITDA as a share of FY26 filed EBITDA. Expectation load is the profit growth that takes today&rsquo;s market value to 30x earnings by FY29. Dashed lines sit at 25%. A position describes AGI&rsquo;s base case against the price; it is not a recommendation.
        {notPlotted.length ? ` Not plotted, as no base case runs yet: ${notPlotted.join(', ')}.` : ''}
      </p>
    </Panel>
  );
}

/* ── evidence ─────────────────────────────────────────────────────────── */

const FEED_TABS = [['all', 'Latest'], ['order', 'Orders'], ['capex', 'Capacity'], ['operating', 'AI exposure']];

function EvidenceCard({ item, open, full = false }) {
  const { r, e, since } = item;
  return (
    <li className="rounded-lg bg-[#131a24] px-4 py-3.5">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
        <button type="button" onClick={() => open(r.m.symbol)} className={`rounded font-mono font-semibold text-[#f1f5f9] hover:text-[#f0a060] ${FOCUS}`}>{r.m.symbol}</button>
        <span className="rounded-full bg-[#1c2533] px-2 py-[1px] text-[12px] text-[#b6c2d1]">{IMPACT[e.kind] || e.kind}</span>
        <span className="ml-auto whitespace-nowrap tabular-nums text-[#6b7684]">{dateLabel(e.date)}</span>
      </p>
      <p className="mt-1.5 text-[15px] leading-snug text-[#e3e8ef]">{e.headline || e.excerpt}</p>
      {full ? (
        <details className="mt-2 text-[13px]">
          <summary className={`cursor-pointer rounded text-[#6cb2f0] ${FOCUS}`}>In the company&rsquo;s words</summary>
          <blockquote className="mt-1.5 leading-relaxed text-[#b6c2d1]">&ldquo;{e.excerpt}&rdquo;</blockquote>
          <p className="mt-1 text-[#6b7684]">{e.document}{e.page ? `, p. ${e.page}` : ''}{since ? ' · found after admission' : ''}</p>
        </details>
      ) : <p className="mt-1 truncate text-[12px] text-[#5b6675]">{e.document}</p>}
    </li>
  );
}

function LatestEvidence({ records, open, onAll }) {
  const [kind, setKind] = React.useState('all');
  const feed = evidenceFeed(records).filter((x) => kind === 'all' || x.e.kind === kind).slice(0, 6);
  return (
    <Panel id="latest-h" title="Latest evidence" sub="From each company's own filings and calls.">
      <Segmented label="Evidence type" options={FEED_TABS} value={kind} onChange={setKind} />
      <ul className="mt-4 space-y-2.5">
        {feed.map((item) => <EvidenceCard key={`${item.r.m.symbol}-${item.e.date}-${item.e.excerpt.slice(0, 20)}`} item={item} open={open} />)}
      </ul>
      <button type="button" onClick={onAll} className={`mt-4 rounded text-[14px] text-[#6cb2f0] hover:text-[#e3e8ef] ${FOCUS}`}>All evidence, with the company&rsquo;s words &rarr;</button>
    </Panel>
  );
}

function EvidenceTab({ records, open }) {
  const [kind, setKind] = React.useState('all');
  const [q, setQ] = React.useState('');
  const all = evidenceFeed(records);
  const needle = q.trim().toLowerCase();
  const feed = all.filter((x) => (kind === 'all' || x.e.kind === kind)
    && (!needle || `${x.r.m.symbol} ${x.r.m.name} ${x.e.headline || ''} ${x.e.excerpt}`.toLowerCase().includes(needle)));
  const undated = records.reduce((n, r) => n + (r.m.supportingEvidence || []).filter((e) => e.undated).length, 0);
  return (
    <Panel
      id="evidence-h"
      title="Evidence"
      sub={`${all.length} dated items: orders, committed capacity and operating disclosures. Headlines are AGI's summary; open one for the company's own words and the document.`}
      action={<input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search company or text" aria-label="Search evidence" className={`w-[240px] rounded-lg bg-[#151c27] px-3 py-2 text-[14px] text-[#e3e8ef] placeholder:text-[#5b6675] ${FOCUS}`} />}
    >
      <Segmented label="Evidence type" options={FEED_TABS.map(([k, l]) => [k, k === 'all' ? 'All' : l])} value={kind} onChange={setKind} />
      <ul className="mt-4 grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
        {feed.map((item) => <EvidenceCard key={`${item.r.m.symbol}-${item.e.date}-${item.e.excerpt.slice(0, 20)}`} item={item} open={open} full />)}
      </ul>
      {!feed.length ? <p className="mt-4 text-[14px] text-[#8b95a3]">Nothing matches.</p> : null}
      {undated ? <p className="mt-4 text-[13px] text-[#6b7684]">{undated} undated item{undated === 1 ? '' : 's'} (a website table, for example) are in the company records but not in this feed, as they carry no change date.</p> : null}
    </Panel>
  );
}

/* ── the stack ────────────────────────────────────────────────────────── */

function Stack({ records, filter, setFilter }) {
  const layers = ['power', 'data_centre', 'semiconductor', 'infrastructure'];
  return (
    <Panel
      id="stack-h"
      title="AI infrastructure stack"
      sub="Four layers, from the grid to the chip. Choose a sub-layer to filter the matrix."
      action={filter ? <button type="button" onClick={() => setFilter(null)} className={`rounded text-[14px] text-[#6cb2f0] ${FOCUS}`}>Clear filter</button> : null}
    >
      <div className="grid gap-x-8 gap-y-6 md:grid-cols-2 xl:grid-cols-4">
        {layers.map((layer) => {
          const inLayer = records.filter((r) => r.m.layer === layer);
          return (
            <div key={layer} className="min-w-0">
              <div className="border-b border-[#1c2430] pb-2">
                <button
                  type="button"
                  onClick={() => setFilter({ layer })}
                  aria-pressed={filter?.layer === layer && !filter?.sub}
                  className={`flex w-full items-baseline justify-between rounded text-left ${FOCUS}`}
                >
                  <span className="text-[17px] font-semibold text-[#f1f5f9]">{LAYER_LABEL[layer]}</span>
                  <span className="text-[14px] tabular-nums text-[#8b95a3]">{inLayer.length}</span>
                </button>
              </div>
              <ul className="mt-2 space-y-1">
                {ALL_SUBS.filter(([l]) => l === layer).map(([, sub]) => {
                  const rs = inLayer.filter((r) => (r.m.subLayers || []).includes(sub));
                  const g = median(rs.map((r) => r.q1));
                  const x = median(rs.map((r) => r.implied?.cagr));
                  const sized = rs.filter((r) => r.m.attribution && r.m.attribution !== 'NOT_ATTRIBUTABLE').length;
                  const active = filter?.layer === layer && filter?.sub === sub;
                  return (
                    <li key={sub}>
                      <button
                        type="button"
                        onClick={() => setFilter({ layer, sub })}
                        aria-pressed={active}
                        disabled={!rs.length}
                        title={rs.length ? `${rs.map((r) => r.m.symbol).join(', ')} · median price needs ${x === null ? '—' : x <= 0 ? 'no growth' : `${pct(x)} a year`}` : 'No company discloses more than intent here yet'}
                        className={`w-full rounded-lg px-2.5 py-2 text-left ${FOCUS} ${active ? 'bg-[#1c2534]' : 'hover:bg-[#141b26]'} disabled:cursor-default disabled:hover:bg-transparent`}
                      >
                        <span className="flex items-baseline justify-between gap-2">
                          <span className={`text-[15px] ${rs.length ? 'text-[#e3e8ef]' : 'text-[#5b6675]'}`}>{SUB_LABEL[sub]}</span>
                          <span className="text-[14px] tabular-nums text-[#8b95a3]">{rs.length || '—'}</span>
                        </span>
                        {rs.length ? (
                          <span className="mt-0.5 block text-[13px] text-[#6b7684]">
                            revenue {signedPct(g)} y/y · {sized} of {rs.length} sized
                          </span>
                        ) : null}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

/* ── the matrix ───────────────────────────────────────────────────────── */

const VIEWS = [['overview', 'Overview'], ['evidence', 'Evidence'], ['financials', 'Financials'], ['estimates', 'AGI estimates']];

/** Column definitions per view: header, provenance tag, cell, sort key. */
function columns(view) {
  const est = (r, s, f) => (r.runs?.[s]?.ok ? f(r.runs[s]) : null);
  const views = {
    overview: [
      ['Evidence', 'D', (r) => <TierMark tier={r.m.attribution} />, (r) => ({ SEGMENT_REPORTED: 3, MANAGEMENT_DISCLOSED: 2, NOT_ATTRIBUTABLE: 1 }[r.m.attribution] || 0)],
      ['Materiality test', null, (r) => <MaterialityChip mat={r.mat} />, (r) => (r.mat ? TIER_RANK[r.mat.tier] : null)],
      ['AI materiality', null, (r) => <span className="inline-flex items-center gap-2"><Band b={r.factors.materiality.band} />{r.factors.materiality.value ? <span className="text-[#9aa5b3]">{r.factors.materiality.value}</span> : null}</span>, (r) => (r.runs?.base.ok ? r.runs.base.materiality : null)],
      ['Revenue y/y', 'I', (r) => signedPct(r.q1), (r) => r.q1],
      ['Market value', 'I', (r) => cr(r.mv), (r) => r.mv],
      ['Expectation load', 'A', (r) => (r.implied ? <span className="inline-flex items-center gap-2"><Band b={r.factors.expectation.band} scale="expectation" /><span className="text-[#9aa5b3]">{r.implied.cagr <= 0 ? 'none' : `${pct(r.implied.cagr)}/yr`}</span></span> : '—'), (r) => r.implied?.cagr ?? null],
      ['Capital quality', 'I', (r) => <Band b={r.factors.capital.band} />, (r) => r.roce],
      ['₹100 cr position', 'I', (r) => (r.liq ? (r.liq.meetsTarget ? 'fits' : r.liq.exception
        ? <span title={r.liq.exception.context || 'Recorded sizing exception'}>{cr(r.liq.maxExecutablePosition / 1e7)}<span className="ml-1.5 text-[12px] text-[#f0a060]">exception</span></span>
        : `up to ${cr(r.liq.maxExecutablePosition / 1e7)}`) : '…'), (r) => (r.liq ? r.liq.maxExecutablePosition : null)],
    ],
    evidence: [
      ['Evidence', 'D', (r) => <TierMark tier={r.m.attribution} />, (r) => ({ SEGMENT_REPORTED: 3, MANAGEMENT_DISCLOSED: 2, NOT_ATTRIBUTABLE: 1 }[r.m.attribution] || 0)],
      ['Hard items', 'D', (r) => r.evidence.length, (r) => r.evidence.length],
      ['Latest', 'D', (r) => dateLabel(r.latest) || '—', (r) => r.latest],
      ['Stated AI/DC figure', 'D', (r) => (r.shares[0] ? <span title={r.shares[0].quote}>{r.shares[0].value}</span> : <span className="text-[#5b6675]">not stated</span>), null],
      ['Watch', 'D', (r) => (r.targets[0] ? <span className="text-[#9aa5b3]">{r.targets[0].target}</span> : <span className="text-[#5b6675]">next results</span>), null],
    ],
    financials: [
      ['FY26 revenue', 'D', (r) => cr(r.row.revenueFY26), (r) => r.row.revenueFY26],
      ['FY26 EBITDA', 'D', (r) => cr(r.ebitda), (r) => r.ebitda],
      ['FY26 profit', 'D', (r) => cr(r.pat), (r) => r.pat],
      ['FCF / revenue', 'I', (r) => signedPct(r.fcf), (r) => r.fcf],
      ['ROCE', 'I', (r) => (r.roce !== null ? <>{pct(r.roce)}{r.row.statedRoceFY26 ? <span className="ml-1 text-[12px] text-[#6cb2f0]">stated</span> : null}</> : '—'), (r) => r.roce],
      ['Order book', 'D', (r) => cr(r.book?.backlogCr), (r) => r.book?.backlogCr ?? null],
      ['Order cover', 'I', (r) => (r.cover !== null ? `${r.cover.toFixed(1)} qtrs` : '—'), (r) => r.cover],
    ],
    estimates: [
      ['Model', null, (r) => (r.model ? <span className="text-[#c9b699]">{r.model.title}</span> : <span className="text-[#5b6675]">not modelled</span>), null],
      ['FY29 AI/DC revenue', 'A', (r) => (r.runs?.base.ok ? <span className="text-[#f5d9b0]">{cr(r.runs.base.aiRevenueCr)}<span className="block text-[12px] text-[#8a7658]">{est(r, 'low', (x) => cr(x.aiRevenueCr)) || '—'} to {est(r, 'high', (x) => cr(x.aiRevenueCr)) || '—'}</span></span> : '—'), (r) => est(r, 'base', (x) => x.aiRevenueCr)],
      ['FY29 AI/DC EBITDA', 'A', (r) => <span className="text-[#f5d9b0]">{est(r, 'base', (x) => cr(x.aiEbitdaCr)) || '—'}</span>, (r) => est(r, 'base', (x) => x.aiEbitdaCr)],
      ['vs FY26 EBITDA', 'A', (r) => <span className="text-[#f5d9b0]">{est(r, 'base', (x) => (x.materiality != null ? pct(x.materiality) : null)) || '—'}</span>, (r) => est(r, 'base', (x) => x.materiality)],
      ['Waits for', null, (r) => (r.runs && !r.runs.base.ok ? r.runs.base.missing.map((k) => r.model.params?.[k]?.label || k).join(', ') : '—'), null],
    ],
  };
  return views[view];
}

/** Summary line that changes with the selected layer. */
function FilterSummary({ rs }) {
  const sum = (xs) => xs.filter(Number.isFinite).reduce((a, b) => a + b, 0);
  const mv = sum(rs.map((r) => r.mv));
  const book = sum(rs.map((r) => r.book?.backlogCr));
  const growth = median(rs.map((r) => r.q1));
  const cover = median(rs.map((r) => r.cover));
  const op = rs.filter((r) => Number.isFinite(r.cap?.operationalMW) && r.cap.operationalMW > 0).map((r) => `${r.m.symbol} ${r.cap.operationalMW} MW`);
  const stats = [
    ['Companies', rs.length],
    ['Market value', rupeesCr(mv)],
    ['Revenue growth, median', growth !== null ? signedPct(growth) : '—'],
    book ? ['Order book', rupeesCr(book)] : null,
    cover !== null ? ['Order cover, median', `${cover.toFixed(1)} qtrs`] : null,
    // Not summed: some companies state IT load and others power capacity.
    op.length ? ['Operating capacity, as stated', op.join(' · ')] : null,
  ].filter(Boolean);
  return (
    <dl className="mb-4 flex flex-wrap gap-x-8 gap-y-3 rounded-lg bg-[#131a24] px-4 py-3">
      {stats.map(([k, v]) => (
        <div key={k}>
          <dt className="text-[12px] text-[#8b95a3]">{k}</dt>
          <dd className="mt-0.5 text-[16px] font-semibold tabular-nums text-[#f1f5f9]">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function Matrix({ records, others, filter, setFilter, open, matrixRef, rules }) {
  const [view, setView] = React.useState('overview');
  const [status, setStatus] = React.useState('members');
  const [q, setQ] = React.useState('');
  const [sort, setSort] = React.useState({ col: 'Market value', dir: -1 });
  const cols = columns(view);
  const fixed = [['Company', null, null, (r) => r.m.symbol], ['Layer', null, null, (r) => r.m.layer]];
  const needle = q.trim().toLowerCase();
  const matches = (r) => (filter?.symbols ? filter.symbols.includes(r.m.symbol)
    : r.m.layer === filter.layer && (!filter.sub || (r.m.subLayers || []).includes(filter.sub)));
  const filtered = records.filter((r) => (!filter || matches(r)) && (!needle || `${r.m.symbol} ${r.m.name}`.toLowerCase().includes(needle)));
  const sortCol = [...fixed, ...cols].find(([h]) => h === sort.col) || ['Market value', null, null, (r) => r.mv];
  const key = sortCol[3] || ((r) => r.mv);
  const shown = [...filtered].sort((a, b) => {
    const x = key(a); const y = key(b);
    if (x === null || x === undefined) return 1;
    if (y === null || y === undefined) return -1;
    return (x < y ? -1 : x > y ? 1 : 0) * sort.dir;
  });
  const filterLabel = filter ? filter.label || `${LAYER_LABEL[filter.layer]}${filter.sub ? ` · ${SUB_LABEL[filter.sub]}` : ''}` : null;
  return (
    <div ref={matrixRef} className="scroll-mt-4">
      <Panel
        id="matrix-h"
        title="Company matrix"
        sub="Every admitted company on one screen. Select a row for its full record: reported facts, AGI's estimate, and what to watch."
        action={<input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search company" aria-label="Search companies" className={`w-[220px] rounded-lg bg-[#151c27] px-3 py-2 text-[14px] text-[#e3e8ef] placeholder:text-[#5b6675] ${FOCUS}`} />}
      >
        <div className="mb-4 flex flex-wrap items-center gap-3">
          <Segmented label="Columns" options={VIEWS} value={view} onChange={setView} />
          <Segmented
            label="Status"
            options={[['members', `Admitted ${records.length}`], ['held', `Held ${others.held.length}`], ['excluded', `Excluded ${others.excluded.length}`]]}
            value={status}
            onChange={setStatus}
          />
          {filterLabel ? (
            <button type="button" onClick={() => setFilter(null)} className={`inline-flex items-center gap-2 rounded-full bg-[#2a1d10] px-3 py-1.5 text-[13px] text-[#f0a060] ${FOCUS}`}>
              {filterLabel}<span aria-hidden="true">×</span><span className="sr-only">Clear filter</span>
            </button>
          ) : null}
        </div>
        {filter && status === 'members' ? <FilterSummary rs={filtered} /> : null}
        {status === 'members' ? (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1120px] text-[14px]">
              <thead>
                <tr className="text-left text-[12px] text-[#8b95a3]">
                  {[...fixed, ...cols].map(([h, tag, , sortKey]) => (
                    <th key={h} scope="col" className="whitespace-nowrap border-b border-[#1c2430] py-2.5 pr-4 font-medium" aria-sort={sort.col === h ? (sort.dir > 0 ? 'ascending' : 'descending') : undefined}>
                      {sortKey ? (
                        <button type="button" onClick={() => setSort((s) => ({ col: h, dir: s.col === h ? -s.dir : (h === 'Company' || h === 'Layer' ? 1 : -1) }))} className={`rounded hover:text-[#e3e8ef] ${FOCUS} ${sort.col === h ? 'text-[#e3e8ef]' : ''}`}>
                          {h}{sort.col === h ? (sort.dir > 0 ? ' ↑' : ' ↓') : ''}
                        </button>
                      ) : h}
                      {tag ? <Tag t={tag} /> : null}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shown.map((r) => (
                  <tr
                    key={r.m.symbol}
                    onClick={() => open(r.m.symbol)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(r.m.symbol); } }}
                    tabIndex={0}
                    aria-label={`Open ${r.m.symbol}`}
                    className="cursor-pointer border-b border-[#151c26] align-middle hover:bg-[#131a24] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#e8833a]"
                  >
                    <td className="py-3 pr-4">
                      <span className="font-mono font-semibold text-[#f1f5f9]">{r.m.symbol}</span>
                      <span className="block max-w-[220px] truncate text-[13px] text-[#6b7684]">{r.m.name}</span>
                    </td>
                    <td className="py-3 pr-4 text-[#b6c2d1]">
                      {LAYER_LABEL[r.m.layer]}
                      <span className="block text-[13px] text-[#6b7684]">{(r.m.subLayers || []).map((s) => SUB_LABEL[s] || s).join(' + ')}</span>
                    </td>
                    {cols.map(([h, , cell]) => <td key={h} className="py-3 pr-4 tabular-nums text-[#dbe2ea]">{cell(r)}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
            {!shown.length ? <p className="py-6 text-[14px] text-[#8b95a3]">No company matches.</p> : null}
          </div>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {others[status].map((c) => (
              <li key={c.symbol} className="rounded-lg bg-[#131a24] px-4 py-3">
                <p><span className="font-mono font-semibold text-[#f1f5f9]">{c.symbol}</span> <span className="text-[14px] text-[#8b95a3]">{c.name}</span></p>
                <p className="mt-1 text-[14px] leading-relaxed text-[#9aa5b3]">{c.note || c.reason}</p>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-4 text-[13px] leading-relaxed text-[#6b7684]">
          Column tags: <Tag t="D" /> disclosed by the company · <Tag t="I" /> AGI arithmetic on disclosed figures · <Tag t="A" /> AGI estimate. Headers sort. No consensus or broker figures are used.
        </p>
        {rules?.text ? (
          <details className="mt-3 text-[13px]">
            <summary className={`cursor-pointer rounded text-[#6cb2f0] ${FOCUS}`}>How the materiality test works</summary>
            <ul className="mt-2 max-w-[90ch] list-disc space-y-1.5 pl-5 leading-relaxed text-[#9aa5b3]">
              {rules.text.map((t) => <li key={t}>{t}</li>)}
              <li>Separate from sizing: the &lsquo;₹100 cr position&rsquo; column is how large a position the stock&rsquo;s turnover can carry, not how large its AI business is.</li>
            </ul>
          </details>
        ) : null}
      </Panel>
    </div>
  );
}

/* ── the chain ────────────────────────────────────────────────────────── */

/** AGI's grouping of members (and held candidates) along the physical chain. */
const CHAIN = [
  ['Compute', ['NETWEB'], []],
  ['Connectivity', ['STLTECH', 'HFCL'], []],
  ['Data centres', ['ADANIENT', 'BHARTIARTL', 'RELIANCE', 'LT', 'ANANTRAJ'], ['ESDS']],
  ['Cooling and MEP', ['BLUESTARCO'], []],
  ['Electrical equipment', ['POWERINDIA', 'ABB', 'GVT&D', 'SCHNEIDER'], ['SIEMENS', 'INDOTECH']],
  ['Backup and prime power', ['CUMMINSIND', 'KIRLOSENG', 'TDPOWERSYS', 'CRAFTSMAN'], []],
  ['Components', ['MTARTECH'], []],
  ['Cables', ['POLYCAB', 'APARINDS', 'DIACABS'], ['KEI']],
  ['Power supply and storage', ['CLEANMAX', 'TATAPOWER', 'ADANIGREEN'], ['NTPCGREEN', 'ACMESOLAR', 'WAAREEENER', 'PREMIERENE']],
  ['Grid and transmission', ['ADANIENSOL', 'POWERGRID'], ['KEC']],
  ['Semiconductors', ['KAYNES', 'CGPOWER', 'SANSERA'], ['FLUOROCHEM', 'NAVINFLUOR', 'SYRMA', 'PARAS']],
];

function SupplyChain({ records, held, setFilter, open }) {
  const bySym = Object.fromEntries(records.map((r) => [r.m.symbol, r]));
  const heldBy = Object.fromEntries(held.map((c) => [c.symbol, c]));
  return (
    <Panel id="chain-h" title="The chain, from compute to the grid" sub="The order power and equipment flow into an AI data centre, read from the rack outward. Choose a stage to filter the matrix. Dashed names are held, not admitted.">
      <ol className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {CHAIN.map(([stage, syms, heldSyms]) => {
          const rs = syms.map((s) => bySym[s]).filter(Boolean);
          const mv = rs.reduce((n, r) => n + (r.mv || 0), 0);
          return (
            <li key={stage} className="rounded-lg bg-[#131a24] px-4 py-3">
              <button type="button" onClick={() => setFilter({ symbols: syms, label: stage })} className={`flex w-full items-baseline justify-between gap-2 rounded text-left ${FOCUS}`}>
                <span className="text-[15px] font-semibold text-[#f1f5f9]">{stage}</span>
                <span className="whitespace-nowrap text-[13px] tabular-nums text-[#8b95a3]">{rupeesCr(mv)}</span>
              </button>
              <p className="mt-2 flex flex-wrap gap-1.5">
                {rs.map((r) => (
                  <button key={r.m.symbol} type="button" onClick={() => open(r.m.symbol)} className={`rounded-md bg-[#1c2533] px-2 py-0.5 font-mono text-[12px] text-[#dbe2ea] hover:bg-[#26324a] ${FOCUS}`}>
                    {r.m.symbol}
                  </button>
                ))}
                {heldSyms.filter((s) => heldBy[s]).map((s) => (
                  <span key={s} title={`Held: ${heldBy[s].note || ''}`} className="rounded-md border border-dashed border-[#2a3444] px-2 py-0.5 font-mono text-[12px] text-[#5b6675]">{s}</span>
                ))}
              </p>
            </li>
          );
        })}
      </ol>
    </Panel>
  );
}

/* ── estimates ────────────────────────────────────────────────────────── */

function EstimatesTab({ records, estimates, open, onResearch }) {
  const modelled = records.filter((r) => r.model);
  const running = modelled.filter((r) => r.runs.base.ok).sort((a, b) => (b.runs.base.materiality || 0) - (a.runs.base.materiality || 0));
  const waiting = modelled.filter((r) => !r.runs.base.ok);
  const exit = estimates?.exitMultiple ? valueOf(estimates.exitMultiple, 'base') : 30;
  const maxM = Math.max(1, ...running.map((r) => r.runs.base.materiality || 0));
  return (
    <div className="space-y-4">
      <section aria-labelledby="est-h" className="rounded-xl border border-dashed border-[#7a5a2e] bg-[#110e0a] p-5 sm:p-6">
        <h2 id="est-h" className="text-[20px] font-semibold tracking-tight text-[#f5d9b0]">AGI estimates<Tag t="A" /></h2>
        <p className="mt-1 max-w-[75ch] text-[14px] leading-relaxed text-[#c9b699]">
          Scenario arithmetic on disclosed figures, to FY29. Every input is either a company figure with its source or an AGI assumption with a range and a reason. These are not company guidance and not consensus. {modelled.length} of {records.length} companies are modelled; {waiting.length} wait for a figure no company discloses. Expectation load uses a {exit}x exit multiple.
        </p>
        <button type="button" onClick={() => onResearch('estimates')} className={`mt-3 rounded text-[14px] text-[#f0a060] hover:text-[#f5d9b0] ${FOCUS}`}>Change the assumptions in Research &rarr;</button>
      </section>
      <ul className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
        {running.map((r) => {
          const b = r.runs.base;
          return (
            <li key={r.m.symbol}>
              <button type="button" onClick={() => open(r.m.symbol)} className={`block w-full rounded-xl bg-[#0e131b] px-5 py-4 text-left hover:bg-[#121925] ${FOCUS}`}>
                <p className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-[15px] font-semibold text-[#f1f5f9]">{r.m.symbol}</span>
                  <TierMark tier={r.m.attribution} />
                </p>
                <p className="mt-0.5 text-[13px] text-[#8a7658]">{r.model.title}</p>
                <div className="mt-3 grid grid-cols-3 gap-2 text-[13px]">
                  {['low', 'base', 'high'].map((s) => (
                    <div key={s}>
                      <p className="text-[12px] capitalize text-[#8a7658]">{s}</p>
                      <p className={`tabular-nums ${s === 'base' ? 'text-[16px] font-semibold text-[#f5d9b0]' : 'text-[#c9b699]'}`}>{r.runs[s].ok ? cr(r.runs[s].aiRevenueCr) : '—'}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-1 text-[12px] text-[#6b7684]">FY29 AI/data-centre revenue</p>
                <div className="mt-3">
                  <p className="flex justify-between text-[13px]"><span className="text-[#9aa5b3]">vs FY26 EBITDA, base</span><span className="tabular-nums text-[#f5d9b0]">{b.materiality != null ? pct(b.materiality) : '—'}</span></p>
                  <div className="mt-1 h-1.5 rounded-full bg-[#1c1812]" aria-hidden="true">
                    <div className="h-1.5 rounded-full bg-[#f0a060]" style={{ width: `${Math.min(100, ((b.materiality || 0) / maxM) * 100)}%` }} />
                  </div>
                </div>
              </button>
            </li>
          );
        })}
      </ul>
      {waiting.length ? (
        <Panel id="waiting-h" title="Waiting for a disclosure" sub="These models do not run on a guess. Each names the figure it needs.">
          <ul className="grid gap-3 md:grid-cols-2">
            {waiting.map((r) => (
              <li key={r.m.symbol} className="rounded-lg bg-[#131a24] px-4 py-3 text-[14px]">
                <button type="button" onClick={() => open(r.m.symbol)} className={`rounded font-mono font-semibold text-[#f1f5f9] hover:text-[#f0a060] ${FOCUS}`}>{r.m.symbol}</button>
                <span className="text-[#8b95a3]"> needs {r.runs.base.missing.map((k) => (r.model.params?.[k]?.label || k).toLowerCase()).join(' and ')}</span>
              </li>
            ))}
          </ul>
        </Panel>
      ) : null}
    </div>
  );
}


/* ── strategy ─────────────────────────────────────────────────────────── */

const RATING_TONE = {
  'Very High': 'bg-[#0f2419] text-[#4ade80]',
  High: 'bg-[#0f2419] text-[#86d9a4]',
  'Medium-High': 'bg-[#18202c] text-[#c7cfda]',
  Medium: 'bg-[#141a23] text-[#8b95a3]',
};
const statusTone = (st) => (/Exception/.test(st) ? 'border border-dashed border-[#7a5a2e] text-[#f0a060]'
  : /High Risk/.test(st) ? 'bg-[#2a1515] text-[#f28b8b]'
    : /Emerging|Optionality|Execution/.test(st) ? 'bg-[#0f1b2a] text-[#6cb2f0]'
      : 'bg-[#1c2533] text-[#f1f5f9]');

/** Filed-figure ratios for one strategy row, from member data or the non-member filings. */
function strategyFigures(row, rec) {
  const f = rec ? rec.row : NON_MEMBER_FILED[row.symbol] || {};
  const num = (v) => (Number.isFinite(v) ? v : null);
  const rev = num(f.revenueFY26);
  const capex = num(f.capexFY26) !== null ? f.capexFY26 + (num(f.capexIntangiblesFY26) || 0) : null;
  const q1 = num(f.revenueQ1FY27) && num(f.revenueQ1FY26) ? f.revenueQ1FY27 / f.revenueQ1FY26 - 1 : null;
  const pat = rec ? rec.pat : num(f.patFY26);
  return {
    q1,
    capexSales: rev && capex !== null ? capex / rev : null,
    fcfSales: rev && num(f.cfoFY26) !== null && capex !== null ? (f.cfoFY26 - capex) / rev : null,
    pe: rec && rec.mv && pat > 0 ? rec.mv / pat : null,
    capital: rec ? rec.factors.capital : capitalQuality(f),
    expectation: rec ? rec.factors.expectation : null,
  };
}

function StrategyTab({ records, open }) {
  const bySym = Object.fromEntries(records.map((r) => [r.m.symbol, r]));
  const rows = STRATEGY_ROWS.map((row) => ({ row, rec: bySym[row.symbol] || null }));
  const netweb = bySym.NETWEB;
  const cols = [
    ['Stock'], ['AI layer'], ['AI materiality'], ['Hard evidence / key KPI'],
    ['Revenue growth, latest qtr', 'I'], ['Capex / sales, FY26', 'I'], ['FCF / sales, FY26', 'I'], ['P/E, FY26 profit', 'I'],
    ['Capital quality', 'I'], ['Expectation load', 'A'], ['AGI status'],
  ];
  const symButton = (sym, label) => (bySym[sym]
    ? <button type="button" onClick={() => open(sym)} className={`rounded-md bg-[#1c2533] px-2 py-0.5 font-mono text-[12px] text-[#dbe2ea] hover:bg-[#26324a] ${FOCUS}`}>{label || sym}</button>
    : <span className="rounded-md border border-dashed border-[#2a3444] px-2 py-0.5 font-mono text-[12px] text-[#8b95a3]" title="Not an index member">{label || sym}</span>);
  return (
    <div className="space-y-4">
      <Panel
        id="strategy-h"
        title="Final AGI basket"
        sub={`Selected on ${STRATEGY_FACTORS.join(', ')}. Layer, AI materiality rating, evidence and status are AGI's judgments; every evidence line is checked against the company's own documents.`}
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1380px] text-[14px]">
            <thead>
              <tr className="text-left text-[12px] text-[#8b95a3]">
                {cols.map(([h, tag]) => (
                  <th key={h} scope="col" className="border-b border-[#1c2430] py-2.5 pr-4 align-bottom font-medium">{h}{tag ? <Tag t={tag} /> : null}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(({ row, rec }) => {
                const x = strategyFigures(row, rec);
                return (
                  <tr key={row.symbol} className="border-b border-[#151c26] align-top">
                    <td className="py-3 pr-4">
                      {rec ? (
                        <button type="button" onClick={() => open(row.symbol)} className={`rounded text-left font-semibold text-[#f1f5f9] hover:text-[#f0a060] ${FOCUS}`}>{row.name}</button>
                      ) : <span className="font-semibold text-[#f1f5f9]">{row.name}</span>}
                      <span className="block font-mono text-[12px] text-[#6b7684]">{row.symbol}{row.member === false ? ' · not an index member' : ''}</span>
                    </td>
                    <td className="py-3 pr-4 text-[#b6c2d1]">{row.layer}</td>
                    <td className="py-3 pr-4"><span className={`inline-block whitespace-nowrap rounded-full px-2 py-[1px] text-[12px] ${RATING_TONE[row.rating] || RATING_TONE.Medium}`}>{row.rating}</span></td>
                    <td className="max-w-[300px] py-3 pr-4 leading-snug text-[#dbe2ea]">{row.evidence}</td>
                    <td className="py-3 pr-4 tabular-nums text-[#dbe2ea]">{signedPct(x.q1)}</td>
                    <td className="py-3 pr-4 tabular-nums text-[#dbe2ea]">{pct(x.capexSales)}</td>
                    <td className="py-3 pr-4 tabular-nums text-[#dbe2ea]">{signedPct(x.fcfSales)}</td>
                    <td className="py-3 pr-4 tabular-nums text-[#dbe2ea]">{x.pe !== null ? `${x.pe.toFixed(0)}x` : <span className="text-[#5b6675]">{rec ? '—' : 'not priced'}</span>}</td>
                    <td className="py-3 pr-4"><Band b={x.capital.band} /></td>
                    <td className="py-3 pr-4">
                      {x.expectation ? (
                        <span className="inline-flex flex-col gap-0.5">
                          <Band b={x.expectation.band} scale="expectation" />
                          {rec.implied ? <span className="text-[12px] text-[#8b95a3]">{rec.implied.cagr <= 0 ? 'no growth needed' : `needs ${pct(rec.implied.cagr)}/yr`}</span> : null}
                        </span>
                      ) : <span className="text-[#5b6675]">not priced</span>}
                    </td>
                    <td className="py-3 pr-4">
                      <span className={`inline-block whitespace-nowrap rounded-full px-2 py-[1px] text-[12px] font-medium ${statusTone(row.status)}`}>{row.status}</span>
                      <span className="mt-1 block text-[12px] text-[#6b7684]">AGI test: {rec?.mat ? MATERIALITY_TIER[rec.mat.tier].label.toLowerCase() : 'not a member'}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="mt-4 max-w-[110ch] text-[13px] leading-relaxed text-[#6b7684]">
          Financial columns are AGI arithmetic on each company&rsquo;s filed FY26 and June-quarter results: revenue growth is the June 2026 quarter against June 2025; capex includes intangibles; FCF is operating cash flow less capex; P/E is AGI&rsquo;s market value at the last close over FY26 profit. Capital quality and expectation load are AGI&rsquo;s factor bands; expectation load is the profit growth that takes today&rsquo;s market value to 30x earnings by FY29. No broker or consensus figures are used. KEC and NTPC Green are held candidates, not index members, so AGI does not price them. The &lsquo;AGI test&rsquo; line is the rule-based materiality tier, shown beside the basket status. A research classification, not a recommendation to buy or sell.
        </p>
      </Panel>

      <Panel id="structures-h" title="How to interpret this list" sub="There are really four different investment structures inside it.">
        <div className="grid gap-3 md:grid-cols-2">
          {STRUCTURES.map((st) => (
            <section key={st.title} className="rounded-lg bg-[#131a24] px-5 py-4">
              <h3 className="text-[16px] font-semibold text-[#f1f5f9]">{st.title}</h3>
              <p className="mt-2 flex flex-wrap gap-1.5">{st.names.map((sym) => <React.Fragment key={sym}>{symButton(sym)}</React.Fragment>)}</p>
              <p className="mt-2.5 text-[14px] leading-relaxed text-[#b6c2d1]">{st.text}</p>
            </section>
          ))}
        </div>
        {netweb ? (
          <p className="mt-4 max-w-[100ch] text-[14px] leading-relaxed text-[#9aa5b3]">
            Netweb, for example, reported AI systems at about 62% of June-quarter revenue and an order book of about ₹2,507 crore, which is why direct economic exposure matters more than simply mentioning AI.
          </p>
        ) : null}
      </Panel>

      <Panel id="outside-h" title="Kept outside the basket for now" sub="Valuable monitor names, not yet in the main basket.">
        <ul className="grid gap-3 md:grid-cols-2">
          {OUTSIDE.map((o) => (
            <li key={o.name} className="rounded-lg bg-[#131a24] px-4 py-3">
              <p className="font-semibold text-[#f1f5f9]">{o.name}</p>
              <p className="mt-1 text-[14px] leading-relaxed text-[#9aa5b3]">{o.text}</p>
            </li>
          ))}
        </ul>
      </Panel>

      <Panel id="metrics-h" title="The five metrics beside every company" sub="Not one aggregate score: five measures, side by side.">
        <dl className="grid gap-3 md:grid-cols-5">
          {FIVE_METRICS.map(([k, v]) => (
            <div key={k} className="rounded-lg bg-[#131a24] px-4 py-3">
              <dt className="font-semibold text-[#f1f5f9]">{k}</dt>
              <dd className="mt-1 text-[14px] leading-relaxed text-[#9aa5b3]">{v}</dd>
            </div>
          ))}
        </dl>
        <p className="mt-4 max-w-[100ch] text-[14px] leading-relaxed text-[#b6c2d1]">
          That makes the difference between something like Netweb and KEC immediately obvious: Netweb has much higher current AI materiality
          {netweb?.implied ? `, but also a far heavier valuation burden (its price needs profit growth of ${pct(netweb.implied.cagr)} a year to reach 30x by FY29)` : ', but also a far heavier valuation burden'};
          KEC has much less AI materiality today. The dashboard exposes that trade-off rather than hiding it inside a single score.
        </p>
      </Panel>
      <p className="text-[12px] text-[#5b6675]">Strategy as of {dateLabel(STRATEGY_ASOF)}.</p>
    </div>
  );
}

/* ── the company drawer ───────────────────────────────────────────────── */

function DrawerSection({ title, tone = 'text-[#8b95a3]', children }) {
  return (
    <section className="mt-6">
      <h4 className={`text-[13px] font-semibold uppercase tracking-[0.12em] ${tone}`}>{title}</h4>
      <div className="mt-2.5">{children}</div>
    </section>
  );
}

function Drawer({ r, onClose, onResearch }) {
  const closeRef = React.useRef(null);
  React.useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);
  if (!r) return null;
  const m = r.m;
  const f = r.factors;
  const params = r.model ? Object.entries(r.model.params || {}).filter(([, p]) => p.kind === 'assumption') : [];
  const evidence = [...(m.admittedOn || []), ...(m.supportingEvidence || [])].sort((a, b) => ((a.date || '') < (b.date || '') ? 1 : -1));
  const facts = [
    ['Stated AI/DC figure', r.shares[0]?.value, 'D'],
    ['FY26 revenue', r.row.revenueFY26 ? cr(r.row.revenueFY26) : null, 'D'],
    ['FY26 EBITDA', r.ebitda ? cr(r.ebitda) : null, 'D'],
    ['FY26 profit', r.pat ? cr(r.pat) : null, 'D'],
    ['Order book', r.book?.backlogCr ? cr(r.book.backlogCr) : null, 'D'],
    ['Order cover', r.cover !== null ? `${r.cover.toFixed(1)} quarters` : null, 'I'],
    ['Market value', r.mv !== null ? cr(r.mv) : null, 'I'],
    ['Revenue, latest quarter y/y', r.q1 !== null ? signedPct(r.q1) : null, 'I'],
  ].filter(([, v]) => v);
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="drawer-h">
      <button type="button" aria-label="Close" onClick={onClose} className="flex-1 bg-black/55" />
      <div className="h-full w-full max-w-[600px] overflow-y-auto bg-[#0b1016] px-6 py-6 shadow-2xl">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h3 id="drawer-h" className="font-mono text-[24px] font-semibold text-[#f5f7fa]">{m.symbol}</h3>
            <p className="mt-0.5 text-[15px] text-[#b6c2d1]">{m.name}</p>
            <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-[#8b95a3]">
              <span>{LAYER_LABEL[m.layer]} · {(m.subLayers || []).map((s) => SUB_LABEL[s] || s).join(' + ')}</span>
              <TierMark tier={m.attribution} />
              <span>member since {dateLabel(m.membershipStart)}</span>
            </p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className={`rounded-lg bg-[#151c27] px-3 py-1.5 text-[13px] text-[#b6c2d1] hover:text-[#f1f5f9] ${FOCUS}`}>Close</button>
        </div>

        {r.vehicle ? (
          <section className="mt-5 rounded-lg bg-[#121822] px-4 py-3.5">
            <dl className="grid grid-cols-[120px_1fr] gap-x-3 gap-y-1.5 text-[14px]">
              <dt className="text-[#8b95a3]">AI vehicle</dt>
              <dd className="text-[#f1f5f9]">{r.vehicle.vehicle} <span className="text-[#8b95a3]">({r.vehicle.relation})</span></dd>
              <dt className="text-[#8b95a3]">Key figure<Tag t="D" /></dt>
              <dd className="text-[#dbe2ea]">{r.vehicle.kpi}</dd>
              <dt className="text-[#8b95a3]">Parent exposure</dt>
              <dd className="leading-relaxed text-[#b6c2d1]">{r.vehicle.exposure}</dd>
            </dl>
            <p className="mt-2 text-[12px] text-[#5b6675]">{r.vehicle.kpiSource}</p>
          </section>
        ) : null}

        <DrawerSection title="Reported facts" tone="text-[#6cb2f0]">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3">
            {facts.map(([k, v, t]) => (
              <div key={k}>
                <dt className="text-[12px] text-[#8b95a3]">{k}<Tag t={t} /></dt>
                <dd className="mt-0.5 text-[16px] tabular-nums text-[#f1f5f9]">{v}</dd>
              </div>
            ))}
          </dl>
          {m.parentGroupNote ? <p className="mt-3 rounded-lg bg-[#15120c] px-3 py-2 text-[13px] leading-relaxed text-[#c9b699]"><span className="font-semibold">Parent group, not this company: </span>{m.parentGroupNote}</p> : null}
        </DrawerSection>

        {r.mat ? (
          <DrawerSection title="Economic materiality">
            <p className="flex flex-wrap items-center gap-2 text-[14px]">
              <MaterialityChip mat={r.mat} long />
              {r.mat.tier === 'material-estimate' ? <span className="text-[#c9b699]">passes only on AGI&rsquo;s FY29 estimate<Tag t="A" /></span> : null}
            </p>
            {r.mat.passes.length ? (
              <ul className="mt-2.5 space-y-1.5 text-[14px]">
                {r.mat.passes.map((x, i) => (
                  <li key={i} className="flex gap-2">
                    <span aria-hidden="true" className="text-[#4ade80]">✓</span>
                    <span className="text-[#dbe2ea]">
                      <span className="text-[#8b95a3]">{TEST_LABEL[x.test]}: </span>{x.text}<Tag t={x.tag} />
                      {x.fact?.steps ? <span className="block text-[12px] text-[#6b7684]">{x.fact.steps}</span> : null}
                    </span>
                  </li>
                ))}
              </ul>
            ) : null}
            {r.mat.misses.length ? (
              <ul className="mt-2 space-y-1 text-[13px] text-[#8b95a3]">
                {r.mat.misses.map((x, i) => <li key={i} className="flex gap-2"><span aria-hidden="true">–</span><span>{x}</span></li>)}
              </ul>
            ) : null}
            <dl className="mt-3 grid grid-cols-[150px_1fr] gap-x-3 gap-y-1 text-[13px]">
              <dt className="text-[#8b95a3]">Evidence confidence</dt>
              <dd className={r.mat.evidenceOk ? 'text-[#dbe2ea]' : 'text-[#f0a060]'}>{r.factors.evidence.band}{r.mat.evidenceOk ? '' : ' (medium or high required)'}</dd>
              <dt className="text-[#8b95a3]">Path within 36 months</dt>
              <dd className={r.mat.path ? 'text-[#dbe2ea]' : 'text-[#f0a060]'}>{r.mat.path ? <>{r.mat.path.note}<Tag t={r.mat.path.tag} /></> : 'not disclosed'}</dd>
            </dl>
            {r.mat.exception ? <p className="mt-2 text-[13px] text-[#f0a060]">Threshold exception, recorded {r.mat.exception.decided}: {r.mat.exception.reason}</p> : null}
          </DrawerSection>
        ) : null}

        <DrawerSection title="AGI assessment">
          <dl className="space-y-2">
            {[['AI materiality', f.materiality], ['Evidence', f.evidence], ['Momentum', f.momentum], ['Capital quality', f.capital], ['Expectation load', f.expectation, 'expectation']].map(([k, x, scale]) => (
              <div key={k} className="grid grid-cols-[130px_1fr] items-baseline gap-3 text-[14px]">
                <dt className="text-[#9aa5b3]">{k}</dt>
                <dd><Band b={x.band} scale={scale} />{x.value ? <span className="ml-2 text-[#c7cfda]">{x.value}</span> : null}</dd>
              </div>
            ))}
          </dl>
        </DrawerSection>

        <DrawerSection title="AGI estimate" tone="text-[#f0a060]">
          {r.model ? (
            <div className="rounded-lg border border-dashed border-[#7a5a2e] bg-[#110e0a] p-4 text-[14px] text-[#c9b699]">
              <p className="text-[#f5d9b0]">{r.model.title}</p>
              {r.runs.base.ok ? (
                <table className="mt-2 w-full tabular-nums">
                  <thead><tr className="text-left text-[12px] text-[#8a7658]"><th className="font-medium">FY29</th><th className="text-right font-medium">Low</th><th className="text-right font-medium">Base</th><th className="text-right font-medium">High</th></tr></thead>
                  <tbody>
                    <tr><td className="py-0.5">AI/DC revenue</td>{['low', 'base', 'high'].map((s) => <td key={s} className="text-right">{r.runs[s].ok ? cr(r.runs[s].aiRevenueCr) : '—'}</td>)}</tr>
                    <tr><td className="py-0.5">AI/DC EBITDA</td>{['low', 'base', 'high'].map((s) => <td key={s} className="text-right">{r.runs[s].ok ? cr(r.runs[s].aiEbitdaCr) : '—'}</td>)}</tr>
                    <tr><td className="py-0.5">vs FY26 EBITDA</td>{['low', 'base', 'high'].map((s) => <td key={s} className="text-right">{r.runs[s].ok && r.runs[s].materiality != null ? pct(r.runs[s].materiality) : '—'}</td>)}</tr>
                  </tbody>
                </table>
              ) : <p className="mt-1.5 text-[#f0a060]">Waits for: {r.runs.base.missing.map((k) => r.model.params?.[k]?.label || k).join(', ')}.</p>}
              {params.length ? (
                <details className="mt-3">
                  <summary className={`cursor-pointer rounded text-[13px] text-[#f0a060] ${FOCUS}`}>Assumptions ({params.length})</summary>
                  <ul className="mt-1.5 space-y-1 text-[13px]">
                    {params.map(([k, p]) => (
                      <li key={k}>{p.label}: {p.value === null ? 'not set' : p.unit === 'pct' ? pct(p.value, 1) : p.value}{p.low != null ? ` (range ${p.unit === 'pct' ? `${pct(p.low, 1)} to ${pct(p.high, 1)}` : `${p.low} to ${p.high}`})` : ''}</li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </div>
          ) : <p className="text-[14px] text-[#8b95a3]">Not modelled: AGI has no defensible anchor for this company&rsquo;s AI economics yet.</p>}
        </DrawerSection>

        <DrawerSection title="What to watch">
          <ul className="list-disc space-y-1.5 pl-5 text-[14px] leading-relaxed text-[#b6c2d1]">
            {r.targets.map((t) => <li key={t.target}>{t.target} <span className="text-[#6b7684]">(company target; {t.source})</span></li>)}
            {r.runs && !r.runs.base.ok ? <li>A disclosed {r.runs.base.missing.map((k) => (r.model.params?.[k]?.label || k).toLowerCase()).join(' and ')} would let the estimate run.</li> : null}
            {m.note ? <li>{m.note}</li> : null}
            {!r.targets.length && !m.note && !(r.runs && !r.runs.base.ok) ? <li>Next quarter&rsquo;s results: order book and any stated AI/DC figure.</li> : null}
          </ul>
        </DrawerSection>

        <DrawerSection title={`Evidence (${evidence.length})`}>
          <ul className="space-y-3">
            {evidence.map((e, i) => (
              <li key={i} className="rounded-lg bg-[#121822] px-4 py-3">
                <p className="flex flex-wrap items-center gap-x-2 text-[12px] text-[#8b95a3]">
                  <span className="rounded-full bg-[#1c2533] px-2 py-[1px] text-[#b6c2d1]">{IMPACT[e.kind] || e.kind}</span>
                  <span className="tabular-nums">{e.undated ? 'undated' : dateLabel(e.date)}</span>
                </p>
                {e.headline ? <p className="mt-1.5 text-[15px] leading-snug text-[#e3e8ef]">{e.headline}</p> : null}
                <blockquote className="mt-1.5 text-[13px] leading-relaxed text-[#9aa5b3]">&ldquo;{e.excerpt}&rdquo;</blockquote>
                <p className="mt-1 text-[12px] text-[#5b6675]">{e.document}{e.page ? `, p. ${e.page}` : ''}</p>
              </li>
            ))}
          </ul>
          {m.exposureNote ? <p className="mt-3 text-[13px] leading-relaxed text-[#8b95a3]">{m.exposureNote}</p> : null}
        </DrawerSection>

        <button type="button" onClick={onResearch} className={`mt-6 rounded text-[14px] text-[#6cb2f0] hover:text-[#e3e8ef] ${FOCUS}`}>
          Open the full research page &rarr;
        </button>
      </div>
    </div>
  );
}

/* ── the dashboard ────────────────────────────────────────────────────── */

export const MONITOR_SECTIONS = [['overview', 'Overview'], ['strategy', 'Strategy'], ['matrix', 'Matrix'], ['evidence', 'Evidence'], ['estimates', 'Estimates']];

export default function MonitorDashboard({
  section = 'overview', onSection, universe, live, marketValue, stage3, estimates, operating, scoring, materiality, onResearch,
}) {
  const [exit, setExit] = React.useState(null);
  const [filter, setFilterState] = React.useState(null);
  const [drawer, setDrawer] = React.useState(null);
  const matrixRef = React.useRef(null);
  React.useEffect(() => {
    let cancelled = false;
    fetchExitability().then((p) => { if (!cancelled) setExit(p); }).catch(() => {});
    return () => { cancelled = true; };
  }, []);
  // Choosing a layer or stage filters the matrix and brings it into view.
  const setFilter = React.useCallback((f) => {
    setFilterState(f);
    if (f) requestAnimationFrame(() => matrixRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
  }, []);
  if (!universe?.members) return <p className="py-10 text-[15px] text-[#8b95a3]">Loading the universe.</p>;
  const records = buildRecords({ universe, operating, estimates, marketValue, stage3, scoring, exit, materiality });
  const others = { held: universe.candidates || [], excluded: universe.excluded || [] };
  const current = drawer ? records.find((r) => r.m.symbol === drawer) : null;
  const matrix = <Matrix records={records} others={others} filter={filter} setFilter={setFilter} open={setDrawer} matrixRef={matrixRef} rules={materiality?.rules} />;
  return (
    // The site stylesheet borders every button and input; the monitor draws its own.
    <div className="space-y-4 text-[15px] [&_button]:border-0 [&_input]:border-0">
      {section === 'overview' ? (
        <>
          <KpiRow records={records} others={others} marketValue={marketValue} live={live} />
          <div className="grid gap-4 xl:grid-cols-[minmax(0,7fr)_minmax(340px,3fr)]">
            <MaterialityScatter records={records} open={setDrawer} />
            <LatestEvidence records={records} open={setDrawer} onAll={() => onSection?.('evidence')} />
          </div>
          <Stack records={records} filter={filter} setFilter={setFilter} />
          {matrix}
        </>
      ) : null}
      {section === 'matrix' ? (
        <>
          {matrix}
          <SupplyChain records={records} held={others.held} setFilter={setFilter} open={setDrawer} />
        </>
      ) : null}
      {section === 'strategy' ? <StrategyTab records={records} open={setDrawer} /> : null}
      {section === 'evidence' ? <EvidenceTab records={records} open={setDrawer} /> : null}
      {section === 'estimates' ? <EstimatesTab records={records} estimates={estimates} open={setDrawer} onResearch={onResearch} /> : null}
      {current ? <Drawer r={current} onClose={() => setDrawer(null)} onResearch={() => { setDrawer(null); onResearch(); }} /> : null}
    </div>
  );
}
