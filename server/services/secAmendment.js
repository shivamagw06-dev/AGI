/**
 * How a 13F-HR/A amendment is classified, and what it does to the holdings it
 * amends.
 *
 * This existed before as two lines inside the ingest path, and both were wrong
 * in ways that only show up against real filings:
 *
 *   const combined = archive.documents.map((d) => d.text).join('\n');
 *   const isRestatement = /<(?:\w+:)?isRestatement>\s*true\s*</i.test(combined);
 *
 * `isRestatement` is not a tag in the SEC 13F schema. The cover page carries
 * `<isAmendment>` and, inside `<amendmentInfo>`, `<amendmentType>` with the
 * value RESTATEMENT or NEW HOLDINGS. Nothing anywhere emits `isRestatement`,
 * so that test returned false for every filing ever ingested.
 *
 * And `archive.documents` did not contain the cover page. The fetch loop
 * ranked the information table first and stopped as soon as it had one, so on
 * a filing laid out as [infotable.xml, submission.txt, primary_doc.xml] it
 * downloaded exactly one file and never saw the cover page at all.
 *
 * Verified against real filings before this was written:
 *
 *   Elliott  0000902664-25-003078  report 2025-03-31  SEC: RESTATEMENT
 *   Baupost  0001567619-18-006456  report 2018-09-30  SEC: RESTATEMENT
 *     both downloaded only the info table, both classified additional_holdings
 *
 *   Berkshire 0000950123-25-008361 report 2025-03-31  SEC: NEW HOLDINGS
 *     confidential treatment expired; the amendment carries ONLY the
 *     previously withheld positions
 *
 * That last case is why an unknown amendment cannot be guessed. Treating a
 * restatement as additional holdings leaves positions the manager removed
 * sitting in the portfolio as phantoms. Treating a NEW HOLDINGS amendment as a
 * restatement deletes every position it does not mention - for Berkshire's
 * filing, almost the entire portfolio. The two errors are opposite and both
 * are severe, so an amendment we cannot classify is escalated rather than
 * assumed.
 */

/** What the SEC cover page says, or null where it does not say. */
export function parseAmendmentCoverPage(xml) {
  const text = String(xml || '');
  if (!text) return { isAmendment: null, amendmentType: null, amendmentNo: null, reason: null };

  const tag = (name) => {
    const match = new RegExp(`<(?:\\w+:)?${name}>\\s*([^<]*?)\\s*<`, 'i').exec(text);
    return match ? match[1].trim() : null;
  };

  const rawType = tag('amendmentType');
  return {
    isAmendment: /<(?:\w+:)?isAmendment>\s*(true|1|y|yes)\s*</i.test(text)
      ? true
      : (/<(?:\w+:)?isAmendment>/i.test(text) ? false : null),
    amendmentType: rawType ? rawType.toUpperCase() : null,
    amendmentNo: tag('amendmentNo'),
    // Useful in the CMS: NEW HOLDINGS amendments are usually expired
    // confidential treatment, and saying so stops it looking like an error.
    reason: tag('reasonForNonConfidentiality'),
  };
}

/**
 * Classify a filing.
 *
 * `original`      - not an amendment at all.
 * `restatement`   - replaces the earlier report in full.
 * `additional_holdings` - adds positions without disturbing the earlier ones.
 * `unknown`       - an amendment whose type could not be read.
 */
export function classifyFiling(formType, coverPageXml) {
  const form = String(formType || '').toUpperCase();
  if (!form.endsWith('/A')) {
    return { amendmentType: 'original', strategy: 'replace', confident: true, cover: null };
  }

  const cover = parseAmendmentCoverPage(coverPageXml);

  if (cover.amendmentType === 'RESTATEMENT') {
    return { amendmentType: 'restatement', strategy: 'replace', confident: true, cover };
  }
  // The SEC vocabulary is "NEW HOLDINGS"; accept the spacing variants filers
  // actually produce rather than only the canonical one.
  if (cover.amendmentType && /^NEW[\s_-]*HOLDINGS$/.test(cover.amendmentType)) {
    return { amendmentType: 'additional_holdings', strategy: 'merge', confident: true, cover };
  }

  return {
    amendmentType: 'unknown',
    strategy: 'review',
    confident: false,
    cover,
    // Said plainly, because this string reaches an operator.
    reviewReason: cover.amendmentType
      ? `Cover page reports an unrecognised amendmentType "${cover.amendmentType}".`
      : 'The amendment cover page was missing or carried no amendmentType.',
  };
}

/**
 * Apply an amendment to the holdings it amends.
 *
 * `replace` returns the amendment's rows alone. Anything the manager dropped is
 * gone, which is the entire point of a restatement.
 *
 * `merge` keeps every prior row and lets the amendment's rows win on a key
 * collision, so previously withheld positions are added without erasing the
 * ones already disclosed.
 *
 * `review` returns the prior rows untouched. The amendment is recorded but not
 * applied, because applying it either way could be badly wrong.
 */
export function applyAmendment({ strategy, priorRows = [], amendmentRows = [], keyOf }) {
  const key = typeof keyOf === 'function' ? keyOf : (row) => String(row?.cusip || '');

  if (strategy === 'replace') return { rows: amendmentRows, applied: true };
  if (strategy === 'review') return { rows: priorRows, applied: false };

  if (strategy === 'merge') {
    const merged = new Map(priorRows.map((row) => [key(row), row]));
    for (const row of amendmentRows) merged.set(key(row), row);
    return { rows: [...merged.values()], applied: true };
  }

  throw new Error(`Unknown amendment strategy: ${strategy}`);
}

/**
 * Positions the prior report carried that the amendment does not.
 *
 * Under `replace` these are correctly gone; the caller records them so a
 * removal is auditable. Under `merge` they are correctly retained. Computing
 * it in one place means the two cases can be asserted against each other.
 */
export function droppedPositions({ priorRows = [], amendmentRows = [], keyOf }) {
  const key = typeof keyOf === 'function' ? keyOf : (row) => String(row?.cusip || '');
  const kept = new Set(amendmentRows.map(key));
  return priorRows.filter((row) => !kept.has(key(row)));
}
