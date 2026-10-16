import crypto from 'node:crypto';
import { slugify } from './entityTypes.js';
import { readEntities, writeEntities } from './store.js';

function now() {
  return new Date().toISOString();
}

export function listEntities({ type, status = 'published', q, limit = 100, offset = 0 } = {}) {
  let rows = readEntities().filter((e) => !status || e.status === status);
  if (type) rows = rows.filter((e) => e.entity_type === type);
  if (q) {
    const needle = q.toLowerCase();
    rows = rows.filter((e) =>
      [e.name, e.description, ...(e.tags || [])].some((f) => String(f || '').toLowerCase().includes(needle))
    );
  }
  rows.sort((a, b) => a.name.localeCompare(b.name));
  const total = rows.length;
  return { entities: rows.slice(offset, offset + limit), total };
}

export function getEntityById(id) {
  return readEntities().find((e) => e.id === id) || null;
}

export function getEntityBySlug(slug) {
  return readEntities().find((e) => e.slug === slug) || null;
}

export function upsertEntity(input, { allowSlugCollision = false } = {}) {
  const entities = readEntities();
  const ts = now();
  let slug = input.slug || slugify(input.name);
  if (!allowSlugCollision) {
    let suffix = 1;
    const base = slug;
    while (entities.some((e) => e.slug === slug && e.id !== input.id)) {
      slug = `${base}-${suffix++}`;
    }
  }

  if (input.id) {
    const idx = entities.findIndex((e) => e.id === input.id);
    if (idx >= 0) {
      entities[idx] = {
        ...entities[idx],
        ...input,
        slug,
        updated_at: ts,
      };
      writeEntities(entities);
      return entities[idx];
    }
  }

  const entity = {
    id: input.id || crypto.randomUUID(),
    slug,
    entity_type: input.entity_type,
    name: input.name,
    description: input.description || '',
    tags: input.tags || [],
    status: input.status || 'published',
    ai_summary: input.ai_summary || null,
    ai_summary_updated_at: input.ai_summary_updated_at || null,
    attachments: input.attachments || [],
    metadata: input.metadata || {},
    source_refs: input.source_refs || [],
    created_by: input.created_by || 'system',
    updated_by: input.updated_by || 'system',
    created_at: input.created_at || ts,
    updated_at: ts,
  };
  entities.push(entity);
  writeEntities(entities);
  return entity;
}

export function updateEntity(id, patch) {
  const entities = readEntities();
  const idx = entities.findIndex((e) => e.id === id);
  if (idx < 0) return null;
  entities[idx] = { ...entities[idx], ...patch, updated_at: now() };
  writeEntities(entities);
  return entities[idx];
}

export function bulkUpsertEntities(rows) {
  const entities = readEntities();
  const bySlug = new Map(entities.map((e) => [e.slug, e]));
  rows.forEach((row) => {
    const existing = bySlug.get(row.slug);
    if (existing) {
      Object.assign(existing, row, { id: existing.id, updated_at: now() });
    } else {
      const entity = {
        id: row.id || crypto.randomUUID(),
        slug: row.slug,
        entity_type: row.entity_type,
        name: row.name,
        description: row.description || '',
        tags: row.tags || [],
        status: row.status || 'published',
        ai_summary: row.ai_summary || null,
        ai_summary_updated_at: row.ai_summary_updated_at || null,
        attachments: row.attachments || [],
        metadata: row.metadata || {},
        source_refs: row.source_refs || [],
        created_by: row.created_by || 'system',
        updated_by: row.updated_by || 'system',
        created_at: row.created_at || now(),
        updated_at: now(),
      };
      entities.push(entity);
      bySlug.set(entity.slug, entity);
    }
  });
  writeEntities(entities);
  return entities;
}

export function entityStats() {
  const entities = readEntities();
  const byType = {};
  entities.forEach((e) => {
    byType[e.entity_type] = (byType[e.entity_type] || 0) + 1;
  });
  return {
    total: entities.length,
    published: entities.filter((e) => e.status === 'published').length,
    byType,
  };
}
