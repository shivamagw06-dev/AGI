import React from 'react';
import {
  fetchFiledFacts, fetchIndexHistory, fetchLive, fetchMarketValue, fetchSnapshots, fetchStage3, fetchUniverse,
} from '@/lib/indiaAiApi';
import {
  BuildFunding, CapexChanges, CapexConcentration, EvidenceComposition, ExposureAttribution,
} from '@/components/indiaAi/FiledEvidenceCharts';
import { nseOpen } from '@/lib/nseSession';

/**
 * India AI Intelligence — research on the left, the monitor on the right.
 *
 * The research argues a position; the monitor says whether it is still true
 * this morning. They are side by side because if the two ever disagree, that
 * disagreement is the most valuable thing on the page.
 *
 * Several panels here have no data source yet, and they say which one they
 * need rather than showing a number. That is not a placeholder style: it is
 * the only honest rendering available, and the specific refusals matter.
 *
 *   - The indexed AI Enablers line cannot be drawn back to 2023. This
 *     universe was admitted on September 2026 filings, so running it
 *     backwards would price a basket using evidence that did not exist at
 *     the time. Index history starts at the first snapshot and no earlier.
 *   - Earnings revisions and forward EPS need a consensus feed. Upstox
 *     serves trailing ratios only. There is no source connected, so there
 *     are no revisions to show.
 *   - The layer heatmap needs twelve months of history that does not exist
 *     yet.
 *
 * Everything with a real source is live: the basket, the layer attribution,
 * the order feed (every line a cited filing), the watchlist prices.
 */

const LAYER_LABEL = {
  power: 'Power', data_centre: 'Data Centers', semiconductor: 'Semiconductors', infrastructure: 'EPC & Project Delivery',
};
const SUB_LABEL = {
  generation: 'Generation', transmission: 'Transmission', equipment: 'Equipment',
  developer: 'Developer', operator: 'Operator', hardware: 'Hardware',
  osat: 'OSAT', materials: 'Materials', epc: 'EPC',
};
const KIND_LABEL = {
  order: 'Signed order', capex: 'Committed capex', operating: 'Operating disclosure',
  partnership: 'Partnership', language: 'Transcript language', news: 'Press item',
};
const ALL_SUBS = [
  ['power', 'generation'], ['power', 'transmission'], ['power', 'equipment'],
  ['data_centre', 'developer'], ['data_centre', 'operator'], ['data_centre', 'hardware'],
  ['semiconductor', 'osat'], ['semiconductor', 'materials'], ['semiconductor', 'hardware'],
  ['infrastructure', 'epc'],
];

const pp = (v) => (Number.isFinite(Number(v)) ? `${Number(v) >= 0 ? '+' : ''}${Number(v).toFixed(2)}pp` : '—');
const pctOf = (v) => (Number.isFinite(Number(v)) ? `${Number(v) * 100 >= 0 ? '+' : ''}${(Number(v) * 100).toFixed(2)}%` : '—');
const upDown = (v) => {
  const n = Number(v);
  if (!Number.isFinite(n) || n === 0) return 'text-[#7d8894]';
  return n > 0 ? 'text-[#4ade80]' : 'text-[#f87171]';
};

/** IST, because the exchange this page is about runs on it. */
function useIstClock() {
  const [now, setNow] = React.useState(() => new Date());
  React.useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1_000);
    return () => clearInterval(timer);
  }, []);
  const date = now.toLocaleDateString('en-GB', {
    weekday: 'short', day: '2-digit', month: 'short', year: 'numeric', timeZone: 'Asia/Kolkata',
  });
  const time = now.toLocaleTimeString('en-GB', { hour12: false, timeZone: 'Asia/Kolkata' });
  return { date, time };
}

/**
 * The state of the product in one line.
 *
 * Everything above this was prose. A visitor needs to know what the basket
 * is, what it refused, and whether it is priced, before deciding whether to
 * read further.
 */
function StatusStrip({ universe, live }) {
  const members = universe?.members || [];
  const filings = members.reduce((sum, one) => sum + (one.admittedOn?.length || 0), 0);
  const filled = new Set(members.flatMap((m) => (m.subLayers || []).map((sl) => `${m.layer}/${sl}`)));
  const priced = live?.index?.status === 'ok';
  const items = [
    [String(members.length), 'admitted'],
    [String(universe?.candidates?.length || 0), 'refused'],
    [String(ALL_SUBS.length - filled.size), 'empty layers'],
    [String(filings), 'supporting filings'],
  ];
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 rounded-md border border-[#1e2634] bg-[#0c1017] px-3.5 py-2.5">
      {items.map(([value, label], i) => (
        <React.Fragment key={label}>
          {i > 0 ? <span className="text-[#2c3542]" aria-hidden>·</span> : null}
          <span className="text-[13px] text-[#8b95a3]">
            <span className="font-semibold tabular-nums text-[#e3e8ef]">{value}</span> {label}
          </span>
        </React.Fragment>
      ))}
      <span className="text-[#2c3542]" aria-hidden>·</span>
      <span className="flex items-center gap-1.5 text-[13px]">
        <span className={`h-1.5 w-1.5 rounded-full ${priced ? 'bg-[#4ade80]' : 'bg-[#4b5563]'}`} />
        <span className={priced ? 'text-[#4ade80]' : 'text-[#8b95a3]'}>
          {priced ? 'Live pricing active' : 'Live pricing pending'}
        </span>
      </span>
    </div>
  );
}

/**
 * Jump links, for sections that exist.
 *
 * No "Risks" entry: there is no risk register on this page, and a selector
 * that scrolls nowhere is the same defect as a nav link that goes nowhere.
 */
const SECTIONS = [
  ['overview', 'Overview'],
  ['filed', 'From the filings'],
  ['universe', 'Universe'],
  ['intensity', 'Intensity'],
  ['value', 'Market value'],
  ['orders', 'Orders'],
  ['capacity', 'Capacity'],
  ['layers', 'Empty layers'],
  ['refused', 'Refused'],
];

function SectionNav() {
  return (
    <nav aria-label="Sections" className="sticky top-[46px] z-20 -mx-4 mb-3 border-b border-[#1a2230] bg-[#080b11]/95 px-4 py-2 backdrop-blur">
      <ul className="flex flex-wrap gap-x-4 gap-y-1">
        {SECTIONS.map(([id, label]) => (
          <li key={id}>
            <a
              href={`#${id}`}
              className="rounded text-[12px] text-[#8b95a3] hover:text-[#e3e8ef] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e8833a]"
            >
              {label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function Panel({ id, title, note, action, children, className = '' }) {
  return (
    <section id={id} className={`rounded-md border border-[#1e2634] bg-[#0c1017] ${className}`}>
      <header className="flex items-baseline gap-2 border-b border-[#1a2230] px-3.5 py-2.5">
        <h3 className="text-[13px] font-semibold tracking-tight text-[#f1f5f9]">{title}</h3>
        {note ? <span className="text-[11px] text-[#7d8894]">{note}</span> : null}
        {action ? <span className="ml-auto text-[11px] text-[#8fb4d8]">{action}</span> : null}
      </header>
      <div className="p-3.5">{children}</div>
    </section>
  );
}

/**
 * A panel with no source connected.
 *
 * Says which source it needs. A panel that renders an empty chart looks
 * broken; a panel that renders a plausible one is worse.
 */
function Needed({ what, source }) {
  return (
    <div className="flex min-h-[86px] flex-col justify-center gap-1.5 rounded border border-dashed border-[#26303f] px-3 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#b38b4d]">Source not connected</p>
      <p className="text-[11px] leading-relaxed text-[#8b95a3]">{what}</p>
      <p className="text-[11px] text-[#7d8894]">Needs: {source}</p>
    </div>
  );
}

const Badge = ({ children, tone = 'neutral' }) => {
  const tones = {
    neutral: 'bg-[#1c2534] text-[#98a3b2]',
    green: 'bg-[#14361f] text-[#4ade80]',
    blue: 'bg-[#13293f] text-[#5aa2e0]',
    amber: 'bg-[#3a2c12] text-[#d9a94a]',
    red: 'bg-[#3a1a1a] text-[#f87171]',
  };
  return (
    <span className={`rounded px-1.5 py-[2px] text-[9px] font-semibold uppercase tracking-wide ${tones[tone]}`}>
      {children}
    </span>
  );
};

/* ── the chart, and what it refuses to draw ───────────────────────────── */

/**
 * The basket against the benchmark, from snapshot history.
 *
 * The mockup for this page showed this line running from January 2023 at
 * +312%. It cannot: the universe was admitted on filings published in
 * September 2026, and re-running it across 2023-2025 would be pricing a
 * basket on evidence nobody had at the time. The result would be the largest
 * and most quoted number on the page and it would be an artefact of hindsight.
 *
 * So the series starts where the snapshots start. Until there are two, the
 * chart says so and draws nothing.
 */
function IndexedChart({ snapshots }) {
  const points = (snapshots || [])
    .filter((one) => one.status === 'ok' && Number.isFinite(Number(one.index?.return_pct)))
    .map((one) => ({
      at: Date.parse(one.at),
      rebuilt: one.origin === 'candles',
      basket: Number(one.index.return_pct) * 100,
      benchmark: Number.isFinite(Number(one.index.relative?.benchmark_return_pp))
        ? Number(one.index.relative.benchmark_return_pp) : null,
    }));

  if (points.length < 2) {
    return (
      <div className="flex min-h-[210px] flex-col items-start justify-center gap-2 px-4">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#7d8894]">
          Index history starts here
        </p>
        <p className="max-w-lg text-[12px] leading-relaxed text-[#8b95a3]">
          This basket was admitted on filings published in September 2026. Running the line
          back through 2023 would price it on evidence that did not exist at the time, so
          there is no history before the first snapshot and none will be manufactured.
        </p>
        <p className="text-[11px] text-[#68727f]">
          {points.length === 0
            ? (nseOpen()
              ? 'No priced snapshots yet. The service has just restarted; it is rebuilding the session from 1-minute candles.'
              : 'No priced snapshots yet — the series begins at the next open session.')
            : 'One snapshot so far; a line needs two.'}
        </p>
      </div>
    );
  }

  const W = 640;
  const H = 210;
  const pad = { l: 34, r: 46, t: 12, b: 22 };
  const values = points.flatMap((one) => [one.basket, one.benchmark]).filter((one) => one !== null);
  const lo = Math.min(...values, 0);
  const hi = Math.max(...values, 0);
  const span = hi - lo || 1;
  const x = (i) => pad.l + (i / (points.length - 1)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - lo) / span) * (H - pad.t - pad.b);
  const path = (pick) => points
    .map((one, i) => (one[pick] === null ? null : `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(one[pick]).toFixed(1)}`))
    .filter(Boolean).join(' ');

  const last = points[points.length - 1];
  // Where the replayed candles hand over to the live feed. Rebuilt minutes
  // are the same arithmetic on closed 1-minute candles, but they were not
  // observed, and the chart says so rather than drawing one seamless line.
  const handover = points.findIndex((one) => !one.rebuilt);
  const rebuiltCount = handover === -1 ? points.length : handover;
  const clock = (ms) => new Date(ms).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' });
  return (
    <>
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="AI Enablers against Nifty 50, indexed from the first snapshot">
      <line x1={pad.l} x2={W - pad.r} y1={y(0)} y2={y(0)} stroke="#1e2634" strokeWidth="1" />
      <text x={pad.l - 6} y={y(0) + 3} textAnchor="end" fill="#68727f" fontSize="8">0%</text>
      {rebuiltCount > 0 ? (
        <rect
          x={pad.l}
          y={pad.t}
          width={Math.max(0, x(Math.min(rebuiltCount, points.length - 1)) - pad.l)}
          height={H - pad.t - pad.b}
          fill="#ffffff"
          opacity="0.025"
        />
      ) : null}
      {rebuiltCount > 0 && rebuiltCount < points.length ? (
        <line
          x1={x(rebuiltCount)}
          x2={x(rebuiltCount)}
          y1={pad.t}
          y2={H - pad.b}
          stroke="#3a4453"
          strokeDasharray="2 3"
        />
      ) : null}
      <path d={path('basket')} fill="none" stroke="#e8833a" strokeWidth="1.8" />
      <path d={path('benchmark')} fill="none" stroke="#5aa2e0" strokeWidth="1.4" />
      <text x={W - pad.r + 4} y={y(last.basket) + 3} fill="#e8833a" fontSize="9" fontWeight="600">
        {pp(last.basket)}
      </text>
      {last.benchmark !== null ? (
        <text x={W - pad.r + 4} y={y(last.benchmark) + 3} fill="#5aa2e0" fontSize="9" fontWeight="600">
          {pp(last.benchmark)}
        </text>
      ) : null}
      <text x={pad.l} y={H - 6} fill="#68727f" fontSize="8">
        {new Date(points[0].at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })}
      </text>
      <text x={W - pad.r} y={H - 6} textAnchor="end" fill="#68727f" fontSize="8">
        {new Date(last.at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })}
      </text>
    </svg>
    {rebuiltCount > 0 ? (
      <p className="mt-1 px-1 text-[10px] text-[#68727f]">
        {rebuiltCount === points.length
          ? `Whole line rebuilt from Upstox 1-minute candles after a restart, to ${clock(last.at)} IST.`
          : `Shaded part (to ${clock(points[rebuiltCount - 1].at)} IST) rebuilt from Upstox 1-minute candles after a restart; live feed from ${clock(points[rebuiltCount].at)}.`}
      </p>
    ) : null}
    </>
  );
}

/**
 * The basket against Nifty 50 since admission, one point per closed session.
 *
 * Daily equal weight, like the live basket, and point-in-time: each member
 * counts from the close of the day it was admitted. The line is short because
 * the basket is new, and it says so rather than reaching back.
 */
function SinceAdmission({ history }) {
  const points = history?.points || [];
  const fmtDate = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  const last = points[points.length - 1];
  const change = (v) => (v === undefined ? '—' : `${v - 100 >= 0 ? '+' : ''}${(v - 100).toFixed(2)}%`);
  return (
    <Panel
      id="history"
      title="Since admission"
      note="daily equal weight · closed sessions · vs Nifty 50"
      action={points.length > 1 ? `${points.length - 1} session${points.length === 2 ? '' : 's'}` : null}
    >
      {points.length < 2 ? (
        <p className="text-[11px] leading-relaxed text-[#8b95a3]">
          {history?.base
            ? `The series starts at the close on ${fmtDate(history.base)}, the first admission date, and gains one point each trading day after that. `
            : 'Loading the series. '}
          Each member counts only from the close of the day it was admitted; nothing is priced before a decision was made.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#7d8894]">AI Enablers</p>
              <p className="mt-0.5 font-mono text-[17px] font-semibold tabular-nums text-[#e8833a]">{change(last.basket)}</p>
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#7d8894]">Nifty 50</p>
              <p className="mt-0.5 font-mono text-[17px] font-semibold tabular-nums text-[#5aa2e0]">{change(last.benchmark)}</p>
            </div>
          </div>
          <SessionLine points={points} />
          <p className="mt-1 text-[10px] text-[#68727f]">
            From the close on {fmtDate(history.base)} to {fmtDate(last.date)}. {last.members} members in the last session
            {last.missing?.length ? `; no close for ${last.missing.join(', ')}` : ''}
            {last.excluded?.length ? `; ${last.excluded.join(', ')} left out on a corporate-action ex-date` : ''}.
          </p>
        </>
      )}
    </Panel>
  );
}

function SessionLine({ points }) {
  const W = 640;
  const H = 150;
  const pad = { l: 34, r: 12, t: 10, b: 20 };
  const values = points.flatMap((one) => [one.basket, one.benchmark]);
  const lo = Math.min(...values, 100);
  const hi = Math.max(...values, 100);
  const span = hi - lo || 1;
  const x = (i) => pad.l + (i / (points.length - 1)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - lo) / span) * (H - pad.t - pad.b);
  const path = (key) => points.map((one, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(one[key]).toFixed(1)}`).join(' ');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 w-full" role="img" aria-label="AI Enablers basket against Nifty 50 since admission, indexed to 100">
      <line x1={pad.l} x2={W - pad.r} y1={y(100)} y2={y(100)} stroke="#1e2634" />
      <text x={pad.l - 6} y={y(100) + 3} textAnchor="end" fill="#68727f" fontSize="9">100</text>
      <path d={path('benchmark')} fill="none" stroke="#5aa2e0" strokeWidth="1.4" />
      <path d={path('basket')} fill="none" stroke="#e8833a" strokeWidth="1.8" />
      {points.map((one, i) => (
        <circle key={one.date} cx={x(i)} cy={y(one.basket)} r="2" fill="#e8833a" />
      ))}
    </svg>
  );
}

/* ── left column: the research ────────────────────────────────────────── */

function ExecutiveSummary({ universe }) {
  const members = universe?.members || [];
  const filings = members.reduce((sum, one) => sum + (one.admittedOn?.length || 0), 0);
  const filled = new Set(members.flatMap((m) => (m.subLayers || []).map((s) => `${m.layer}/${s}`)));
  // Where each member was first found, said plainly: a lead from a reported
  // broker list is still a lead, and admission was on the company's filings.
  const fromLeads = members.filter((one) => String(one.discoveredVia || '').startsWith('EXTERNAL_LEAD')).length;
  const emptyCount = ALL_SUBS.length - filled.size;
  const items = [
    { k: 'Admitted on filings',
      v: fromLeads
        ? `${members.length} companies, each on its own disclosures. ${members.length - fromLeads} came from AGI's screen; ${fromLeads} were first read as leads from a reported broker list and passed the same standard.`
        : `${members.length} companies admitted from AGI's own screen over public filings — none on a broker's list.` },
    { k: 'Every member cited',
      v: `${filings} first-party disclosures admit the basket: signed orders, committed capex, operating figures.` },
    { k: 'Refused on principle',
      v: `${universe?.candidates?.length || 0} candidates found and held back — partnerships and forecasts do not admit a company.` },
    { k: `${emptyCount === 1 ? 'One layer' : `${emptyCount} layers`} empty`,
      v: `${emptyCount} of ${ALL_SUBS.length} sub-layers have nothing disclosed beyond intent, and ${emptyCount === 1 ? 'is' : 'are'} shown empty.` },
    { k: 'Not yet an index',
      v: 'Filings have been read for the members and candidates only, and investment intensity sits beside each member as context, not as a gate. Positions are sized for liquidity at a Rs 100 crore target.' },
  ];
  return (
    <div className="rounded-md border border-[#1e2634] bg-[#0c1017] p-4">
      <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#68727f]">Executive summary</p>
      <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((one) => (
          <div key={one.k} className="border-l-2 border-[#2c3542] pl-3">
            <p className="text-[11px] font-semibold text-[#e3e8ef]">{one.k}</p>
            <p className="mt-1 text-[11px] leading-relaxed text-[#8b95a3]">{one.v}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function KeyTakeaways({ universe, live }) {
  const members = universe?.members || [];
  const filings = members.reduce((sum, one) => sum + (one.admittedOn?.length || 0), 0);
  const index = live?.index;
  const rows = [
    { v: String(members.length), k: 'Companies admitted', s: 'on hard, first-party evidence' },
    { v: String(filings), k: 'Filings cited', s: 'every one openable on this page' },
    { v: index?.status === 'ok' ? pp(index.return_pp) : '—', k: 'Basket today',
      s: index?.status === 'ok' ? 'equal-weighted' : 'not priced right now' },
    { v: index?.relative ? pp(index.relative.excess_pp) : '—', k: 'vs Nifty 50',
      s: index?.relative ? 'today only' : 'benchmark not priced' },
  ];
  return (
    <div className="rounded-md border border-[#1e2634] bg-[#0c1017] p-4">
      <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-[#68727f]">Key takeaways</p>
      <div className="space-y-3">
        {rows.map((one) => (
          <div key={one.k} className="flex items-baseline gap-3">
            <span className="w-20 shrink-0 text-[22px] font-semibold tabular-nums text-[#f1f5f9]">{one.v}</span>
            <span>
              <span className="block text-[11px] font-semibold text-[#e3e8ef]">{one.k}</span>
              <span className="block text-[11px] text-[#7d8894]">{one.s}</span>
            </span>
          </div>
        ))}
      </div>
      <p className="mt-4 border-t border-[#1a2230] pt-3 text-[10px] leading-relaxed text-[#68727f]">
        No cumulative return and no market-size estimate. Both would need history this basket
        does not have, or a forecast AGI has not made.
      </p>
    </div>
  );
}

function LayerCards({ universe }) {
  const members = universe?.members || [];
  const layers = [
    { id: 'power', thesis: 'A data centre is a power problem before it is a computing one. Generation, evacuation and the transformers in between are all disclosed, orderable and dated.' },
    { id: 'data_centre', thesis: 'Capacity is the unit. The developers hold the land and the shells, the operators sell the megawatts, and the hardware makers ship what fills them.' },
    { id: 'semiconductor', thesis: 'India’s silicon layer is mostly back-end. Assembly and test is where money has been committed; equipment has its first order-backed supplier, and materials remain pre-revenue.' },
    { id: 'infrastructure', thesis: 'The contractors who build the halls and fit them out. Admitted only on a named project, a contracted role and an identified exposure — a builder is not an owner.' },
  ];
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {layers.map((layer) => {
        const inLayer = members.filter((one) => one.layer === layer.id);
        return (
          <div key={layer.id} className="rounded-md border border-[#1e2634] bg-[#0c1017] p-4">
            <h4 className="text-[13px] font-semibold text-[#e3e8ef]">{LAYER_LABEL[layer.id]}</h4>
            <p className="mt-1 text-[11px] text-[#7d8894]">
              {inLayer.length} admitted · {[...new Set(inLayer.flatMap((one) => one.subLayers || []))].map((s) => SUB_LABEL[s] || s).join(', ') || 'none'}
            </p>
            <p className="mt-2 text-[11px] leading-relaxed text-[#8b95a3]">{layer.thesis}</p>
            <p className="mt-3 flex flex-wrap gap-1">
              {inLayer.map((one) => (
                <span key={one.symbol} className="rounded bg-[#1c2534] px-1.5 py-[2px] font-mono text-[9px] text-[#98a3b2]">
                  {one.symbol}
                </span>
              ))}
            </p>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Stage 3: investment intensity, beside each member.
 *
 * Context, not a gate. Membership is decided by filed evidence; this says
 * whether a member is building harder or softer than its peers here. The
 * medians are of this group, which was already selected for exposure, so the
 * bar is high and "below" means below these peers, not "not investing". A
 * verdict says how many of the four tests it rests on, and a figure that
 * could not be read shows as a dash, never as a zero.
 */
const INTENSITY_TESTS = [
  ['revenueCagr3y', 'Revenue CAGR', '3 years'],
  ['capexGrowth', 'Capex growth', 'FY26 vs FY25'],
  ['capexToSales', 'Capex / sales', 'FY26'],
  ['rndToSales', 'R&D / sales', 'FY26'],
];

function InvestmentIntensity({ data }) {
  if (!data?.rows?.length) {
    return (
      <Panel id="intensity" title="Investment intensity" note="stage 3">
        <p className="text-[11px] text-[#68727f]">Loading the stage 3 inputs.</p>
      </Panel>
    );
  }
  const members = data.rows.filter((one) => one.kind === 'member');
  const candidates = data.rows.filter((one) => one.kind === 'candidate');
  const t = data.thresholds || {};
  const fmt = (v) => (v === null || v === undefined ? '—' : `${(v * 100).toFixed(1)}%`);
  const passCount = members.filter((one) => one.verdict === 'PASS').length;
  const verdictChip = (row) => {
    if (row.verdict === 'PASS') {
      return <span className="rounded bg-[#10261a] px-1.5 py-[2px] text-[10px] text-[#4ade80]">Above on {row.met.length}</span>;
    }
    if (row.verdict === 'BELOW') {
      return <span className="rounded bg-[#2a2110] px-1.5 py-[2px] text-[10px] text-[#d9a94a]">Below · {row.tested.length} of 4 tested</span>;
    }
    return <span className="rounded bg-[#161c26] px-1.5 py-[2px] text-[10px] text-[#7d8894]">Not screened</span>;
  };
  return (
    <Panel
      id="intensity"
      title="Investment intensity"
      note="stage 3 · context, not a gate"
      action={`${passCount} of ${members.length} members above a median`}
    >
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {INTENSITY_TESTS.map(([key, label, period]) => (
          <div key={key} className="rounded border border-[#1a2230] px-2.5 py-2">
            <p className="text-[10px] uppercase tracking-wider text-[#7d8894]">{label}</p>
            <p className="mt-0.5 font-mono text-[15px] font-semibold tabular-nums text-[#e3e8ef]">{fmt(t[key])}</p>
            <p className="text-[10px] text-[#68727f]">median · {period} · {data.distributions?.[key]?.count ?? 0} with data</p>
          </div>
        ))}
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[560px] text-[11px]">
          <thead>
            <tr className="text-left text-[10px] uppercase tracking-wider text-[#68727f]">
              <th className="py-1.5 pr-2 font-medium">Member</th>
              {INTENSITY_TESTS.map(([key, label]) => (
                <th key={key} className="py-1.5 pr-2 text-right font-medium">{label}</th>
              ))}
              <th className="py-1.5 font-medium">Verdict</th>
            </tr>
          </thead>
          <tbody>
            {members.map((row) => (
              <tr key={row.symbol} className="border-t border-[#1a2230]">
                <td className="py-1.5 pr-2 font-mono text-[#d3dae3]" title={row.excluded || row.capexNote || ''}>{row.symbol}</td>
                {INTENSITY_TESTS.map(([key]) => {
                  const v = row[key];
                  const above = v !== null && t[key] !== null && v >= t[key];
                  return (
                    <td
                      key={key}
                      className={`py-1.5 pr-2 text-right font-mono tabular-nums ${v === null ? 'text-[#4b5563]' : above ? 'text-[#4ade80]' : 'text-[#9aa5b3]'}`}
                    >
                      {fmt(v)}
                    </td>
                  );
                })}
                <td className="py-1.5">{verdictChip(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[10px] leading-relaxed text-[#68727f]">
        A member passes on any one test at or above the median. The medians are of the
        {` ${data.rows.length} `}members and candidates screened here, a group already chosen for
        AI-infrastructure exposure, so below means less intensive than these peers, not idle.
        Stage 3 does not remove anyone; membership rests on filed evidence.
        Candidates: {candidates.filter((one) => one.verdict === 'PASS').length} of {candidates.length} above a median.
        A dash is a figure not read, never a zero. Revenue growth compares total revenue with total revenue;
        capex is the cash-flow purchase of property, plant and equipment; R&amp;D is usually a company-level figure.
        Figures as of {data.asOf}.
      </p>
    </Panel>
  );
}

/**
 * Market value by layer and by sector.
 *
 * Close times the share count each company filed, so every bar is a sum of
 * figures a reader can check. It is whole-company value: most members do not
 * attribute revenue to data centres, so a layer's bar says how much listed
 * value has a filed AI-infrastructure link, not how much the link is worth.
 * A member without a current share count is named under the bars rather than
 * dropped from them.
 */
const fmtCr = (v) => {
  if (v === null || v === undefined) return '—';
  if (v >= 100_000) return `₹${(v / 100_000).toFixed(2)} lakh cr`;
  return `₹${Math.round(v).toLocaleString('en-IN')} cr`;
};

function ValueBars({ title, totals, label }) {
  const top = totals?.groups?.[0]?.marketValueCr || 1;
  return (
    <div className="min-w-0">
      <p className="text-[10px] uppercase tracking-wider text-[#7d8894]">{title}</p>
      <ul className="mt-2 space-y-2">
        {(totals?.groups || []).map((group) => (
          <li key={group.key}>
            <div className="flex items-baseline justify-between gap-2 text-[11px]">
              <span className="truncate text-[#d3dae3]" title={group.members.join(', ')}>{label(group.key)}</span>
              <span className="shrink-0 font-mono tabular-nums text-[#9aa5b3]">
                {fmtCr(group.marketValueCr)} · {(group.share * 100).toFixed(1)}%
              </span>
            </div>
            <div className="mt-1 h-[6px] rounded-sm bg-[#141b26]">
              <div className="h-full rounded-sm bg-[#e8833a]" style={{ width: `${(group.marketValueCr / top) * 100}%` }} />
            </div>
            <p className="mt-0.5 text-[10px] text-[#68727f]">{group.members.length} {group.members.length === 1 ? 'member' : 'members'}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

const LEFT_OUT = {
  NO_SHARE_COUNT: 'no filed share count yet',
  NO_CLOSE: 'no close',
  SHARE_COUNT_PREDATES_CORPORATE_ACTION: 'share count predates a bonus, split or rights issue',
};

function MarketValue({ data }) {
  if (!data) {
    return (
      <Panel id="value" title="Market value" note="by layer and sector">
        <p className="text-[11px] text-[#68727f]">Loading closes and share counts.</p>
      </Panel>
    );
  }
  if (!data.ok) {
    return (
      <Panel id="value" title="Market value" note="by layer and sector">
        <p className="text-[11px] text-[#f87171]">Could not compute market value: {data.error}</p>
      </Panel>
    );
  }
  const flagged = data.rows.filter((row) => row.crossCheck?.within === false);
  const leftOut = data.byLayer.leftOut || [];
  return (
    <Panel
      id="value"
      title="Market value"
      note="close × filed shares · whole company, not AI exposure"
      action={`${fmtCr(data.byLayer.totalCr)} across ${data.rows.length - leftOut.length} members`}
    >
      <div className="grid gap-5 sm:grid-cols-2">
        <ValueBars title="By layer" totals={data.byLayer} label={(key) => LAYER_LABEL[key] || key} />
        <ValueBars title="By sector (Upstox profile)" totals={data.bySector} label={(key) => key} />
      </div>
      <details className="mt-3">
        <summary className="cursor-pointer rounded text-[11px] text-[#8fb4d8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e8833a]">
          Every member&rsquo;s figure
        </summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[560px] text-[11px]">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-wider text-[#68727f]">
                <th className="py-1.5 pr-2 font-medium">Member</th>
                <th className="py-1.5 pr-2 text-right font-medium">Close</th>
                <th className="py-1.5 pr-2 text-right font-medium">Shares</th>
                <th className="py-1.5 pr-2 text-right font-medium">Market value</th>
                <th className="py-1.5 text-right font-medium">vs P/B × book</th>
              </tr>
            </thead>
            <tbody>
              {[...data.rows].sort((a, b) => (b.marketValueCr ?? -1) - (a.marketValueCr ?? -1)).map((row) => (
                <tr key={row.symbol} className="border-t border-[#1a2230]">
                  <td className="py-1.5 pr-2 font-mono text-[#d3dae3]" title={row.sharesSource ? `${row.sharesSource}, as of ${row.sharesAsOf}` : ''}>{row.symbol}</td>
                  <td className="py-1.5 pr-2 text-right font-mono tabular-nums text-[#9aa5b3]">{row.close ? row.close.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—'}</td>
                  <td className="py-1.5 pr-2 text-right font-mono tabular-nums text-[#9aa5b3]">{row.shares ? `${(row.shares / 1e7).toFixed(2)} cr` : '—'}</td>
                  <td className="py-1.5 pr-2 text-right font-mono tabular-nums text-[#e3e8ef]">{row.marketValueCr != null ? fmtCr(row.marketValueCr) : LEFT_OUT[row.status] || row.status}</td>
                  <td className={`py-1.5 text-right font-mono tabular-nums ${row.crossCheck?.within === false ? 'text-[#d9a94a]' : 'text-[#68727f]'}`}>
                    {row.crossCheck?.gap != null ? pctOf(row.crossCheck.gap) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="mt-3 text-[10px] leading-relaxed text-[#68727f]">
        Market value is the close on {data.closeDate || '—'}{data.closeDates?.length > 1 ? ` (some members earlier: ${data.closeDates.slice(0, -1).join(', ')})` : ''} times the equity shares each company last filed
        with the exchange; partly-paid shares are left out. It is the value of the whole company: most members
        do not report what share of their business serves data centres, so a layer&rsquo;s bar measures listed
        value with a filed link to AI infrastructure, not the value of that link. P/B × book is an independent
        route to the same figure; {flagged.length ? `${flagged.map((row) => row.symbol).join(', ')} ${flagged.length === 1 ? 'differs' : 'differ'} by more than 25%. Where that has been checked against filed share counts, the P/B route is the one that is off, so it is shown for reference and neither these figures nor the size screen use it.` : 'every member agrees within 25%.'}
        {leftOut.length ? ` Left out: ${leftOut.map((one) => `${one.symbol} (${LEFT_OUT[one.status] || one.status})`).join('; ')}.` : ''}
        {' '}Sector is Upstox&rsquo;s classification{data.sectorAliases && Object.keys(data.sectorAliases).length ? `, with two labels it spells two ways merged (${Object.entries(data.sectorAliases).map(([from, to]) => `${from} → ${to}`).join('; ')})` : ''}. A size mix (large, mid, small) needs AMFI&rsquo;s list and is not shown.
      </p>
    </Panel>
  );
}

/* ── right column: the monitor ────────────────────────────────────────── */

function BasketPanel({ live }) {
  const index = live?.index;
  const q = live?.quality;
  if (index?.status !== 'ok') {
    return (
      <Panel title="AGI AI Enablers" note="equal-weighted">
        <p className="font-mono text-[10px] uppercase tracking-wider text-[#d9a94a]">{index?.status || 'no data'}</p>
        <p className="mt-1.5 text-[11px] leading-relaxed text-[#8b95a3]">
          {index?.reason || 'The basket has not been computed yet.'}
        </p>
        {index?.missing?.length ? (
          <p className="mt-1.5 font-mono text-[11px] text-[#7d8894]">{index.missing.join(' · ')}</p>
        ) : null}
      </Panel>
    );
  }
  return (
    <Panel
      title="AGI AI Enablers"
      note="equal-weighted"
      action={`${Math.round(index.coverage * 100)}% priced`}
    >
      <div className="grid grid-cols-4 gap-2">
        {[
          ['Today', pp(index.return_pp), upDown(index.return_pp)],
          ['vs Nifty', index.relative ? pp(index.relative.excess_pp) : '—', upDown(index.relative?.excess_pp)],
          ['Breadth', `${index.breadth.advancing}/${index.priced}`, 'text-[#e3e8ef]'],
          ['Live', `${q?.live ?? 0}/${index.total}`, q?.live === index.total ? 'text-[#4ade80]' : 'text-[#d9a94a]'],
        ].map(([label, value, cls]) => (
          <div key={label}>
            <p className="text-[10px] uppercase tracking-wider text-[#7d8894]">{label}</p>
            <p className={`mt-0.5 text-[17px] font-semibold tabular-nums ${cls}`}>{value}</p>
          </div>
        ))}
      </div>
      {q?.last_good ? (
        <p className="mt-2 text-[10px] text-[#d9a94a]">{q.last_good} member{q.last_good === 1 ? '' : 's'} on last-good price, not live</p>
      ) : null}
      {index.priceBreak?.length ? (
        <p className="mt-2 text-[10px] text-[#d9a94a]">
          Excluded today for a corporate action (bonus, split or rights):{' '}
          {index.priceBreak.map((one) => one.symbol).join(', ')}. Its price
          change would be the share count changing, not the market.
        </p>
      ) : null}
      {live?.corporateActions?.unread?.length ? (
        <p className="mt-2 text-[10px] text-[#7d8894]">
          Corporate actions not checked for {live.corporateActions.unread.map((one) => one.symbol).join(', ')}
        </p>
      ) : null}
    </Panel>
  );
}

function LayerAttribution({ live }) {
  const index = live?.index;
  const rows = index?.contributions?.byLayer || [];
  if (index?.status !== 'ok' || !rows.length) {
    return (
      <Panel title="Today's move" note="attribution">
        <p className="text-[11px] text-[#68727f]">Available when the basket is priced.</p>
      </Panel>
    );
  }
  const widest = Math.max(...rows.map((one) => Math.abs(one.contribution_pp)), 0.01);
  const subs = index.contributions.bySubLayer || [];
  return (
    <Panel title="Today's move" note="contribution, pp">
      <div className="space-y-2.5">
        {rows.map((row) => (
          <div key={row.layer}>
            <div className="flex items-baseline justify-between">
              <span className="text-[12px] text-[#d3dae3]">{LAYER_LABEL[row.layer] || row.layer}</span>
              <span className={`font-mono text-[11px] tabular-nums ${upDown(row.contribution_pp)}`}>{pp(row.contribution_pp)}</span>
            </div>
            <div className="mt-1 h-[3px] rounded bg-[#1a2230]">
              <div
                className={`h-[3px] rounded ${row.contribution_pp >= 0 ? 'bg-[#4ade80]' : 'bg-[#f87171]'}`}
                style={{ width: `${Math.max(2, (Math.abs(row.contribution_pp) / widest) * 100)}%` }}
              />
            </div>
            <div className="mt-1 flex flex-wrap gap-x-3">
              {subs.filter((one) => one.subLayer.startsWith(`${row.layer}/`)).map((one) => (
                <span key={one.subLayer} className="text-[10px] text-[#7d8894]">
                  {SUB_LABEL[one.subLayer.split('/')[1]] || one.subLayer}
                  <span className={`ml-1 font-mono ${upDown(one.contribution_pp)}`}>{pp(one.contribution_pp)}</span>
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
      {index.subLayerResidual_ok === false ? (
        <p className="mt-2 border-t border-[#1a2230] pt-2 text-[10px] text-[#d9a94a]">
          Sub-layers short by {pp(index.subLayerResidual_pp)}
          {index.unclassified?.length ? ` — ${index.unclassified.join(', ')} sits in no sub-layer` : ''}
        </p>
      ) : null}
    </Panel>
  );
}

/**
 * The order feed, from the evidence that admitted each member.
 *
 * Real, and the panel the mockup got right: every line is a filing with a
 * date, and clicking through to the excerpt is the point. It is not a live
 * wire — these arrive when the screen reruns, not by the minute — so it is
 * labelled by what it is.
 */
function OrderFeed({ universe }) {
  const rows = (universe?.members || [])
    .flatMap((m) => (m.admittedOn || []).map((e) => ({ ...e, symbol: m.symbol })))
    .sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
  const [open, setOpen] = React.useState(null);
  return (
    <Panel id="orders" title="Order announcements" note={`${rows.length} cited filings · newest first`}>
      <div className="max-h-[260px] space-y-0.5 overflow-y-auto">
        {rows.map((row, i) => (
          <div key={i}>
            <button
              type="button"
              onClick={() => setOpen(open === i ? null : i)}
              className="flex w-full items-start gap-2 rounded px-1 py-1.5 text-left hover:bg-[#141b26]"
            >
              <span className="w-[68px] shrink-0 whitespace-nowrap font-mono text-[11px] text-[#7d8894]">{row.date || '—'}</span>
              <span className="w-[86px] shrink-0 truncate font-mono text-[12px] text-[#d3dae3]">{row.symbol}</span>
              <span className="hidden min-w-0 flex-1 truncate text-[11px] text-[#9aa5b3] sm:block">{row.document}</span>
              <span className="ml-auto shrink-0 sm:ml-0">
                <Badge tone={row.kind === 'order' ? 'green' : row.kind === 'capex' ? 'blue' : 'neutral'}>
                  {KIND_LABEL[row.kind] || row.kind}
                </Badge>
              </span>
            </button>
            {open === i ? (
              <p className="mx-1 mb-1.5 border-l-2 border-[#2f5d3f] bg-[#0a0e14] px-3 py-2 text-[11px] leading-relaxed text-[#c7cfda]">
                &ldquo;{row.excerpt}&rdquo;
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </Panel>
  );
}

/**
 * Data centre capacity, only where a member disclosed it.
 *
 * The mockup showed a maintained project register with locations and
 * completion dates. This is not that: it is the megawatt figures that appear
 * in the filings which admitted these companies, and nothing else. A project
 * table with rows AGI has not sourced would be the easiest thing on the page
 * to believe and the hardest to defend.
 */
function CapacityDisclosed({ universe }) {
  const rows = (universe?.members || [])
    .filter((m) => m.layer === 'data_centre' || m.subLayers?.includes('generation'))
    .flatMap((m) => (m.admittedOn || [])
      .filter((e) => /\b\d[\d,.]*\s?(?:MW|megawatt)/i.test(e.excerpt || ''))
      .map((e) => ({ symbol: m.symbol, date: e.date, excerpt: e.excerpt, document: e.document })));
  if (!rows.length) {
    return (
      <Panel title="Capacity disclosed" note="megawatts, from filings">
        <Needed
          what="No admitted member has disclosed a megawatt figure in its admitting evidence."
          source="a filing that states capacity"
        />
      </Panel>
    );
  }
  return (
    <Panel id="capacity" title="Capacity disclosed" note="megawatts, as filed">
      <div className="space-y-2">
        {rows.map((row, i) => (
          <div key={i} className="border-b border-[#1a2230] pb-2 last:border-0 last:pb-0">
            <p className="flex items-baseline gap-2">
              <span className="font-mono text-[12px] text-[#d3dae3]">{row.symbol}</span>
              <span className="text-[10px] text-[#7d8894]">{row.date} · {row.document}</span>
            </p>
            <p className="mt-0.5 text-[11px] leading-relaxed text-[#9aa5b3]">&ldquo;{row.excerpt}&rdquo;</p>
          </div>
        ))}
      </div>
      <p className="mt-2 border-t border-[#1a2230] pt-2 text-[10px] leading-relaxed text-[#7d8894]">
        Only what members disclosed. Not a project register — AGI does not maintain one, and
        rows it had not sourced would be the easiest thing here to believe.
      </p>
    </Panel>
  );
}

/**
 * Why this company is here.
 *
 * The terminal rewrite of this page lost the per-company evidence expansion
 * the earlier version had: evidence survived only aggregated in the order
 * feed, never attributable to a company a reader clicks. That is the single
 * thing this basket has that a thematic list does not, so it is restored here
 * and stated in full - the evidence class, whether the source is the company
 * itself, the exact document and page, the excerpt, and why it is sufficient.
 *
 * "Why this is enough" is written from the classification rather than typed
 * per company, so it cannot drift from the rule that actually admitted them.
 */
const HARD_KINDS = new Set(['order', 'capex', 'operating']);

const SUFFICIENCY = {
  order: 'A signed order is a commitment by a counterparty, disclosed by the company, for work it has won.',
  capex: 'Committed or incurred capex is money the company reports having spent or contracted to spend.',
  operating: 'An operating disclosure is a figure from a completed period: revenue, capacity or an order book.',
};

function MemberEvidence({ member }) {
  const [open, setOpen] = React.useState(false);
  const evidence = member.admittedOn || [];
  const hard = evidence.filter((one) => HARD_KINDS.has(one.kind));
  const panelId = `evidence-${member.symbol}`;
  return (
    <div className="border-b border-[#1a2230] last:border-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full items-center gap-3 px-1 py-2.5 text-left hover:bg-[#141b26] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#e8833a]"
      >
        <span className="w-4 shrink-0 text-center text-[12px] text-[#5b6675]" aria-hidden>{open ? '\u2212' : '+'}</span>
        <span className="w-[96px] shrink-0 font-mono text-[12px] text-[#e3e8ef]">{member.symbol}</span>
        <span className="min-w-0 flex-1 truncate text-[12px] text-[#8b95a3]">{member.name}</span>
        <span className="hidden shrink-0 text-[11px] text-[#7d8894] sm:block">
          {LAYER_LABEL[member.layer]} &middot; {(member.subLayers || []).map((sl) => SUB_LABEL[sl] || sl).join(' + ')}
        </span>
        <Badge tone={hard.length ? 'green' : 'neutral'}>{hard.length ? 'Hard' : 'Soft'}</Badge>
      </button>

      {open ? (
        <div id={panelId} className="space-y-3 bg-[#0a0e14] px-8 pb-4 pt-2">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1.5 sm:grid-cols-4">
            {[
              ['Evidence class', hard.length ? 'Hard' : 'Soft'],
              ['First-party source', hard.length ? 'Yes' : 'Not established'],
              ['Layer', `${LAYER_LABEL[member.layer]} \u2192 ${(member.subLayers || []).map((sl) => SUB_LABEL[sl] || sl).join(' + ')}`],
              ['Reviewed by analyst', member.reviewedBy || 'Not yet'],
            ].map(([label, value]) => (
              <div key={label}>
                <dt className="text-[10px] uppercase tracking-[0.12em] text-[#68727f]">{label}</dt>
                <dd className="mt-0.5 text-[12px] text-[#e3e8ef]">{value}</dd>
              </div>
            ))}
          </dl>

          <div>
            <p className="text-[10px] uppercase tracking-[0.12em] text-[#68727f]">Evidence</p>
            <ul className="mt-1.5 space-y-2.5">
              {evidence.map((one, i) => (
                <li key={i} className="border-l-2 border-[#2f5d3f] pl-3">
                  <p className="text-[11px] text-[#7d8894]">
                    <span className="font-semibold text-[#8fcfa4]">{KIND_LABEL[one.kind] || one.kind}</span>
                    {' \u00b7 '}{one.document}{one.date ? ` \u00b7 ${one.date}` : ''}
                    {one.source ? ` \u00b7 ${one.source}` : ''}
                  </p>
                  <p className="mt-1 text-[12px] leading-relaxed text-[#c7cfda]">&ldquo;{one.excerpt}&rdquo;</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded border border-[#22303c] bg-[#0c1319] px-3 py-2">
            <p className="text-[10px] uppercase tracking-[0.12em] text-[#68727f]">Why this is enough</p>
            <p className="mt-1 text-[12px] leading-relaxed text-[#c7cfda]">
              {hard.length
                ? `${SUFFICIENCY[hard[0].kind]} It is disclosed by the company itself and names AI infrastructure, so it is attributable and dated rather than inferred.`
                : 'It is not. This member is held on soft evidence and should not be in the basket \u2014 partnerships, memoranda and sector commentary describe intent, not activity.'}
            </p>
          </div>

          <p className="text-[10px] text-[#5b6675]">ISIN {member.isin} &middot; instrument {member.instrumentKey}</p>
        </div>
      ) : null}
    </div>
  );
}

function AdmittedUniverse({ universe }) {
  const members = universe?.members || [];
  return (
    <section id="universe" className="rounded-md border border-[#1e2634] bg-[#0c1017]">
      <header className="flex items-baseline gap-2 border-b border-[#1a2230] px-3.5 py-2.5">
        <h2 className="text-[14px] font-semibold text-[#e3e8ef]">Why these companies are here</h2>
        <span className="text-[11px] text-[#7d8894]">{members.length} admitted &middot; expand for the filing</span>
      </header>
      <div className="px-2 py-1">
        {members.map((member) => <MemberEvidence key={member.symbol} member={member} />)}
      </div>
    </section>
  );
}

function Watchlist({ universe, live }) {
  const members = universe?.members || [];
  const byName = live?.index?.contributions?.byName || [];
  const at = (symbol) => byName.find((one) => one.symbol === symbol);
  return (
    <Panel title="Company watchlist" note={`${members.length} admitted`}>
      <table className="w-full">
        <thead>
          <tr className="text-[10px] uppercase tracking-wider text-[#7d8894]">
            <th className="pb-1 text-left font-medium">Company</th>
            <th className="pb-1 text-left font-medium">Layer</th>
            <th className="pb-1 text-right font-medium">Day</th>
            <th className="pb-1 text-right font-medium">Contrib</th>
            <th className="pb-1 text-right font-medium">Vol</th>
            <th className="pb-1 text-right font-medium">EPS rev</th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => {
            const row = at(member.symbol);
            const volume = live?.volumes?.[member.symbol];
            return (
              <tr key={member.symbol} className="border-t border-[#1a2230]">
                <td className="py-1.5 font-mono text-[12px] text-[#d3dae3]">{member.symbol}</td>
                <td className="py-1.5 text-[11px] text-[#9aa5b3]">{LAYER_LABEL[member.layer]}</td>
                <td className={`py-1.5 text-right font-mono text-[11px] tabular-nums ${row ? upDown(row.return_pct) : 'text-[#4b5563]'}`}>
                  {row ? pctOf(row.return_pct) : '—'}
                </td>
                <td className={`py-1.5 text-right font-mono text-[11px] tabular-nums ${row ? upDown(row.contribution_pp) : 'text-[#4b5563]'}`}>
                  {row ? pp(row.contribution_pp) : '—'}
                </td>
                <td className="py-1.5 text-right font-mono text-[11px] tabular-nums text-[#8b95a3]">
                  {volume?.ratio != null ? `${volume.ratio.toFixed(1)}×` : '—'}
                </td>
                <td className="py-1.5 text-right font-mono text-[11px] text-[#5b6675]">n/a</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 border-t border-[#1a2230] pt-2 text-[10px] leading-relaxed text-[#7d8894]">
        No EPS revision column: Upstox serves trailing ratios only and no consensus feed is
        connected, so there is nothing to revise against. No signal badges yet either.
      </p>
    </Panel>
  );
}

function EmptyLayersPanel({ universe }) {
  const filled = new Set((universe?.members || []).flatMap((m) => (m.subLayers || []).map((s) => `${m.layer}/${s}`)));
  const empty = ALL_SUBS.filter(([l, s]) => !filled.has(`${l}/${s}`));
  return (
    <Panel id="layers" title="Empty layers" note={`${empty.length} of ${ALL_SUBS.length}`}>
      {empty.length === 0 ? (
        <p className="text-[12px] text-[#9aa5b3]">Every sub-layer has an admitted company.</p>
      ) : (
        <>
          <div className="space-y-1">
            {empty.map(([l, s]) => (
              <div key={`${l}/${s}`} className="flex items-center gap-2 rounded border border-dashed border-[#26303f] px-2 py-1.5">
                <span className="text-[12px] text-[#d3dae3]">{LAYER_LABEL[l]} <span className="text-[#4b5563]">→</span> {SUB_LABEL[s] || s}</span>
                <Badge tone="amber">pre-revenue</Badge>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px] leading-relaxed text-[#7d8894]">
            Empty because nothing was disclosed beyond intent, not because the screen has not
            looked. Admitting one would mean admitting on intent.
          </p>
        </>
      )}
    </Panel>
  );
}

function Candidates({ universe }) {
  const rows = universe?.candidates || [];
  const [open, setOpen] = React.useState(null);
  return (
    <Panel id="refused" title="Candidates refused" note={`${rows.length}`}>
      <div className="max-h-[200px] space-y-0.5 overflow-y-auto">
        {rows.map((c) => (
          <div key={c.symbol}>
            <button
              type="button"
              onClick={() => setOpen(open === c.symbol ? null : c.symbol)}
              className="flex w-full items-center gap-2 rounded px-1 py-1.5 text-left hover:bg-[#141b26]"
            >
              <span className="w-[86px] shrink-0 truncate font-mono text-[12px] text-[#d3dae3]">{c.symbol}</span>
              <span className="hidden min-w-0 flex-1 truncate text-[11px] text-[#7d8894] sm:block">{c.name}</span>
              <span className="ml-auto shrink-0 sm:ml-0">
                <Badge>{c.suggestedSubLayers?.length ? SUB_LABEL[c.suggestedSubLayers[0]] || c.suggestedSubLayers[0] : 'unplaced'}</Badge>
              </span>
            </button>
            {open === c.symbol ? (
              <p className="mx-1 mb-1.5 border-l-2 border-[#26303f] bg-[#0a0e14] px-3 py-2 text-[11px] leading-relaxed text-[#9aa5b3]">
                {c.note}
              </p>
            ) : null}
          </div>
        ))}
      </div>
    </Panel>
  );
}

/* ── the page ─────────────────────────────────────────────────────────── */

/**
 * Only routes that exist.
 *
 * The design this page was built from showed Research, Markets, Intelligence,
 * Portfolio and About. There is no /intelligence route and no /portfolio
 * route in this app, so those two are not here: a nav label that goes nowhere
 * is worse than an absent one, and pointing them at a plausible neighbour
 * would be inventing a destination.
 *
 * There is also no search route and no search handler anywhere in the app, so
 * the design's search field is not reproduced either.
 */
const NAV = [
  { label: 'Research', href: '/research' },
  { label: 'Markets', href: '/markets' },
  { label: 'About', href: '/about' },
];

export default function IndiaAiIntelligencePage() {
  const [universe, setUniverse] = React.useState(null);
  const [live, setLive] = React.useState(null);
  const [snapshots, setSnapshots] = React.useState([]);
  const [filed, setFiled] = React.useState(null);
  const [stage3, setStage3] = React.useState(null);
  const [history, setHistory] = React.useState(null);
  const [marketValue, setMarketValue] = React.useState(null);
  const [liveError, setLiveError] = React.useState(null);
  const [error, setError] = React.useState(null);
  const clock = useIstClock();
  const open = nseOpen();

  React.useEffect(() => {
    let cancelled = false;
    fetchUniverse()
      .then((payload) => { if (!cancelled) setUniverse(payload); })
      .catch((err) => { if (!cancelled) setError(String(err?.message || err)); });
    fetchFiledFacts()
      .then((payload) => { if (!cancelled) setFiled(payload); })
      .catch(() => {});
    fetchStage3()
      .then((payload) => { if (!cancelled) setStage3(payload); })
      .catch(() => {});
    fetchIndexHistory()
      .then((payload) => { if (!cancelled) setHistory(payload); })
      .catch(() => {});
    fetchMarketValue()
      .then((payload) => { if (!cancelled) setMarketValue(payload); })
      .catch((err) => { if (!cancelled) setMarketValue({ ok: false, error: String(err?.message || err) }); });
    return () => { cancelled = true; };
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    const load = () => {
      fetchLive()
        .then((payload) => { if (!cancelled) { setLive(payload); setLiveError(null); } })
        .catch((err) => { if (!cancelled) setLiveError(String(err?.message || err)); });
      fetchSnapshots()
        .then((payload) => { if (!cancelled) setSnapshots(payload.snapshots || []); })
        .catch(() => {});
    };
    load();
    const timer = setInterval(load, 30_000);
    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  return (
    <div className="min-h-screen bg-[#080b11] text-[#e3e8ef]">
      {/* chrome */}
      <header className="sticky top-0 z-30 border-b border-[#1a2230] bg-[#0a0e14]/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1680px] items-center gap-6 px-4 py-2.5">
          <a href="/" className="flex items-center gap-2 shrink-0">
            <span className="grid h-7 w-7 place-items-center rounded bg-[#e8833a] text-[13px] font-bold text-[#0a0e14]">A</span>
            <span className="hidden sm:block leading-tight">
              <span className="block text-[11px] font-bold tracking-wide">AGARWAL</span>
              <span className="block text-[8px] tracking-[0.2em] text-[#68727f]">GLOBAL INVESTMENTS</span>
            </span>
          </a>
          <nav className="hidden items-center gap-5 md:flex" aria-label="Main">
            {NAV.map((item) => (
              <a
                key={item.href}
                href={item.href}
                aria-current={item.label === 'Research' ? 'page' : undefined}
                className={`rounded text-[12px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e8833a] ${
                  item.label === 'Research'
                    ? 'border-b-2 border-[#e8833a] pb-[2px] font-semibold text-[#e3e8ef]'
                    : 'text-[#8b95a3] hover:text-[#e3e8ef]'}`}
              >
                {item.label}
              </a>
            ))}
          </nav>
          <p className="ml-auto hidden text-right text-[10px] leading-tight text-[#68727f] lg:block">
            Ideas for<br />a more prosperous tomorrow.
          </p>
        </div>
      </header>

      {error ? (
        <p className="mx-auto max-w-[1680px] px-4 py-16 text-[12px] text-[#f87171]">
          Could not load the universe: {error}
        </p>
      ) : (
        <div className="mx-auto max-w-[1680px] px-4 py-4">
          <nav className="mb-3 text-[11px] text-[#7d8894]" aria-label="Breadcrumb">
            <a href="/research" className="rounded text-[#9aa5b3] hover:text-[#e3e8ef] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e8833a]">Research</a>
            <span className="px-1 text-[#3a4453]">›</span>
            <a href="/themes" className="rounded text-[#9aa5b3] hover:text-[#e3e8ef] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e8833a]">Themes</a>
            <span className="px-1 text-[#3a4453]">›</span>
            <span aria-current="page">India AI Infrastructure</span>
          </nav>

          <SectionNav />

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
            {/* ── research ── */}
            <div className="min-w-0 space-y-4">
              <div id="overview">
                <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#e8833a]">Strategic research</p>
                <h1 className="mt-2 text-[28px] font-semibold leading-tight tracking-tight sm:text-[40px]">
                  India&rsquo;s Hidden AI Infrastructure Trade
                </h1>
                <p className="mt-1.5 text-[15px] text-[#8b95a3] sm:text-[18px]">
                  The companies building it, admitted only on what they disclosed
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <span className="text-[11px] text-[#68727f]">AGI Investment Intelligence</span>
                  <span className="text-[#3a4453]">|</span>
                  <span className="text-[11px] text-[#68727f]">
                    Screen run {universe?.version || '—'}
                  </span>
                  <span className="rounded-full border border-[#b38b4d]/40 bg-[#b38b4d]/10 px-2.5 py-0.5 text-[11px] font-semibold text-[#d9a94a]">
                    Universe: {universe?.status === 'partial' ? 'Partial' : universe?.status || '—'} · Evidence-qualified
                  </span>
                </div>
              </div>

              <StatusStrip universe={universe} live={live} />

              <ExecutiveSummary universe={universe} />

              <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
                <Panel title="AI Enablers vs. Nifty 50" note="from the first snapshot — no back-history">
                  <IndexedChart snapshots={snapshots} />
                  <div className="mt-1 flex gap-4 px-1">
                    <span className="flex items-center gap-1.5 text-[11px] text-[#9aa5b3]">
                      <span className="h-[2px] w-4 bg-[#e8833a]" /> AI Enablers (AGI basket)
                    </span>
                    <span className="flex items-center gap-1.5 text-[11px] text-[#9aa5b3]">
                      <span className="h-[2px] w-4 bg-[#5aa2e0]" /> Nifty 50
                    </span>
                  </div>
                </Panel>
                <KeyTakeaways universe={universe} live={live} />
              </div>

              <SinceAdmission history={history} />

              <div id="method">
                <h2 className="text-[20px] font-semibold tracking-tight">Executive Intelligence</h2>
                <p className="mt-1.5 text-[12px] text-[#8b95a3]">
                  The method is the product. Each statement below is a count this page can show you the
                  workings for.
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  {[
                    {
                      head: 'What we found',
                      body: `${(universe?.members || []).length} companies currently meet the evidence threshold \u2014 each disclosed something it had done, not something it intends.`,
                    },
                    {
                      head: 'What we refused',
                      body: `${universe?.candidates?.length || 0} candidates were excluded because the evidence was limited to intent, commentary, projections or capability claims.`,
                    },
                    {
                      head: 'What remains empty',
                      body: 'Two sub-layers have no qualifying listed company with evidence of operational activity. They are shown empty rather than filled.',
                    },
                  ].map((one) => (
                    <div key={one.head} className="rounded-md border border-[#1e2634] bg-[#0c1017] p-3.5">
                      <h3 className="text-[13px] font-semibold text-[#e3e8ef]">{one.head}</h3>
                      <p className="mt-1.5 text-[12px] leading-relaxed text-[#8b95a3]">{one.body}</p>
                    </div>
                  ))}
                </div>
                <blockquote className="mt-4 max-w-2xl border-l-2 border-[#e8833a] pl-4">
                  <p className="text-[14px] italic leading-relaxed text-[#c7cfda]">
                    A basket you cannot audit is a list. Every member here opens into the filing that
                    admitted it.
                  </p>
                  <cite className="mt-1 block text-[10px] uppercase tracking-[0.16em] not-italic text-[#68727f]">
                    AGI Investment Intelligence
                  </cite>
                </blockquote>
              </div>

              <section id="filed" className="space-y-3">
                <div>
                  <h2 className="text-[20px] font-semibold tracking-tight">From the filings</h2>
                  <p className="mt-1.5 max-w-3xl text-[12px] leading-relaxed text-[#8b95a3]">
                    Everything below is read from an annual report this system opened, and every
                    figure carries a company, a document and a page. There is no consensus, no
                    forecast and no third-party estimate here, which is why there are four charts
                    rather than forty &mdash; and why two of them are about what could not be
                    established.
                  </p>
                </div>
                <div className="grid gap-3 lg:grid-cols-2">
                  <ExposureAttribution companies={filed?.companies} />
                  <CapexConcentration company={filed?.companies?.CGPOWER} />
                  <BuildFunding companies={filed?.companies} />
                  <EvidenceComposition universe={universe} />
                </div>
              </section>

              <AdmittedUniverse universe={universe} />

              <InvestmentIntensity data={stage3} />

              <LayerCards universe={universe} />

              <MarketValue data={marketValue} />
            </div>

            {/* ── monitor ── */}
            <div className="min-w-0 space-y-3 xl:sticky xl:top-[60px] xl:self-start">
              <div className="rounded-md border border-[#1e2634] bg-[#0c1017] px-3 py-2.5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h2 className="text-[16px] font-semibold tracking-tight">India AI Intelligence Monitor</h2>
                    <p className="mt-0.5 text-[11px] text-[#7d8894]">
                      Live where a source exists. Named where one does not.
                    </p>
                  </div>
                  <div className="shrink-0 text-right">
                    <span className="flex items-center justify-end gap-1.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${live?.quality?.live ? 'bg-[#4ade80]' : 'bg-[#4b5563]'}`} />
                      <span className={`text-[10px] font-bold uppercase tracking-wider ${live?.quality?.live ? 'text-[#4ade80]' : 'text-[#68727f]'}`}>
                        {live?.quality?.live ? 'Live' : open ? 'No ticks' : 'NSE closed'}
                      </span>
                    </span>
                    <p className="mt-0.5 font-mono text-[10px] tabular-nums text-[#7d8894]">
                      {clock.date} · {clock.time} IST
                    </p>
                  </div>
                </div>
                {liveError ? (
                  <p className="mt-2 border-t border-[#1a2230] pt-2 text-[10px] text-[#d9a94a]">{liveError}</p>
                ) : null}
              </div>

              <BasketPanel live={live} />
              <LayerAttribution live={live} />

              <Panel title="Earnings revisions" note="last 90 days">
                <Needed
                  what="Upstox serves trailing ratios only — P/E, P/B, ROE, EV/EBITDA — with no forward estimates, so there is no consensus to revise against."
                  source="a consensus estimates feed"
                />
              </Panel>

              <Panel title="Capex changes" note="year on year, from filings">
                <CapexChanges companies={filed?.companies} />
              </Panel>

              <OrderFeed universe={universe} />
              <CapacityDisclosed universe={universe} />

              <Panel title="AI layer heatmap" note="12-month view">
                <Needed
                  what="A twelve-month heatmap needs twelve months of snapshots. The first was taken today."
                  source="time"
                />
              </Panel>

              <Watchlist universe={universe} live={live} />
              <EmptyLayersPanel universe={universe} />
              <Candidates universe={universe} />
            </div>
          </div>

          <footer className="mt-6 border-t border-[#1a2230] pt-4 pb-8">
            <p className="max-w-4xl text-[10px] leading-relaxed text-[#68727f]">
              AGI&rsquo;s own screen over public filings. Admission requires at least one hard,
              first-party disclosure — a signed order, committed capex, or an operating figure.
              Partnerships, memoranda and sector forecasts do not admit a company. Prices from
              Upstox; a basket below its coverage floor reports coverage instead of a level. No
              cumulative return is shown for periods before this basket existed, and no panel on
              this page displays a figure AGI has not sourced.
            </p>
            <p className="mt-2 text-[9px] text-[#4b5563]">© 2026 AGI. Not investment advice.</p>
          </footer>
        </div>
      )}
    </div>
  );
}
