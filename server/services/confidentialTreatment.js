/**
 * Filings whose information table does not contain the holdings.
 *
 * Two of Norges Bank's stored quarters held exactly one position against a
 * median of 2,108, and the obvious reading - the parser broke - is wrong. The
 * SEC document really does contain one row, and the row is not a holding:
 *
 *   <infoTable>
 *     <nameOfIssuer>NA</nameOfIssuer>
 *     <titleOfClass>NA</titleOfClass>
 *     <cusip>000000000</cusip>
 *     <value>0</value>
 *     <shrsOrPrnAmt><sshPrnamt>0</sshPrnamt><sshPrnamtType>SH</sshPrnamtType></shrsOrPrnAmt>
 *     ...
 *   </infoTable>
 *
 * Norges Bank files under a standing request for confidential treatment. It
 * submits a schema-valid but empty table on the due date and files the real
 * holdings as a 13F-HR/A one year later, when the confidentiality lapses. The
 * pattern runs the length of its history: Q1 2026, Q3 2025, Q1 2025, Q3 2024,
 * Q1 2024, Q3 2023, Q2 2023, Q1 2023 and back, every one of them a ~4.6 KB
 * placeholder followed twelve months on by a ~900 KB amendment.
 *
 * The cover page says all of this outright, in the summary page we were not
 * reading:
 *
 *   Norges Bank, Q1 2026   entries 1507  value $864,690,921,985  omitted true
 *   Norges Bank, Q3 2025   entries 1516  value $870,104,905,340  omitted true
 *
 * So the filing declares its own true size, and the gap between that number
 * and the number of rows actually present is the whole signal. It is a better
 * check than any comparison against the manager's own history, because it is
 * the filer's assertion about this filing rather than our inference from
 * neighbouring ones - Alphabet really did hold two positions in 2016, and no
 * heuristic keyed to a median can tell that from a table that went missing.
 *
 * The distinction that matters, and the reason this is not simply "reject
 * confidential filings": withholding is usually partial. Berkshire's Q1 2025
 * report carries isConfidentialOmitted true with 110 entries present and
 * correct - it withheld a handful of positions it was still building, and
 * disclosed them four months later. That filing is complete data with a
 * footnote. Norges Bank's is no data at all. The flag is identical in both;
 * only the row count separates them.
 */

/** A CUSIP of all zeros, or one that is not nine characters of anything. */
const NULL_CUSIP = /^0{9}$/;

/**
 * A row that occupies the schema's shape without carrying a position.
 *
 * Deliberately conservative: an issuer of NA or nothing, a null CUSIP, and no
 * value and no shares. A real holding fails at least one of these - a position
 * being wound down still has a CUSIP and a name, and a position whose value
 * rounds to zero still has share count. Requiring all four together is what
 * keeps this from eating a genuine row.
 */
export function isPlaceholderRow(row) {
  if (!row) return true;
  const issuer = String(row.issuer_name || '').trim().toUpperCase();
  const cusip = String(row.cusip || '').trim();
  const namelessIssuer = issuer === '' || issuer === 'NA' || issuer === 'N/A' || issuer === 'NONE';
  const nullCusip = cusip === '' || NULL_CUSIP.test(cusip);
  const empty = Number(row.value_usd || 0) === 0 && Number(row.shares || 0) === 0;
  return namelessIssuer && nullCusip && empty;
}

function tag(xml, name) {
  const match = new RegExp(`<(?:\\w+:)?${name}>\\s*([^<]*?)\\s*<`, 'i').exec(String(xml || ''));
  return match ? match[1].trim() : null;
}

function whole(value) {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(String(value).replace(/[^0-9.-]/g, ''));
  return Number.isFinite(parsed) ? parsed : null;
}

/**
 * The `<summaryPage>` block of a 13F cover page.
 *
 * `tableEntryTotal` and `tableValueTotal` are required of every holdings
 * report and have been since the XML schema replaced the text form, so they
 * are present on everything we ingest from 2013 onward. Older filings predate
 * them; every field here is nullable and callers must treat null as "the
 * filing did not say" rather than as zero.
 */
export function parseSummaryPage(coverPageXml) {
  const text = String(coverPageXml || '');
  if (!text) {
    return { declaredEntries: null, declaredValueUsd: null, confidentialOmitted: null, otherManagers: null };
  }
  return {
    declaredEntries: whole(tag(text, 'tableEntryTotal')),
    declaredValueUsd: whole(tag(text, 'tableValueTotal')),
    confidentialOmitted: /<(?:\w+:)?isConfidentialOmitted>\s*(true|1|y|yes)\s*</i.test(text)
      ? true
      : (/<(?:\w+:)?isConfidentialOmitted>/i.test(text) ? false : null),
    otherManagers: whole(tag(text, 'otherIncludedManagersCount')),
  };
}

/**
 * Below this share of the declared entry count, a table is not merely
 * imprecise - it is missing.
 *
 * A filer's own total and the rows it shipped disagree by small amounts often
 * enough: a manager amends the summary page and not the table, or counts a
 * put and a call as one entry. Half is far outside any of that. The two
 * Norges Bank filings sit at 1/1507 and 1/1516.
 */
const MISSING_TABLE_SHARE = 0.5;

/**
 * Decide what a parsed information table actually is.
 *
 * `rawRows` must be the rows as parsed, before duplicate collapsing. A filing
 * that reports one security under several `otherManager` values has more table
 * entries than it has distinct positions, and `tableEntryTotal` counts the
 * entries; comparing against the collapsed set would read every multi-manager
 * filing as short.
 *
 * Returns one of three states:
 *
 *   `complete`      - the rows are the holdings. Ingest them.
 *   `confidential`  - the filer withheld the table under a confidential
 *                     treatment request and shipped a placeholder. There are
 *                     no holdings to store and none are coming until the
 *                     amendment lands. Record the filing, store nothing.
 *   `short`         - rows are missing and the filing does not say they were
 *                     withheld. Something on our side failed. Fail loudly.
 *
 * A partial withholding - flag set, rows present - is `complete`, because that
 * is what it is: the filing carries the positions it discloses.
 */
export function assessInformationTable({ rawRows = [], summary = null } = {}) {
  const rows = Array.isArray(rawRows) ? rawRows : [];
  const placeholders = rows.filter(isPlaceholderRow);
  const realRows = rows.filter((row) => !isPlaceholderRow(row));
  const { declaredEntries = null, declaredValueUsd = null, confidentialOmitted = null } = summary || {};

  const base = {
    realRows,
    placeholderCount: placeholders.length,
    declaredEntries,
    declaredValueUsd,
    confidentialOmitted: confidentialOmitted === true,
  };

  const declared = Number.isFinite(declaredEntries) && declaredEntries > 0 ? declaredEntries : null;
  const shortfall = declared !== null && realRows.length < declared * MISSING_TABLE_SHARE;

  // No positions survived, or the table is a fraction of what the filing says
  // it holds. Whether that is expected turns entirely on the flag.
  if (!realRows.length || shortfall) {
    if (confidentialOmitted === true) {
      return {
        ...base,
        status: 'confidential',
        reason: declared !== null
          ? `The filer requested confidential treatment and withheld the information table: `
            + `the cover page declares ${declared.toLocaleString('en-US')} entries but the table carries `
            + `${realRows.length}. The holdings are normally filed as a 13F-HR/A when the `
            + `confidentiality lapses.`
          : 'The filer requested confidential treatment and the information table carries no positions. '
            + 'The holdings are normally filed as a 13F-HR/A when the confidentiality lapses.',
      };
    }
    return {
      ...base,
      status: 'short',
      reason: declared !== null
        ? `The information table carries ${realRows.length} position(s) against the `
          + `${declared.toLocaleString('en-US')} its own cover page declares, and the filing does not `
          + `report withholding anything. The table was not read in full.`
        : 'The information table carries no positions and the filing does not report withholding any.',
    };
  }

  // Rows are present, so the filing is complete as filed. The flag stays on
  // the record and is not turned into a count of what was withheld: a filer
  // that withholds positions omits them from `tableEntryTotal` as well.
  // Berkshire's Q1 2025 declares 110 and ships 110 while holding back four it
  // disclosed that August, so `declared - present` is zero there and the four
  // are unknowable from this filing. Reporting a derived number would be
  // inventing one.
  return { ...base, status: 'complete', reason: null };
}
