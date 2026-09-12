/**
 * File-backed newsletter store with optional Supabase sync.
 * Does not replace articles CMS — only distribution data.
 */

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(__dirname, '../../data/newsletter');

const FILES = {
  subscribers: 'subscribers.json',
  imports: 'imports.json',
  jobs: 'publish_jobs.json',
  events: 'events.json',
  campaigns: 'campaigns.json',
};

function ensureDir() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

function readList(key) {
  ensureDir();
  const file = path.join(DATA_DIR, FILES[key]);
  if (!fs.existsSync(file)) return [];
  try {
    const raw = JSON.parse(fs.readFileSync(file, 'utf8'));
    return Array.isArray(raw) ? raw : [];
  } catch {
    return [];
  }
}

function writeList(key, list) {
  ensureDir();
  const file = path.join(DATA_DIR, FILES[key]);
  fs.writeFileSync(file, JSON.stringify(list, null, 2), 'utf8');
}

export function newId(prefix = '') {
  return `${prefix}${crypto.randomUUID()}`;
}

export function newToken() {
  return crypto.randomBytes(24).toString('hex');
}

export function resetStoreForTests() {
  ensureDir();
  for (const key of Object.keys(FILES)) writeList(key, []);
}

export const store = {
  listSubscribers: () => readList('subscribers'),
  saveSubscribers: (rows) => writeList('subscribers', rows),
  listImports: () => readList('imports'),
  saveImports: (rows) => writeList('imports', rows),
  listJobs: () => readList('jobs'),
  saveJobs: (rows) => writeList('jobs', rows),
  listEvents: () => readList('events'),
  saveEvents: (rows) => writeList('events', rows),
  listCampaigns: () => readList('campaigns'),
  saveCampaigns: (rows) => writeList('campaigns', rows),
};

export async function supabaseUpsert(table, rows, onConflict) {
  const url = (process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key || !rows?.length) return { ok: false, skipped: true };
  try {
    const params = new URLSearchParams();
    if (onConflict) params.set('on_conflict', onConflict);
    const qs = params.toString();
    const resp = await fetch(`${url}/rest/v1/${table}${qs ? `?${qs}` : ''}`, {
      method: 'POST',
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
        Prefer: 'resolution=merge-duplicates,return=minimal',
      },
      body: JSON.stringify(rows),
    });
    if (!resp.ok) {
      const text = await resp.text();
      console.warn(`[newsletter-store] supabase ${table} failed:`, text.slice(0, 200));
      return { ok: false, error: text };
    }
    return { ok: true };
  } catch (err) {
    console.warn(`[newsletter-store] supabase ${table} error:`, err.message);
    return { ok: false, error: err.message };
  }
}
