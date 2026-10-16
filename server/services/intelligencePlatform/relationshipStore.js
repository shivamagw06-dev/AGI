import crypto from 'node:crypto';
import { readRelationships, writeRelationships } from './store.js';
import { getEntityById } from './entityStore.js';

export function listRelationships({ fromEntityId, toEntityId, relationType } = {}) {
  let rows = readRelationships();
  if (fromEntityId) rows = rows.filter((r) => r.from_entity_id === fromEntityId);
  if (toEntityId) rows = rows.filter((r) => r.to_entity_id === toEntityId);
  if (relationType) rows = rows.filter((r) => r.relation_type === relationType);
  return rows;
}

export function addRelationship({ fromEntityId, toEntityId, relationType, label, metadata = {} }) {
  const relationships = readRelationships();
  const key = `${fromEntityId}:${toEntityId}:${relationType}`;
  const existing = relationships.find(
    (r) => `${r.from_entity_id}:${r.to_entity_id}:${r.relation_type}` === key
  );
  if (existing) return existing;

  const rel = {
    id: crypto.randomUUID(),
    from_entity_id: fromEntityId,
    to_entity_id: toEntityId,
    relation_type: relationType,
    label: label || null,
    metadata,
    created_at: new Date().toISOString(),
  };
  relationships.push(rel);
  writeRelationships(relationships);
  return rel;
}

export function bulkAddRelationships(rows) {
  const relationships = readRelationships();
  const seen = new Set(relationships.map((r) => `${r.from_entity_id}:${r.to_entity_id}:${r.relation_type}`));
  rows.forEach((row) => {
    const key = `${row.from_entity_id}:${row.to_entity_id}:${row.relation_type}`;
    if (seen.has(key)) return;
    relationships.push({
      id: row.id || crypto.randomUUID(),
      from_entity_id: row.from_entity_id,
      to_entity_id: row.to_entity_id,
      relation_type: row.relation_type,
      label: row.label || null,
      metadata: row.metadata || {},
      created_at: row.created_at || new Date().toISOString(),
    });
    seen.add(key);
  });
  writeRelationships(relationships);
  return relationships;
}

export function getEntityRelationships(entityId) {
  const rows = readRelationships().filter(
    (r) => r.from_entity_id === entityId || r.to_entity_id === entityId
  );
  return rows.map((r) => {
    const isFrom = r.from_entity_id === entityId;
    const otherId = isFrom ? r.to_entity_id : r.from_entity_id;
    const other = getEntityById(otherId);
    return {
      ...r,
      direction: isFrom ? 'outbound' : 'inbound',
      other_entity: other
        ? { id: other.id, slug: other.slug, name: other.name, entity_type: other.entity_type }
        : null,
    };
  });
}

export function relationshipStats() {
  const relationships = readRelationships();
  const byType = {};
  relationships.forEach((r) => {
    byType[r.relation_type] = (byType[r.relation_type] || 0) + 1;
  });
  return { total: relationships.length, byType };
}
