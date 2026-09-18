import React from 'react';
import { fetchExitability } from '@/lib/indiaAiApi';
import { ALL_SUBS, LAYER_LABEL, SUB_LABEL, rupeesCr } from '@/lib/indiaAiSummary';
import { impliedGrowth, runModel, valueOf } from '@/lib/indiaAiEstimates';
import {
  aiMateriality, capitalQuality, earningsMomentum, evidenceConfidence, expectationLoad,
} from '@/lib/indiaAiFactors';

/**
 * India AI Infrastructure Monitor: the dashboard view of the page.
 *
 * Built only from AGI's own data: the evidence record, filed figures, AGI's
 * market value and AGI's estimate models. Every figure carries a provenance
 * tag - D disclosed by the company, I AGI arithmetic on disclosed figures,
 * A an AGI estimate - so fact and analysis cannot be confused. There is no
 * consensus tag because AGI has no consensus source, and no broker figure
 * appears anywhere in this view.
 */

const TAGS = {
  D: ['Disclosed', 'Stated by the company in its own filing, release, presentation or call.', 'text-[#4ade80] border-[#2f5d3f]'],
  I: ['AGI arithmetic', 'Calculated by AGI from disclosed figures (for example close x filed shares, or order book / quarterly revenue). No assumption involved.', 'text-[#8fb4d8] border-[#2a4a66]'],
  A: ['AGI estimate', 'Depends on AGI assumptions (growth, margin, exit multiple). See the AGI estimates section for every input.', 'text-[#f0a060] border-[#7a5a2e]'],
};
function Tag({ t }) {
  const [label, why, tone] = TAGS[t];
  return (
    <abbr title={`${label}: ${why}`} className={`ml-1 inline-block rounded border px-[3px] text-[9px] font-semibold leading-[13px] no-underline ${tone}`}>
      {t}
    </abbr>
  );
}

const BAND_TONE = {
  high: 'bg-[#10261a] text-[#4ade80]', strong: 'bg-[#10261a] text-[#4ade80]',
  medium: 'bg-[#1a2230] text-[#8fb4d8]', moderate: 'bg-[#1a2230] text-[#8fb4d8]',
  low: 'bg-[#2a2110] text-[#d9a94a]', weak: 'bg-[#2b1414] text-[#f87171]', 'capital-hungry': 'bg-[#2a2110] text-[#d9a94a]',
  'very high': 'bg-[#2b1414] text-[#f87171]', 'stated only': 'bg-[#1a2230] text-[#9aa5b3]', 'not measurable': 'bg-[#161c26] text-[#68727f]',
};
const Band = ({ b }) => <span className={`whitespace-nowrap rounded px-1.5 py-[1px] text-[11px] ${BAND_TONE[b] || 'bg-[#161c26] text-[#9aa5b3]'}`}>{b}</span>;

const TIER_LABEL = { SEGMENT_REPORTED: 'Audited segment', MANAGEMENT_DISCLOSED: 'Company-stated', NOT_ATTRIBUTABLE: 'Linked, not sized' };
const TIER_TONE = { SEGMENT_REPORTED: 'text-[#4ade80]', MANAGEMENT_DISCLOSED: 'text-[#8fb4d8]', NOT_ATTRIBUTABLE: 'text-[#d9a94a]' };
const HARD = new Set(['order', 'capex', 'operating']);
const KIND = { order: 'Order', capex: 'Committed capex', operating: 'Operating disclosure' };

const median = (xs) => {
  const v = xs.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return null;
  const m = Math.floor(v.length / 2);
  return v.length % 2 ? v[m] : (v[m - 1] + v[m]) / 2;
};
const pct = (v, d = 0) => (Number.isFinite(v) ? `${v >= 0 ? '' : '−'}${Math.abs(v * 100).toFixed(d)}%` : '—');
const signedPct = (v, d = 0) => (Number.isFinite(v) ? `${v >= 0 ? '+' : '−'}${Math.abs(v * 100).toFixed(d)}%` : '—');
const cr = (v) => (Number.isFinite(v) ? rupeesCr(v) : '—');

/** Everything AGI holds about one member, in one record. */
function buildRecords({ universe, operating, estimates, marketValue, stage3, scoring, exit }) {
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
  return (universe?.members || []).map((m) => {
    const model = models[m.symbol];
    const runs = model ? Object.fromEntries(['low', 'base', 'high'].map((s) => [s, runModel(model, { scenario: s })])) : null;
    const row = sc[m.symbol] || {};
    const pat = model ? valueOf(model.params?.patFY26Cr, 'base') : row.patFY26 ?? null;
    const ebitda = model ? valueOf(model.params?.totalEbitdaFY26Cr, 'base') : null;
    const book = books[m.symbol];
    const evidence = [...(m.admittedOn || []), ...(m.supportingEvidence || [])].filter((e) => HARD.has(e.kind));
    const q1 = row.revenueQ1FY27 && row.revenueQ1FY26 ? row.revenueQ1FY27 / row.revenueQ1FY26 - 1 : null;
    return {
      m, model, runs, row, pat, ebitda, book, cap: caps[m.symbol], liq: liq[m.symbol],
      shares: shares[m.symbol] || [], targets: targets[m.symbol] || [], evidence,
      latest: evidence.map((e) => e.date).filter(Boolean).sort().at(-1) || null,
      mv: mv[m.symbol] ?? null, stage3: s3[m.symbol] || null, q1,
      cover: book?.backlogCr && book?.quarterRevenueCr ? book.backlogCr / book.quarterRevenueCr : null,
      implied: impliedGrowth({ marketValueCr: mv[m.symbol], patCr: pat, exitMultiple, years }),
      factors: {
        materiality: aiMateriality({ model, statedShare: shares[m.symbol]?.[0]?.value }),
        evidence: evidenceConfidence(m),
        momentum: earningsMomentum(row),
        capital: capitalQuality(row),
        expectation: expectationLoad({ marketValueCr: mv[m.symbol], patCr: pat, exitMultiple, years }),
      },
    };
  });
}

function Kpi({ label, value, sub, tag }) {
  return (
    <div className="rounded-md border border-[#1e2634] bg-[#0c1017] px-3 py-2.5">
      <p className="text-[11px] uppercase tracking-wider text-[#7d8894]">{label}</p>
      <p className="mt-0.5 font-mono text-[20px] font-semibold tabular-nums text-[#f1f5f9]">{value}{tag ? <Tag t={tag} /> : null}</p>
      <p className="text-[11px] leading-snug text-[#68727f]">{sub}</p>
    </div>
  );
}

function StackMap({ records, filter, setFilter }) {
  const layers = ['power', 'data_centre', 'semiconductor', 'infrastructure'];
  return (
    <section aria-labelledby="stack-h" className="rounded-md border border-[#1e2634] bg-[#0c1017] p-3.5">
      <div className="flex flex-wrap items-baseline gap-2">
        <h3 id="stack-h" className="text-[15px] font-semibold text-[#f1f5f9]">AI infrastructure stack</h3>
        <span className="text-[12px] text-[#7d8894]">click a sub-layer to filter the matrix · medians over members with the figure</span>
        {filter ? <button type="button" onClick={() => setFilter(null)} className="ml-auto rounded text-[12px] text-[#8fb4d8] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#e8833a]">Clear filter</button> : null}
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {layers.map((layer) => {
          const inLayer = records.filter((r) => r.m.layer === layer);
          return (
            <div key={layer} className="rounded border border-[#1a2230] p-2.5">
              <button
                type="button"
                onClick={() => setFilter({ layer })}
                aria-pressed={filter?.layer === layer && !filter?.sub}
                className="flex w-full items-baseline justify-between rounded text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#e8833a]"
              >
                <span className="text-[14px] font-semibold text-[#e3e8ef]">{LAYER_LABEL[layer]}</span>
                <span className="font-mono text-[12px] text-[#7d8894]">{inLayer.length}</span>
              </button>
              <ul className="mt-2 space-y-1.5">
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
                        className={`w-full rounded px-1.5 py-1 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#e8833a] ${active ? 'bg-[#1c2534]' : 'hover:bg-[#141b26]'}`}
                      >
                        <span className="flex items-baseline justify-between text-[13px]">
                          <span className="text-[#c7cfda]">{SUB_LABEL[sub]}</span>
                          <span className="font-mono text-[12px] text-[#7d8894]">{rs.length || 'empty'}</span>
                        </span>
                        {rs.length ? (
                          <span className="mt-0.5 block text-[11px] leading-snug text-[#68727f]">
                            revenue {signedPct(g)}<Tag t="I" /> · price needs {x === null ? '—' : x <= 0 ? 'none' : `${pct(x)}/yr`}<Tag t="A" /> · {sized}/{rs.length} sized<Tag t="D" />
                          </span>
                        ) : <span className="mt-0.5 block text-[11px] text-[#4b5563]">nothing disclosed beyond intent</span>}
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

const VIEWS = [['investment', 'Investment'], ['evidence', 'Evidence'], ['financials', 'Financials'], ['estimates', 'Estimates']];

function Matrix({ records, others, filter, view, setView, status, setStatus, open }) {
  const shown = records.filter((r) => !filter || (r.m.layer === filter.layer && (!filter.sub || (r.m.subLayers || []).includes(filter.sub))))
    .sort((a, b) => (b.mv || 0) - (a.mv || 0));
  const cols = {
    investment: ['Evidence', 'AI materiality', 'Revenue y/y', 'Market value', 'Price needs', 'Capital quality', '₹100 cr fits'],
    evidence: ['Exposure tier', 'Hard items', 'Latest', 'Stated AI/DC figure', 'Last verified'],
    financials: ['FY26 revenue', 'FY26 EBITDA', 'FY26 profit', 'FCF / revenue', 'ROCE', 'Order book', 'Cover'],
    estimates: ['Model', 'FY29 AI/DC revenue (low · base · high)', 'FY29 AI/DC EBITDA', 'vs FY26 EBITDA', 'Waits for'],
  }[view];
  const cell = (r) => {
    const f = r.factors;
    if (view === 'investment') {
      return [
        <span className={TIER_TONE[r.m.attribution]}>{TIER_LABEL[r.m.attribution] || '—'}<Tag t="D" /></span>,
        <><Band b={f.materiality.band} />{f.materiality.value ? <span className="ml-1 text-[#9aa5b3]">{f.materiality.value}</span> : null}</>,
        r.q1 !== null ? <>{signedPct(r.q1)}<Tag t="I" /></> : '—',
        r.mv !== null ? <>{cr(r.mv)}<Tag t="I" /></> : '—',
        r.implied ? (r.implied.cagr <= 0 ? <>none: under 30x<Tag t="A" /></> : <>{pct(r.implied.cagr)}/yr<Tag t="A" /></>) : '—',
        <Band b={f.capital.band} />,
        r.liq ? (r.liq.meetsTarget ? 'yes' : `up to ${cr(r.liq.maxExecutablePosition / 1e7)}`) : '…',
      ];
    }
    if (view === 'evidence') {
      return [
        <span className={TIER_TONE[r.m.attribution]}>{TIER_LABEL[r.m.attribution] || '—'}</span>,
        String(r.evidence.length),
        r.latest || '—',
        r.shares[0] ? <span title={r.shares[0].quote}>{r.shares[0].value}<Tag t="D" /></span> : <span className="text-[#4b5563]">not stated</span>,
        r.m.evidenceReadOn || r.m.admittedOn?.[0]?.date || '—',
      ];
    }
    if (view === 'financials') {
      const fcf = r.row.revenueFY26 && Number.isFinite(r.row.cfoFY26) && Number.isFinite(r.row.capexFY26)
        ? (r.row.cfoFY26 - r.row.capexFY26 - (r.row.capexIntangiblesFY26 || 0)) / r.row.revenueFY26 : null;
      const roce = r.row.statedRoceFY26 ?? (r.row.ebitFY26 && r.row.capitalEmployedFY26 ? r.row.ebitFY26 / r.row.capitalEmployedFY26 : null);
      return [
        r.row.revenueFY26 ? <>{cr(r.row.revenueFY26)}<Tag t="D" /></> : '—',
        r.ebitda ? <>{cr(r.ebitda)}<Tag t="D" /></> : '—',
        r.pat ? <>{cr(r.pat)}<Tag t="D" /></> : '—',
        fcf !== null ? <>{signedPct(fcf)}<Tag t="I" /></> : '—',
        roce !== null ? <>{pct(roce)}<Tag t={r.row.statedRoceFY26 ? 'D' : 'I'} /></> : '—',
        r.book?.backlogCr ? <>{cr(r.book.backlogCr)}<Tag t="D" /></> : '—',
        r.cover !== null ? <>{r.cover.toFixed(1)} q<Tag t="I" /></> : '—',
      ];
    }
    const run = r.runs;
    return [
      r.model ? r.model.title : <span className="text-[#4b5563]">not modelled</span>,
      run?.base.ok ? <>{[run.low, run.base, run.high].map((x) => (x.ok ? cr(x.aiRevenueCr) : '—')).join(' · ')}<Tag t="A" /></> : '—',
      run?.base.ok ? <>{cr(run.base.aiEbitdaCr)}<Tag t="A" /></> : '—',
      run?.base.ok && run.base.materiality != null ? <>{pct(run.base.materiality)}<Tag t="A" /></> : '—',
      run && !run.base.ok ? run.base.missing.map((k) => r.model.params?.[k]?.label || k).join(', ') : '—',
    ];
  };
  return (
    <section aria-labelledby="matrix-h" className="rounded-md border border-[#1e2634] bg-[#0c1017]">
      <header className="flex flex-wrap items-center gap-2 border-b border-[#1a2230] px-3.5 py-2.5">
        <h3 id="matrix-h" className="text-[15px] font-semibold text-[#f1f5f9]">Intelligence matrix</h3>
        {filter ? <span className="text-[12px] text-[#f0a060]">{LAYER_LABEL[filter.layer]}{filter.sub ? ` · ${SUB_LABEL[filter.sub]}` : ''}</span> : null}
        <span className="ml-auto flex flex-wrap gap-1" role="group" aria-label="View">
          {VIEWS.map(([k, label]) => (
            <button key={k} type="button" onClick={() => setView(k)} aria-pressed={view === k}
              className={`rounded px-2 py-0.5 text-[12px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#e8833a] ${view === k ? 'bg-[#e8833a] text-[#0a0e14]' : 'border border-[#2a3444] text-[#9aa5b3]'}`}>{label}</button>
          ))}
        </span>
      </header>
      <div className="flex flex-wrap gap-1 px-3.5 pt-2" role="group" aria-label="Status">
        {[['members', `Members (${records.length})`], ['held', `Held (${others.held.length})`], ['excluded', `Excluded (${others.excluded.length})`]].map(([k, label]) => (
          <button key={k} type="button" onClick={() => setStatus(k)} aria-pressed={status === k}
            className={`rounded px-2 py-0.5 text-[12px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#e8833a] ${status === k ? 'bg-[#1c2534] text-[#e3e8ef]' : 'text-[#7d8894]'}`}>{label}</button>
        ))}
      </div>
      <div className="overflow-x-auto p-3.5 pt-2">
        {status === 'members' ? (
          <table className="w-full min-w-[980px] text-[12px]">
            <thead className="sticky top-0 bg-[#0c1017]">
              <tr className="text-left text-[11px] uppercase tracking-wider text-[#68727f]">
                <th className="py-1.5 pr-2 font-medium">Company</th>
                <th className="py-1.5 pr-2 font-medium">Layer</th>
                {cols.map((c) => <th key={c} className="py-1.5 pr-2 font-medium">{c}</th>)}
              </tr>
            </thead>
            <tbody>
              {shown.map((r) => (
                <tr
                  key={r.m.symbol}
                  onClick={() => open(r.m.symbol)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(r.m.symbol); } }}
                  tabIndex={0}
                  role="button"
                  aria-label={`Open ${r.m.symbol} research drawer`}
                  className="cursor-pointer border-t border-[#1a2230] align-top hover:bg-[#121925] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-[#e8833a]"
                >
                  <td className="py-1.5 pr-2"><span className="font-mono text-[#e3e8ef]">{r.m.symbol}</span><span className="block text-[11px] text-[#68727f]">{r.m.name}</span></td>
                  <td className="py-1.5 pr-2 text-[#9aa5b3]">{LAYER_LABEL[r.m.layer]}<span className="block text-[11px] text-[#68727f]">{(r.m.subLayers || []).map((s) => SUB_LABEL[s] || s).join(' + ')}</span></td>
                  {cell(r).map((c, i) => <td key={i} className="py-1.5 pr-2 text-[#c7cfda]">{c}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <ul className="space-y-2">
            {others[status].map((c) => (
              <li key={c.symbol} className="border-t border-[#1a2230] pt-2 text-[13px]">
                <span className="font-mono text-[#e3e8ef]">{c.symbol}</span> <span className="text-[#7d8894]">{c.name}</span>
                <p className="mt-0.5 text-[12px] leading-relaxed text-[#9aa5b3]">{c.note || c.reason}</p>
              </li>
            ))}
          </ul>
        )}
        <p className="mt-2 text-[11px] leading-relaxed text-[#68727f]">
          <Tag t="D" /> disclosed · <Tag t="I" /> AGI arithmetic on disclosed figures · <Tag t="A" /> AGI estimate (assumptions in AGI estimates). Hover a tag for its meaning. No consensus or broker figures are used. Click a row for the research drawer.
        </p>
      </div>
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
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-labelledby="drawer-h">
      <button type="button" aria-label="Close" onClick={onClose} className="flex-1 bg-black/50" />
      <div className="h-full w-full max-w-[560px] overflow-y-auto border-l border-[#1e2634] bg-[#0a0e14] p-4">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 id="drawer-h" className="font-mono text-[18px] font-semibold text-[#f1f5f9]">{m.symbol}</h3>
            <p className="text-[13px] text-[#9aa5b3]">{m.name} · {LAYER_LABEL[m.layer]} · {(m.subLayers || []).map((s) => SUB_LABEL[s] || s).join(' + ')}</p>
            <p className={`mt-0.5 text-[12px] ${TIER_TONE[m.attribution]}`}>{TIER_LABEL[m.attribution]} · member since {m.membershipStart}</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className="rounded border border-[#2a3444] px-2 py-0.5 text-[12px] text-[#9aa5b3] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#e8833a]">Close</button>
        </div>

        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3">
          {[
            ['Stated AI/DC figure', r.shares[0]?.value, 'D'],
            ['Market value', r.mv !== null ? cr(r.mv) : null, 'I'],
            ['Order book', r.book?.backlogCr ? cr(r.book.backlogCr) : null, 'D'],
            ['Order cover', r.cover !== null ? `${r.cover.toFixed(1)} quarters` : null, 'I'],
            ['FY26 EBITDA', r.ebitda ? cr(r.ebitda) : null, 'D'],
            ['FY26 profit', r.pat ? cr(r.pat) : null, 'D'],
          ].map(([k, v, t]) => (
            <div key={k} className="rounded border border-[#1a2230] px-2 py-1.5">
              <p className="text-[10px] uppercase tracking-wider text-[#68727f]">{k}</p>
              <p className="text-[13px] text-[#e3e8ef]">{v || '—'}{v ? <Tag t={t} /> : null}</p>
            </div>
          ))}
        </div>

        <h4 className="mt-4 text-[12px] uppercase tracking-[0.12em] text-[#7d8894]">Five factors</h4>
        <dl className="mt-1.5 space-y-1">
          {[['AI materiality', f.materiality], ['Evidence', f.evidence], ['Momentum', f.momentum], ['Capital quality', f.capital], ['Expectation load', f.expectation]].map(([k, x]) => (
            <div key={k} className="grid grid-cols-[120px_1fr] gap-2 text-[12px]">
              <dt className="text-[#9aa5b3]">{k}</dt>
              <dd><Band b={x.band} />{x.value ? <span className="ml-1.5 text-[#c7cfda]">{x.value}</span> : null}</dd>
            </div>
          ))}
        </dl>

        <h4 className="mt-4 text-[12px] uppercase tracking-[0.12em] text-[#7d8894]">Evidence</h4>
        <ul className="mt-1.5 space-y-2">
          {[...(m.admittedOn || []), ...(m.supportingEvidence || [])].map((e, i) => (
            <li key={i} className="border-l-2 border-[#2f5d3f] pl-2.5">
              <p className="text-[11px] text-[#7d8894]">{KIND[e.kind] || e.kind} · {e.document} · {e.date}{e.page ? ` · p. ${e.page}` : ''}</p>
              <p className="text-[13px] leading-relaxed text-[#c7cfda]">&ldquo;{e.excerpt}&rdquo;</p>
            </li>
          ))}
        </ul>
        {m.exposureNote ? <p className="mt-2 text-[12px] leading-relaxed text-[#9aa5b3]">{m.exposureNote}</p> : null}
        {m.parentGroupNote ? <p className="mt-2 rounded border border-[#3a3222] bg-[#12100c] px-2 py-1.5 text-[12px] leading-relaxed text-[#c9b699]"><span className="font-semibold">Parent group, not this company: </span>{m.parentGroupNote}</p> : null}

        <h4 className="mt-4 text-[12px] uppercase tracking-[0.12em] text-[#f0a060]">AGI estimate</h4>
        {r.model ? (
          <div className="mt-1.5 rounded border border-dashed border-[#7a5a2e] bg-[#0f0d0a] p-2.5 text-[12px] text-[#c9b699]">
            <p className="text-[#f5d9b0]">{r.model.title}</p>
            {r.runs.base.ok ? (
              <table className="mt-1.5 w-full">
                <thead><tr className="text-left text-[10px] uppercase text-[#8a7658]"><th className="font-medium">FY29</th><th className="text-right font-medium">Low</th><th className="text-right font-medium">Base</th><th className="text-right font-medium">High</th></tr></thead>
                <tbody>
                  <tr><td>AI/DC revenue</td>{['low', 'base', 'high'].map((s) => <td key={s} className="text-right font-mono">{r.runs[s].ok ? cr(r.runs[s].aiRevenueCr) : '—'}</td>)}</tr>
                  <tr><td>AI/DC EBITDA</td>{['low', 'base', 'high'].map((s) => <td key={s} className="text-right font-mono">{r.runs[s].ok ? cr(r.runs[s].aiEbitdaCr) : '—'}</td>)}</tr>
                  <tr><td>vs FY26 EBITDA</td>{['low', 'base', 'high'].map((s) => <td key={s} className="text-right font-mono">{r.runs[s].ok && r.runs[s].materiality != null ? pct(r.runs[s].materiality) : '—'}</td>)}</tr>
                </tbody>
              </table>
            ) : <p className="mt-1 text-[#d9a94a]">Waits for: {r.runs.base.missing.map((k) => r.model.params?.[k]?.label || k).join(', ')}.</p>}
            <p className="mt-2 text-[10px] uppercase tracking-wider text-[#8a7658]">Assumptions (base; range)</p>
            <ul className="mt-0.5 space-y-0.5">
              {params.map(([k, p]) => (
                <li key={k}>{p.label}: {p.value === null ? 'not set' : p.unit === 'pct' ? pct(p.value, 1) : p.value}{p.low != null ? ` (${p.unit === 'pct' ? `${pct(p.low, 1)}–${pct(p.high, 1)}` : `${p.low}–${p.high}`})` : ''}</li>
              ))}
            </ul>
          </div>
        ) : <p className="mt-1.5 text-[12px] text-[#68727f]">Not modelled: AGI has no defensible anchor for this company&rsquo;s AI economics yet.</p>}

        <h4 className="mt-4 text-[12px] uppercase tracking-[0.12em] text-[#7d8894]">Watch</h4>
        <ul className="mt-1.5 list-disc space-y-1 pl-4 text-[12px] leading-relaxed text-[#9aa5b3]">
          {r.targets.map((t) => <li key={t.target}>{t.target} <span className="text-[#68727f]">({t.source}; a company target)</span></li>)}
          {r.runs && !r.runs.base.ok ? <li>A disclosed {r.runs.base.missing.map((k) => (r.model.params?.[k]?.label || k).toLowerCase()).join(' and ')} would let the estimate run.</li> : null}
          {m.note ? <li>{m.note}</li> : null}
          {!r.targets.length && !m.note && !(r.runs && !r.runs.base.ok) ? <li>Next quarter&rsquo;s results: order book, stated AI/DC figures.</li> : null}
        </ul>

        <button type="button" onClick={onResearch} className="mt-4 rounded text-[13px] text-[#8fb4d8] hover:text-[#e3e8ef] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#e8833a]">
          Open the full research page &rarr;
        </button>
      </div>
    </div>
  );
}

export default function MonitorDashboard({
  universe, live, history, marketValue, stage3, estimates, operating, scoring, onResearch,
}) {
  const [exit, setExit] = React.useState(null);
  const [filter, setFilter] = React.useState(null);
  const [view, setView] = React.useState('investment');
  const [status, setStatus] = React.useState('members');
  const [drawer, setDrawer] = React.useState(null);
  React.useEffect(() => {
    let cancelled = false;
    fetchExitability().then((p) => { if (!cancelled) setExit(p); }).catch(() => {});
    return () => { cancelled = true; };
  }, []);
  if (!universe?.members) return <p className="py-10 text-[13px] text-[#68727f]">Loading the universe.</p>;
  const records = buildRecords({ universe, operating, estimates, marketValue, stage3, scoring, exit });
  const others = { held: universe.candidates || [], excluded: universe.excluded || [] };
  const read = records.length + others.held.length + others.excluded.length;
  const sized = records.filter((r) => r.m.attribution && r.m.attribution !== 'NOT_ATTRIBUTABLE').length;
  const segment = records.filter((r) => r.m.attribution === 'SEGMENT_REPORTED').length;
  const growth = median(records.map((r) => r.q1));
  const withGrowth = records.filter((r) => r.q1 !== null).length;
  const hardItems = records.reduce((n, r) => n + r.evidence.length, 0);
  const index = live?.index;
  const lastTrade = live?.quality?.closed && live?.quality?.session_last;
  const current = drawer ? records.find((r) => r.m.symbol === drawer) : null;
  return (
    <div className="space-y-4">
      <header>
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#e8833a]">AGI Investment Intelligence</p>
        <h1 className="mt-1 text-[28px] font-semibold leading-tight tracking-tight sm:text-[34px]">India AI Infrastructure Monitor</h1>
        <p className="text-[14px] text-[#8b95a3]">
          {records.length} listed companies admitted on their own filings, from {read} read, across power, data centres, semiconductors and EPC
          {marketValue?.closeDate ? ` · prices to ${marketValue.closeDate}` : ''} · evidence read {universe.version || ''}
        </p>
      </header>

      <div className="grid grid-cols-2 gap-2 md:grid-cols-3 xl:grid-cols-6">
        <Kpi label="Admitted" value={records.length} sub={`of ${read} read; ${(universe.reportedList || []).length} on the reported list`} />
        <Kpi label="Market value" value={marketValue?.byLayer ? rupeesCr(marketValue.byLayer.totalCr) : '—'} sub="close x filed shares; whole companies" tag="I" />
        <Kpi label="AI/DC business sized" value={`${sized} / ${records.length}`} sub={`${segment} audited segment, ${sized - segment} company-stated`} tag="D" />
        <Kpi label={lastTrade ? 'Basket, last session' : 'Basket today'} value={index?.status === 'ok' ? signedPct(index.return_pp / 100, 2) : '—'} sub={index?.relative ? `vs Nifty 50 ${signedPct(index.relative.excess_pp / 100, 2)} · equal weight` : 'not priced'} tag="D" />
        <Kpi label="Revenue growth, median" value={growth !== null ? signedPct(growth) : '—'} sub={`latest quarter y/y · ${withGrowth} members with filed figures`} tag="I" />
        <Kpi label="Hard evidence" value={hardItems} sub="filed orders, capex and operating disclosures" tag="D" />
      </div>

      <StackMap records={records} filter={filter} setFilter={setFilter} />

      <Matrix records={records} others={others} filter={filter} view={view} setView={setView} status={status} setStatus={setStatus} open={setDrawer} />

      {current ? <Drawer r={current} onClose={() => setDrawer(null)} onResearch={() => { setDrawer(null); onResearch(); }} /> : null}
    </div>
  );
}
