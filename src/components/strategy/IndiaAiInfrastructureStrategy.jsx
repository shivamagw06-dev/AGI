import React from 'react';
import { Link } from 'react-router-dom';
import {
  fetchEstimates, fetchMarketValue, fetchMateriality, fetchOperatingData, fetchScoring, fetchUniverse,
} from '@/lib/indiaAiApi';
import { MATERIALITY_TIER } from '@/lib/indiaAiMateriality';
import { buildRecords, filedRatios } from '@/lib/indiaAiRecords';
import {
  FIVE_METRICS, NON_MEMBER_FILED, OUTSIDE, STRATEGY_ASOF, STRATEGY_FACTORS, STRATEGY_ROWS, STRUCTURES,
} from './indiaAiInfrastructureContent';
import { Band, FOCUS, Tag, dateLabel, pct, signedPct } from './strategyUi';

/**
 * India AI Infrastructure: the strategy table and its reading, on the white
 * strategy page. The editorial columns are the portfolio owner's; the
 * financial columns are computed live from the India AI monitor's data (filed
 * results and AGI market value), the same records the monitor itself uses.
 */

const RATING_TONE = {
  'Very High': 'bg-[#e3f4ea] text-[#17693a]',
  High: 'bg-[#eef8f2] text-[#1f7a45]',
  'Medium-High': 'bg-[#eef1f5] text-[#34404f]',
  Medium: 'bg-[#f3f4f6] text-[#5b6573]',
};
const statusTone = (st) => (/Exception/.test(st) ? 'border border-dashed border-[#d9a36a] text-[#9a520c]'
  : /High Risk/.test(st) ? 'bg-[#fdecec] text-[#b42318]'
    : /Emerging|Optionality|Execution/.test(st) ? 'bg-[#e8f1fb] text-[#1f5f9e]'
      : 'bg-[#0f1720] text-white');

function useIndiaAiData() {
  const [data, setData] = React.useState({});
  React.useEffect(() => {
    let cancelled = false;
    const load = (key, fn) => fn().then((v) => { if (!cancelled) setData((d) => ({ ...d, [key]: v })); }).catch(() => {});
    load('universe', fetchUniverse);
    load('marketValue', fetchMarketValue);
    load('scoring', fetchScoring);
    load('estimates', fetchEstimates);
    load('operating', fetchOperatingData);
    load('materiality', fetchMateriality);
    return () => { cancelled = true; };
  }, []);
  return data;
}

export default function IndiaAiInfrastructureStrategy({ monitor }) {
  const d = useIndiaAiData();
  const records = d.universe?.members ? buildRecords(d) : [];
  const bySym = Object.fromEntries(records.map((r) => [r.m.symbol, r]));
  const loading = !d.universe || !d.scoring;
  const priced = Boolean(d.marketValue?.rows);
  const netweb = bySym.NETWEB;
  const cols = [
    ['Stock'], ['AI layer'], ['AI materiality'], ['Hard evidence / key KPI'],
    ['Revenue growth, latest qtr', 'I'], ['Capex / sales, FY26', 'I'], ['FCF / sales, FY26', 'I'], ['P/E, FY26 profit', 'I'],
    ['Capital quality', 'I'], ['Expectation load', 'A'], ['AGI status'],
  ];
  const wait = <span className="text-[#a0a8b3]">…</span>;
  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <p className="text-[14px] text-[#5b6573]">
          {STRATEGY_ROWS.length} names · strategy as of {dateLabel(STRATEGY_ASOF)}
          {d.marketValue?.closeDate ? ` · prices to ${dateLabel(d.marketValue.closeDate)}` : ''}
        </p>
        <Link
          to={monitor.to}
          className={`inline-flex items-center gap-2 rounded-lg bg-[#0f1720] px-5 py-2.5 text-[15px] font-semibold text-white shadow-sm hover:bg-[#26303d] ${FOCUS}`}
        >
          {monitor.label}<span aria-hidden="true">&rarr;</span>
        </Link>
      </div>

      <div className="mt-4 overflow-x-auto rounded-xl border border-[#e5e8ec]">
        <table className="w-full min-w-[1380px] text-[14px]">
          <thead className="bg-[#f7f8fa]">
            <tr className="text-left text-[12px] font-semibold text-[#5b6573]">
              {cols.map(([h, tag]) => (
                <th key={h} scope="col" className="border-b border-[#e5e8ec] px-4 py-3 align-bottom">{h}{tag ? <Tag t={tag} /> : null}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {STRATEGY_ROWS.map((row) => {
              const rec = bySym[row.symbol] || null;
              const x = filedRatios(rec, NON_MEMBER_FILED[row.symbol]);
              const member = row.member !== false;
              return (
                <tr key={row.symbol} className="border-b border-[#eef0f3] align-top last:border-b-0 hover:bg-[#fafbfc]">
                  <td className="px-4 py-3.5">
                    <span className="whitespace-nowrap font-semibold text-[#0f1720]">{row.name}</span>
                    <span className="block font-mono text-[12px] text-[#8a93a0]">{row.symbol}{member ? '' : ' · not an index member'}</span>
                  </td>
                  <td className="px-4 py-3.5 text-[#34404f]">{row.layer}</td>
                  <td className="px-4 py-3.5"><span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-[12px] font-medium ${RATING_TONE[row.rating] || RATING_TONE.Medium}`}>{row.rating}</span></td>
                  <td className="min-w-[280px] max-w-[420px] px-4 py-3.5 leading-snug text-[#1f2a37]">{row.evidence}</td>
                  <td className="px-4 py-3.5 tabular-nums text-[#1f2a37]">{loading && member ? wait : signedPct(x.q1)}</td>
                  <td className="px-4 py-3.5 tabular-nums text-[#1f2a37]">{loading && member ? wait : pct(x.capexSales)}</td>
                  <td className="px-4 py-3.5 tabular-nums text-[#1f2a37]">{loading && member ? wait : signedPct(x.fcfSales)}</td>
                  <td className="px-4 py-3.5 tabular-nums text-[#1f2a37]">
                    {!member ? <span className="text-[#a0a8b3]">not priced</span> : !priced ? wait : x.pe !== null ? `${x.pe.toFixed(0)}x` : '—'}
                  </td>
                  <td className="px-4 py-3.5">{loading && member ? wait : <Band b={x.capital.band} />}</td>
                  <td className="px-4 py-3.5">
                    {!member ? <span className="text-[#a0a8b3]">not priced</span> : !priced ? wait : x.expectation ? (
                      <span className="inline-flex flex-col gap-1">
                        <Band b={x.expectation.band} scale="expectation" />
                        {x.implied ? <span className="text-[12px] text-[#5b6573]">{x.implied.cagr <= 0 ? 'no growth needed' : `needs ${pct(x.implied.cagr)}/yr`}</span> : null}
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3.5">
                    <span className={`inline-block whitespace-nowrap rounded-full px-2.5 py-0.5 text-[12px] font-semibold ${statusTone(row.status)}`}>{row.status}</span>
                    <span className="mt-1.5 block whitespace-nowrap text-[12px] text-[#8a93a0]">
                      AGI test: {rec?.mat ? MATERIALITY_TIER[rec.mat.tier].label.toLowerCase() : member ? '…' : 'not a member'}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 max-w-[110ch] text-[13px] leading-relaxed text-[#6b7480]">
        Selected on {STRATEGY_FACTORS.join(', ')}. Layer, AI materiality rating, evidence and status are AGI&rsquo;s judgments, and every evidence line is checked against the company&rsquo;s own documents.
        Financial columns are AGI arithmetic on filed FY26 and June-quarter results: revenue growth is the June 2026 quarter on June 2025; capex includes intangibles; FCF is operating cash flow less capex; P/E is AGI&rsquo;s market value at the last close over FY26 profit. Expectation load is the profit growth that takes today&rsquo;s market value to 30x earnings by FY29.
        No broker or consensus figures are used. KEC and NTPC Green are held candidates in the monitor, so AGI does not price them. &lsquo;AGI test&rsquo; is the monitor&rsquo;s rule-based materiality tier.
        A research classification, not a recommendation to buy or sell.
      </p>

      <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#0f1720]">How to interpret this list</h3>
      <p className="mt-1 text-[15px] text-[#5b6573]">There are really four different investment structures inside it.</p>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {STRUCTURES.map((st) => (
          <section key={st.title} className="rounded-xl bg-[#f7f8fa] px-5 py-4">
            <h4 className="text-[16px] font-semibold text-[#0f1720]">{st.title}</h4>
            <p className="mt-2 flex flex-wrap gap-1.5">
              {st.names.map((sym) => <span key={sym} className="rounded-md bg-white px-2 py-0.5 font-mono text-[12px] text-[#34404f] ring-1 ring-[#e5e8ec]">{sym}</span>)}
            </p>
            <p className="mt-2.5 text-[15px] leading-relaxed text-[#34404f]">{st.text}</p>
          </section>
        ))}
      </div>
      {netweb ? (
        <p className="mt-4 max-w-[100ch] text-[15px] leading-relaxed text-[#34404f]">
          Netweb, for example, reported AI systems at about 62% of June-quarter revenue and an order book of about ₹2,507 crore, which is why direct economic exposure matters more than simply mentioning AI.
        </p>
      ) : null}

      <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#0f1720]">Kept outside the basket for now</h3>
      <p className="mt-1 text-[15px] text-[#5b6573]">Valuable monitor names, not yet in the main basket.</p>
      <ul className="mt-4 grid gap-4 md:grid-cols-2">
        {OUTSIDE.map((o) => (
          <li key={o.name} className="rounded-xl border border-[#e5e8ec] px-5 py-4">
            <p className="font-semibold text-[#0f1720]">{o.name}</p>
            <p className="mt-1 text-[15px] leading-relaxed text-[#34404f]">{o.text}</p>
          </li>
        ))}
      </ul>

      <h3 className="mt-10 text-[20px] font-semibold tracking-tight text-[#0f1720]">The five metrics beside every company</h3>
      <p className="mt-1 text-[15px] text-[#5b6573]">Not one aggregate score: five measures, side by side.</p>
      <dl className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {FIVE_METRICS.map(([k, v]) => (
          <div key={k} className="rounded-xl bg-[#f7f8fa] px-4 py-4">
            <dt className="font-semibold text-[#0f1720]">{k}</dt>
            <dd className="mt-1 text-[14px] leading-relaxed text-[#34404f]">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-4 max-w-[100ch] text-[15px] leading-relaxed text-[#34404f]">
        That makes the difference between something like Netweb and KEC immediately obvious: Netweb has much higher current AI materiality
        {netweb?.implied ? `, but also a far heavier valuation burden (its price needs profit growth of ${pct(netweb.implied.cagr)} a year to reach 30x by FY29)` : ', but also a far heavier valuation burden'};
        KEC has much less AI materiality today. The monitor exposes that trade-off rather than hiding it inside a single score.
      </p>
    </>
  );
}
