import { rest } from './liveAlphaPersistence.js';

// Bounded, on-demand sample. Never a calibration set or a portfolio backtest.
export function summarizeAlphaEvidence(rows = [], { truncated = false } = {}) {
  const groups = new Map(); const missingReasons = {};
  for (const row of rows) {
    const engine = row.signal?.run?.engine || 'unknown';
    const key = `${engine}|${row.horizon}`;
    const g = groups.get(key) || { engine, horizon: row.horizon, completed: 0, pending: 0, missed: 0, invalid: 0, wins: 0, sum: 0, costs: [], sessions: new Set() };
    if (row.status === 'completed') {
      const value = row.directional_return_pct;
      const cost = row.estimated_cost_bps;
      if (value !== null && value !== undefined && Number.isFinite(Number(value)) && cost !== null && cost !== undefined && Number.isFinite(Number(cost)) && Number(cost) >= 0) {
        const net = Number(value) - Number(cost) / 100;
        g.completed++; g.sum += net; g.wins += net > 0 ? 1 : 0; g.costs.push(Number(cost));
        if (row.signal?.run?.as_of) g.sessions.add(row.signal.run.as_of.slice(0, 10));
      } else g.invalid++;
    } else if (row.status === 'pending') g.pending++;
    else if (row.status === 'missed') { g.missed++; const reason=row.last_error||'not_recorded'; missingReasons[reason]=(missingReasons[reason]||0)+1; }
    groups.set(key, g);
  }
  return {
    scope: 'Most recent outcome rows due in the past 30 calendar days; at most 5,000 rows. Overlapping signals are not independent trades.',
    missing_reasons: missingReasons, truncated, sampled_rows: rows.length, research_only: true, portfolio_backtest: false,
    rows: [...groups.values()].map(({ sum, wins, costs, sessions, ...g }) => ({ ...g,
      sessions: sessions.size,
      mean_net_directional_return_pct: g.completed ? sum / g.completed : null,
      positive_outcome_pct: g.completed ? wins / g.completed * 100 : null,
      minimum_cost_bps: costs.length ? Math.min(...costs) : null,
      maximum_cost_bps: costs.length ? Math.max(...costs) : null,
    })),
  };
}
let cached = null;
let pending = null;
export async function getLiveAlphaEvidence({ now = new Date(), request = rest } = {}) {
  if (request === rest && cached && now.getTime() - cached.at < 5 * 60_000) return cached.value;
  if (request === rest && pending) return pending;
  const load = async () => {
    const rows = [];
    const start = new Date(now.getTime() - 30 * 86400_000).toISOString();
    for (let offset = 0; offset < 5000; offset += 1000) {
      const query = new URLSearchParams({
        select: 'id,horizon,status,last_error,directional_return_pct,estimated_cost_bps,signal:live_alpha_signals!inner(run:live_alpha_runs!inner(engine,as_of))',
        due_at: `gte.${start}`, and: `(due_at.lte.${now.toISOString()})`,
        order: 'due_at.desc,id.desc', offset: String(offset), limit: '1000',
      });
      const page = await request('live_alpha_signal_outcomes', { method: 'GET', query: query.toString(), prefer: undefined }) || [];
      rows.push(...page);
      if (page.length < 1000) break;
    }
    const completedQuery=new URLSearchParams({select:'id,horizon,status,last_error,directional_return_pct,estimated_cost_bps,signal:live_alpha_signals!inner(run:live_alpha_runs!inner(engine,as_of))',status:'eq.completed',due_at:`gte.${start}`,and:`(due_at.lte.${now.toISOString()})`,order:'due_at.desc,id.desc',limit:'1000'});
    const completedRows=await request('live_alpha_signal_outcomes',{method:'GET',query:completedQuery.toString(),prefer:undefined})||[];
    const value = { ...summarizeAlphaEvidence(rows, { truncated: rows.length >= 5000 }), completed_sample: {...summarizeAlphaEvidence(completedRows,{truncated:completedRows.length>=1000}),scope:'Separate sample: latest 1,000 completed outcomes in the same 30-day window. Excludes missing outcomes; not an overall success rate.'}, generated_at: now.toISOString() };
    if (request === rest) cached = { at: now.getTime(), value };
    return value;
  };
  if (request !== rest) return load();
  pending = load();
  try { return await pending; } finally { pending = null; }
}
