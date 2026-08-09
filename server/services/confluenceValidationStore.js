import { calculateConfluenceOutcome, createConfluenceOutcomeSchedule, summarizeConfluenceOutcomes } from './confluenceOutcomeValidation.js';

function config() { const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, ''), key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim(); if (!url || !key) throw new Error('Confluence validation requires Supabase credentials.'); return { url, key }; }
async function rest(table, { method = 'GET', query = '', body, prefer } = {}) { const { url, key } = config(); const response = await fetch(`${url}/rest/v1/${table}${query ? `?${query}` : ''}`, { method, headers: { apikey: key, Authorization: `Bearer ${key}`, 'Content-Type': 'application/json', ...(prefer ? { Prefer: prefer } : {}) }, body: body == null ? undefined : JSON.stringify(body) }); if (!response.ok) { const error = new Error(`Confluence validation storage failed (${response.status}): ${(await response.text()).slice(0, 240)}`); error.status = response.status; throw error; } const text = await response.text(); return text ? JSON.parse(text) : []; }
const validPrice = (value) => Number.isFinite(Number(value)) && Number(value) > 0;

export async function saveConfluenceEvents(queue, universe) {
  const memberBySymbol = new Map((universe?.members || []).map((member) => [member.symbol, member]));
  const rows = [];
  for (const item of queue?.items || []) {
    const anchors = item.anchors, member = memberBySymbol.get(item.symbol);
    if (!anchors?.captured_at || !member || ![anchors.price_at_signal, anchors.benchmark_at_signal, anchors.sector_index_at_signal].every(validPrice)) continue;
    const live = item.components?.live || {};
    rows.push({ event_key: `${item.symbol}:${item.confluence_class}:${anchors.captured_at}`, symbol: item.symbol, captured_at: anchors.captured_at, classification: item.confluence_class, fundamental_score: item.scores.fundamental_score, valuation_score: item.scores.valuation_score, eod_confirmation: item.scores.eod_confirmation_score, live_confirmation: item.scores.live_confirmation_score, catalyst_score: item.scores.catalyst_relevance_score, leadership: live.leadership?.effective, activity: live.activity?.effective, breakout: live.breakout?.effective, dislocation: live.dislocation?.effective, positioning: live.positioning?.effective, research_priority: item.research_priority_score, market_regime: anchors.market_regime, sector: item.sector, instrument_key: member.instrumentKey, benchmark_instrument_key: universe.benchmarkKey, sector_instrument_key: member.sectorInstrumentKey, price_at_signal: anchors.price_at_signal, benchmark_at_signal: anchors.benchmark_at_signal, sector_index_at_signal: anchors.sector_index_at_signal, completeness: item.flags, evidence_snapshot: item, research_only: true });
  }
  if (!rows.length) return { events: 0, outcomes: 0 };
  const saved = await rest('research_confluence_events', { method: 'POST', query: 'on_conflict=event_key', body: rows, prefer: 'resolution=merge-duplicates,return=representation' });
  const schedules = saved.flatMap((event) => createConfluenceOutcomeSchedule(event.id, event.captured_at));
  if (schedules.length) await rest('research_confluence_outcomes', { method: 'POST', query: 'on_conflict=event_id,horizon', body: schedules, prefer: 'resolution=ignore-duplicates,return=minimal' });
  return { events: saved.length, outcomes: schedules.length };
}

async function firstSnapshot(instrumentKey, dueAt) {
  const query = `select=ltp,observed_at&instrument_key=eq.${encodeURIComponent(instrumentKey)}&observed_at=gte.${encodeURIComponent(dueAt)}&order=observed_at.asc&limit=1`;
  return (await rest('live_market_snapshots', { query }))?.[0] || null;
}

export async function completeDueConfluenceOutcomes({ now = new Date(), limit = 200 } = {}) {
  const due = await rest('research_confluence_outcomes', { query: `select=*,event:research_confluence_events(*)&status=eq.pending&due_at=lte.${encodeURIComponent(now.toISOString())}&order=due_at.asc&limit=${Math.min(500, limit)}` });
  const summary = { due: due.length, completed: 0, deferred: 0, failed: 0 };
  for (const row of due) {
    try {
      const event = row.event; const [stock, benchmark, sector] = await Promise.all([firstSnapshot(event.instrument_key, row.due_at), firstSnapshot(event.benchmark_instrument_key, row.due_at), firstSnapshot(event.sector_instrument_key, row.due_at)]);
      if (!stock || !benchmark || !sector) { summary.deferred += 1; continue; }
      const result = calculateConfluenceOutcome({ priceAtSignal: event.price_at_signal, futurePrice: stock.ltp, benchmarkAtSignal: event.benchmark_at_signal, futureBenchmark: benchmark.ltp, sectorAtSignal: event.sector_index_at_signal, futureSector: sector.ltp });
      await rest('research_confluence_outcomes', { method: 'PATCH', query: `id=eq.${row.id}`, body: { status: 'completed', observed_at: stock.observed_at, future_price: stock.ltp, future_benchmark: benchmark.ltp, future_sector: sector.ltp, ...result }, prefer: 'return=minimal' }); summary.completed += 1;
    } catch (error) { summary.failed += 1; await rest('research_confluence_outcomes', { method: 'PATCH', query: `id=eq.${row.id}`, body: { attempt_count: Number(row.attempt_count || 0) + 1, last_error: error.message.slice(0, 500) }, prefer: 'return=minimal' }).catch(() => {}); }
  }
  return summary;
}

export async function getConfluenceLedger({ limit = 100, symbol } = {}) {
  const filter = symbol ? `&event.symbol=eq.${encodeURIComponent(String(symbol).toUpperCase())}` : '';
  return rest('research_confluence_outcomes', { query: `select=horizon,due_at,observed_at,status,excess_return_pct,sector_adjusted_alpha_pct,positive_excess,event:research_confluence_events(symbol,captured_at,classification,research_priority,market_regime,sector)&order=due_at.desc&limit=${Math.min(500, limit)}${filter}` });
}

export async function getConfluenceValidationSummary({ limit = 10000 } = {}) {
  const rows = await rest('research_confluence_outcomes', { query: `select=horizon,status,excess_return_pct,sector_adjusted_alpha_pct,event:research_confluence_events(classification,market_regime)&status=eq.completed&limit=${Math.min(10000, limit)}` });
  return summarizeConfluenceOutcomes(rows.map((row) => ({ ...row, classification: row.event?.classification, market_regime: row.event?.market_regime })));
}
