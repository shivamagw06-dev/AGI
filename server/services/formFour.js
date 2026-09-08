/**
 * Reading a Form 4.
 *
 * An insider filing says what an officer, director or ten-per-cent holder did
 * with the issuer's stock. It is timely - filed within two business days,
 * against 13F's forty-five - which is what makes it worth having.
 *
 * The thing that decides whether a feature built on it informs or misleads is
 * the transaction code. Most insider "selling" is not a decision:
 *
 *   F  shares withheld by the issuer to pay tax on a vesting grant
 *   M  an option exercised, usually on a schedule set years earlier
 *   A  a grant or award, which the recipient did not choose to buy
 *   G  a gift
 *
 * Counting those alongside a discretionary sale produces a stream of alarming
 * "insider selling" that reflects a vesting calendar. The codes that carry a
 * decision are P - an open-market purchase - and a discretionary S, and even
 * an S may have been scheduled: aff10b5One marks a trade made under a Rule
 * 10b5-1 plan adopted months earlier, which says nothing about what the
 * insider thinks today.
 *
 * So every transaction is classified and the discretionary ones are named as
 * such, rather than the caller being handed a pile of shares and left to work
 * it out.
 */

/**
 * The raw XML behind a Form 4, given the document EDGAR names.
 *
 * `primaryDocument` points at the XSL-rendered view - xslF345X06/form4.xml -
 * which is HTML for a browser, not the filing. Fetching it returns a page the
 * parser cannot read, and the failure is quiet: no owner, no transactions, a
 * filing that looks like it contained nothing.
 *
 * The raw document sits at the same path with the stylesheet directory
 * removed, so that is what is asked for.
 */
export function rawDocumentPath(primaryDocument) {
  const doc = String(primaryDocument || '').trim();
  if (!doc) return null;
  return doc.replace(/^xsl[^/]*\//i, '');
}

const val = (block, tag) => {
  const outer = new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>`).exec(block || '');
  if (!outer) return null;
  const inner = /<value>([\s\S]*?)<\/value>/.exec(outer[1]);
  return (inner ? inner[1] : outer[1]).trim() || null;
};
const flat = (block, tag) => {
  const m = new RegExp(`<${tag}>([\\s\\S]*?)</${tag}>`).exec(block || '');
  return m ? m[1].trim() || null : null;
};
const num = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(String(value).replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
};

/** What the code means, and whether a decision sits behind it. */
export const TRANSACTION_CODES = {
  P: { label: 'Open-market purchase', discretionary: true, direction: 'buy' },
  S: { label: 'Open-market sale', discretionary: true, direction: 'sell' },
  A: { label: 'Grant or award', discretionary: false, direction: 'acquire' },
  M: { label: 'Option or derivative exercise', discretionary: false, direction: 'acquire' },
  F: { label: 'Shares withheld for tax', discretionary: false, direction: 'dispose' },
  G: { label: 'Gift', discretionary: false, direction: null },
  D: { label: 'Disposition to the issuer', discretionary: false, direction: 'dispose' },
  C: { label: 'Conversion of a derivative', discretionary: false, direction: 'acquire' },
  X: { label: 'In-the-money option exercise', discretionary: false, direction: 'acquire' },
};

/** How the filer described the person: officer, director, ten-per-cent holder. */
export function reportingOwners(xml) {
  return [...String(xml || '').matchAll(/<reportingOwner>([\s\S]*?)<\/reportingOwner>/g)].map(([, block]) => {
    const roles = [];
    if (/<isDirector>\s*(1|true)\s*<\/isDirector>/i.test(block)) roles.push('director');
    if (/<isOfficer>\s*(1|true)\s*<\/isOfficer>/i.test(block)) roles.push('officer');
    if (/<isTenPercentOwner>\s*(1|true)\s*<\/isTenPercentOwner>/i.test(block)) roles.push('ten_percent_owner');
    if (/<isOther>\s*(1|true)\s*<\/isOther>/i.test(block)) roles.push('other');
    return {
      cik: flat(block, 'rptOwnerCik'),
      name: flat(block, 'rptOwnerName'),
      roles,
      officer_title: flat(block, 'officerTitle'),
    };
  });
}

/**
 * Every transaction in the filing.
 *
 * Derivative and non-derivative rows are both read and marked, because an
 * option grant and a share purchase are different events that a reader must
 * not have to infer from the numbers.
 */
export function transactions(xml) {
  const doc = String(xml || '');
  const out = [];
  for (const [table, derivative] of [['nonDerivativeTransaction', false], ['derivativeTransaction', true]]) {
    for (const [, block] of doc.matchAll(new RegExp(`<${table}>([\\s\\S]*?)</${table}>`, 'g'))) {
      const code = val(block, 'transactionCode') || flat(block, 'transactionCode');
      const meta = TRANSACTION_CODES[code] || { label: `Unrecognised code ${code || '(none)'}`, discretionary: false, direction: null };
      const shares = num(val(block, 'transactionShares'));
      const price = num(val(block, 'transactionPricePerShare'));
      out.push({
        security_title: val(block, 'securityTitle'),
        transaction_date: val(block, 'transactionDate'),
        code,
        code_label: meta.label,
        // Whether a person chose to do this, or a vesting calendar did.
        discretionary: meta.discretionary,
        direction: val(block, 'transactionAcquiredDisposedCode') === 'D' ? 'dispose'
          : val(block, 'transactionAcquiredDisposedCode') === 'A' ? 'acquire' : meta.direction,
        shares,
        price_per_share: price,
        // Null rather than zero when either side is missing: a grant has no
        // price, and a zero would read as a transaction worth nothing.
        value_usd: shares !== null && price !== null ? shares * price : null,
        shares_owned_after: num(val(block, 'sharesOwnedFollowingTransaction')),
        ownership: val(block, 'directOrIndirectOwnership'),
        derivative,
      });
    }
  }
  return out;
}

/**
 * One Form 4, read.
 *
 * `planned` is the Rule 10b5-1 flag. A sale made under a plan adopted months
 * earlier says nothing about what the insider thinks now, and presenting it
 * beside a discretionary sale is how an insider feed becomes noise.
 */
export function parseFormFour(xml) {
  const doc = String(xml || '');
  if (!/<ownershipDocument/.test(doc)) return null;
  const issuer = /<issuer>([\s\S]*?)<\/issuer>/.exec(doc)?.[1] || '';
  const rows = transactions(doc);

  return {
    document_type: flat(doc, 'documentType'),
    period_of_report: flat(doc, 'periodOfReport'),
    issuer_cik: flat(issuer, 'issuerCik'),
    issuer_name: flat(issuer, 'issuerName'),
    ticker: flat(issuer, 'issuerTradingSymbol'),
    planned: /<aff10b5One>\s*(1|true)\s*<\/aff10b5One>/i.test(doc),
    owners: reportingOwners(doc),
    transactions: rows,
    // The summary a reader actually wants, computed once so every caller
    // draws the same line between a decision and a vesting event.
    discretionary_buy_value: rows.filter((r) => r.discretionary && r.direction === 'acquire').reduce((s, r) => s + (r.value_usd || 0), 0),
    discretionary_sell_value: rows.filter((r) => r.discretionary && r.direction === 'dispose').reduce((s, r) => s + (r.value_usd || 0), 0),
    has_discretionary: rows.some((r) => r.discretionary),
  };
}
