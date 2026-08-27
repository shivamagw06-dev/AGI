import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const DATA_DIR = path.join(__dirname, '../../data/intelligence_platform');
export const ENTITIES_FILE = path.join(DATA_DIR, 'entities.json');
export const RELATIONSHIPS_FILE = path.join(DATA_DIR, 'relationships.json');
export const TIMELINE_FILE = path.join(DATA_DIR, 'timeline.json');

export function ensureDataDir() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
}

export function readJson(file, fallback) {
  ensureDataDir();
  if (!fs.existsSync(file)) {
    fs.writeFileSync(file, JSON.stringify(fallback, null, 2));
    return fallback;
  }
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

export function writeJson(file, data) {
  ensureDataDir();
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
}

export function readEntities() {
  return readJson(ENTITIES_FILE, { entities: [], bootstrapped: false }).entities || [];
}

export function writeEntities(entities, extra = {}) {
  writeJson(ENTITIES_FILE, { entities, bootstrapped: true, updated_at: new Date().toISOString(), ...extra });
}

export function isBootstrapped() {
  const data = readJson(ENTITIES_FILE, { bootstrapped: false });
  return Boolean(data.bootstrapped);
}

export function readRelationships() {
  return readJson(RELATIONSHIPS_FILE, { relationships: [] }).relationships || [];
}

export function writeRelationships(relationships) {
  writeJson(RELATIONSHIPS_FILE, { relationships, updated_at: new Date().toISOString() });
}

export function readTimelineEvents() {
  return readJson(TIMELINE_FILE, { events: [] }).events || [];
}

export function writeTimelineEvents(events) {
  writeJson(TIMELINE_FILE, { events, updated_at: new Date().toISOString() });
}
