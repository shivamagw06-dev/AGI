/**
 * Subscriber system — validation, CSV import, preferences, search, GDPR delete architecture.
 */

import { newId, newToken, store, supabaseUpsert } from './store.js';

export const PREFERENCE_KEYS = [
  'daily_market_brief',
  'weekly_newsletter',
  'macro_research',
  'company_research',
  'sector_reports',
  'forecast_updates',
  'investment_office_brief',
  'product_updates',
];

export const SOURCES = [
  'website_signup',
  'newsletter_popup',
  'research_download',
  'linkedin_campaign',
  'manual_import',
  'csv_upload',
  'referral',
  'api',
  'website',
];

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/i;

export function validEmail(email) {
  return EMAIL_RE.test(String(email || '').trim());
}

function normalizeEmail(email) {
  return String(email || '').trim().toLowerCase();
}

function defaultPreferences(partial = {}) {
  const prefs = {};
  for (const key of PREFERENCE_KEYS) {
    prefs[key] = partial[key] ?? true;
  }
  return prefs;
}

function toPublic(row) {
  if (!row) return null;
  const { unsubscribe_token, ...rest } = row;
  return {
    ...rest,
    has_unsubscribe_token: Boolean(unsubscribe_token),
  };
}

export function listSubscribers({
  q,
  email,
  name,
  source,
  tags,
  preference,
  status,
  limit = 100,
  offset = 0,
} = {}) {
  let rows = store.listSubscribers();
  if (email) {
    const e = normalizeEmail(email);
    rows = rows.filter((r) => r.email.includes(e));
  }
  if (name) {
    const n = String(name).toLowerCase();
    rows = rows.filter(
      (r) =>
        `${r.first_name || ''} ${r.last_name || ''}`.toLowerCase().includes(n),
    );
  }
  if (source) rows = rows.filter((r) => r.source === source);
  if (status) rows = rows.filter((r) => r.status === status);
  if (tags) {
    const wanted = Array.isArray(tags) ? tags : String(tags).split(',').map((t) => t.trim()).filter(Boolean);
    rows = rows.filter((r) => wanted.every((t) => (r.tags || []).includes(t)));
  }
  if (preference) {
    rows = rows.filter((r) => r.preferences?.[preference] === true);
  }
  if (q) {
    const query = String(q).toLowerCase();
    rows = rows.filter((r) => {
      const blob = `${r.email} ${r.first_name || ''} ${r.last_name || ''} ${r.source || ''} ${(r.tags || []).join(' ')}`.toLowerCase();
      return blob.includes(query);
    });
  }
  rows.sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  const total = rows.length;
  return {
    total,
    subscribers: rows.slice(offset, offset + limit).map(toPublic),
  };
}

export async function subscribe({
  email,
  first_name,
  last_name,
  source = 'website_signup',
  preferences,
  tags = [],
  verified = false,
}) {
  if (!validEmail(email)) {
    return { ok: false, error: 'Invalid email', status: 400 };
  }
  const normalized = normalizeEmail(email);
  const rows = store.listSubscribers();
  const existing = rows.find((r) => r.email === normalized);
  if (existing) {
    if (existing.status === 'unsubscribed' || existing.is_active === false) {
      existing.status = 'active';
      existing.is_active = true;
      existing.preferences = defaultPreferences({ ...existing.preferences, ...preferences });
      if (tags?.length) existing.tags = Array.from(new Set([...(existing.tags || []), ...tags]));
      store.saveSubscribers(rows);
      await supabaseUpsert('subscribers', [existing], 'email');
      return { ok: true, mode: 'reactivated', subscriber: toPublic(existing) };
    }
    return { ok: true, mode: 'exists', subscriber: toPublic(existing) };
  }

  const row = {
    id: newId(),
    email: normalized,
    first_name: first_name || null,
    last_name: last_name || null,
    source: SOURCES.includes(source) ? source : source || 'api',
    status: 'active',
    verified: Boolean(verified),
    preferences: defaultPreferences(preferences),
    tags: Array.isArray(tags) ? tags : [],
    is_active: true,
    unsubscribe_token: newToken(),
    created_at: new Date().toISOString(),
    last_opened: null,
    last_clicked: null,
    last_email_sent: null,
  };
  rows.push(row);
  store.saveSubscribers(rows);
  await supabaseUpsert('subscribers', [row], 'email');
  return { ok: true, mode: 'created', subscriber: toPublic(row) };
}

export function previewCsvImport(csvText, { source = 'csv_upload' } = {}) {
  const lines = String(csvText || '')
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (!lines.length) {
    return { preview: [], imported: 0, skipped: 0, duplicates: 0, errors: 0, rows: [] };
  }

  let start = 0;
  let headers = null;
  const first = lines[0].toLowerCase();
  if (first.includes('email')) {
    headers = lines[0].split(',').map((h) => h.trim().toLowerCase().replace(/^"|"$/g, ''));
    start = 1;
  }

  const existing = new Set(store.listSubscribers().map((s) => s.email));
  const seen = new Set();
  const preview = [];
  let imported = 0;
  let skipped = 0;
  let duplicates = 0;
  let errors = 0;
  const rows = [];

  for (let i = start; i < lines.length; i += 1) {
    const cols = lines[i].split(',').map((c) => c.trim().replace(/^"|"$/g, ''));
    const get = (name, idx) => {
      if (headers) {
        const hi = headers.indexOf(name);
        return hi >= 0 ? cols[hi] : '';
      }
      return cols[idx] || '';
    };
    const email = normalizeEmail(get('email', 0));
    const first_name = get('first_name', 1) || get('firstname', 1) || '';
    const last_name = get('last_name', 2) || get('lastname', 2) || '';
    const tagCol = get('tags', 3);

    if (!email) {
      errors += 1;
      preview.push({ line: i + 1, email, status: 'error', reason: 'Missing email' });
      continue;
    }
    if (!validEmail(email)) {
      errors += 1;
      skipped += 1;
      preview.push({ line: i + 1, email, status: 'skipped', reason: 'Invalid email' });
      continue;
    }
    if (existing.has(email) || seen.has(email)) {
      duplicates += 1;
      preview.push({ line: i + 1, email, status: 'duplicate', reason: 'Already subscribed / in file' });
      continue;
    }
    seen.add(email);
    imported += 1;
    const row = {
      email,
      first_name: first_name || null,
      last_name: last_name || null,
      source,
      tags: tagCol ? tagCol.split('|').map((t) => t.trim()).filter(Boolean) : [],
    };
    rows.push(row);
    preview.push({ line: i + 1, email, status: 'import', first_name, last_name });
  }

  return { preview: preview.slice(0, 200), imported, skipped, duplicates, errors, rows, source };
}

export async function commitCsvImport(csvText, { source = 'csv_upload', filename, dryRun = false, created_by } = {}) {
  const result = previewCsvImport(csvText, { source });
  if (dryRun) {
    return { ...result, committed: false };
  }
  let created = 0;
  for (const row of result.rows) {
    const out = await subscribe({ ...row, source, verified: false });
    if (out.mode === 'created') created += 1;
  }
  const imports = store.listImports();
  const record = {
    id: newId(),
    source,
    filename: filename || null,
    imported: created,
    skipped: result.skipped,
    duplicates: result.duplicates,
    errors: result.errors,
    preview: result.preview.slice(0, 50),
    created_at: new Date().toISOString(),
    created_by: created_by || null,
  };
  imports.unshift(record);
  store.saveImports(imports.slice(0, 200));
  await supabaseUpsert('newsletter_imports', [record]);
  return { ...result, imported: created, committed: true, import_id: record.id };
}

export async function updatePreferences({ email, token, preferences }) {
  const rows = store.listSubscribers();
  const normalized = email ? normalizeEmail(email) : null;
  const row = rows.find(
    (r) => (normalized && r.email === normalized) || (token && r.unsubscribe_token === token),
  );
  if (!row) return { ok: false, error: 'Subscriber not found', status: 404 };
  row.preferences = defaultPreferences({ ...row.preferences, ...preferences });
  store.saveSubscribers(rows);
  await supabaseUpsert('subscribers', [row], 'email');
  return { ok: true, subscriber: toPublic(row) };
}

export async function unsubscribe({ email, token }) {
  const rows = store.listSubscribers();
  const normalized = email ? normalizeEmail(email) : null;
  const row = rows.find(
    (r) => (token && r.unsubscribe_token === token) || (normalized && r.email === normalized),
  );
  if (!row) return { ok: false, error: 'Subscriber not found', status: 404 };
  row.status = 'unsubscribed';
  row.is_active = false;
  store.saveSubscribers(rows);
  await supabaseUpsert('subscribers', [row], 'email');

  const events = store.listEvents();
  events.push({
    id: newId(),
    job_id: null,
    subscriber_id: row.id,
    email: row.email,
    event_type: 'unsubscribe',
    meta: {},
    created_at: new Date().toISOString(),
  });
  store.saveEvents(events);
  return { ok: true, subscriber: toPublic(row) };
}

/** GDPR-style deletion architecture — hard delete + event tombstone */
export async function deleteSubscriber({ email, token }) {
  const rows = store.listSubscribers();
  const normalized = email ? normalizeEmail(email) : null;
  const idx = rows.findIndex(
    (r) => (token && r.unsubscribe_token === token) || (normalized && r.email === normalized),
  );
  if (idx < 0) return { ok: false, error: 'Subscriber not found', status: 404 };
  const [removed] = rows.splice(idx, 1);
  store.saveSubscribers(rows);
  const events = store.listEvents();
  events.push({
    id: newId(),
    job_id: null,
    subscriber_id: removed.id,
    email: 'redacted',
    event_type: 'gdpr_delete',
    meta: { deleted_at: new Date().toISOString() },
    created_at: new Date().toISOString(),
  });
  store.saveEvents(events);
  return { ok: true, deleted: true };
}

export function segmentSubscribers(segment = 'all') {
  const rows = store.listSubscribers().filter((r) => r.status === 'active' && r.is_active !== false);
  const map = {
    all: () => true,
    macro: (r) => r.preferences?.macro_research !== false,
    stock_research: (r) => r.preferences?.company_research !== false,
    forecast: (r) => r.preferences?.forecast_updates !== false,
    investment_office: (r) => r.preferences?.investment_office_brief !== false,
    linkedin: (r) => r.source === 'linkedin_campaign' || (r.tags || []).includes('linkedin'),
    weekly: (r) => r.preferences?.weekly_newsletter !== false,
    daily: (r) => r.preferences?.daily_market_brief !== false,
  };
  if (String(segment).startsWith('tag:')) {
    const tag = segment.slice(4);
    return rows.filter((r) => (r.tags || []).includes(tag));
  }
  const fn = map[segment] || map.all;
  return rows.filter(fn);
}

export function markEmailSent(emails = []) {
  const set = new Set(emails.map(normalizeEmail));
  const rows = store.listSubscribers();
  const now = new Date().toISOString();
  for (const row of rows) {
    if (set.has(row.email)) row.last_email_sent = now;
  }
  store.saveSubscribers(rows);
}
