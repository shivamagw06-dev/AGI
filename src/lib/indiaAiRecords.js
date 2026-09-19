/**
 * One record per India AI basket member: evidence, filed figures, AGI's
 * market value, AGI's estimate runs, the five factors and the materiality
 * tier. Shared by the monitor and the strategy page so both read a company
 * the same way.
 */
import { impliedGrowth, runModel, valueOf } from './indiaAiEstimates.js';
import {
  aiMateriality, capitalQuality, earningsMomentum, evidenceConfidence, expectationLoad, materialityConfidence,
} from './indiaAiFactors.js';
import { classifyMateriality } from './indiaAiMateriality.js';

const HARD = new Set(['order', 'capex', 'operating']);

/** Everything AGI holds about one member, in one record. */
export function buildRecords({ universe, operating, estimates, marketValue, stage3, scoring, exit, materiality }) {
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
        materialityConf: materialityConfidence(m),
        momentum: earningsMomentum(row),
        capital: capitalQuality(row),
        expectation: expectationLoad({ marketValueCr: mv[m.symbol], patCr: pat, exitMultiple, years }),
      },
    };
  });
}

/**
 * Ratios from filed results for one company: a member's record, or a filed
 * row for a company AGI does not price. Revenue growth is the latest quarter
 * on the same quarter a year earlier; capex includes intangibles; FCF is
 * operating cash flow less capex; P/E is AGI market value over FY26 profit.
 */
export function filedRatios(rec, filed = {}) {
  const f = rec ? rec.row : filed;
  const num = (v) => (Number.isFinite(v) ? v : null);
  const rev = num(f.revenueFY26);
  const capex = num(f.capexFY26) !== null ? f.capexFY26 + (num(f.capexIntangiblesFY26) || 0) : null;
  const pat = rec ? rec.pat : num(f.patFY26);
  return {
    q1: num(f.revenueQ1FY27) && num(f.revenueQ1FY26) ? f.revenueQ1FY27 / f.revenueQ1FY26 - 1 : null,
    capexSales: rev && capex !== null ? capex / rev : null,
    fcfSales: rev && num(f.cfoFY26) !== null && capex !== null ? (f.cfoFY26 - capex) / rev : null,
    pe: rec && rec.mv && pat > 0 ? rec.mv / pat : null,
    capital: rec ? rec.factors.capital : capitalQuality(f),
    expectation: rec ? rec.factors.expectation : null,
    implied: rec ? rec.implied : null,
  };
}
