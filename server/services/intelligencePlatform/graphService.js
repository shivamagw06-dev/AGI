import { readRelationships, readEntities } from './store.js';
import { getEntityById } from './entityStore.js';
import { listTimelineEvents } from './timelineService.js';
import { nodeColorForType, entityPublicPath, entityTypeLabel } from './entityTypes.js';

function parseList(value) {
  if (!value) return null;
  if (Array.isArray(value)) return value;
  return String(value).split(',').map((s) => s.trim()).filter(Boolean);
}

function serializeNode(entity, { depth, includeAiSummary, relationshipCount, timelineCount }) {
  const meta = entity.metadata || {};
  return {
    id: entity.id,
    slug: entity.slug,
    name: entity.name,
    entity_type: entity.entity_type,
    entity_type_label: entityTypeLabel(entity.entity_type),
    description: entity.description || '',
    status: entity.status,
    tags: entity.tags || [],
    color: nodeColorForType(entity.entity_type),
    logo: meta.logo || null,
    depth,
    path: entityPublicPath(entity),
    relationship_count: relationshipCount,
    timeline_count: timelineCount,
    ai_summary: includeAiSummary ? (entity.ai_summary || null) : undefined,
    metadata: {
      aum: meta.aum,
      industry: meta.industry,
      status: meta.status,
      fundSize: meta.fundSize,
      title: meta.title,
      hq: meta.hq,
    },
    updated_at: entity.updated_at,
  };
}

function serializeEdge(rel, fromId, toId) {
  return {
    id: rel.id,
    from: fromId,
    to: toId,
    relation_type: rel.relation_type,
    label: rel.label || rel.relation_type.replace(/_/g, ' '),
  };
}

/**
 * BFS graph expansion from a root entity.
 */
export function buildEntityGraph(rootEntityId, options = {}) {
  const depth = Math.min(Math.max(Number(options.depth) || 2, 1), 3);
  const limit = Math.min(Number(options.limit) || 80, 200);
  const entityTypeFilter = parseList(options.entityTypes || options.entity_types);
  const relationTypeFilter = parseList(options.relationshipTypes || options.relationship_types);
  const includeTimeline = options.includeTimeline === true || options.include_timeline === 'true';
  const includeAiSummary = options.includeAiSummary !== false && options.include_ai_summary !== 'false';

  const root = getEntityById(rootEntityId);
  if (!root) return null;

  const allRels = readRelationships();
  const adjacency = new Map();

  allRels.forEach((rel) => {
    if (relationTypeFilter && !relationTypeFilter.includes(rel.relation_type)) return;
    if (!adjacency.has(rel.from_entity_id)) adjacency.set(rel.from_entity_id, []);
    if (!adjacency.has(rel.to_entity_id)) adjacency.set(rel.to_entity_id, []);
    adjacency.get(rel.from_entity_id).push({ rel, neighborId: rel.to_entity_id, direction: 'out' });
    adjacency.get(rel.to_entity_id).push({ rel, neighborId: rel.from_entity_id, direction: 'in' });
  });

  const visited = new Map();
  const edges = [];
  const edgeKeys = new Set();
  const queue = [{ id: rootEntityId, depth: 0 }];
  visited.set(rootEntityId, 0);

  while (queue.length && visited.size < limit) {
    const { id, depth: currentDepth } = queue.shift();
    if (currentDepth >= depth) continue;

    const neighbors = adjacency.get(id) || [];
    for (const { rel, neighborId } of neighbors) {
      const neighbor = getEntityById(neighborId);
      if (!neighbor || neighbor.status !== 'published') continue;
      if (entityTypeFilter && !entityTypeFilter.includes(neighbor.entity_type)) continue;

      const edgeKey = [rel.from_entity_id, rel.to_entity_id, rel.relation_type].join(':');
      if (!edgeKeys.has(edgeKey)) {
        edgeKeys.add(edgeKey);
        edges.push(serializeEdge(rel, rel.from_entity_id, rel.to_entity_id));
      }

      if (!visited.has(neighborId) && visited.size < limit) {
        visited.set(neighborId, currentDepth + 1);
        queue.push({ id: neighborId, depth: currentDepth + 1 });
      }
    }
  }

  const relCounts = new Map();
  edges.forEach((e) => {
    relCounts.set(e.from, (relCounts.get(e.from) || 0) + 1);
    relCounts.set(e.to, (relCounts.get(e.to) || 0) + 1);
  });

  const nodes = [];
  for (const [entityId, nodeDepth] of visited) {
    const entity = getEntityById(entityId);
    if (!entity) continue;
    const timeline = includeTimeline ? listTimelineEvents(entityId, { limit: 5 }) : [];
    nodes.push(serializeNode(entity, {
      depth: nodeDepth,
      includeAiSummary,
      relationshipCount: relCounts.get(entityId) || 0,
      timelineCount: timeline.length,
    }));
  }

  const positions = computeLayout(nodes, edges, rootEntityId);

  return {
    root_id: rootEntityId,
    root_slug: root.slug,
    depth,
    node_count: nodes.length,
    edge_count: edges.length,
    nodes: nodes.map((n) => ({ ...n, ...positions[n.id] })),
    edges,
    generated_at: new Date().toISOString(),
  };
}

/** Radial hierarchical layout — center root, rings by depth, sector by type. */
function computeLayout(nodes, edges, rootId) {
  const positions = {};
  const byDepth = {};
  nodes.forEach((n) => {
    if (!byDepth[n.depth]) byDepth[n.depth] = [];
    byDepth[n.depth].push(n);
  });

  positions[rootId] = { x: 0, y: 0 };

  Object.entries(byDepth).forEach(([depthStr, group]) => {
    const depth = Number(depthStr);
    if (depth === 0) return;
    const radius = 140 + depth * 120;
    const sorted = [...group].sort((a, b) => a.entity_type.localeCompare(b.entity_type));
    sorted.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / sorted.length - Math.PI / 2;
      positions[node.id] = {
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
      };
    });
  });

  return positions;
}

export function getRelatedContent(entityId) {
  const entity = getEntityById(entityId);
  if (!entity) return null;

  const allRels = readRelationships();
  const connected = allRels.filter(
    (r) => r.from_entity_id === entityId || r.to_entity_id === entityId
  );

  const buckets = {
    funds: [],
    portfolio_companies: [],
    companies: [],
    people: [],
    transactions: [],
    industries: [],
    articles: [],
    news: [],
    firms: [],
    comparables: [],
  };

  const seen = new Set();

  connected.forEach((rel) => {
    const otherId = rel.from_entity_id === entityId ? rel.to_entity_id : rel.from_entity_id;
    if (seen.has(otherId)) return;
    seen.add(otherId);
    const other = getEntityById(otherId);
    if (!other || other.status !== 'published') return;

    const item = {
      id: other.id,
      slug: other.slug,
      name: other.name,
      entity_type: other.entity_type,
      relation_type: rel.relation_type,
      path: entityPublicPath(other),
      logo: other.metadata?.logo,
      description: other.description?.slice(0, 120),
      ai_summary: other.ai_summary?.slice(0, 200),
    };

    if (rel.relation_type === 'COMPETES_WITH') buckets.comparables.push(item);
    else if (other.entity_type === 'fund') buckets.funds.push(item);
    else if (other.entity_type === 'portfolio_company') buckets.portfolio_companies.push(item);
    else if (other.entity_type === 'company') buckets.companies.push(item);
    else if (other.entity_type === 'person') buckets.people.push(item);
    else if (other.entity_type === 'transaction') buckets.transactions.push(item);
    else if (other.entity_type === 'industry') buckets.industries.push(item);
    else if (other.entity_type === 'article') buckets.articles.push(item);
    else if (other.entity_type === 'news') buckets.news.push(item);
    else if (other.entity_type === 'pe_firm') buckets.firms.push(item);
  });

  // Comparable firms: same industry tags if no COMPETES_WITH
  if (buckets.comparables.length === 0 && entity.entity_type === 'pe_firm') {
    const peers = readEntities()
      .filter((e) => e.entity_type === 'pe_firm' && e.id !== entityId && e.status === 'published')
      .slice(0, 4)
      .map((e) => ({
        id: e.id,
        slug: e.slug,
        name: e.name,
        entity_type: e.entity_type,
        relation_type: 'COMPETES_WITH',
        path: entityPublicPath(e),
        logo: e.metadata?.logo,
        description: e.description?.slice(0, 120),
      }));
    buckets.comparables = peers;
  }

  return buckets;
}
