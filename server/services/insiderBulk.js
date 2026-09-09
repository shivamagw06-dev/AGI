/**
 * The SEC's bulk Form 345 datasets, turned into the rows the crawl produces.
 *
 * The nightly EDGAR crawl asks one company at a time and downloads one filing
 * at a time. Against five thousand issuers it needs ten nights to make a pass,
 * and it had never completed one. The SEC publishes the same data quarterly as
 * flat files: one 8 MB download carries 36,422 filings and 59,679 transactions
 * for every issuer, already structured, with the trading symbol on the
 * submission - so no CIK lookup, and none of the 797 tickers the crawl skips
 * for want of one.
 *
 * The output shape is deliberately identical to what parseFormFour produces.
 * The insider panel reads parsed_data.transactions, parsed_data.owners and
 * parsed_data.planned, and it must not be able to tell which route a filing
 * arrived by - otherwise a fund page shows two different summaries for the
 * same quarter depending on what ran last.
 *
 * The crawl still has a job: the bulk files stop at the last completed
 * quarter, so this covers history and EDGAR covers this week.
 */
import { TRANSACTION_CODES } from './formFour.js';
import { summariseTransactions, plausibleFilingDate } from './insiderValuation.js';

const MONTHS = {
  JAN: '01', FEB: '02', MAR: '03', APR: '04', MAY: '05', JUN: '06',
  JUL: '07', AUG: '08', SEP: '09', OCT: '10', NOV: '11', DEC: '12',
};

/**
 * The dataset writes dates as 31-OCT-2025.
 *
 * Null for anything else, including the blanks that are common in these files.
 * The empty string is what took the nightly job down, and it would do the same
 * here.
 */
export function bulkDate(value) {
  const text = String(value ?? '').trim().toUpperCase();
  const match = /^(\d{2})-([A-Z]{3})-(\d{4})$/.exec(text);
  if (!match) return null;
  const month = MONTHS[match[2]];
  if (!month) return null;
  const day = Number(match[1]);
  if (day < 1 || day > 31) return null;
  return plausibleFilingDate(`${match[3]}-${month}-${match[1]}`);
}

/** A number, where blank and absent are both null rather than zero. */
function num(value) {
  const text = String(value ?? '').trim();
  if (!text) return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * Tab-separated rows into objects.
 *
 * Split on tabs only. These files carry free text in REMARKS and footnote
 * columns, and a CSV-style parser that honoured quotes would swallow rows
 * whose text contains an unbalanced quotation mark - which company remarks
 * routinely do.
 */
export function parseTsv(text) {
  const lines = String(text || '').split(/\r?\n/);
  if (!lines.length) return [];
  const header = lines[0].split('\t').map((cell) => cell.trim());
  const rows = [];
  for (let i = 1; i < lines.length; i += 1) {
    if (!lines[i]) continue;
    const cells = lines[i].split('\t');
    const row = {};
    for (let c = 0; c < header.length; c += 1) row[header[c]] = cells[c] ?? '';
    rows.push(row);
  }
  return rows;
}

/** Group rows by accession, so each filing is assembled from one pass. */
export function groupByAccession(rows) {
  const map = new Map();
  for (const row of rows || []) {
    const key = String(row?.ACCESSION_NUMBER || '').trim();
    if (!key) continue;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(row);
  }
  return map;
}

/** One transaction, in the shape formFour.transactions produces. */
function transactionFrom(row, derivative) {
  const code = String(row.TRANS_CODE || '').trim().toUpperCase();
  const meta = TRANSACTION_CODES[code] || { label: `Unrecognised code ${code || '(none)'}`, discretionary: false, direction: null };
  const shares = num(row.TRANS_SHARES);
  const price = num(row.TRANS_PRICEPERSHARE);
  const disposal = String(row.TRANS_ACQUIRED_DISP_CD || '').trim().toUpperCase();

  return {
    security_title: String(row.SECURITY_TITLE || '').trim(),
    transaction_date: bulkDate(row.TRANS_DATE),
    code,
    code_label: meta.label,
    discretionary: meta.discretionary,
    direction: disposal === 'D' ? 'dispose' : disposal === 'A' ? 'acquire' : meta.direction,
    shares,
    price_per_share: price,
    // Null rather than zero when either side is missing: a grant has no price,
    // and a zero would read as a transaction worth nothing.
    value_usd: shares !== null && price !== null ? shares * price : null,
    shares_owned_after: num(row.SHRS_OWND_FOLWNG_TRANS),
    ownership: String(row.DIRECT_INDIRECT_OWNERSHIP || '').trim(),
    derivative,
  };
}

/** Roles, from the relationship field the dataset flattens them into. */
function ownerFrom(row) {
  const relationship = String(row.RPTOWNER_RELATIONSHIP || '').toLowerCase();
  const roles = [];
  if (relationship.includes('director')) roles.push('director');
  if (relationship.includes('officer')) roles.push('officer');
  if (relationship.includes('10 percent') || relationship.includes('tenpercent')) roles.push('ten_percent_owner');
  if (relationship.includes('other')) roles.push('other');
  return {
    cik: String(row.RPTOWNERCIK || '').trim(),
    name: String(row.RPTOWNERNAME || '').trim(),
    roles,
    officer_title: String(row.RPTOWNER_TITLE || '').trim(),
  };
}

/**
 * Assemble filings from the dataset's four tables.
 *
 * `tickers`, when given, restricts output to issuers actually held. Passing
 * null keeps everything, which is a much larger dataset than the holdings
 * layer needs.
 */
export function assembleFilings({ submissions, owners, nonDeriv, deriv, tickers = null } = {}) {
  const ownersBy = groupByAccession(owners);
  const nonDerivBy = groupByAccession(nonDeriv);
  const derivBy = groupByAccession(deriv);
  const wanted = tickers ? new Set([...tickers].map((t) => String(t).toUpperCase())) : null;

  const filings = [];
  let skippedTicker = 0;
  let skippedForm = 0;

  for (const submission of submissions || []) {
    const accession = String(submission.ACCESSION_NUMBER || '').trim();
    const ticker = String(submission.ISSUERTRADINGSYMBOL || '').trim().toUpperCase();
    const documentType = String(submission.DOCUMENT_TYPE || '').trim();

    // Form 4 and its amendments only. The archive also carries Form 3 (initial
    // statements of ownership) and Form 5 (annual catch-ups), which are not
    // transactions and would land in a transaction feed as empty filings.
    if (!/^4(\/A)?$/.test(documentType)) { skippedForm += 1; continue; }
    if (!accession) continue;
    if (wanted && !wanted.has(ticker)) { skippedTicker += 1; continue; }

    const rows = [
      ...(nonDerivBy.get(accession) || []).map((row) => transactionFrom(row, false)),
      ...(derivBy.get(accession) || []).map((row) => transactionFrom(row, true)),
    ];
    const people = (ownersBy.get(accession) || []).map(ownerFrom);
    const cik = String(submission.ISSUERCIK || '').trim();

    filings.push({
      accession_number: accession,
      issuer_cik: cik,
      ticker,
      form_type: documentType,
      event_type: 'insider_transaction',
      filed_at: bulkDate(submission.FILING_DATE),
      report_date: bulkDate(submission.PERIOD_OF_REPORT),
      source_url: `https://www.sec.gov/Archives/edgar/data/${cik.replace(/^0+/, '')}/${accession.replace(/-/g, '')}/`,
      parsed_data: {
        document_type: documentType,
        period_of_report: bulkDate(submission.PERIOD_OF_REPORT),
        issuer_cik: cik,
        issuer_name: String(submission.ISSUERNAME || '').trim(),
        ticker,
        // The Rule 10b5-1 flag. A sale under a plan adopted months earlier
        // says nothing about what the insider thinks now, and losing this
        // field is how an insider feed becomes noise.
        planned: String(submission.AFF10B5ONE || '').trim() === '1',
        owners: people,
        transactions: rows,
        ...summariseTransactions(rows),
        // Recorded so a filing's route is auditable, without the panel needing
        // to care which one it came by.
        source: 'sec_bulk_form345',
      },
    });
  }

  return { filings, skippedTicker, skippedForm };
}
