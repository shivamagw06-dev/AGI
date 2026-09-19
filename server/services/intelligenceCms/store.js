import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import crypto from 'node:crypto';
import { getModule } from './modules.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '../../data/intelligence_cms');
const RECORDS_FILE = path.join(DATA_DIR, 'records.json');
const VERSIONS_FILE = path.join(DATA_DIR, 'versions.json');

function ensureStore() {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  if (!fs.existsSync(RECORDS_FILE)) {
    fs.writeFileSync(
      RECORDS_FILE,
      JSON.stringify({ records: [...seedValuationRows(), ...seedTransactionRows()] }, null, 2)
    );
  }
  if (!fs.existsSync(VERSIONS_FILE)) {
    fs.writeFileSync(VERSIONS_FILE, JSON.stringify({ versions: [] }, null, 2));
  }
}

function seedValuationRows() {
  const now = new Date().toISOString();
  const mk = (data, detail = {}, status = 'published') => ({
    id: crypto.randomUUID(),
    module: 'valuation_monitor',
    status,
    data,
    detail,
    relationships: [],
    version: 1,
    created_by: 'system',
    updated_by: 'system',
    published_at: status === 'published' ? now : null,
    scheduled_at: null,
    created_at: now,
    updated_at: now,
  });
  return [
    mk(
      { company: 'Enterprise SaaS Platform', sector: 'Technology', ev_revenue: '8.2x', ev_ebitda: '22.4x', pe_ratio: '—', growth: '14%', margin: '28%', geography: 'North America', agi_rating: 'Neutral', analyst: 'AGI Research' },
      { commentary: 'Premium SaaS multiples compressing from 2021 peaks; selective on rule-of-40 leaders.', risks: 'Customer concentration, NDR deceleration' }
    ),
    mk(
      { company: 'Regional Healthcare Services', sector: 'Healthcare', ev_revenue: '4.1x', ev_ebitda: '16.8x', pe_ratio: '—', growth: '11%', margin: '18%', geography: 'India', agi_rating: 'Constructive', analyst: 'AGI Research' },
      { commentary: 'Consolidation theme intact; pay attention to regulatory and payer mix.', risks: 'Policy changes, labour inflation' }
    ),
    mk(
      { company: 'Industrial Components Group', sector: 'Industrials', ev_revenue: '2.8x', ev_ebitda: '12.1x', pe_ratio: '18x', growth: '8%', margin: '14%', geography: 'Europe', agi_rating: 'Core', analyst: 'AGI Research' },
      { commentary: 'Cyclical recovery priced modestly; prefer export-oriented niches.', risks: 'Energy costs, China demand' },
      'review'
    ),
  ];
}

function seedTransactionRows() {
  const now = new Date().toISOString();
  const mk = (data, detail = {}, status = 'published') => ({
    id: crypto.randomUUID(),
    module: 'transactions',
    status,
    data,
    detail,
    relationships: [],
    version: 1,
    created_by: 'system',
    updated_by: 'system',
    published_at: status === 'published' ? now : null,
    scheduled_at: null,
    created_at: now,
    updated_at: now,
  });

  return [
    mk({ date: '2026-07-30', target: 'Healthcare Services Co.', buyer: 'KKR', seller: 'Public shareholders', enterprise_value: '$4.8B', deal_value: '$4.2B', industry: 'Healthcare', country: 'United States', status: 'Announced' }),
    mk({ date: '2026-07-28', target: 'Data Center Platform', buyer: 'Blackstone', seller: 'Founders', enterprise_value: '$13.0B', deal_value: '$12.5B', industry: 'Infrastructure', country: 'United States', status: 'Completed' }),
    mk({ date: '2026-07-27', target: 'Industrial Tech Platform', buyer: 'Apollo', seller: 'Family owners', enterprise_value: '$3.1B', deal_value: '$2.8B', industry: 'Industrials', country: 'Germany', status: 'Completed' }),
    mk({ date: '2026-07-26', target: 'Consumer Retail Chain', buyer: 'Bain Capital', seller: 'PE consortium', enterprise_value: '$1.3B', deal_value: '$1.1B', industry: 'Consumer', country: 'India', status: 'Announced' }),
    mk({ date: '2026-07-25', target: 'Business Services Group', buyer: 'Advent International', seller: 'Corporate carve-out', enterprise_value: '$3.6B', deal_value: '$3.4B', industry: 'Business Services', country: 'United Kingdom', status: 'Pending' }),
    mk({ date: '2026-07-24', target: 'HealthTech Platform', buyer: 'TPG', seller: 'Founders + early investors', enterprise_value: '$950M', deal_value: '$890M', industry: 'Healthcare', country: 'United States', status: 'Completed' }),
  ];
}

function readRecords() {
  ensureStore();
  return JSON.parse(fs.readFileSync(RECORDS_FILE, 'utf8')).records || [];
}

function writeRecords(records) {
  ensureStore();
  fs.writeFileSync(RECORDS_FILE, JSON.stringify({ records, updated_at: new Date().toISOString() }, null, 2));
}

function readVersions() {
  ensureStore();
  return JSON.parse(fs.readFileSync(VERSIONS_FILE, 'utf8')).versions || [];
}

function appendVersion(record, changedBy) {
  const versions = readVersions();
  versions.push({
    id: crypto.randomUUID(),
    record_id: record.id,
    version: record.version,
    snapshot: { ...record },
    changed_by: changedBy || record.updated_by,
    created_at: new Date().toISOString(),
  });
  fs.writeFileSync(VERSIONS_FILE, JSON.stringify({ versions }, null, 2));
}

export function listRecords(moduleId, { status, q, limit = 500 } = {}) {
  let rows = readRecords().filter((r) => r.module === moduleId);
  if (status) rows = rows.filter((r) => r.status === status);
  if (q) {
    const needle = q.toLowerCase();
    rows = rows.filter((r) => JSON.stringify(r.data).toLowerCase().includes(needle));
  }
  rows.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
  return rows.slice(0, limit);
}

export function getRecord(id) {
  return readRecords().find((r) => r.id === id) || null;
}

export function createRecord(moduleId, payload, actor = 'admin') {
  const mod = getModule(moduleId);
  if (!mod) throw new Error('Unknown module');
  if (!mod.enabled) {
    throw new Error(`Module "${moduleId}" is not enabled yet`);
  }
  const now = new Date().toISOString();
  const record = {
    id: crypto.randomUUID(),
    module: moduleId,
    status: payload.status || 'draft',
    data: payload.data || {},
    detail: payload.detail || {},
    relationships: payload.relationships || [],
    version: 1,
    created_by: actor,
    updated_by: actor,
    published_at: payload.status === 'published' ? now : null,
    scheduled_at: payload.scheduled_at || null,
    created_at: now,
    updated_at: now,
  };
  const records = readRecords();
  records.push(record);
  writeRecords(records);
  appendVersion(record, actor);
  return record;
}

export function updateRecord(id, payload, actor = 'admin') {
  const records = readRecords();
  const idx = records.findIndex((r) => r.id === id);
  if (idx < 0) return null;
  const prev = records[idx];
  const next = {
    ...prev,
    ...payload,
    data: payload.data !== undefined ? payload.data : prev.data,
    detail: payload.detail !== undefined ? payload.detail : prev.detail,
    relationships: payload.relationships !== undefined ? payload.relationships : prev.relationships,
    version: prev.version + 1,
    updated_by: actor,
    updated_at: new Date().toISOString(),
  };
  if (payload.status === 'published' && !next.published_at) {
    next.published_at = new Date().toISOString();
  }
  records[idx] = next;
  writeRecords(records);
  appendVersion(next, actor);
  return next;
}

export function deleteRecord(id) {
  const records = readRecords().filter((r) => r.id !== id);
  writeRecords(records);
  return true;
}

export function getDashboardStats() {
  const records = readRecords();
  const today = new Date().toISOString().slice(0, 10);
  const drafts = records.filter((r) => r.status === 'draft').length;
  const review = records.filter((r) => r.status === 'review').length;
  const publishedToday = records.filter((r) => r.published_at?.startsWith(today)).length;
  const scheduled = records.filter((r) => r.scheduled_at && r.status !== 'published').length;
  const aiDrafts = records.filter((r) => r.detail?.ai_draft?.trim()).length;
  const missingMeta = records.filter((r) => !r.data || Object.keys(r.data).length === 0).length;
  const brokenRelationships = records.filter((r) =>
    (r.relationships || []).some((rel) => !rel.relation_type || !rel.target_label)
  ).length;
  return {
    drafts,
    review,
    publishedToday,
    scheduled,
    recentlyEdited: records.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)).slice(0, 8),
    aiDraftsAwaitingReview: aiDrafts,
    missingMetadata: missingMeta,
    brokenRelationships,
    totalRecords: records.length,
  };
}

export function exportModuleCsv(moduleId) {
  const mod = getModule(moduleId);
  if (!mod) throw new Error('Unknown module');
  const cols = mod.columns.map((c) => c.key);
  const rows = listRecords(moduleId);
  const header = [...cols, 'status'].join(',');
  const lines = rows.map((r) =>
    [...cols.map((k) => `"${String(r.data?.[k] ?? '').replace(/"/g, '""')}"`), r.status].join(',')
  );
  return [header, ...lines].join('\n');
}

const RECORD_STATUSES = ['draft', 'review', 'published', 'archived'];

export function importModuleCsv(moduleId, csvText, actor = 'admin') {
  const mod = getModule(moduleId);
  if (!mod) throw new Error('Unknown module');
  const lines = csvText.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return { imported: 0 };
  const headers = lines[0].split(',').map((h) => h.replace(/^"|"$/g, '').trim());
  let imported = 0;
  for (const line of lines.slice(1)) {
    const cells = line.match(/("([^"]|"")*"|[^,]+)/g) || [];
    const values = cells.map((c) => c.replace(/^"|"$/g, '').replace(/""/g, '"'));
    const data = {};
    headers.forEach((h, i) => {
      if (h !== 'status') data[h] = values[i] || '';
    });
    const status = values[headers.indexOf('status')] || 'draft';
    createRecord(moduleId, { data, status: RECORD_STATUSES.includes(status) ? status : 'draft' }, actor);
    imported += 1;
  }
  return { imported };
}

export function getRecordVersions(recordId) {
  return readVersions().filter((v) => v.record_id === recordId).sort((a, b) => b.version - a.version);
}
