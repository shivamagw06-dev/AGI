/**
 * Economic materiality: is a member's AI/data-centre business already large
 * enough to matter?
 *
 * A tier inside the basket, separate from admission (thematic evidence on the
 * company's own paper) and from sizing (how large a position the stock's
 * turnover can carry). The rules live in the materiality config, decided by
 * the portfolio owner; this function only applies them, and says which test
 * passed, on what basis, and why a member did not.
 *
 * Provenance travels with every pass: D disclosed, I AGI arithmetic on
 * disclosed figures, A AGI estimate. A member whose only pass is an estimate
 * is still Material, and is labelled as resting on an estimate.
 */

const TEST_LABEL = {
  amount: 'Rs 100 cr+ revenue or orders',
  share: '5%+ of revenue',
  estimate: '5%+ of EBITDA by FY29 (AGI base case)',
  contracted: 'Contracted capacity, named customer',
};

const fmtCr = (v) => `Rs ${Math.round(v).toLocaleString('en-IN')} cr`;
const fmtPct = (v) => `${(v * 100).toFixed(1).replace(/\.0$/, '')}%`;

/**
 * Classify one member.
 *
 * entry: the member's block from the materiality config ({ facts, path, note })
 * rules: the config's rules
 * evidenceBand: 'high' | 'medium' | 'low' from evidenceConfidence()
 * hardItems: count of filed orders, capex and operating disclosures
 * fy29Materiality: AGI base-case FY29 AI/DC EBITDA / FY26 EBITDA, or null
 * orderCover: order book / quarterly revenue, or null
 * exception: a recorded exception for this member, or null
 */
export function classifyMateriality({
  entry = {}, rules, evidenceBand, hardItems = 0, fy29Materiality = null, orderCover = null, exception = null,
}) {
  const facts = entry.facts || [];
  const passes = [];
  const misses = [];

  for (const f of facts) {
    if (f.test === 'amount') {
      if (f.valueCr >= rules.amountCr) passes.push({ test: 'amount', tag: f.basis, text: `${fmtCr(f.valueCr)}: ${f.label}`, fact: f });
      else misses.push(`${fmtCr(f.valueCr)} (${f.label}) is under ${fmtCr(rules.amountCr)}`);
    } else if (f.test === 'share') {
      if (f.share >= rules.revenueShare) passes.push({ test: 'share', tag: f.basis, text: `${fmtPct(f.share)}: ${f.label}`, fact: f });
      else misses.push(`${fmtPct(f.share)} (${f.label}) is under ${fmtPct(rules.revenueShare)}`);
    } else if (f.test === 'contracted') {
      // Capacity counts only where it is a representative denominator for the
      // listed company; a JV's megawatts inside a diversified parent do not
      // establish the parent's materiality on their own. Share is adjusted
      // for the listed company's economic ownership.
      const share = Number.isFinite(f.capacityShare) ? f.capacityShare * (Number.isFinite(f.ownership) ? f.ownership : 1) : null;
      const sized = share !== null;
      if (f.representative === false) {
        misses.push(`${f.mw} MW of ${f.label}${f.customerNamed ? ` (${f.customers || 'named customer'})` : ''}; capacity is not a representative measure for this parent${Number.isFinite(f.ownership) && f.ownership < 1 ? ` (${fmtPct(f.ownership)}-owned JV)` : ''}, so materiality must come from revenue, orders or the FY29 EBITDA route`);
      } else if (f.customerNamed && sized && share >= rules.capacityShare) {
        passes.push({ test: 'contracted', tag: f.basis, text: `${f.mw} MW, ${fmtPct(share)} of capacity: ${f.label}`, fact: f });
      } else if (!f.customerNamed) {
        misses.push(`${f.mw} MW of ${f.label || 'contracted capacity'}, but no customer is named`);
      } else if (!sized) {
        misses.push(`Exposure confirmed: ${f.mw} MW contracted with ${f.customers || 'a named customer'}; its revenue or EBITDA contribution is not disclosed`);
      } else {
        misses.push(`${f.mw} MW is ${fmtPct(share)} of capacity, under ${fmtPct(rules.capacityShare)}`);
      }
    }
  }
  if (Number.isFinite(fy29Materiality)) {
    if (fy29Materiality >= rules.fy29EbitdaShare) {
      passes.push({ test: 'estimate', tag: 'A', text: `${fmtPct(fy29Materiality)} of FY26 EBITDA by FY29 in AGI's base case` });
    } else {
      misses.push(`AGI's base case puts FY29 AI/DC EBITDA at ${fmtPct(fy29Materiality)} of FY26 EBITDA, under ${fmtPct(rules.fy29EbitdaShare)}`);
    }
  }
  if (!facts.length && !Number.isFinite(fy29Materiality)) misses.push(entry.note || 'No disclosed amount, share or contracted capacity');
  else if (!facts.length && entry.note) misses.unshift(entry.note);

  const evidenceOk = hardItems > 0 && (rules.evidenceBands || []).includes(evidenceBand);
  const estimateOnly = passes.length > 0 && passes.every((p) => p.tag === 'A');

  // The path from order or capacity to revenue.
  let path = null;
  if (entry.path) {
    path = { kind: entry.path.kind, tag: entry.path.kind === 'judged' ? 'A' : 'D', note: entry.path.note };
  } else if (passes.some((p) => p.test === 'amount') && Number.isFinite(orderCover) && orderCover <= rules.orderCoverQuarters) {
    path = { kind: 'cover', tag: 'I', note: `Order book covers ${orderCover.toFixed(1)} quarters of revenue, inside ${rules.orderCoverQuarters}.` };
  } else if (estimateOnly) {
    path = { kind: 'model', tag: 'A', note: 'The estimate runs to FY29, inside 36 months.' };
  }

  const reasons = [];
  if (!passes.length) reasons.push('No materiality test passed');
  if (!evidenceOk) reasons.push(hardItems ? `Evidence confidence is ${evidenceBand}; medium or high is required` : 'No filed hard evidence');
  if (passes.length && !path) reasons.push('No path to revenue within 36 months is disclosed');

  const passed = passes.length > 0 && evidenceOk && Boolean(path);
  let tier = passed ? (estimateOnly ? 'material-estimate' : 'material') : 'not-yet';
  if (!passed && exception) tier = 'exception';
  return { tier, passes, misses, reasons, path, evidenceOk, estimateOnly, exception };
}

export const MATERIALITY_TIER = {
  material: { label: 'Material', short: 'Material' },
  'material-estimate': { label: 'Material, on AGI estimate', short: 'Material · est.' },
  exception: { label: 'Threshold exception', short: 'Exception' },
  'not-yet': { label: 'Not yet material', short: 'Not yet' },
};

export { TEST_LABEL };
