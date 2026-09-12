import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { enqueueIntelligenceLearning } from './intelligenceLearningJobs.js';

const asArray = (value) => (Array.isArray(value) ? value.filter(Boolean) : []);
const clamp = (value, fallback = 0.5) => {
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : fallback;
};

export function sourceAuthority(documentType = '', source = '') {
  const blob = `${documentType} ${source}`.toLowerCase();
  if (/rbi|sebi|government|mospi|ministry|regulator|official filing|nse_bse_filing|sec_filing/.test(blob)) return { tier: 1, reliability: 0.95 };
  if (/earnings_transcript|official release|investor presentation|annual_report|quarterly_report/.test(blob)) return { tier: 2, reliability: 0.9 };
  if (/capital iq|bloomberg|institutional|broker_research|buy_side|sell_side/.test(blob)) return { tier: 3, reliability: 0.82 };
  if (/reuters|financial times|economist|mint|business standard|financial publication|market_news/.test(blob)) return { tier: 4, reliability: 0.75 };
  if (/agi_research|agi_note|agi_cio|agi_investment/.test(blob)) return { tier: 5, reliability: 0.8 };
  if (/blog|opinion|newsletter/.test(blob)) return { tier: 6, reliability: 0.58 };
  return { tier: 7, reliability: 0.45 };
}

function claimRows(research = {}, investment = {}) {
  const subject = asArray(investment.companies)[0] || asArray(investment.tickers)[0] || null;
  const horizon = research.time_horizon || null;
  const rows = [];
  const add = (claimType, factOpinion, stance, values, predicate) => {
    for (const value of asArray(values)) {
      rows.push({ claim_type: claimType, fact_opinion: factOpinion, stance, subject, predicate, object_text: String(value), time_horizon: horizon, confidence: 0.65 });
    }
  };
  if (research.investment_thesis) add('thesis', 'analysis', 'supporting', [research.investment_thesis], 'investment_thesis');
  add('bull_case', 'analysis', 'supporting', research.bull_case, 'supports');
  add('bear_case', 'analysis', 'opposing', research.bear_case, 'challenges');
  add('counter_argument', 'analysis', 'opposing', research.counter_arguments, 'challenges');
  add('forecast', 'forecast', 'neutral', research.forecasts, 'forecasts');
  add('risk', 'analysis', 'opposing', research.risks, 'risk');
  add('catalyst', 'analysis', 'supporting', research.catalysts, 'catalyst');
  add('assumption', 'assumption', 'neutral', research.assumptions, 'assumes');
  add('evidence', 'fact', 'neutral', research.supporting_evidence, 'supported_by');
  return rows;
}

function entityRows(investment = {}) {
  const groups = {
    company: investment.companies,
    ticker: investment.tickers,
    industry: investment.industries,
    sector: investment.sectors,
    country: investment.countries,
    theme: investment.themes,
    macro_topic: investment.macro_topics,
  };
  return Object.entries(groups).flatMap(([entity_type, values]) =>
    asArray(values).map((canonical_name) => ({ entity_type, canonical_name: String(canonical_name), confidence: 0.8 }))
  );
}

function relationshipRows(investment = {}) {
  const anchors = asArray(investment.tickers).length ? asArray(investment.tickers) : asArray(investment.companies);
  const targets = [
    ['operates_in_sector', investment.sectors],
    ['operates_in_industry', investment.industries],
    ['exposed_to_theme', investment.themes],
    ['exposed_to_macro_topic', investment.macro_topics],
    ['operates_in_country', investment.countries],
  ];
  return anchors.flatMap((source_entity) => targets.flatMap(([relation, values]) =>
    asArray(values).map((target_entity) => ({ source_entity: String(source_entity), relation, target_entity: String(target_entity), confidence: 0.75 }))
  ));
}

export async function persistResearchKnowledge({ job, ingestResult, verified = true } = {}) {
  const admin = createSupabaseAdmin();
  if (!admin) return { ok: false, skipped: true, reason: 'Supabase admin unavailable' };
  const doc = ingestResult || {};
  const metadata = doc.document || {};
  const investment = doc.investment || {};
  const research = doc.research || {};
  const knowledge = doc.knowledge || {};
  const authority = sourceAuthority(metadata.document_type || job?.payload?.document_type, metadata.source || job?.payload?.source);
  const articleId = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(job?.article_id || ''))
    ? String(job.article_id)
    : null;
  const documentRow = {
    article_id: articleId,
    kip_document_id: job?.document_id || doc.document_id,
    content_hash: job?.content_hash,
    title: metadata.title || job?.payload?.title || 'Untitled source',
    slug: job?.slug || job?.payload?.metadata?.slug || null,
    author: metadata.author || job?.payload?.author || null,
    publisher: metadata.source || job?.payload?.source || null,
    publication_date: metadata.date || job?.payload?.date || null,
    document_type: metadata.document_type || job?.payload?.document_type || 'agi_research',
    language: metadata.language || job?.payload?.language || 'en',
    source_tier: authority.tier,
    source_reliability: clamp(knowledge.source_reliability, authority.reliability),
    confidence: clamp(knowledge.confidence, 0.5),
    quality: clamp(job?.quality, 0.7),
    summary: knowledge.summary || null,
    topics: [...new Set([...asArray(investment.themes), ...asArray(investment.macro_topics)])],
    keywords: [...new Set([...asArray(investment.tickers), ...asArray(investment.sectors), ...asArray(investment.industries)])],
    related_document_ids: asArray(knowledge.related_documents),
    pipeline_stages: asArray(doc.pipeline_stages),
    validation_status: verified ? 'validated' : 'pending',
    embedding_version: job?.embedding_version || null,
    knowledge_version: doc.knowledge_version || null,
    source_metadata: job?.payload?.metadata || {},
    validated_at: verified ? new Date().toISOString() : null,
    updated_at: new Date().toISOString(),
  };
  const { data: saved, error } = await admin
    .from('research_knowledge_documents')
    .upsert(documentRow, { onConflict: 'kip_document_id' })
    .select('id')
    .single();
  if (error) return { ok: false, error: error.message || String(error) };

  const documentId = saved.id;
  await Promise.all([
    admin.from('research_knowledge_entities').delete().eq('document_id', documentId),
    admin.from('research_knowledge_claims').delete().eq('document_id', documentId),
    admin.from('research_knowledge_relationships').delete().eq('document_id', documentId),
  ]);
  const entities = entityRows(investment).map((row) => ({ ...row, document_id: documentId }));
  const claims = claimRows(research, investment).map((row) => ({ ...row, document_id: documentId }));
  const relationships = relationshipRows(investment).map((row) => ({ ...row, document_id: documentId }));
  const writes = [];
  if (entities.length) writes.push(admin.from('research_knowledge_entities').insert(entities));
  if (claims.length) writes.push(admin.from('research_knowledge_claims').insert(claims));
  if (relationships.length) writes.push(admin.from('research_knowledge_relationships').insert(relationships));
  const results = await Promise.all(writes);
  const childError = results.find((result) => result.error)?.error;
  if (childError) return { ok: false, document_id: documentId, error: childError.message || String(childError) };
  const learning = await enqueueIntelligenceLearning(documentId).catch((error) => ({
    ok: false,
    skipped: true,
    reason: 'enqueue_exception',
    error: error?.message || String(error),
  }));
  return { ok: true, document_id: documentId, entities: entities.length, claims: claims.length, relationships: relationships.length, validation_status: documentRow.validation_status, learning };
}

export async function getResearchKnowledgeCard(articleId) {
  const admin = createSupabaseAdmin();
  if (!admin) return null;
  const { data: document, error } = await admin
    .from('research_knowledge_documents')
    .select('*')
    .eq('article_id', articleId)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error || !document) return null;
  const [entities, claims, relationships] = await Promise.all([
    admin.from('research_knowledge_entities').select('*').eq('document_id', document.id),
    admin.from('research_knowledge_claims').select('*').eq('document_id', document.id),
    admin.from('research_knowledge_relationships').select('*').eq('document_id', document.id),
  ]);
  return { document, entities: entities.data || [], claims: claims.data || [], relationships: relationships.data || [] };
}
