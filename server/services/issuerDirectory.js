/**
 * Who a ticker belongs to, across every list the SEC publishes.
 *
 * company_tickers.json lists operating companies, and it is the only one the
 * classifier consulted. That is why 8.6% of the book by value was
 * Unclassified: most of it was funds. SPY at $326bn, QQQ at $140bn, IVV, IWM,
 * VOO, TLT, SOXX - an index ETF is not an operating company and has no entry
 * there, so every one of them was skipped in silence.
 *
 * Three files, in precedence order:
 *
 *   company_tickers.json           operating companies
 *   company_tickers_exchange.json  exchange-listed registrants, which is the
 *                                  only one of the three that has SPY - the
 *                                  SPDR trust is a unit investment trust and
 *                                  appears in neither of the others
 *   company_tickers_mf.json        registered funds, 28,501 tickers
 *
 * Operating companies win where a ticker appears in more than one, because a
 * SIC code from a real registrant says more than "this is a fund".
 *
 * A fund needs no SIC lookup at all. Its own filings would return 6726,
 * investment offices, which this map reads as Financials - and calling an S&P
 * 500 index fund a financials position is worse than leaving it unclassified,
 * because it is confidently wrong. Funds get their own sector, which is the
 * honest answer and the useful one: a reader wants to know what share of a
 * book is index exposure.
 */

export const FUND_SECTOR = 'Funds & ETFs';
export const FUND_INDUSTRY = 'Fund or ETF';

const upper = (value) => String(value ?? '').trim().toUpperCase();
const cik = (value) => String(value ?? '').replace(/\D/g, '').padStart(10, '0');

/**
 * Build the lookup from the three parsed SEC payloads. Any may be omitted.
 *
 * @returns {Map<string, {cik: string, title: string|null, kind: 'company'|'fund'}>}
 */
export function issuerDirectory({ companies, exchange, funds } = {}) {
  const directory = new Map();

  // Lowest precedence first: each later pass overwrites what came before, so
  // the order here is the reverse of the precedence described above.
  for (const row of fundRows(funds)) {
    if (!row.symbol) continue;
    directory.set(row.symbol, { cik: cik(row.cik), title: null, kind: 'fund' });
  }
  for (const row of exchangeRows(exchange)) {
    if (!row.ticker) continue;
    // The exchange file mixes operating companies and the funds that list on
    // an exchange. A ticker already known as a fund stays a fund - that file
    // does not distinguish them, and the fund list does.
    const known = directory.get(row.ticker);
    directory.set(row.ticker, { cik: cik(row.cik), title: row.name || null, kind: known?.kind === 'fund' ? 'fund' : 'company' });
  }
  for (const row of companyRows(companies)) {
    if (!row.ticker) continue;
    directory.set(row.ticker, { cik: cik(row.cik), title: row.title || null, kind: 'company' });
  }

  return directory;
}

/** The already-parsed company_tickers.json shape, or a Map of one. */
function companyRows(payload) {
  if (!payload) return [];
  if (payload instanceof Map) {
    return [...payload.entries()].map(([ticker, value]) => ({ ticker: upper(ticker), cik: value?.cik, title: value?.title }));
  }
  return Object.values(payload).map((row) => ({ ticker: upper(row?.ticker), cik: row?.cik_str ?? row?.cik, title: row?.title }));
}

/** The fields/data shape both of the other two files use. */
function tabular(payload) {
  const fields = payload?.fields;
  const data = payload?.data;
  if (!Array.isArray(fields) || !Array.isArray(data)) return [];
  return data.map((row) => Object.fromEntries(fields.map((field, index) => [field, row?.[index]])));
}

function exchangeRows(payload) {
  return tabular(payload).map((row) => ({ ticker: upper(row.ticker), cik: row.cik, name: row.name }));
}

function fundRows(payload) {
  return tabular(payload).map((row) => ({ symbol: upper(row.symbol), cik: row.cik }));
}
