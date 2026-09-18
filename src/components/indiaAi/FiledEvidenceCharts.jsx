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
      <h3 className="text-[13px] font-semibold tracking-tight text-[#f1f5f9]">{title}</h3>
      {note ? <span className="text-[11px] text-[#7d8894]">{note}</span> : null}
    </header>
    <div className="p-3.5">{children}</div>
    {source ? (
      <p className="border-t border-[#1a2230] px-3.5 py-2 text-[10px] leading-relaxed text-[#68727f]">{source}</p>
    ) : null}
  </section>
);

/**
 * Whether each member's theme exposure can be sized from its own accounts.
 *
 * The most consequential thing five filings produced, and it is a negative
 * result: one member reports the theme as a segment. The others are admitted
 * on sound, dated, first-party evidence and still cannot be attributed,
 * because a joint venture sits outside consolidation, or a single reporting
 * segment absorbs the line, or no segment exists at all.
 */
export function ExposureAttribution({ companies }) {
  const rows = Object.entries(companies || {}).map(([symbol, one]) => ({
    symbol,
    attributable: one.exposureAttributable ?? null,
    // A line written to stand alone here, rather than the first sentence of a
    // longer note cut mid-argument.
    verdict: one.exposureVerdict || String(one.exposureFinding || '').split('. ')[0],
  }));
  if (!rows.length) return null;
  const yes = rows.filter((r) => r.attributable === true).length;
  const no = rows.filter((r) => r.attributable === false).length;
  const open = rows.length - yes - no;
  const sorted = [...rows].sort((a, b) => Number(b.attributable === true) - Number(a.attributable === true));

  return (
    <Panel
      title="Can the exposure be sized?"
      note={`${yes} of ${rows.length} from the accounts`}
      source="Read from each company's FY2025-26 filing. A member counts as attributable only where the theme is a reported operating segment under Ind AS 108."
    >
      <div className="mb-3 flex h-2 overflow-hidden rounded-full bg-[#141b26]">
        <div className="bg-[#4ade80]" style={{ width: `${(yes / rows.length) * 100}%` }} />
        <div className="bg-[#3a4453]" style={{ width: `${(no / rows.length) * 100}%` }} />
        <div className="bg-[#d9a94a]/50" style={{ width: `${(open / rows.length) * 100}%` }} />
      </div>
      <ul className="space-y-2">
        {sorted.map((row) => (
          <li key={row.symbol} className="flex items-start gap-2.5">
            <span
              className={`mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full ${
                row.attributable === true ? 'bg-[#4ade80]'
                  : row.attributable === false ? 'bg-[#3a4453]' : 'bg-[#d9a94a]'}`}
              aria-hidden
            />
            <span className="min-w-0">
              <span className="font-mono text-[11px] text-[#d3dae3]">{row.symbol}</span>
              <span className="ml-2 text-[10px] uppercase tracking-wider text-[#68727f]">
                {row.attributable === true ? 'segment reported'
                  : row.attributable === false ? 'not attributable' : 'unresolved'}
              </span>
              <span className="mt-0.5 block text-[11px] leading-relaxed text-[#8b95a3]">
                {row.verdict}
              </span>
            </span>
          </li>
        ))}
      </ul>
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
        <span className="text-[11px] text-[#c7cfda]">{label}</span>
        <span className="font-mono text-[13px] font-semibold tabular-nums" style={{ color: tone }}>
          {(share * 100).toFixed(1)}%
        </span>
      </div>
      <div className="mt-1 h-2.5 rounded bg-[#141b26]">
        <div className="h-2.5 rounded" style={{ width: `${Math.max(1.5, share * 100)}%`, background: tone }} />
      </div>
      <p className="mt-1 text-[10px] tabular-nums text-[#68727f]">
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
      <p className="mt-3 border-t border-[#1a2230] pt-2.5 text-[11px] leading-relaxed text-[#8b95a3]">
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
              <p className="font-mono text-[11px] text-[#d3dae3]">{row.symbol}</p>
              <div className="mt-1.5 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-[78px] shrink-0 text-[10px] text-[#68727f]">capex out</span>
                  <div className="h-2.5 flex-1 rounded bg-[#141b26]">
                    <div className="h-2.5 rounded bg-[#e8833a]" style={{ width: `${(Math.abs(row.capex) / scale) * 100}%` }} />
                  </div>
                  <span className="w-[96px] shrink-0 text-right font-mono text-[10px] tabular-nums text-[#c7cfda]">{fmt(row.capex)}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-[78px] shrink-0 text-[10px] text-[#68727f]">cash from ops</span>
                  <div className="h-2.5 flex-1 rounded bg-[#141b26]">
                    <div
                      className={`h-2.5 rounded ${row.cfo < 0 ? 'bg-[#a13a2b]' : 'bg-[#4ade80]'}`}
                      style={{ width: `${(Math.abs(row.cfo) / scale) * 100}%` }}
                    />
                  </div>
                  <span className={`w-[96px] shrink-0 text-right font-mono text-[10px] tabular-nums ${row.cfo < 0 ? 'text-[#f87171]' : 'text-[#4ade80]'}`}>
                    {fmt(row.cfo)}
                  </span>
                </div>
              </div>
              {row.cfo < 0 ? (
                <p className="mt-1.5 text-[10px] leading-relaxed text-[#8b95a3]">
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
          <li key={kind} className="flex items-center gap-2 text-[11px]">
            <span className="h-1.5 w-1.5 rounded-full" style={{ background: TONE[kind] || '#2c3542' }} aria-hidden />
            <span className="text-[#c7cfda]">{LABEL[kind] || kind}</span>
            <span className="ml-auto font-mono tabular-nums text-[#8b95a3]">{n}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}
