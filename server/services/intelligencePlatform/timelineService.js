import crypto from 'node:crypto';
import { readTimelineEvents, writeTimelineEvents } from './store.js';

export function listTimelineEvents(entityId, { limit = 50 } = {}) {
  return readTimelineEvents()
    .filter((e) => e.entity_id === entityId)
    .sort((a, b) => new Date(b.occurred_at) - new Date(a.occurred_at))
    .slice(0, limit);
}

export function addTimelineEvent(event) {
  const events = readTimelineEvents();
  const row = {
    id: event.id || crypto.randomUUID(),
    entity_id: event.entity_id,
    event_type: event.event_type,
    title: event.title,
    description: event.description || '',
    occurred_at: event.occurred_at,
    source_type: event.source_type || null,
    source_id: event.source_id || null,
    metadata: event.metadata || {},
    created_at: new Date().toISOString(),
  };
  events.push(row);
  writeTimelineEvents(events);
  return row;
}

export function bulkAddTimelineEvents(rows) {
  const events = readTimelineEvents();
  const seen = new Set(events.map((e) => `${e.entity_id}:${e.event_type}:${e.occurred_at}:${e.title}`));
  rows.forEach((row) => {
    const key = `${row.entity_id}:${row.event_type}:${row.occurred_at}:${row.title}`;
    if (seen.has(key)) return;
    events.push({
      id: row.id || crypto.randomUUID(),
      entity_id: row.entity_id,
      event_type: row.event_type,
      title: row.title,
      description: row.description || '',
      occurred_at: row.occurred_at,
      source_type: row.source_type || null,
      source_id: row.source_id || null,
      metadata: row.metadata || {},
      created_at: row.created_at || new Date().toISOString(),
    });
    seen.add(key);
  });
  writeTimelineEvents(events);
  return events;
}

export function timelineStats() {
  return { total: readTimelineEvents().length };
}
