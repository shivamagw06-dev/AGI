import { istDateKey } from './liveAlphaSession.js';
import { RADAR_VERSION } from './liveAlphaEarlyRadar.js';
export const radarEventKey = e => `${e.version}|${e.symbol}|${e.event_at}|${e.stage}`;
async function request(table, { method = 'GET', query = '', body, prefer } = {}) {
  const url = process.env.SUPABASE_URL, key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error('Radar database not configured');
  const response = await fetch(`${url.replace(/\/$/,'')}/rest/v1/${table}?${query}`, {
    method, signal: AbortSignal.timeout(8000),
    headers: { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', ...(prefer ? { Prefer: prefer } : {}) },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });
  if (!response.ok) throw new Error(`Radar storage unavailable (${response.status})`);
  const text = await response.text(); return text ? JSON.parse(text) : [];
}
export class RadarRepository {
  constructor({ transport = request } = {}) { this.transport = transport; this.saved = new Set(); }
  async load(now = new Date()) {
    const session = istDateKey(now), records = [];
    for (let offset = 0; offset < 2000; offset += 500) {
      const page = await this.transport('live_alpha_radar_state', { query: `select=observation&session_date=eq.${session}&version=eq.${RADAR_VERSION}&order=state_key&limit=500&offset=${offset}` });
      records.push(...page); if (page.length < 500) break;
    }
    const events = await this.transport('live_alpha_radar_events', { query: `select=observation&session_date=eq.${session}&version=eq.${RADAR_VERSION}&order=event_at.desc,event_key.desc&limit=100` });
    const observations = events.map(e => e.observation).reverse();
    observations.forEach(e => this.saved.add(radarEventKey(e)));
    return { version: RADAR_VERSION, episodes: records.map(r => r.observation), events: observations };
  }
  async save({ events }) {
    const pending = events.filter(e => !this.saved.has(radarEventKey(e)));
    if (!pending.length) return;
    for (let i = 0; i < pending.length; i += 100) {
      const chunk = pending.slice(i, i + 100);
      await this.transport('live_alpha_radar_events', { method: 'POST', query: 'on_conflict=event_key', prefer: 'resolution=ignore-duplicates,return=minimal',
        body: chunk.map(e => ({ event_key: radarEventKey(e), version: e.version, symbol: e.symbol, session_date: e.session, event_at: e.event_at, stage: e.stage, observation: e })) });
      const states = new Map();
      for (const e of chunk) states.set(`${e.version}|${e.session}|${e.symbol}`, e);
      await this.transport('live_alpha_radar_state', { method: 'POST', query: 'on_conflict=state_key', prefer: 'resolution=merge-duplicates,return=minimal',
        body: [...states].map(([state_key,e]) => ({ state_key, version:e.version, symbol:e.symbol, session_date:e.session, event_at:e.event_at, observation:e })) });
      chunk.forEach(e => this.saved.add(radarEventKey(e)));
    }
    // Keep only keys still in the bounded in-memory event window.
    this.saved = new Set(events.map(radarEventKey));
  }
}
