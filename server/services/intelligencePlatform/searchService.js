import { readEntities } from './store.js';
import {
  searchGroupForType,
  SEARCH_GROUP_ORDER,
  entityTypeLabel,
  entityPublicPath,
  nodeColorForType,
} from './entityTypes.js';
import { computeIntelligenceScore } from './intelligenceScoreService.js';

function scoreEntity(entity, query) {
  const q = query.toLowerCase();
  let score = 0;
  const name = (entity.name || '').toLowerCase();
  if (name === q) score += 100;
  else if (name.startsWith(q)) score += 60;
  else if (name.includes(q)) score += 40;

  const desc = (entity.description || '').toLowerCase();
  if (desc.includes(q)) score += 15;

  (entity.tags || []).forEach((tag) => {
    if (String(tag).toLowerCase().includes(q)) score += 20;
  });

  const meta = entity.metadata || {};
  Object.values(meta).forEach((v) => {
    if (String(v).toLowerCase().includes(q)) score += 5;
  });

  return score;
}

function serializeSearchResult(entity, score) {
  const meta = entity.metadata || {};
  const intel = computeIntelligenceScore(entity.id);
  return {
    id: entity.id,
    slug: entity.slug,
    name: entity.name,
    entity_type: entity.entity_type,
    entity_type_label: entityTypeLabel(entity.entity_type),
    description: entity.description?.slice(0, 140) || '',
    ai_summary: entity.ai_summary?.slice(0, 180) || '',
    logo: meta.logo || null,
    color: nodeColorForType(entity.entity_type),
    score,
    path: entityPublicPath(entity),
    updated_at: entity.updated_at,
    intelligence_score: intel?.score,
    intelligence_label: intel?.label,
    metadata: {
      aum: meta.aum,
      industry: meta.industry,
      status: meta.status,
      hq: meta.hq,
    },
  };
}

export function universalSearch(query, { limit = 8 } = {}) {
  const q = String(query || '').trim();
  if (!q || q.length < 2) {
    return { query: q, groups: [], total: 0, took_ms: 0 };
  }

  const start = Date.now();
  const entities = readEntities().filter((e) => e.status === 'published');
  const scored = entities
    .map((entity) => ({ entity, score: scoreEntity(entity, q) }))
    .filter((row) => row.score > 0)
    .sort((a, b) => b.score - a.score);

  const grouped = {};
  scored.forEach(({ entity, score }) => {
    const group = searchGroupForType(entity.entity_type);
    if (!grouped[group]) grouped[group] = [];
    if (grouped[group].length < limit) {
      grouped[group].push(serializeSearchResult(entity, score));
    }
  });

  const groups = SEARCH_GROUP_ORDER
    .filter((name) => grouped[name]?.length)
    .map((name) => ({ name, results: grouped[name] }));

  Object.keys(grouped).forEach((name) => {
    if (!groups.find((g) => g.name === name)) {
      groups.push({ name, results: grouped[name] });
    }
  });

  return {
    query: q,
    groups,
    total: scored.length,
    took_ms: Date.now() - start,
  };
}

export function searchSuggestions(query, { limit = 6 } = {}) {
  const result = universalSearch(query, { limit: 3 });
  return result.groups.flatMap((g) => g.results).slice(0, limit);
}

export { entityPublicPath };
