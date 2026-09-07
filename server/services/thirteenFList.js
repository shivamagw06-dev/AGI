/**
 * The SEC's own quarterly list of Section 13(f) securities, as an identity source.
 *
 * Every quarter the SEC publishes the complete list of securities eligible for
 * 13F reporting: CUSIP, issuer name, a class description, and whether the line
 * was added or deleted that quarter. It is free, authoritative, and - the part
 * that matters here - it is published *per quarter*, which makes it
 * point-in-time by construction rather than by assumption.
 *
 * That is what was missing. OpenFIGI answers one question: what does this CUSIP
 * map to *now*. It has no view of what a CUSIP meant in 2019, and no view of
 * securities whose CUSIP has since changed. Both gaps were producing the same
 * symptom - "No identifier found" on securities that are real, listed and
 * heavily held - and the two are distinguishable only against a source that
 * knows what each quarter looked like.
 *
 * Measured against the 2026 Q2 list, the forty largest unresolved holdings in
 * our data broke down as:
 *
 *   17  common equity   real and listed; the vendor simply lacks the CUSIP
 *   12  CUSIP changed   Aptiv, Labcorp, Unilever, Cooper, Qiagen, Cushman
 *    8  convertible notes
 *    3  preferred
 *
 * So roughly seventy per cent was an identity problem and thirty per cent was
 * instruments that are not common equity and never will be. Before this source
 * existed both looked identical from the outside, which is why a backoff was
 * nearly shipped that would have set the first group aside along with the
 * second.
 *
 * Licensing. The list carries a CUSIP Global Services / American Bankers
 * Association copyright and the notice "No redistribution without permission".
 * Preparing and processing 13F data is the list's stated purpose, so resolving
 * identity against it server-side is within that. Issuer names and tickers we
 * derive are not CGS data and can be shown. The list itself is not republished
 * and is not exposed through any API.
 */

/**
 * Rows in the PDF text extract arrive as one field per line, in this order:
 *
 *   G0403H        issuer number, six characters
 *   10            issue number, two characters
 *   8             check digit
 *   *             present when the issue also has listed options
 *   AON PLC       issuer name
 *   SHS CL A      issuer description - the class
 *   ADDED         optional; ADDED or DELETED this quarter
 *
 * The three-part CUSIP is why the option encoding is legible at all. Issue
 * number 90 is the call and 95 the put on the same issuer:
 *
 *   G0403H 10 8 * AON PLC  SHS CL A
 *   G0403H 90 8   AON PLC  CALL
 *   G0403H 95 8   AON PLC  PUT
 */
const ISSUER = /^[0-9A-Z]{6}$/;
const ISSUE = /^[0-9A-Z]{2}$/;
const CHECK = /^[0-9]$/;
const STATUS = new Set(['ADDED', 'DELETED']);

/**
 * Classify a security from the SEC's own description.
 *
 * This is the field that was missing. "Western Digital" is an equity, a
 * convertible note and a pair of options all at once, and the holdings table
 * carries all of them under the same issuer name. Guessing from the name
 * relabels the note as the stock; reading the class does not.
 *
 * Order matters. A description like "NOTE 3.000%11/1" contains no equity word
 * and "SER A MAND CNV" contains no debt word, but "DEP CONV PFD A" would match
 * a loose equity pattern on the "A", so the narrower classes are tested first.
 */
export function classifySecurity(description) {
  const d = String(description || '').trim().toUpperCase();
  if (!d) return 'unknown';
  if (d === 'CALL' || d === 'PUT') return 'option';
  if (/\b(NOTE|DEB|BOND|SR NT|CV SR)\b/.test(d)) return 'debt';
  if (/\b(PFD|PREFERRED|MAND CNV|DEP CONV)\b/.test(d)) return 'preferred';
  // A dated instrument is a warrant, right or SPAC unit. An undated "unit" is
  // a trust unit - the tradeable share of a unit investment trust. The
  // difference is the whole ETF universe: SPY is "TR UNIT" and QQQ is
  // "UNIT SER 1", while a SPAC unit is "UNIT 05/22/2031". Matching \bUNIT\b
  // without the date excludes the two most widely held securities in 13F data.
  if (/^\*W\b|\bWARRANT\b|\bWTS?\b/.test(d)) return 'derivative';
  if (/\b(RIGHT|UNIT)\b.*\d{2}\/\d{2}\/\d{2,4}/.test(d)) return 'derivative';
  if (/\b(COM|ORD|SHS|SHARES|ADR|ADS|COMMON|SH BEN INT|CL [A-Z]|UNIT|ETF|FD|FUND)\b/.test(d)) return 'equity';
  // Not "definitely not equity" - merely not classified. The list truncates
  // descriptions at 28 characters, and for funds that field carries the fund's
  // name rather than a class code ("CORE S&P500 ETF", "RUSSELL 2000 ETF"), so
  // a great many real, tradeable securities land here. Callers must treat this
  // as unknown and still attempt vendor resolution; treating it as an
  // exclusion would drop a fifth of the list.
  return 'other';
}

/**
 * Parse the text extracted from one quarterly list.
 *
 * Driven off the CUSIP triple rather than off line offsets, because the page
 * furniture - run date, page number, column headers - repeats throughout the
 * document and is not a fixed number of lines. A run of three lines shaped like
 * an issuer number, an issue number and a check digit is the record marker;
 * everything else is skipped.
 */
export function parseThirteenFList(text, { quarter = null } = {}) {
  const lines = String(text || '').split('\n');
  const records = [];
  let i = 0;

  while (i < lines.length - 4) {
    const issuer = lines[i].trim();
    const issue = lines[i + 1].trim();
    const check = lines[i + 2].trim();

    if (!ISSUER.test(issuer) || !ISSUE.test(issue) || !CHECK.test(check)) {
      i += 1;
      continue;
    }

    let cursor = i + 3;
    // A bare asterisk marks an issue that also has listed options. It sits
    // between the check digit and the name, so it has to be consumed before
    // the name is read or every optioned security's name becomes "*".
    const hasOptions = lines[cursor]?.trim() === '*';
    if (hasOptions) cursor += 1;

    const name = lines[cursor]?.trim() || '';
    const description = lines[cursor + 1]?.trim() || '';
    let status = '';
    if (STATUS.has(lines[cursor + 2]?.trim())) {
      status = lines[cursor + 2].trim();
      cursor += 1;
    }

    records.push({
      cusip: issuer + issue + check,
      issuer_number: issuer,
      issue_number: issue,
      issuer_name: name,
      description,
      security_class: classifySecurity(description),
      has_listed_options: hasOptions,
      status,
      quarter,
    });

    i = cursor + 2;
  }

  return records;
}

/**
 * Normalise an issuer name for matching across quarters and against the SEC's
 * ticker file.
 *
 * The two sources spell the same company differently - "COOPER COS INC" against
 * "COOPER COMPANIES, INC." - and the list itself truncates at 28 characters, so
 * "TWO HARBORS INVENTMENT CORPO" is what a real row looks like, typo included.
 * Suffixes carry no identity and are dropped; what remains is compared.
 *
 * Comparison is exact after normalisation, never fuzzy. The list truncates at
 * 28 characters and carries the occasional typo - "TWO HARBORS INVENTMENT
 * CORPO" is a real row - so some securities will not match and will stay
 * unmapped. That is the intended outcome: a near-miss resolved by edit distance
 * is a guess, and a guess here labels one company's holdings with another
 * company's ticker.
 */
export function normaliseIssuerName(value) {
  let s = String(value || '').toUpperCase();
  s = s.replace(/[^A-Z0-9 ]+/g, ' ');
  const noise = ['INCORPORATED', 'INC', 'CORPORATION', 'CORP', 'CORPO', 'COMPANY', 'COMPANIES',
    'CO', 'COS', 'PLC', 'LTD', 'LIMITED', 'LLC', 'LP', 'HOLDINGS', 'HLDGS', 'HLDG', 'HOLDING',
    'GROUP', 'GRP', 'THE', 'AND', 'NV', 'SA', 'AG', 'AB', 'ASA', 'NEW', 'CLASS', 'COM', 'TR', 'TRUST'];
  for (const word of noise) s = s.replace(new RegExp(`\\b${word}\\b`, 'g'), ' ');
  return s.replace(/\s+/g, ' ').trim();
}

/**
 * Chain a CUSIP's identity across quarters.
 *
 * A security whose CUSIP changes appears under one identifier up to some
 * quarter and a different one afterwards. Recovering that turns "Aptiv is not
 * in the vendor's index" into "Aptiv was G6095L109 and is now G3265R107".
 *
 * Sharing a name is not enough, and three rules were tried before one held.
 *
 * Grouping on name alone produced 534 renames across two quarters, all of them
 * coexistence: AstraZeneca carries G0593M107 for the ordinary shares and
 * 046353108 for the sponsored ADR at the same time.
 *
 * Requiring that identifiers never share a quarter rejected every real rename,
 * because both are listed during the changeover.
 *
 * What separates them is whether the old identifier *continues*. So each link
 * holds when one identifier's last quarter is exactly the next one's first.
 * Later means they ran alongside; earlier leaves a gap, and Seadrill absent for
 * five years before a same-named line appears is not evidence of a rename.
 *
 * There is one more case, and it is the reason `throughQuarter` exists. When
 * the changeover falls in the last quarter loaded, the evidence that would
 * settle it - does the old identifier appear again? - has not been published
 * yet. Ascendis shows 04351P101 across seven years and K08588103 in the final
 * quarter alone, which is the exact shape of both a rename in progress and a
 * newly listed second class. 239 of 1,660 chains ended on such a link. Those
 * links are left uncrossed until another quarter exists to decide them.
 *
 * A link that fails for any of these reasons ends a chain rather than voiding
 * the group, so ReTo's four verified reverse splits are kept and only its
 * unproven fifth is held back.
 *
 * Only equities are considered. Two bonds from one issuer share a name and a
 * class while being entirely different instruments.
 */
export function chainIdentities(records, { throughQuarter = null } = {}) {
  const groups = new Map();
  let latest = throughQuarter || '';
  for (const record of records || []) {
    if (record?.quarter && record.quarter > latest) latest = record.quarter;
    if (record?.security_class !== 'equity') continue;
    const key = normaliseIssuerName(record.issuer_name);
    if (!key) continue;
    if (!groups.has(key)) groups.set(key, new Map());
    const byCusip = groups.get(key);
    if (!byCusip.has(record.cusip)) {
      byCusip.set(record.cusip, { cusip: record.cusip, quarters: new Set(), issuer_name: record.issuer_name });
    }
    if (record.quarter) byCusip.get(record.cusip).quarters.add(record.quarter);
  }
  const edge = throughQuarter || latest;
  const lastOf = (entry) => entry.quarters[entry.quarters.length - 1] || '';

  const out = [];
  for (const [key, byCusip] of groups) {
    const ordered = [...byCusip.values()]
      .map((entry) => ({ ...entry, quarters: [...entry.quarters].sort() }))
      .sort((a, b) => (a.quarters[0] || '').localeCompare(b.quarters[0] || ''));

    let segment = [ordered[0]];
    let heldAtEdge = false;

    const flush = () => {
      out.push({
        name_key: key,
        // The earliest identifier in the segment, so history filed under the
        // old CUSIP is not orphaned when the identifier changes.
        security_key: segment[0]?.cusip || null,
        issuer_name: segment[0]?.issuer_name || null,
        cusips: segment,
        changed_identifier: segment.length > 1,
        // The chain was cut because the changeover sits on the edge of the
        // loaded window. Another quarter may join these two segments; until
        // one exists, they are kept apart.
        held_at_edge: heldAtEdge,
      });
      heldAtEdge = false;
    };

    for (let i = 1; i < ordered.length; i += 1) {
      const ends = lastOf(segment[segment.length - 1]);
      const begins = ordered[i].quarters[0] || '';
      const joins = ends === begins;
      const unproven = joins && ends === edge;
      if (joins && !unproven) {
        segment.push(ordered[i]);
        continue;
      }
      heldAtEdge = unproven;
      flush();
      segment = [ordered[i]];
    }
    flush();
  }
  return out;
}
