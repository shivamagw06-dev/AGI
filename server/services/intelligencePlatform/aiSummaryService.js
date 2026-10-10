import { completeChat } from '../llmClient.js';
import { updateEntity, getEntityById } from './entityStore.js';
import { getEntityRelationships } from './relationshipStore.js';
import { listTimelineEvents } from './timelineService.js';
import { entityTypeLabel } from './entityTypes.js';

function buildDeterministicSummary(entity, relationships, timeline) {
  const type = entityTypeLabel(entity.entity_type);
  const meta = entity.metadata || {};
  const relNames = relationships
    .slice(0, 5)
    .map((r) => r.other_entity?.name)
    .filter(Boolean);

  const parts = [`${entity.name} is tracked in AGI as a ${type}.`];

  if (entity.description) parts.push(entity.description);

  if (entity.entity_type === 'pe_firm') {
    if (meta.aum) parts.push(`The firm reports ${meta.aum} in assets under management.`);
    if (meta.founded) parts.push(`Founded in ${meta.founded}, it operates across ${(meta.geoFocus || []).join(', ') || 'global markets'}.`);
    if (meta.strategy) parts.push(meta.strategy);
    const invested = relationships.filter((r) => r.relation_type === 'INVESTED_IN').length;
    const funds = relationships.filter((r) => r.relation_type === 'MANAGES').length;
    if (invested) parts.push(`AGI tracks ${invested} portfolio holdings and ${funds} fund relationships.`);
  }

  if (entity.entity_type === 'portfolio_company' || entity.entity_type === 'company') {
    if (meta.industry) parts.push(`Sector focus: ${meta.industry}.`);
    if (meta.country) parts.push(`Headquartered in ${meta.country}.`);
    if (meta.status) parts.push(`Investment status: ${meta.status}.`);
  }

  if (entity.entity_type === 'fund') {
    if (meta.fundSize) parts.push(`Fund size: ${meta.fundSize}.`);
    if (meta.strategy) parts.push(`Strategy: ${meta.strategy}.`);
    if (meta.vintage) parts.push(`Vintage ${meta.vintage}.`);
  }

  if (entity.entity_type === 'transaction') {
    if (meta.dealValue) parts.push(`Deal value: ${meta.dealValue}.`);
    if (meta.status) parts.push(`Status: ${meta.status}.`);
  }

  if (entity.entity_type === 'person') {
    if (meta.title) parts.push(`${entity.name} serves as ${meta.title}.`);
    if (meta.office) parts.push(`Based in ${meta.office}.`);
  }

  if (relNames.length) parts.push(`Connected to ${relNames.join(', ')}.`);

  const recent = timeline.slice(0, 2);
  if (recent.length) {
    parts.push(`Recent activity includes ${recent.map((e) => e.title.toLowerCase()).join(' and ')}.`);
  }

  return parts.join(' ');
}

export async function generateEntitySummary(entityId, { force = false } = {}) {
  const entity = getEntityById(entityId);
  if (!entity) return null;

  const relationships = getEntityRelationships(entityId);
  const timeline = listTimelineEvents(entityId, { limit: 8 });

  if (!force && entity.ai_summary && entity.ai_summary_updated_at) {
    const age = Date.now() - new Date(entity.ai_summary_updated_at).getTime();
    if (age < 24 * 60 * 60 * 1000) return entity.ai_summary;
  }

  let summary = buildDeterministicSummary(entity, relationships, timeline);

  try {
    const llm = await completeChat({
      system: 'You are an institutional private markets intelligence analyst. Write concise, authoritative summaries in plain English. Return JSON: {"summary":"..."}',
      user: {
        entity: {
          name: entity.name,
          type: entity.entity_type,
          description: entity.description,
          metadata: entity.metadata,
          tags: entity.tags,
        },
        relationships: relationships.slice(0, 12).map((r) => ({
          type: r.relation_type,
          name: r.other_entity?.name,
        })),
        recentEvents: timeline.slice(0, 6).map((e) => ({ title: e.title, date: e.occurred_at })),
      },
      temperature: 0.2,
    });
    if (llm?.json?.summary) summary = llm.json.summary;
  } catch {
    /* keep deterministic summary */
  }

  const ts = new Date().toISOString();
  updateEntity(entityId, { ai_summary: summary, ai_summary_updated_at: ts });
  return summary;
}

export async function refreshStaleSummaries({ max = 10 } = {}) {
  const { listEntities } = await import('./entityStore.js');
  const { entities } = listEntities({ limit: 500 });
  const stale = entities.filter((e) => {
    if (!e.ai_summary || !e.ai_summary_updated_at) return true;
    return Date.now() - new Date(e.ai_summary_updated_at).getTime() > 7 * 24 * 60 * 60 * 1000;
  });
  const updated = [];
  for (const entity of stale.slice(0, max)) {
    const summary = await generateEntitySummary(entity.id, { force: true });
    if (summary) updated.push(entity.slug);
  }
  return updated;
}
