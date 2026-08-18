import API_ORIGIN from '@/config';
const API_BASE = API_ORIGIN || '';

async function platformFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}/api/intelligence/platform${path}`, {
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Platform API ${res.status}`);
  return data;
}

export function searchEntities(q, { limit = 8 } = {}) {
  const params = new URLSearchParams({ q, limit: String(limit) });
  return platformFetch(`/search?${params}`);
}

export function fetchEntity(slug, { refresh = false } = {}) {
  const qs = refresh ? '?refresh=1' : '';
  return platformFetch(`/entities/${encodeURIComponent(slug)}${qs}`);
}

export function fetchEntityFull(slug, { refresh = false } = {}) {
  const qs = refresh ? '?refresh=1' : '';
  return platformFetch(`/entities/${encodeURIComponent(slug)}/full${qs}`);
}

export function fetchEntityGraph(slug, {
  depth = 2,
  entity_types,
  relationship_types,
  limit,
  include_ai_summary = true,
  include_timeline = true,
} = {}) {
  const params = new URLSearchParams();
  if (depth) params.set('depth', String(depth));
  if (entity_types) params.set('entity_types', entity_types);
  if (relationship_types) params.set('relationship_types', relationship_types);
  if (limit) params.set('limit', String(limit));
  if (include_ai_summary) params.set('include_ai_summary', 'true');
  if (include_timeline) params.set('include_timeline', 'true');
  const qs = params.toString();
  return platformFetch(`/entities/${encodeURIComponent(slug)}/graph${qs ? `?${qs}` : ''}`);
}

export function fetchEntityTimeline(slug) {
  return platformFetch(`/entities/${encodeURIComponent(slug)}/timeline`);
}

export function fetchEntityRelated(slug) {
  return platformFetch(`/entities/${encodeURIComponent(slug)}/related`);
}

export function fetchPlatformStats() {
  return platformFetch('/stats');
}

export function fetchPipelineStatus() {
  return platformFetch('/pipeline/status');
}

export function fetchEntities({ type, q, limit = 50 } = {}) {
  const params = new URLSearchParams();
  if (type) params.set('type', type);
  if (q) params.set('q', q);
  if (limit) params.set('limit', String(limit));
  const qs = params.toString();
  return platformFetch(`/entities${qs ? `?${qs}` : ''}`);
}

export function entityPublicPath(entity) {
  if (!entity) return '/private-markets';
  if (entity.entity_type === 'pe_firm' || entity.entity_type === 'general_partner') {
    return `/private-markets/firms/${entity.slug}`;
  }
  if (entity.entity_type === 'article' || entity.entity_type === 'news') {
    const articleId = entity.metadata?.article_id;
    if (articleId) return `/articles/${articleId}`;
    return `/research?q=${encodeURIComponent(entity.name)}`;
  }
  return `/private-markets/entities/${entity.slug}`;
}
