/**
 * Five factors for each member, kept apart on purpose.
 *
 * There is no composite score. Each factor answers one question from AGI's
 * own data - filings, the evidence record, AGI's market value and AGI's
 * estimate models - and says how it was measured and what it could not see.
 * No broker estimate or consensus figure enters any factor; in particular
 * earnings revisions are absent because AGI has no consensus feed.
 *
 * Bands are fixed thresholds, stated beside each factor, not rankings.
 */
import { impliedGrowth, runModel } from './indiaAiEstimates.js';

const pct = (v, d = 0) => `${(v * 100).toFixed(d)}%`;
const num = (v) => (Number.isFinite(v) ? v : null);

/** How much of the business AI/data centres could be, by AGI's base case or the company's own share. */
export function aiMateriality({ model, statedShare }) {
  const out = model ? runModel(model, { scenario: 'base' }) : null;
  if (out?.ok && out.materiality !== null) {
    const m = out.materiality;
    return {
      band: m >= 0.25 ? 'high' : m >= 0.05 ? 'medium' : 'low',
      value: pct(m),
      basis: 'AGI base case: FY29 AI/DC EBITDA as a share of FY26 filed EBITDA',
    };
  }
  if (statedShare) return { band: 'stated only', value: statedShare, basis: 'company-stated share; no base-case model runs' };
  return { band: 'not measurable', value: null, basis: model ? 'model waits for a figure no company discloses' : 'no model and no stated share' };
}

const TIER = {
  SEGMENT_REPORTED: 'audited segment',
  MANAGEMENT_DISCLOSED: 'company-stated figure',
  NOT_ATTRIBUTABLE: 'linked, not sized',
};

/** How good the evidence is: the exposure tier, and how much dated hard evidence stands behind it. */
export function evidenceConfidence(member) {
  const items = [...(member.admittedOn || []), ...(member.supportingEvidence || [])]
    .filter((e) => ['order', 'capex', 'operating'].includes(e.kind));
  const latest = items.map((e) => e.date).filter(Boolean).sort().at(-1) || null;
  const tier = member.attribution;
  const band = tier === 'SEGMENT_REPORTED' || (tier === 'MANAGEMENT_DISCLOSED' && items.length >= 3) ? 'high'
    : tier === 'MANAGEMENT_DISCLOSED' ? 'medium' : 'low';
  return {
    band,
    value: `${TIER[tier] || 'not recorded'} · ${items.length} hard item${items.length === 1 ? '' : 's'}${latest ? `, latest ${latest}` : ''}`,
    basis: 'exposure tier, plus the count and date of filed orders, capex and operating disclosures',
  };
}

/** Recent operating momentum from filings: quarter revenue growth, and intake against revenue. */
export function earningsMomentum(row) {
  const r1 = num(row?.revenueQ1FY27);
  const r0 = num(row?.revenueQ1FY26);
  if (!(r1 > 0 && r0 > 0)) return { band: 'not measurable', value: null, basis: 'quarter revenue not collected' };
  const g = r1 / r0 - 1;
  const intake = num(row?.intakeQ1FY27);
  const btb = intake > 0 ? intake / r1 : null;
  return {
    band: g >= 0.25 ? 'high' : g >= 0.10 ? 'medium' : 'low',
    value: `revenue ${g >= 0 ? '+' : ''}${pct(g)} y/y${btb !== null ? ` · book-to-bill ${btb.toFixed(2)}` : ''}`,
    basis: 'latest quarter revenue against the same quarter a year earlier; intake/revenue where intake is reported. No consensus revisions (AGI has no consensus feed).',
  };
}

/** Whether growth is paying for itself: free cash flow margin and return on capital, from FY26 filings. */
export function capitalQuality(row) {
  const rev = num(row?.revenueFY26);
  const cfo = num(row?.cfoFY26);
  const capex = num(row?.capexFY26);
  const intang = num(row?.capexIntangiblesFY26) || 0;
  const fcf = cfo !== null && capex !== null && rev > 0 ? (cfo - capex - intang) / rev : null;
  const roce = num(row?.statedRoceFY26) ?? (num(row?.ebitFY26) !== null && num(row?.capitalEmployedFY26) > 0 ? row.ebitFY26 / row.capitalEmployedFY26 : null);
  if (fcf === null && roce === null) return { band: 'not measurable', value: null, basis: 'cash flow and capital figures not collected' };
  let band = 'moderate';
  if (roce !== null && roce >= 0.2 && (fcf === null || fcf > 0)) band = 'strong';
  else if ((roce !== null && roce < 0.12) && (fcf !== null && fcf < 0)) band = 'weak';
  else if (fcf !== null && fcf < -0.25) band = 'capital-hungry';
  return {
    band,
    value: [fcf !== null ? `FCF ${pct(fcf)} of revenue` : null, roce !== null ? `ROCE ${pct(roce)}` : null].filter(Boolean).join(' · '),
    basis: 'FY26 operating cash flow less capex, over revenue; ROCE as the company states it, else EBIT over equity plus borrowings',
  };
}

/** How much growth today's price already asks for, at an exit multiple the reader can see. */
export function expectationLoad({ marketValueCr, patCr, exitMultiple, years }) {
  const out = impliedGrowth({ marketValueCr, patCr, exitMultiple, years });
  if (!out) return { band: 'not measurable', value: null, basis: 'needs market value and positive FY26 profit' };
  const c = out.cagr;
  return {
    band: c >= 0.4 ? 'very high' : c >= 0.25 ? 'high' : c >= 0.1 ? 'moderate' : 'low',
    value: c <= 0
      ? `${out.trailingMultiple}x FY26 profit · already at or under ${exitMultiple}x; no growth needed`
      : `${out.trailingMultiple}x FY26 profit · needs ${pct(c)} a year to reach ${exitMultiple}x`,
    basis: 'profit growth that makes AGI’s market value equal the exit multiple by the horizon; no broker estimate',
  };
}
