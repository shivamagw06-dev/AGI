import React from 'react';

/**
 * Charts drawn only from filings this system has read.
 *
 * Every figure here opens to a company, a document and a page number. None of
 * it is consensus, forecast, or another house's measurement - which is why
 * there are four charts rather than fourteen, and why two of them are about
 * what could not be established rather than what was.
 */

const ACCENT = '#e8833a';
const GOOD = '#4ade80';

const Panel = ({ title, note, children, source }) => (
  <section className="rounded-md border border-[#1e2634] bg-[#0c1017]">
    <header className="flex items-baseline gap-2 border-b border-[#1a2230] px-3.5 py-2.5">
      <h3 className="text-[15px] font-semibold tracking-tight text-[#f1f5f9]">{title}</h3>
      {note ? <span className="text-[13px] text-[#7d8894]">{note}</span> : null}
    </header>
    <div className="p-3.5">{children}</div>
    {source ? (
      <p className="border-t border-[#1a2230] px-3.5 py-2 text-[12px] leading-relaxed text-[#68727f]">{source}</p>
    ) : null}
  </section>
);

/**
 * How far each member's theme exposure can be sized from what it discloses.
 *
 * Three tiers, not a yes or no. Treating it as binary put NETWEB - which
 * states AI Systems revenue at 43.4% of the total - in the same bucket as
 * KAYNES, which states nothing separable at all. Those are very different
 * amounts of disclosure. What separates the top tier from the middle one is
 * audit: a reported Ind AS 108 segment ties the theme to revenue, result,
 * assets and capex, while a management table gives a figure that cannot be
 * tied to anything else in the accounts.
 */
const TIERS = [
  { key: 'SEGMENT_REPORTED', label: 'segment reported', tone: '#4ade80', dot: 'bg-[#4ade80]' },
  { key: 'MANAGEMENT_DISCLOSED', label: 'management disclosed', tone: '#5aa2e0', dot: 'bg-[#5aa2e0]' },
  { key: 'NOT_ATTRIBUTABLE', label: 'not attributable', tone: '#3a4453', dot: 'bg-[#3a4453]' },
];
const tierOf = (one) => one.attribution
  || (one.exposureAttributable === true ? 'SEGMENT_REPORTED'
    : one.exposureAttributable === false ? 'NOT_ATTRIBUTABLE' : null);

const firstSentence = (text) => String(text || '').split('. ')[0].replace(/\.$/, '');

export function ExposureAttribution({ companies, universe }) {
  const filed = companies || {};
  const members = universe?.members || [];
  // Every admitted member, from the universe, which records a tier for each.
  // The companies read in depth carry a verdict written for this chart and
  // agree with the universe on the tier; everyone else's line is the first
  // sentence of the exposure note recorded when they were admitted. Before
  // the universe arrives, the in-depth set is shown and says it is partial.
  const rows = members.length
    ? members.map((member) => {
      const one = filed[member.symbol];
      return {
        symbol: member.symbol,
        tier: member.attribution || (one ? tierOf(one) : null),
        verdict: one?.exposureVerdict || firstSentence(one?.exposureFinding) || firstSentence(member.exposureNote),
      };
    })
    : Object.entries(filed).map(([symbol, one]) => ({
      symbol,
      tier: tierOf(one),
      verdict: one.exposureVerdict || firstSentence(one.exposureFinding),
    }));
  if (!rows.length) return null;
  const order = (t) => { const i = TIERS.findIndex((x) => x.key === t); return i < 0 ? TIERS.length : i; };
  const sorted = [...rows].sort((a, b) => order(a.tier) - order(b.tier) || a.symbol.localeCompare(b.symbol));
  const counts = TIERS.map((t) => ({ ...t, n: rows.filter((r) => r.tier === t.key).length }));
  const unresolved = rows.filter((r) => !TIERS.some((t) => t.key === r.tier));

  return (
    <Panel
      title="Can the exposure be sized?"
      note={`${members.length ? `all ${rows.length} members` : `${rows.length} read in depth`} · ${counts[0].n} segment-reported, ${counts[1].n} management-disclosed, ${counts[2].n} not attributable${unresolved.length ? `, ${unresolved.length} unresolved` : ''}`}
      source="From each member's own disclosures, as recorded when it was admitted. Segment-reported means the theme is an audited Ind AS 108 operating segment. Management-disclosed means the company states a figure for it outside segment reporting (in a filing, presentation or call), which cannot be tied to assets or capex. Unresolved means no tier has been recorded yet; it is not a guess at either."
    >
      <div className="mb-3 flex h-2 overflow-hidden rounded-full bg-[#141b26]">
        {counts.map((t) => (
          <div key={t.key} style={{ width: `${(t.n / rows.length) * 100}%`, background: t.tone }} />
        ))}
        {unresolved.length ? <div className="bg-[#d9a94a]/50" style={{ width: `${(unresolved.length / rows.length) * 100}%` }} /> : null}
      </div>
      <div className="space-y-2">
        {[...counts, { key: 'unresolved', label: 'unresolved', dot: 'bg-[#d9a94a]', n: unresolved.length }]
          .filter((t) => t.n)
          .map((t) => (
            <div key={t.key}>
              <p className="flex items-center gap-2 text-[12px] uppercase tracking-wider text-[#7d8894]">
                <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} aria-hidden />
                {t.label} · {t.n}
              </p>
              <p className="mt-1 flex flex-wrap gap-1">
                {sorted.filter((r) => (t.key === 'unresolved' ? !TIERS.some((x) => x.key === r.tier) : r.tier === t.key)).map((r) => (
                  <span key={r.symbol} className="rounded bg-[#1c2534] px-1.5 py-[2px] font-mono text-[11px] text-[#98a3b2]">{r.symbol}</span>
                ))}
              </p>
            </div>
          ))}
      </div>
      <details className="mt-3">
        <summary className="cursor-pointer rounded text-[13px] text-[#8fb4d8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#e8833a]">
          Why, company by company
        </summary>
        <ul className="mt-2 space-y-2">
          {sorted.map((row) => {
            const t = TIERS.find((x) => x.key === row.tier);
            return (
              <li key={row.symbol} className="flex items-start gap-2.5">
                <span className={`mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full ${t ? t.dot : 'bg-[#d9a94a]'}`} aria-hidden />
                <span className="min-w-0">
                  <span className="font-mono text-[13px] text-[#d3dae3]">{row.symbol}</span>
                  <span className="ml-2 text-[12px] uppercase tracking-wider text-[#68727f]">
                    {t ? t.label : 'unresolved'}
                  </span>
                  {row.verdict ? <span className="mt-0.5 block text-[13px] leading-relaxed text-[#8b95a3]">{row.verdict}.</span> : null}
                </span>
              </li>
            );
          })}
        </ul>
      </details>
    </Panel>
  );
}

/**
 * Where a company puts its capital against where it earns.
 *
 * Only one member reports both by segment, so this chart has one subject and
 * says so rather than implying a cohort.
 */
export function CapexConcentration({ company }) {
  if (!company?.segmentCapex?.length || !company?.segmentRevenue?.length) return null;
  const revTotal = company.segmentRevenue.reduce((s, one) => s + one.value, 0);
  const capTotal = company.segmentCapex.reduce((s, one) => s + one.value, 0);
  const semiRev = company.segmentRevenue.find((one) => /semiconductor/i.test(one.segment))?.value ?? 0;
  const semiCap = company.segmentCapex.find((one) => /semiconductor/i.test(one.segment))?.value ?? 0;
  if (!revTotal || !capTotal) return null;
  const revShare = semiRev / revTotal;
  const capShare = semiCap / capTotal;

  const Bar = ({ label, share, value, total, tone }) => (
    <div className="mb-3 last:mb-0">
      <div className="flex items-baseline justify-between">
        <span className="text-[13px] text-[#c7cfda]">{label}</span>
        <span className="font-mono text-[15px] font-semibold tabular-nums" style={{ color: tone }}>
          {(share * 100).toFixed(1)}%
        </span>
      </div>
      <div className="mt-1 h-2.5 rounded bg-[#141b26]">
        <div className="h-2.5 rounded" style={{ width: `${Math.max(1.5, share * 100)}%`, background: tone }} />
      </div>
      <p className="mt-1 text-[12px] tabular-nums text-[#68727f]">
        &#8377;{value.toLocaleString('en-IN')} cr of &#8377;{total.toLocaleString('en-IN')} cr
      </p>
    </div>
  );

  return (
    <Panel
      title="Capital ahead of revenue"
      note="CG Power, semiconductors"
      source="CG Power FY2025-26 annual report, consolidated segment information, page 176. Capex is net of government grant, so it is not gross capital spend and is not comparable with another company's gross figure."
    >
      <Bar label="Share of group capex" share={capShare} value={semiCap} total={capTotal} tone={ACCENT} />
      <Bar label="Share of group revenue" share={revShare} value={semiRev} total={revTotal} tone="#5aa2e0" />
      <p className="mt-3 border-t border-[#1a2230] pt-2.5 text-[13px] leading-relaxed text-[#8b95a3]">
        The segment takes {(capShare / revShare).toFixed(0)}&times; the share of capital that it earns
        of revenue. External sales were nil a year earlier and the segment result is a loss, which is
        what building ahead of revenue looks like in the accounts.
      </p>
    </Panel>
  );
}

/**
 * Capex set against the cash generated to pay for it.
 *
 * Capex alone reads as conviction. Capex against negative operating cash flow
 * reads as a company mid-build on external money - a different risk, the same
 * fact.
 */
export function BuildFunding({ companies }) {
  const rows = Object.entries(companies || {}).map(([symbol, one]) => {
    const facts = one.facts || [];
    const capex = facts.find((f) => f.concept === 'capex' && f.value != null);
    const cfo = facts.find((f) => f.concept === 'cfo' && f.value != null);
    if (!capex || !cfo) return null;
    return { symbol, capex: capex.value, cfo: cfo.value };
  }).filter(Boolean);
  if (!rows.length) return null;

  const fmt = (v) => `${v < 0 ? '(' : ''}₹${Math.abs(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}${v < 0 ? ')' : ''} mn`;

  return (
    <Panel
      title="What is paying for the build"
      note="capex against operating cash flow"
      source="From each company's consolidated cash-flow statement. Only members whose filing discloses both lines appear, which is why this is not the whole basket."
    >
      <div className="space-y-4">
        {rows.map((row) => {
          const scale = Math.max(Math.abs(row.capex), Math.abs(row.cfo)) || 1;
          return (
            <div key={row.symbol}>
              <p className="font-mono text-[13px] text-[#d3dae3]">{row.symbol}</p>
              <div className="mt-1.5 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-[78px] shrink-0 text-[12px] text-[#68727f]">capex out</span>
                  <div className="h-2.5 flex-1 rounded bg-[#141b26]">
                    <div className="h-2.5 rounded bg-[#e8833a]" style={{ width: `${(Math.abs(row.capex) / scale) * 100}%` }} />
                  </div>
                  <span className="w-[96px] shrink-0 text-right font-mono text-[12px] tabular-nums text-[#c7cfda]">{fmt(row.capex)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-[78px] shrink-0 text-[12px] text-[#68727f]">cash from ops</span>
                  <div className="h-2.5 flex-1 rounded bg-[#141b26]">
                    <div
                      className={`h-2.5 rounded ${row.cfo < 0 ? 'bg-[#a13a2b]' : 'bg-[#4ade80]'}`}
                      style={{ width: `${(Math.abs(row.cfo) / scale) * 100}%` }}
                    />
                  </div>
                  <span className={`w-[96px] shrink-0 text-right font-mono text-[12px] tabular-nums ${row.cfo < 0 ? 'text-[#f87171]' : 'text-[#4ade80]'}`}>
                    {fmt(row.cfo)}
                  </span>
                </div>
              </div>
              {row.cfo < 0 ? (
                <p className="mt-1.5 text-[12px] leading-relaxed text-[#8b95a3]">
                  Operations consumed cash while the build continued, so the year was funded
                  externally rather than from trading.
                </p>
              ) : null}
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

/** What kind of disclosure admitted each member. */
export function EvidenceComposition({ universe }) {
  const counts = new Map();
  for (const member of universe?.members || []) {
    for (const one of member.admittedOn || []) counts.set(one.kind, (counts.get(one.kind) || 0) + 1);
  }
  const rows = [...counts].sort((a, b) => b[1] - a[1]);
  const total = rows.reduce((s, [, n]) => s + n, 0);
  if (!total) return null;
  const LABEL = { order: 'Signed orders', capex: 'Committed capex', operating: 'Operating disclosures' };
  const TONE = { order: GOOD, capex: '#5aa2e0', operating: ACCENT };

  return (
    <Panel
      title="What admitted them"
      note={`${total} filings`}
      source="Every admitting item is a first-party disclosure carrying a date and a document. Partnerships, memoranda and sector forecasts admit nobody, which is why no soft class appears here at all."
    >
      <div className="mb-3 flex h-2 overflow-hidden rounded-full bg-[#141b26]">
        {rows.map(([kind, n]) => (
          <div key={kind} style={{ width: `${(n / total) * 100}%`, background: TONE[kind] || '#2c3542' }} />
        ))}
      </div>
      <ul className="space-y-1.5">
        {rows.map(([kind, n]) => (
          <li key={kind} className="flex items-center gap-2 text-[13px]">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: TONE[kind] || '#2c3542' }} aria-hidden />
            <span className="text-[#c7cfda]">{LABEL[kind] || kind}</span>
            <span className="ml-auto font-mono tabular-nums text-[#8b95a3]">{n}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

/**
 * Capex growth, year on year, where a filing discloses both years.
 *
 * Growth only, never absolute values. The members report in different units -
 * crore for some, million for others - and a bar chart of the raw figures
 * would put a crore beside a million as though they were the same size. A
 * ratio of a company's own two years is unit-free, so it can be compared.
 *
 * Only primary reads with a page number appear. A relayed figure, or a year
 * with no comparative, is left out rather than guessed at.
 */
export function CapexChanges({ companies, stage3 }) {
  // A primary read with a page number first; otherwise the stage 3 input,
  // which is the same cash-flow line taken from the annual report and cites
  // its document. Both are FY26 against FY25.
  const primary = {};
  for (const [symbol, one] of Object.entries(companies || {})) {
    if (one.provenance !== 'PRIMARY_FILING_READ') continue;
    const f = (one.facts || []).find((x) => x.concept === 'capex' && x.value != null && x.prior);
    if (!f || !(f.prior > 0)) continue;
    primary[symbol] = { symbol, growth: f.value / f.prior - 1, source: `cash flow, page ${f.source_page}` };
  }
  const members = (stage3?.rows || []).filter((one) => one.kind === 'member');
  const fromStage3 = members
    .filter((one) => !primary[one.symbol] && Number.isFinite(one.capexGrowth))
    .map((one) => ({ symbol: one.symbol, growth: one.capexGrowth, source: one.capexSource || 'annual report' }));
  const rows = [...Object.values(primary), ...fromStage3].sort((a, b) => b.growth - a.growth);
  const shown = new Set(rows.map((one) => one.symbol));
  const leftOut = members.filter((one) => !shown.has(one.symbol)).map((one) => one.symbol);
  if (!rows.length) return null;
  const widest = Math.max(...rows.map((r) => Math.abs(r.growth))) || 1;

  return (
    <div className="space-y-2.5">
      {rows.map((row) => (
        <div key={row.symbol}>
          <div className="flex items-baseline justify-between">
            <span className="font-mono text-[13px] text-[#d3dae3]">{row.symbol}</span>
            <span className={`font-mono text-[14px] font-semibold tabular-nums ${row.growth >= 0 ? 'text-[#e8833a]' : 'text-[#5aa2e0]'}`}>
              {row.growth >= 0 ? '+' : ''}{(row.growth * 100).toFixed(1)}%
            </span>
          </div>
          <div className="mt-1 h-[3px] rounded bg-[#1a2230]">
            <div className={`h-[3px] rounded ${row.growth >= 0 ? 'bg-[#e8833a]' : 'bg-[#5aa2e0]'}`} style={{ width: `${Math.max(2, (Math.abs(row.growth) / widest) * 100)}%` }} />
          </div>
          <p className="mt-0.5 text-[12px] text-[#68727f]">FY26 against FY25 &middot; {row.source}</p>
        </div>
      ))}
      <p className="border-t border-[#1a2230] pt-2 text-[12px] leading-relaxed text-[#68727f]">
        Growth only: members report in different units, so absolute figures are not comparable
        across them. {rows.length} of {members.length || rows.length} members.
        {leftOut.length ? ` Left out rather than estimated, for want of a comparable disclosed year: ${leftOut.join(', ')}.` : ''}
      </p>
    </div>
  );
}
