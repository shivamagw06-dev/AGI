import crypto from 'node:crypto';

export const STRATEGIES = Object.freeze({
  SECTOR: 'agi_sector_rotation_v1',
  EQUITY: 'agi_equity_opportunity_v1',
});

const ROTATIONS = new Set(['leading', 'improving', 'weakening', 'lagging']);
const TRENDS = new Set(['positive', 'mixed', 'negative']);
const RISKS = new Set(['low', 'moderate', 'high']);

export class IngestError extends Error {
  constructor(message, { status = 400, code = 'INVALID_PAYLOAD' } = {}) {
    super(message);
    this.name = 'IngestError';
    this.status = status;
    this.code = code;
  }
}

function text(value, field, { pattern, max = 120 } = {}) {
  const result = String(value ?? '').trim();
  if (!result || result.length > max || (pattern && !pattern.test(result))) {
    throw new IngestError(`Invalid ${field}.`);
  }
  return result;
}

function number(value, field, { min = -Infinity, max = Infinity, nullable = true } = {}) {
  if (value === null || value === undefined || value === '') {
    if (nullable) return null;
    throw new IngestError(`Missing ${field}.`);
  }
  const result = Number(value);
  if (!Number.isFinite(result) || result < min || result > max) {
    throw new IngestError(`Invalid ${field}.`);
  }
  return result;
}

function integer(value, field, options = {}) {
  const result = number(value, field, { ...options, nullable: false });
  if (!Number.isInteger(result)) throw new IngestError(`Invalid ${field}.`);
  return result;
}

function choice(value, field, choices) {
  const result = String(value ?? '').trim().toLowerCase();
  if (!choices.has(result)) throw new IngestError(`Invalid ${field}.`);
  return result;
}

function asArray(value, field, { max = 600 } = {}) {
  if (!Array.isArray(value) || value.length > max) throw new IngestError(`Invalid ${field}.`);
  return value;
}

function optionalObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function metric(row, ...keys) {
  for (const key of keys) if (row[key] !== undefined) return row[key];
  return null;
}

function commonSignal(row, label) {
  if (!row || typeof row !== 'object' || Array.isArray(row)) throw new IngestError(`Invalid ${label}.`);
  return {
    score: number(row.score, `${label}.score`, { min: 0, max: 100, nullable: false }),
    close: number(row.close, `${label}.close`),
    return_20d: number(metric(row, 'return_20d', 'ret_20d'), `${label}.return_20d`),
    return_60d: number(metric(row, 'return_60d', 'ret_60d'), `${label}.return_60d`),
    relative_20d: number(metric(row, 'relative_20d', 'rel_20d'), `${label}.relative_20d`),
    relative_60d: number(metric(row, 'relative_60d', 'rel_60d'), `${label}.relative_60d`),
    volatility_20d: number(metric(row, 'volatility_20d', 'vol_20d'), `${label}.volatility_20d`, { min: 0 }),
    risk: choice(row.risk, `${label}.risk`, RISKS),
  };
}

function normalizeSector(payload) {
  const source = payload.sectors ?? payload.rankings ?? payload.results;
  const rows = asArray(source, 'sectors', { max: 100 });
  if (!rows.length) throw new IngestError('sectors cannot be empty.');
  const seenSectors = new Set();
  const seenRanks = new Set();
  const signals = rows.map((row, index) => {
    const label = `sectors[${index}]`;
    const sector = text(row?.sector ?? row?.symbol, `${label}.sector`, { pattern: /^[A-Z0-9&_-]+$/, max: 40 }).toUpperCase();
    const rank = integer(row.rank, `${label}.rank`, { min: 1, max: 100 });
    if (seenSectors.has(sector) || seenRanks.has(rank)) throw new IngestError('Sector and rank must be unique within a run.');
    seenSectors.add(sector);
    seenRanks.add(rank);
    return {
      sector,
      rank,
      ...commonSignal(row, label),
      return_5d: number(metric(row, 'return_5d', 'ret_5d'), `${label}.return_5d`),
      max_drawdown: number(row.max_drawdown, `${label}.max_drawdown`, { max: 0 }),
      rotation: choice(row.rotation, `${label}.rotation`, ROTATIONS),
      factors: optionalObject(row.factors),
    };
  });
  return { table: 'sector_rotation_signals', signals, coverage: signals.length };
}

function normalizeEquity(payload) {
  const candidates = asArray(payload.candidates ?? payload.opportunities ?? [], 'candidates');
  const deteriorating = asArray(payload.deteriorating ?? payload.risk_reviews ?? [], 'deteriorating');
  if (!candidates.length && !deteriorating.length) throw new IngestError('Equity results cannot be empty.');
  const seen = new Set();
  const seenRanks = new Set();
  const mapRow = (row, index, signal) => {
    const group = signal === 'research_candidate' ? 'candidates' : 'deteriorating';
    const label = `${group}[${index}]`;
    const symbol = text(row?.symbol, `${label}.symbol`, { pattern: /^[A-Z0-9&-]+$/, max: 32 }).toUpperCase();
    const key = `${symbol}:${signal}`;
    if (seen.has(key)) throw new IngestError(`Duplicate ${symbol} ${signal}.`);
    seen.add(key);
    const rank = signal === 'research_candidate' ? integer(row.rank, `${label}.rank`, { min: 1, max: 600 }) : null;
    if (rank !== null && seenRanks.has(rank)) throw new IngestError('Candidate ranks must be unique within a run.');
    if (rank !== null) seenRanks.add(rank);
    return {
      symbol,
      signal,
      rank,
      ...commonSignal(row, label),
      volume_ratio: number(row.volume_ratio, `${label}.volume_ratio`, { min: 0 }),
      trend: choice(row.trend, `${label}.trend`, TRENDS),
      volume_confirmation: Boolean(row.volume_confirmation),
      reasons: Array.isArray(row.reasons) ? row.reasons.slice(0, 20).map(String) : [],
      factors: optionalObject(row.factors),
    };
  };
  const signals = [
    ...candidates.map((row, index) => mapRow(row, index, 'research_candidate')),
    ...deteriorating.map((row, index) => mapRow(row, index, 'risk_review')),
  ];
  const statedCoverage = payload.processed ?? payload.coverage;
  const uniqueSymbolCoverage = new Set(signals.map((signal) => signal.symbol)).size;
  const coverage = statedCoverage === undefined
    ? uniqueSymbolCoverage
    : integer(statedCoverage, 'processed', { min: uniqueSymbolCoverage, max: 5000 });
  return { table: 'equity_opportunity_signals', signals, coverage };
}

export function normalizePayload(payload, { now = new Date(), maxAgeHours = 48 } = {}) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) throw new IngestError('JSON object required.');
  const strategy = text(payload.strategy, 'strategy', { max: 50 });
  if (!Object.values(STRATEGIES).includes(strategy)) throw new IngestError('Unsupported strategy.');
  const runId = text(payload.run_id, 'run_id', { max: 180 });
  if (!runId.startsWith(`${strategy}:`)) throw new IngestError('run_id must start with the strategy name.');
  const asOf = new Date(payload.as_of);
  if (Number.isNaN(asOf.getTime())) throw new IngestError('Invalid as_of timestamp.');
  const ageMs = now.getTime() - asOf.getTime();
  if (ageMs > maxAgeHours * 3_600_000 || ageMs < -10 * 60_000) throw new IngestError('as_of timestamp is outside the accepted window.', { code: 'STALE_RUN' });
  if (payload.research_only !== true) throw new IngestError('research_only must be true.');
  const schemaVersion = String(payload.schema_version ?? '1.0').trim();
  if (schemaVersion !== '1.0') throw new IngestError('Unsupported schema_version.');
  const normalized = strategy === STRATEGIES.SECTOR ? normalizeSector(payload) : normalizeEquity(payload);
  const errors = Array.isArray(payload.errors) ? payload.errors : [];
  return {
    run: {
      strategy,
      run_id: runId,
      as_of: asOf.toISOString(),
      source: 'groww_cloud',
      schema_version: schemaVersion,
      research_only: true,
      status: 'validated',
      coverage: normalized.coverage,
      error_count: errors.length,
      raw_payload: payload,
    },
    ...normalized,
  };
}

export function verifySignature(rawBody, suppliedSignature, secret) {
  if (!secret || !suppliedSignature || !rawBody) return false;
  const supplied = String(suppliedSignature).replace(/^sha256=/i, '').trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(supplied)) return false;
  const expected = crypto.createHmac('sha256', secret).update(rawBody).digest('hex');
  return crypto.timingSafeEqual(Buffer.from(expected, 'hex'), Buffer.from(supplied, 'hex'));
}

export function payloadHash(rawBody) {
  return crypto.createHash('sha256').update(rawBody).digest('hex');
}

function supabaseConfig() {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key) throw new IngestError('Research signal storage is not configured.', { status: 503, code: 'NOT_CONFIGURED' });
  return { url, key };
}

async function request(table, { method = 'GET', query = '', body, prefer } = {}) {
  const { url, key } = supabaseConfig();
  const response = await fetch(`${url}/rest/v1/${table}${query ? `?${query}` : ''}`, {
    method,
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...(prefer ? { Prefer: prefer } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const responseText = await response.text();
  const data = responseText ? JSON.parse(responseText) : null;
  if (!response.ok) {
    const error = new Error(data?.message || `Storage request failed (${response.status}).`);
    error.storageCode = data?.code;
    throw error;
  }
  return data;
}

export const researchSignalRepository = {
  async findRun(runId) {
    const rows = await request('research_strategy_runs', { query: new URLSearchParams({ select: 'id,status', run_id: `eq.${runId}`, limit: '1' }).toString() });
    return rows?.[0] || null;
  },
  async createRun(run) {
    const rows = await request('research_strategy_runs', { method: 'POST', body: run, prefer: 'return=representation' });
    return rows?.[0];
  },
  async insertSignals(table, signals) {
    await request(table, { method: 'POST', body: signals, prefer: 'return=minimal' });
  },
  async markProcessed(id) {
    await request('research_strategy_runs', { method: 'PATCH', query: `id=eq.${encodeURIComponent(id)}`, body: { status: 'processed', processed_at: new Date().toISOString() }, prefer: 'return=minimal' });
  },
  async removeRun(id) {
    await request('research_strategy_runs', { method: 'DELETE', query: `id=eq.${encodeURIComponent(id)}`, prefer: 'return=minimal' });
  },
};

export async function ingestPayload(payload, rawBody, { repository = researchSignalRepository, now, maxAgeHours } = {}) {
  const normalized = normalizePayload(payload, { now, maxAgeHours });
  const existing = await repository.findRun(normalized.run.run_id);
  if (existing) return { duplicate: true, runId: normalized.run.run_id, status: existing.status, accepted: 0 };
  const run = await repository.createRun({ ...normalized.run, payload_hash: payloadHash(rawBody) });
  if (!run?.id) throw new Error('Storage did not return a run id.');
  try {
    const rows = normalized.signals.map((signal) => ({ ...signal, strategy_run_id: run.id }));
    await repository.insertSignals(normalized.table, rows);
    await repository.markProcessed(run.id);
    return { duplicate: false, runId: normalized.run.run_id, strategy: normalized.run.strategy, status: 'processed', accepted: rows.length };
  } catch (error) {
    await repository.removeRun(run.id).catch(() => {});
    throw error;
  }
}
