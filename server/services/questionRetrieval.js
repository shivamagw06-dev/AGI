/**
 * Finding sentences for a question nobody wrote a pattern for.
 *
 * Thirteen of the hundred have no retrieval rule, and several of them are the
 * ones a reader most wants: what the company sells, how it makes money, how
 * seasonal revenue is. A paragraph answers those and a regular expression does
 * not, and a rule loose enough to catch them catches most of a report.
 *
 * So the question retrieves for itself. Its own content words are the query,
 * and the sentences that use most of them are the candidates. This finds
 * nothing a pattern would have found better; it finds something where there
 * was nothing, and hands it to a tier that checks every figure it produces and
 * may refuse.
 *
 * Deliberately crude. It is a way of putting plausible evidence in front of a
 * verifier, not a way of deciding an answer, and its output is never published
 * without a person reading it.
 */

// Words that appear in almost every sentence and would otherwise decide the
// ranking. "What is the company's EBITDA margin" must not match on "is".
const STOPWORDS = new Set([
  'what', 'which', 'how', 'who', 'when', 'where', 'why', 'does', 'did', 'do', 'is', 'are',
  'was', 'were', 'the', 'a', 'an', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'from',
  'by', 'with', 'at', 'as', 'it', 'its', 'that', 'this', 'there', 'their', 'has', 'have',
  'had', 'been', 'be', 'company', 'companys', 'business', 'much', 'many', 'any', 'much',
  'about', 'into', 'over', 'than', 'then', 'they', 'them', 'you', 'your', 'our', 'we',
]);

const words = (text) => String(text || '').toLowerCase().match(/[a-z][a-z'-]{2,}/g) || [];

/** The content words a question is asking about. */
export function queryOf(question) {
  const seen = new Set();
  for (const word of words(question?.ask)) {
    const stem = word.replace(/(?:ies|ing|ed|s)$/, '');
    if (STOPWORDS.has(word) || stem.length < 3) continue;
    seen.add(stem);
  }
  return [...seen];
}

/**
 * Sentences that use the question's words, best first.
 *
 * Scored by how many distinct query words a sentence uses, because a sentence
 * that mentions two of them is about the subject and one that repeats a single
 * word is usually not. Ties break towards the shorter sentence: a long one
 * matching the same words is more likely to be a list or a table row.
 */
export function candidatesFor(question, sentences, { limit = 6, minimum = 2 } = {}) {
  const query = queryOf(question);
  if (query.length < 2) return [];
  const scored = [];
  for (const entry of sentences || []) {
    const text = typeof entry === 'string' ? entry : entry?.text;
    if (!text) continue;
    const used = new Set();
    const low = text.toLowerCase();
    for (const stem of query) if (low.includes(stem)) used.add(stem);
    // A question with few words cannot demand many matches.
    if (used.size < Math.min(minimum, query.length)) continue;
    scored.push({ text, score: used.size, length: text.length });
  }
  scored.sort((a, b) => (b.score - a.score) || (a.length - b.length));
  return scored.slice(0, limit).map(({ text }) => ({ text }));
}

/**
 * Document vocabulary for questions no pattern reaches.
 *
 * The question's own words do not work: "What does the company actually sell?"
 * shares no word with "The Company is engaged in activities spanning across
 * hydrocarbon exploration and production", which is the answer. An analyst and
 * a filing describe the same thing in different language, which is the same
 * lesson as remuneration against compensation.
 *
 * So these are the filing's words, not the question's. They are a query rather
 * than a rule: the sentences using most of them are put in front of the
 * judgement tier, which grounds an answer in them or refuses. A term that
 * retrieves the wrong sentence costs a refusal, not a wrong answer - which is
 * why a looser instrument is affordable here and was not affordable in FINDS.
 */
export const SUBJECT_TERMS = new Map([
  [1, ['engaged in', 'products', 'services', 'businesses span', 'portfolio of businesses', 'manufactures', 'refining', 'retailing']],
  [2, ['revenue from operations', 'revenue streams', 'business model', 'monetis', 'subscription', 'tariff']],
  [9, ['recurring revenue', 'subscription revenue', 'annuity', 'contracted revenue']],
  [13, ['acquisition contributed', 'organic growth', 'inorganic', 'acquired during the year']],
  [20, ['seasonal', 'festive season', 'monsoon']],
  [51, ['maintenance capex', 'sustaining capital', 'maintenance capital expenditure']],
  [52, ['growth capex', 'expansion project', 'growth capital expenditure', 'growth projects']],
  [56, ['commissioned', 'expected to be commissioned', 'on stream', 'scheduled for completion']],
  [58, ['expected returns', 'payback', 'internal rate of return', 'project returns']],
  [26, ['costs increased', 'cost inflation', 'expenses increased', 'input costs']],
  [27, ['fixed costs', 'variable costs', 'operating leverage']],
  [83, ['top five customers', 'top ten customers', 'largest customers']],
  [84, ['contract expires', 'contract renewal', 'up for renewal', 'expiry of the contract']],
  [87, ['single source', 'sole supplier', 'dependent on one', 'supplier concentration']],
  [98, ['promoter', 'shareholding pattern', 'beneficially own', 'shares pledged']],
]);

/**
 * The sentences to put in front of a judgement for one question.
 *
 * A question with a retrieval rule uses it; one without falls back to its
 * subject terms. A question with neither gets nothing, and the tier refuses
 * rather than reasoning from whatever happened to be nearby.
 */
export function evidenceSentencesFor(question, sentences, { finds, limit = 6 } = {}) {
  const pattern = finds?.get?.(question?.n);
  const matched = [];
  if (pattern) {
    for (const entry of sentences || []) {
      const text = typeof entry === 'string' ? entry : entry?.text;
      if (!text || !pattern.test(text)) continue;
      matched.push({ text });
      if (matched.length >= limit) break;
    }
  }
  if (matched.length) return matched;
  // The pattern found nothing, so the subject terms get a turn. Question 20
  // looks for "seasonal" and Reliance writes "PVC demand declined by 6.4%
  // mainly in pipe sector on account of extended monsoon season" - a pattern
  // tuned on one filing should not stop a looser query on another, when what
  // it retrieves goes to a tier that can refuse it.
  const terms = SUBJECT_TERMS.get(question?.n);
  if (!terms) return [];
  return candidatesFor({ ask: terms.join(' ') }, sentences, { limit, minimum: 1 });
}
