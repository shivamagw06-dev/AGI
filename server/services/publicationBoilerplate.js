/**
 * Legal and accounting boilerplate, which is not a risk and not an
 * expectation.
 *
 * A filing states its risks in the same grammar it states its disclaimers, so
 * the cues that find "PacifiCorp will incur material additional losses" also
 * find "forward-looking statements are subject to risks and uncertainties".
 * Reviewing Berkshire's two documents, 28 of the 56 claims in these two slots
 * were rejected, and in the quarterly report - which is mostly notes - it was
 * 8 of 11. Every one was boilerplate.
 *
 * Only `risks` and `expectations` consult this. `why` was rejected 7 times in
 * 201 claims and needs no such rule; blocking sentences everywhere would cost
 * real causes to fix a problem those two slots have.
 *
 * Each rule carries the sentence that justified it. A rule without one is a
 * guess about what a filing looks like, and this file is the wrong place to
 * guess: what it removes, nobody ever sees.
 *
 * These rules are deliberately narrow. They match the disclaimer's own
 * machinery - the phrase a lawyer writes and a manager never would - rather
 * than the subject it is about. A rule broad enough to catch the shape of
 * legal prose catches the real disclosures written in the same shape, and the
 * approved "It is reasonably possible that adverse changes ... could result in
 * the recognition of impairment losses in our Consolidated Financial
 * Statements" is the proof: it names the financial statements, it hedges, and
 * it is exactly the sentence this slot exists for.
 */

export const BOILERPLATE = [
  {
    id: 'safe_harbour',
    // "Forward-looking statements are based on current expectations and
    // projections about future events and are subject to risks, uncertainties
    // and assumptions about Berkshire..."
    re: /\bforward[-\s]looking statements?\b/i,
    why: 'a safe-harbour disclaimer about statements, not a statement about the business',
  },
  {
    id: 'results_will_differ',
    // "Actual payments will likely vary, perhaps materially, from any
    // forecasted payments..." and "the actual ultimate claim amounts will
    // likely differ from the currently recorded..."
    re: /\bactual\b[^.!?]{0,80}\bwill likely (?:differ|vary)\b/i,
    why: 'the standard accounting caveat that an estimate is an estimate',
  },
  {
    id: 'amounts_will_be_adjusted',
    // "Accordingly, certain amounts currently recorded in our Consolidated
    // Financial Statements will likely be adjusted in the future based on new
    // available information."
    re: /\bwill likely be adjusted\b/i,
    why: 'a caveat that recorded amounts may change, stating nothing about the business',
  },
  {
    id: 'future_disclosure',
    // "We expect to include such disclosures in our interim Consolidated
    // Financial Statements for the period ending September 30, 2026."
    re: /\bexpect to include\b[^.!?]{0,40}\bdisclosures?\b/i,
    why: 'a promise about a future filing, not about the business',
  },
  {
    id: 'not_materially_different',
    // "Except as otherwise disclosed in this Quarterly Report, our contractual
    // obligations as of June 30, 2026 were, in the aggregate, not materially
    // different from those..." - a statement that nothing changed.
    re: /\bnot materially different\b/i,
    why: 'a statement that nothing changed, which is the opposite of a risk',
  },
  {
    id: 'securities_value_circularity',
    // "Any adverse effect on our business, financial condition or operating
    // results could result in a decline in the value of our securities and the
    // loss of all or part of your investment." True of every company that has
    // ever issued a security.
    re: /\bdecline in the value of (?:our|the) securities\b/i,
    why: 'the generic risk-factor sentence, true of every issuer',
  },
  {
    id: 'generic_risk_summary',
    // "Any of these risks may adversely affect our business, financial
    // condition, results of operations or cash flows." A sentence that refers
    // back to the risks above and names none of them.
    re: /\bany of these risks\b/i,
    why: 'a summary of the risks above, naming none of them',
  },
  {
    id: 'read_the_report',
    // "You should read this Quarterly Report on Form 10-Q completely and
    // understand that our actual future results may be materially different
    // from what we expect."
    re: /\byou should read this (?:quarterly |annual )?report\b|\bactual (?:future )?results may be materially different\b/i,
    why: 'an instruction to the reader, not a statement about the business',
  },
];

/**
 * Whether a sentence is boilerplate, and which rule says so.
 *
 * Returns null for anything no rule matches, so a caller reads it as "keep".
 */
export function boilerplateIn(sentence) {
  const text = String(sentence || '');
  for (const rule of BOILERPLATE) {
    if (rule.re.test(text)) return { id: rule.id, why: rule.why };
  }
  return null;
}

/** The slots that consult the stoplist. */
export const BOILERPLATE_SLOTS = new Set(['risks', 'expectations']);
