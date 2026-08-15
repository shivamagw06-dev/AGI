/**
 * Institutional Ask fallback when the Python engine is cold/OOM.
 * Uses Node AGI intelligence + market snapshot only — never fabricates prices.
 * Shapes output with Response Constitution v1.0 section order when possible.
 */

import { getAgiIntelligence } from './intelligenceService.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

function asText(v, fallback = '') {
  if (v == null) return fallback;
  if (typeof v === 'string') return v.trim();
  if (typeof v === 'object' && typeof v.text === 'string') return v.text.trim();
  return String(v);
}

function plainText(value = '') {
  return String(value)
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;|&#160;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/\s+/g, ' ')
    .trim();
}

function completeSentences(value = '') {
  return plainText(value)
    .split(/(?<=[.!?])\s+(?=[A-Z0-9₹])/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => sentence.length >= 35 && /[.!?]$/.test(sentence));
}

function articleAnalysis(article = {}) {
  const excerpt = plainText(article.excerpt || '');
  const excerptComplete = excerpt.length >= 100 && /[.!?]$/.test(excerpt);
  const fullText = plainText(article.content_md || article.content || '');
  const sentences = completeSentences(excerptComplete ? excerpt : fullText);
  const usable = sentences.filter((sentence) =>
    !/^(agarwal global investments|agi research|published|defence & aerospace|india telecom)/i.test(sentence)
  );
  const summarySentences = (usable.length ? usable : sentences).slice(0, 2);
  const summary = summarySentences.join(' ').slice(0, 1_200).trim() || excerpt || plainText(article.title);
  const candidates = completeSentences(fullText).slice(0, 80);
  const select = (pattern, limit = 3) => candidates.filter((sentence) => pattern.test(sentence)).slice(0, limit);
  const risks = select(/\b(risk|execution|margin|churn|pressure|competition|cash|working capital|delay|weak|downside|uncertain)/i);
  const catalysts = select(/\b(catalyst|order|tariff|revenue|growth|demand|visibility|expansion|pricing|recovery|opportunity)/i);
  const monitoring = [...risks, ...catalysts].slice(0, 4);
  return {
    summary,
    risks: risks.length ? risks : ['Execution against the report’s stated operating assumptions remains the principal risk to monitor.'],
    catalysts: catalysts.length ? catalysts : ['Confirmation of the report’s stated business drivers would strengthen AGI’s published view.'],
    monitoring,
  };
}

function searchTerms(question = '') {
  const ignored = new Set([
    'about', 'agi', 'crore', 'does', 'have', 'india', 'indian', 'order', 'report',
    'says', 'technologies', 'that', 'the', 'this', 'view', 'what', 'with',
  ]);
  return [...new Set(String(question).toLowerCase().match(/[a-z0-9]{3,}/g) || [])]
    .filter((term) => !ignored.has(term));
}

export function rankPublishedResearch(question, rows = []) {
  const terms = searchTerms(question);
  if (!terms.length) return [];
  return rows
    .map((article) => {
      const title = plainText(article?.title).toLowerCase();
      const tags = plainText(Array.isArray(article?.tags) ? article.tags.join(' ') : article?.tags).toLowerCase();
      const body = plainText(`${article?.excerpt || ''} ${article?.content_md || ''} ${article?.content || ''}`).toLowerCase();
      const score = terms.reduce(
        (sum, term) => sum + (title.includes(term) ? 8 : 0) + (tags.includes(term) ? 4 : 0) + (body.includes(term) ? 1 : 0),
        0
      );
      return { article, score };
    })
    .filter(({ score }) => score >= 8)
    .sort((a, b) => b.score - a.score || String(b.article?.published_at || '').localeCompare(String(a.article?.published_at || '')));
}

export async function findPublishedResearch(question) {
  const admin = createSupabaseAdmin();
  if (!admin) return null;
  const { data, error } = await admin
    .from('articles')
    .select('id,title,slug,excerpt,content,content_md,tags,section,published_at')
    .eq('status', 'published')
    .order('published_at', { ascending: false, nullsFirst: false })
    .limit(100);
  if (error) throw error;
  return rankPublishedResearch(question, Array.isArray(data) ? data : [])[0]?.article || null;
}

export function publishedResearchPack(question, article) {
  const analysis = articleAnalysis(article);
  const summary = analysis.summary;
  const url = article.slug ? `/article/${encodeURIComponent(article.slug)}` : '/research';
  const evidence = {
    id: article.id,
    source: 'AGI Research',
    type: 'agi_research',
    title: article.title,
    url,
    href: url,
    published_at: article.published_at || null,
    note: summary,
  };
  const directAnswer = `AGI's published view: ${summary}`;
  const confidenceExplanation = 'High confidence that this reflects AGI\'s house research because it is taken directly from the published report. It is not a fresh independent re-analysis of facts released after that publication.';
  const why = [
    `Matched the question to AGI's published report “${plainText(article.title)}”.`,
    article.published_at ? `Report publication date: ${String(article.published_at).slice(0, 10)}.` : null,
    'The answer preserves the report’s stated view; live market and post-publication developments require a refreshed analysis.',
  ].filter(Boolean);
  const followUps = ['Open the full AGI report', 'What could change AGI\'s view?', 'How material is the order to revenue?', 'What are the execution risks?'];
  const bottomLine = analysis.monitoring.length
    ? `What to monitor: ${analysis.monitoring.slice(0, 3).join(' ')}`
    : `What to monitor: whether subsequent evidence confirms the operating assumptions in AGI's published report.`;
  const responseConstitution = {
    enabled: true,
    version: '1.0',
    direct_answer: directAnswer,
    why_agib_thinks_this: why,
    investment_thesis: {
      business: summary,
      risks: analysis.risks[0],
      catalysts: analysis.catalysts[0],
    },
    bull_vs_bear: {
      bull_case: analysis.catalysts,
      bear_case: analysis.risks,
    },
    bottom_line: bottomLine,
    supporting_intelligence: { evidence_notes: [evidence.note] },
    suggested_follow_ups: followUps,
    confidence: { score: 90, explanation: confidenceExplanation },
  };
  return {
    ok: true,
    question,
    mode: 'published_agi_research_fallback',
    evidence_grade: 'published_agi_research',
    degraded: false,
    retryable: false,
    status: 'evidence_backed',
    intent: 'company_event_analysis',
    executive_summary: directAnswer,
    confidence: 90,
    answer: { executive_summary: directAnswer, summary, why, bottom_line: bottomLine, confidence_explanation: confidenceExplanation, response_constitution: responseConstitution },
    why,
    key_risks: analysis.risks,
    key_catalysts: analysis.catalysts,
    bull_case: analysis.catalysts,
    bear_case: analysis.risks,
    what_changes_view: analysis.monitoring,
    follow_up_questions: followUps,
    answer_construction: { enabled: true, executive: directAnswer, why, bottom_line: bottomLine, confidence_explanation: confidenceExplanation, response_constitution: responseConstitution },
    supporting_research: [evidence],
    supporting_evidence: [evidence],
    evidence_used: [evidence],
    evidence: [evidence],
    ask_orchestration: { engine_reached: false, fallback: true, fallback_used: true, reason: 'published_research_fast_fallback' },
    meta: { surface: 'ask_published_research_fallback', generated_at: new Date().toISOString() },
  };
}

export function mergePublishedResearch(pack, question, article) {
  if (!pack || typeof pack !== 'object' || !article) return pack;
  const articlePack = publishedResearchPack(question, article);
  const primaryEvidence = articlePack.evidence[0];
  const mergeEvidence = (rows) => {
    const combined = [primaryEvidence, ...(Array.isArray(rows) ? rows : [])];
    const seen = new Set();
    return combined.filter((row) => {
      const key = String(row?.id || row?.url || row?.href || row?.title || '').toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };
  const existingExecutive = asText(pack.answer?.executive_summary || pack.executive_summary);
  const publishedExecutive = articlePack.executive_summary;
  const executive = existingExecutive && !existingExecutive.includes(publishedExecutive)
    ? `${publishedExecutive}\n\nCurrent intelligence context: ${existingExecutive}`
    : publishedExecutive;
  const existingWhy = Array.isArray(pack.answer?.why) ? pack.answer.why : Array.isArray(pack.why) ? pack.why : [];
  return {
    ...pack,
    evidence_grade: 'published_agi_research',
    published_research_match: {
      id: article.id,
      title: article.title,
      slug: article.slug,
      published_at: article.published_at || null,
      role: 'primary_evidence',
    },
    executive_summary: executive,
    answer: {
      ...(pack.answer || {}),
      executive_summary: executive,
      summary: publishedExecutive,
      why: [...articlePack.why, ...existingWhy].slice(0, 8),
    },
    why: [...articlePack.why, ...existingWhy].slice(0, 8),
    supporting_research: mergeEvidence(pack.supporting_research),
    supporting_evidence: mergeEvidence(pack.supporting_evidence),
    evidence_used: mergeEvidence(pack.evidence_used),
    evidence: mergeEvidence(pack.evidence),
    ask_orchestration: {
      ...(pack.ask_orchestration || {}),
      published_research: {
        matched: true,
        article_id: article.id,
        title: article.title,
        role: 'primary_evidence',
      },
    },
  };
}

export async function buildAskDeskFallback(question) {
  const q = String(question || '').trim();
  try {
    const article = await findPublishedResearch(q);
    if (article) return publishedResearchPack(q, article);
  } catch {
    // Supabase retrieval is best-effort; retain the honest market-only fallback.
  }
  let intel = null;
  try {
    intel = await getAgiIntelligence();
  } catch {
    intel = null;
  }

  const summary =
    asText(intel?.summary) ||
    asText(intel?.outlook?.summary) ||
    'AGIB research desk is warming up. Below is the latest institutional market context from the live Node intelligence gateway.';

  const sectors = Array.isArray(intel?.sectors) ? intel.sectors.slice(0, 6) : [];
  const stocks = Array.isArray(intel?.stocksInFocus) ? intel.stocksInFocus.slice(0, 6) : [];
  const indices = Array.isArray(intel?.indexSentiments) ? intel.indexSentiments.slice(0, 8) : [];
  const bias = asText(intel?.outlook?.bias) || 'Monitoring';

  // Honest unavailable posture — do NOT pretend the market blurb answers the research question.
  const directAnswer =
    `AGIB could not complete a research answer for “${q}” because the intelligence engine did not respond in time. ` +
    `This is not a finished company or macro brief. Retry Ask in a moment. ` +
    `While the desk recovers, live market context reads: ${summary}`;
  const why = [
    'Node gateway fallback: the Python research engine timed out, returned 5xx/HTML, or was unreachable.',
    'No company-level evidence pack was retrieved for this question on the fallback path.',
    indices[0]
      ? `${indices[0].label || 'Index'} currently reads ${indices[0].sentiment || 'mixed'} (${indices[0].strength || 'AGI model'}) — market context only.`
      : 'Index sentiment models are syncing; treat this as market context, not a research conclusion.',
    sectors[0]
      ? `Sector tape focus: ${sectors[0].name || sectors[0].label || 'leadership'} (not evidence for the asked question).`
      : 'Sector leadership will refresh with the next market cycle.',
  ].filter(Boolean);

  const bull = stocks[0]
    ? [`Names in focus such as ${stocks[0].name || stocks[0].symbol || 'leaders'} stay on the institutional watchlist because liquidity and attention are concentrated there.`]
    : ['A clearer risk-on tape would support cyclical and growth leadership if earnings hold up.'];
  const bear = [
    'Because the full company evidence pack is offline, any single-name conclusion would be too thin — investors should treat this as market context, not a finished thesis.',
  ];

  const bottomLine =
    `Bottom line: AGIB can share live market context while the research desk restarts, but confidence is limited until company-level evidence returns. ` +
    `Current desk bias reads ${bias}. Retry Ask AGI in a moment for the full constitution-shaped brief.`;

  const confidenceExplanation =
    'AGIB has limited confidence (45%) because this answer uses the Node market gateway while the Python research desk is unavailable.';

  const followUps = [
    'Retry the full research desk',
    'Market outlook tomorrow',
    'Which sectors are in focus?',
    'What is driving index sentiment?',
  ];

  const responseConstitution = {
    enabled: true,
    version: '1.0',
    programme: 'AGIB Response Constitution — Human First Institutional Research',
    section_order: [
      'direct_answer',
      'why_agib_thinks_this',
      'investment_thesis',
      'bull_vs_bear',
      'bottom_line',
      'supporting_intelligence',
      'suggested_follow_ups',
    ],
    direct_answer: directAnswer,
    why_agib_thinks_this: why,
    investment_thesis: {
      business: 'Company-level business detail will return when the research desk is warm.',
      growth: 'Near-term growth debate is being framed through live sector and index context only.',
      financial_quality: 'Financial statements are not available in this fallback path.',
      valuation: 'Valuation conclusions are withheld until the full engine reloads evidence.',
      risks: bear[0],
      catalysts: 'A successful desk restart and the next earnings/news cycle are the main checkpoints.',
    },
    bull_vs_bear: { bull_case: bull, bear_case: bear },
    bottom_line: bottomLine,
    supporting_intelligence: {
      layers: ['Market Intelligence', 'Sector Intelligence'],
      evidence_notes: why,
    },
    suggested_follow_ups: followUps,
    confidence: { score: 45, explanation: confidenceExplanation },
    voice: 'human_first_institutional_research',
    degraded: true,
  };

  return {
    ok: true,
    question: q,
    mode: 'node_desk_fallback',
    degraded: true,
    retryable: true,
    status: 'degraded',
    intent: 'unavailable',
    entities: { ticker: null, companies: [] },
    providers_queried: [],
    internet_used: false,
    fabricated: false,
    executive_summary: directAnswer,
    confidence: 45,
    ask_orchestration: {
      engine_reached: false,
      fallback: true,
      fallback_used: true,
      reason: 'node_desk_fallback',
      diagnostics_visibility: 'internal',
      evidence: {
        retrieved: 0,
        ranked: 0,
        passed: 0,
        referenced: 0,
        utilization: 0,
        efficiency: 0,
        precision: 0,
      },
    },
    answer: {
      executive_summary: directAnswer,
      summary,
      why,
      house_view_label: bias,
      bottom_line: bottomLine,
      confidence_explanation: confidenceExplanation,
      response_constitution: responseConstitution,
      answer_structure: 'response_constitution_v1',
    },
    why,
    bull_case: bull,
    bear_case: bear,
    follow_up_questions: followUps,
    answer_construction: {
      enabled: true,
      executive: directAnswer,
      why,
      bottom_line: bottomLine,
      confidence_explanation: confidenceExplanation,
      response_constitution: responseConstitution,
      answer_structure: 'response_constitution_v1',
    },
    market_context: {
      breadth: intel?.breadth || null,
      outlook: intel?.outlook || null,
      index_sentiments: indices,
      sectors,
      stocks_in_focus: stocks,
      disclaimer: intel?.disclaimer || 'AGI proprietary analytics · Not raw exchange data',
    },
    evidence: [
      {
        source: 'agi_node_intelligence',
        title: 'Live market intelligence gateway',
        note: 'Served while the Python research desk restarts.',
      },
    ],
    note:
      'Research desk unavailable or restarting. This is an institutional Node fallback — retry Ask AGI in a moment for the full engine brief.',
    meta: {
      surface: 'ask_fallback',
      ui_version: 'ask-desk-fallback-v1',
      generated_at: new Date().toISOString(),
    },
  };
}
