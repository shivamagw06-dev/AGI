import { getHistoricalCandles } from '../providers/upstox.js';
import { buildMinuteVolumeBaselines } from './minuteVolumeBaseline.js';

const IST_OFFSET_MS = 5.5 * 60 * 60_000;

function dateOnly(date) { return date.toISOString().slice(0, 10); }
function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }

async function historicalCandlesWithBackoff(instrumentKey, range) {
  let lastError;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      return await getHistoricalCandles(instrumentKey, range);
    } catch (error) {
      lastError = error;
      if (error?.status !== 429 || attempt === 2) throw error;
      await wait((attempt + 1) * 10_000);
    }
  }
  throw lastError;
}

function normalizedObservations(instrumentKey, payload) {
  const rows = [];
  const sessions = new Map();
  for (const candle of payload?.data?.candles || []) {
    const [timestamp, , , , close, volume] = candle || [];
    const at = new Date(timestamp);
    const amount = Number(volume);
    if (Number.isNaN(at.getTime()) || !(Number(close) > 0) || !Number.isFinite(amount) || amount < 0) continue;
    const session = new Date(at.getTime() + IST_OFFSET_MS).toISOString().slice(0, 10);
    const values = sessions.get(session) || [];
    values.push({ at, amount });
    sessions.set(session, values);
  }
  for (const values of sessions.values()) {
    values.sort((left, right) => left.at - right.at);
    let cumulative = 0;
    for (const value of values) {
      cumulative += value.amount;
      rows.push({ instrument_key: instrumentKey, observed_at: value.at.toISOString(), cumulative_volume: cumulative });
    }
  }
  return rows;
}

/** Build genuine prior-session baselines; never substitutes fabricated volume. */
export async function bootstrapLiveAlphaVolumeBaselines({ members, persistence, baselineIndex, now = new Date(), minimumSessions = 5 } = {}) {
  if (!members?.length || !persistence || !baselineIndex) return { status: 'skipped', reason: 'not_configured', rows: 0, failures: [] };
  const throughSession = new Date(now.getTime() + IST_OFFSET_MS).toISOString().slice(0, 10);
  const to = dateOnly(new Date(now.getTime() - 86_400_000));
  const from = dateOnly(new Date(now.getTime() - 12 * 86_400_000));
  const observations = [];
  const failures = [];
  for (let index = 0; index < members.length; index += 1) {
    const member = members[index];
    try {
      // Keep well below the shared historical-data rate limit; other AGI
      // collectors may be using the same provider quota at boot.
      if (index > 0) await wait(1_500);
      const payload = await historicalCandlesWithBackoff(member.instrumentKey, { unit: 'minutes', interval: 1, from, to });
      observations.push(...normalizedObservations(member.instrumentKey, payload));
    } catch (error) {
      failures.push({ symbol: member.symbol, error: error.message });
    }
  }
  const rows = buildMinuteVolumeBaselines(observations, { minimumSessions, throughSession }).map((row) => ({
    ...row,
    calculated_through: to,
    method: 'median_prior_sessions',
    updated_at: new Date().toISOString(),
  }));
  await persistence.saveVolumeBaselines(rows);
  baselineIndex.replace(rows);
  return { status: rows.length ? 'ready' : 'insufficient_history', rows: rows.length, failures };
}

export { normalizedObservations };
