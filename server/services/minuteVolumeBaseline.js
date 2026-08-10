const IST_OFFSET_MS = 5.5 * 60 * 60 * 1000;

function istClock(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) throw new Error('Invalid observation timestamp.');
  const shifted = new Date(date.getTime() + IST_OFFSET_MS);
  return {
    session: shifted.toISOString().slice(0, 10),
    minute: shifted.getUTCHours() * 60 + shifted.getUTCMinutes() - (9 * 60 + 15),
  };
}

function median(values) {
  const sorted = [...values].sort((left, right) => left - right);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

/** Build point-in-time-safe cumulative-volume baselines from prior sessions. */
export function buildMinuteVolumeBaselines(observations, { minimumSessions = 5, throughSession } = {}) {
  if (!Array.isArray(observations)) throw new Error('observations must be an array.');
  const perSession = new Map();
  for (const row of observations) {
    const key = String(row.instrument_key || '').trim();
    const volume = Number(row.cumulative_volume);
    if (!key || !Number.isFinite(volume) || volume < 0) continue;
    const { session, minute } = istClock(row.observed_at);
    if (minute < 0 || minute > 375 || (throughSession && session >= throughSession)) continue;
    // Instrument keys themselves contain `|`; encode tuple keys rather than
    // parsing a delimiter that is also valid inside the instrument key.
    const sessionKey = JSON.stringify([key, minute, session]);
    perSession.set(sessionKey, Math.max(volume, perSession.get(sessionKey) ?? 0));
  }
  const groups = new Map();
  for (const [compound, volume] of perSession) {
    const [instrumentKey, minute] = JSON.parse(compound);
    const groupKey = JSON.stringify([instrumentKey, minute]);
    const values = groups.get(groupKey) || [];
    values.push(volume);
    groups.set(groupKey, values);
  }
  const output = [];
  for (const [groupKey, values] of groups) {
    if (values.length < minimumSessions) continue;
    const [instrumentKey, minute] = JSON.parse(groupKey);
    output.push({
      instrument_key: instrumentKey,
      minute_of_session: minute,
      expected_cumulative_volume: median(values),
      sample_sessions: values.length,
    });
  }
  return output.sort((left, right) => left.instrument_key.localeCompare(right.instrument_key) || left.minute_of_session - right.minute_of_session);
}

export function minuteOfSession(iso) {
  return istClock(iso).minute;
}

export class VolumeBaselineIndex {
  constructor(rows = []) {
    this.values = new Map(rows.map((row) => [`${row.instrument_key}|${row.minute_of_session}`, Number(row.expected_cumulative_volume)]));
  }
  get(instrumentKey, minute) {
    return this.values.get(`${instrumentKey}|${minute}`) ?? null;
  }
  replace(rows = []) {
    this.values = new Map(rows.map((row) => [`${row.instrument_key}|${row.minute_of_session}`, Number(row.expected_cumulative_volume)]));
    return this.values.size;
  }
}
