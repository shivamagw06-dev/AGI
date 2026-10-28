import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

const PAGE_SIZE = 1000;
const CACHE_TTL_MS = Math.max(60_000, Number(process.env.INSTITUTIONAL_DECISION_CACHE_TTL_MS || 5 * 60_000));

let cached = null;
let cacheExpiresAt = 0;

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function clamp(value, minimum = 0, maximum = 100) {
  return Math.max(minimum, Math.min(maximum, number(value)));
}

function rounded(value, digits = 1) {
  const scale = 10 ** digits;
  return Math.round(number(value) * scale) / scale;
}

function daysBetween(start, end) {
  if (!start || !end) return null;
  const difference = new Date(end).getTime() - new Date(start).getTime();
  return Number.isFinite(difference) ? Math.max(0, Math.round(difference / 86_400_000)) : null;
}

async function collect(factory) {
  const rows = [];
  for (let from = 0; ; from += PAGE_SIZE) {
    const { data, error } = await factory().range(from, from + PAGE_SIZE - 1);
    if (error) throw error;
    rows.push(...(data || []));
    if (!data || data.length < PAGE_SIZE) break;
  }
  return rows;
}

function latestByManager(filings) {
  const output = new Map();
  for (const filing of [...filings].sort((a, b) => {
    const report = String(b.report_date || '').localeCompare(String(a.report_date || ''));
    return report || String(b.filed_at || '').localeCompare(String(a.filed_at || ''));
  })) {
    if (!output.has(filing.manager_id)) output.set(filing.manager_id, filing);
  }
  return output;
}

function modalQuarter(filings) {
  const counts = new Map();
  for (const filing of filings) counts.set(filing.report_date, (counts.get(filing.report_date) || 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1] || String(b[0]).localeCompare(String(a[0])))[0]?.[0] || null;
}

function securityKey(row) {
  return String(row.ticker || row.cusip || '').trim().toUpperCase();
}

function scoreLabel(score) {
  if (score >= 80) return 'Very high';
  if (score >= 65) return 'High';
  if (score >= 45) return 'Moderate';
  if (score >= 25) return 'Low';
  return 'Very low';
}

function buildSecurityUniverse({ holdings, changes, filings, managers }) {
  const filingMap = new Map(filings.map((row) => [row.id, row]));
  const managerMap = new Map(managers.map((row) => [row.id, row]));
  const buckets = new Map();
  const bucketFor = (row) => {
    const key = securityKey(row);
    if (!key) return null;
    if (!buckets.has(key)) buckets.set(key, {
      key,
      ticker: row.ticker || null,
      cusip: row.cusip,
      issuer_name: row.issuer_name,
      owners: new Map(),
      changes: new Map(),
    });
    return buckets.get(key);
  };

  for (const holding of holdings.filter((row) => !row.put_call)) {
    const bucket = bucketFor(holding);
    if (bucket) bucket.owners.set(holding.manager_id, holding);
  }
  for (const change of changes) {
    const bucket = bucketFor(change);
    if (!bucket) continue;
    const previous = bucket.changes.get(change.manager_id);
    if (!previous || Math.abs(number(change.weight_change)) > Math.abs(number(previous.weight_change))) {
      bucket.changes.set(change.manager_id, change);
    }
  }

  const managerCount = managers.length;
  return [...buckets.values()].map((bucket) => {
    const owners = [...bucket.owners.values()];
    const activity = [...bucket.changes.values()];
    const counts = { new: 0, increased: 0, reduced: 0, exited: 0 };
    activity.forEach((row) => { if (Object.hasOwn(counts, row.change_type)) counts[row.change_type] += 1; });
    const aggregateWeight = owners.reduce((sum, row) => sum + number(row.portfolio_weight), 0);
    const aggregateValue = owners.reduce((sum, row) => sum + number(row.value_usd), 0);
    const positiveWeight = activity.filter((row) => ['new', 'increased'].includes(row.change_type)).reduce((sum, row) => sum + Math.max(0, number(row.weight_change)), 0);
    const negativeWeight = activity.filter((row) => ['reduced', 'exited'].includes(row.change_type)).reduce((sum, row) => sum + Math.abs(Math.min(0, number(row.weight_change))), 0);
    const positiveBreadth = counts.new + counts.increased;
    const negativeBreadth = counts.reduced + counts.exited;
    const breadth = managerCount ? owners.length / managerCount : 0;
    const averageWeight = owners.length ? aggregateWeight / owners.length : 0;
    const averageQuality = owners.length
      ? owners.reduce((sum, row) => sum + number(managerMap.get(row.manager_id)?.quality_weight || 1), 0) / owners.length
      : 1;
    const consensus = clamp(breadth * 60 + Math.min(averageWeight, 8) * 3 + Math.min(averageQuality, 1.25) / 1.25 * 16);
    const accumulation = clamp((positiveBreadth / Math.max(managerCount, 1)) * 70 + Math.min(positiveWeight, 12) * 2.5 - (negativeBreadth / Math.max(managerCount, 1)) * 20);
    const exitPressure = clamp((negativeBreadth / Math.max(managerCount, 1)) * 70 + Math.min(negativeWeight, 12) * 2.5);
    const crowding = clamp(breadth * 55 + Math.min(averageWeight, 12) / 12 * 45);
    const newIdea = clamp((counts.new / Math.max(managerCount, 1)) * 75 + Math.min(averageWeight, 10) * 2.5);
    const netBreadth = positiveBreadth - negativeBreadth;
    const evidence = [...new Set([...owners, ...activity].map((row) => row.filing_id))]
      .map((id) => filingMap.get(id))
      .filter(Boolean)
      .slice(0, 12)
      .map((filing) => ({
        manager: managerMap.get(filing.manager_id)?.display_name || 'Institutional manager',
        report_date: filing.report_date,
        filed_at: filing.filed_at,
        accession_number: filing.accession_number,
        source_url: filing.source_url,
        is_amendment: filing.is_amendment,
      }));
    return {
      key: bucket.key,
      ticker: bucket.ticker,
      cusip: bucket.cusip,
      issuer_name: bucket.issuer_name,
      owner_count: owners.length,
      aggregate_weight: rounded(aggregateWeight, 2),
      aggregate_value_usd: aggregateValue,
      average_weight: rounded(averageWeight, 2),
      mapped: Boolean(bucket.ticker),
      activity: counts,
      net_breadth: netBreadth,
      scores: {
        consensus: { score: rounded(consensus), label: scoreLabel(consensus), components: { ownership_breadth: rounded(breadth * 100), average_portfolio_weight: rounded(averageWeight, 2), average_manager_quality_weight: rounded(averageQuality, 2) } },
        accumulation: { score: rounded(accumulation), label: scoreLabel(accumulation), components: { new_buyers: counts.new, increasers: counts.increased, positive_weight_change: rounded(positiveWeight, 2), opposing_actions: negativeBreadth } },
        exit_pressure: { score: rounded(exitPressure), label: scoreLabel(exitPressure), components: { reducers: counts.reduced, exits: counts.exited, negative_weight_change: rounded(negativeWeight, 2) } },
        crowding: { score: rounded(crowding), label: scoreLabel(crowding), components: { ownership_breadth: rounded(breadth * 100), average_portfolio_weight: rounded(averageWeight, 2) } },
        new_idea: { score: rounded(newIdea), label: scoreLabel(newIdea), components: { new_buyers: counts.new, average_portfolio_weight: rounded(averageWeight, 2) } },
      },
      evidence,
    };
  });
}

function ranking(universe, score, minimumActivity = false) {
  return universe
    .filter((row) => !minimumActivity || Object.values(row.activity).some((value) => value > 0))
    .sort((a, b) => number(b.scores[score]?.score) - number(a.scores[score]?.score) || b.aggregate_weight - a.aggregate_weight)
    .slice(0, 20);
}

function buildManagerScorecards({ managers, filings, holdings, changes, allFilings }) {
  const filingMap = new Map(filings.map((row) => [row.manager_id, row]));
  return managers.map((manager) => {
    const filing = filingMap.get(manager.id);
    const owned = filing ? holdings.filter((row) => row.manager_id === manager.id && !row.put_call) : [];
    const activity = filing ? changes.filter((row) => row.manager_id === manager.id) : [];
    const topTen = [...owned].sort((a, b) => number(b.portfolio_weight) - number(a.portfolio_weight)).slice(0, 10);
    const topTenConcentration = topTen.reduce((sum, row) => sum + number(row.portfolio_weight), 0);
    const mappedValue = owned.filter((row) => row.ticker).reduce((sum, row) => sum + number(row.value_usd), 0);
    const totalValue = owned.reduce((sum, row) => sum + number(row.value_usd), 0);
    const mappingCoverage = totalValue ? mappedValue / totalValue * 100 : 0;
    const filingLag = filing ? daysBetween(filing.report_date, filing.filed_at) : null;
    const historyCount = allFilings.filter((row) => row.manager_id === manager.id).length;
    const turnoverProxy = activity.reduce((sum, row) => sum + Math.abs(number(row.weight_change)), 0) / 2;
    const completeness = clamp(mappingCoverage * 0.55 + Math.min(historyCount, 12) / 12 * 25 + (filing ? 20 : 0));
    return {
      id: manager.id,
      slug: manager.slug,
      display_name: manager.display_name,
      strategy: manager.strategy,
      report_date: filing?.report_date || null,
      filed_at: filing?.filed_at || null,
      filing_lag_days: filingLag,
      history_quarters: historyCount,
      position_count: owned.length,
      top_ten_concentration: rounded(topTenConcentration),
      turnover_proxy: rounded(turnoverProxy),
      mapping_coverage: rounded(mappingCoverage),
      data_quality_score: rounded(completeness),
      data_quality_label: scoreLabel(completeness),
      activity: {
        new: activity.filter((row) => row.change_type === 'new').length,
        increased: activity.filter((row) => row.change_type === 'increased').length,
        reduced: activity.filter((row) => row.change_type === 'reduced').length,
        exited: activity.filter((row) => row.change_type === 'exited').length,
      },
      performance: {
        status: 'not_calculable',
        reason: 'Filing-aware adjusted price history is required before alpha, hit rate or manager skill can be reported.',
      },
    };
  }).sort((a, b) => number(b.data_quality_score) - number(a.data_quality_score));
}

function buildOverlap(managerScorecards, holdings) {
  const sets = new Map();
  for (const manager of managerScorecards) sets.set(manager.id, new Set());
  for (const row of holdings.filter((item) => !item.put_call)) sets.get(row.manager_id)?.add(securityKey(row));
  const pairs = [];
  for (let left = 0; left < managerScorecards.length; left += 1) {
    for (let right = left + 1; right < managerScorecards.length; right += 1) {
      const a = managerScorecards[left];
      const b = managerScorecards[right];
      const aSet = sets.get(a.id) || new Set();
      const bSet = sets.get(b.id) || new Set();
      const shared = [...aSet].filter((key) => bSet.has(key));
      if (!shared.length) continue;
      const union = new Set([...aSet, ...bSet]).size;
      pairs.push({
        left: { slug: a.slug, name: a.display_name },
        right: { slug: b.slug, name: b.display_name },
        shared_count: shared.length,
        overlap_score: rounded(union ? shared.length / union * 100 : 0),
        shared_securities: shared.slice(0, 12),
      });
    }
  }
  return pairs.sort((a, b) => b.overlap_score - a.overlap_score || b.shared_count - a.shared_count).slice(0, 20);
}

async function buildDecisionIntelligence() {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Institutional database is not configured.');
  const [{ data: managers, error: managerError }, { data: allFilings, error: filingError }] = await Promise.all([
    client.from('institutional_managers').select('*').eq('active', true).order('display_name'),
    client.from('institutional_filings').select('*').eq('is_active', true).order('report_date', { ascending: false }),
  ]);
  if (managerError) throw managerError;
  if (filingError) throw filingError;
  const latestMap = latestByManager(allFilings || []);
  const latest = [...latestMap.values()];
  const asOfQuarter = modalQuarter(latest);
  const comparableFilings = latest.filter((row) => row.report_date === asOfQuarter);
  const comparableManagerIds = new Set(comparableFilings.map((row) => row.manager_id));
  const comparableManagers = (managers || []).filter((row) => comparableManagerIds.has(row.id));
  const filingIds = comparableFilings.map((row) => row.id);
  const holdings = filingIds.length ? await collect(() => client.from('institutional_holdings').select('*').in('filing_id', filingIds)) : [];
  const changes = filingIds.length ? await collect(() => client.from('holding_changes').select('*').in('filing_id', filingIds)) : [];
  const universe = buildSecurityUniverse({ holdings, changes, filings: comparableFilings, managers: comparableManagers });
  const managerScorecards = buildManagerScorecards({ managers: comparableManagers, filings: comparableFilings, holdings, changes, allFilings: allFilings || [] });
  const totalValue = holdings.filter((row) => !row.put_call).reduce((sum, row) => sum + number(row.value_usd), 0);
  const mappedValue = holdings.filter((row) => !row.put_call && row.ticker).reduce((sum, row) => sum + number(row.value_usd), 0);
  const mappedRows = holdings.filter((row) => !row.put_call && row.ticker).length;
  const ordinaryRows = holdings.filter((row) => !row.put_call).length;
  const newestAcceptance = comparableFilings.map((row) => row.filed_at).filter(Boolean).sort().reverse()[0] || null;
  const positiveActions = changes.filter((row) => ['new', 'increased'].includes(row.change_type)).length;
  const negativeActions = changes.filter((row) => ['reduced', 'exited'].includes(row.change_type)).length;
  const accumulationLeader = ranking(universe, 'accumulation', true)[0];
  const exitLeader = ranking(universe, 'exit_pressure', true)[0];
  const marketTone = positiveActions > negativeActions * 1.1 ? 'Accumulation-led' : negativeActions > positiveActions * 1.1 ? 'Reduction-led' : 'Balanced rotation';

  return {
    generated_at: new Date().toISOString(),
    as_of_quarter: asOfQuarter,
    acceptance_cutoff: newestAcceptance,
    methodology: {
      basis: 'Latest active SEC Form 13F filing for managers reporting the modal comparable quarter.',
      point_in_time_rule: 'A holding becomes knowable only at the SEC acceptance timestamp.',
      instrument_rule: 'Ordinary disclosed positions are scored separately from put and call rows.',
      universe_rule: `${comparableManagers.length} managers with comparable ${asOfQuarter || 'current'} filings; stale quarters are excluded from cross-manager scores.`,
      warning: '13F does not disclose cash, shorts, most derivatives, private assets, non-US securities or transactions after the reporting date.',
    },
    data_health: {
      tracked_managers: (managers || []).length,
      comparable_managers: comparableManagers.length,
      stale_or_pending_managers: Math.max(0, (managers || []).length - comparableManagers.length),
      filing_versions: (allFilings || []).length,
      ordinary_positions: ordinaryRows,
      option_positions: holdings.filter((row) => Boolean(row.put_call)).length,
      ticker_mapping_by_rows: rounded(ordinaryRows ? mappedRows / ordinaryRows * 100 : 0),
      ticker_mapping_by_value: rounded(totalValue ? mappedValue / totalValue * 100 : 0),
      score: rounded(clamp((comparableManagers.length / Math.max((managers || []).length, 1)) * 45 + (totalValue ? mappedValue / totalValue : 0) * 35 + Math.min((allFilings || []).length / Math.max((managers || []).length * 4, 1), 1) * 20)),
    },
    market_read: {
      tone: marketTone,
      positive_actions: positiveActions,
      negative_actions: negativeActions,
      active_securities: universe.filter((row) => Object.values(row.activity).some((value) => value > 0)).length,
      headline: accumulationLeader
        ? `${marketTone}: ${accumulationLeader.ticker || accumulationLeader.issuer_name} has the strongest verified positive breadth${exitLeader ? `, while ${exitLeader.ticker || exitLeader.issuer_name} carries the highest exit pressure` : ''}.`
        : 'Comparable filing history is still building; no market direction is inferred.',
    },
    rankings: {
      consensus: ranking(universe, 'consensus'),
      accumulation: ranking(universe, 'accumulation', true),
      exit_pressure: ranking(universe, 'exit_pressure', true),
      crowding: ranking(universe, 'crowding'),
      new_ideas: ranking(universe, 'new_idea', true),
    },
    overlap: buildOverlap(managerScorecards, holdings),
    managers: managerScorecards,
    screener: [...universe]
      .sort((a, b) => b.scores.consensus.score - a.scores.consensus.score)
      .slice(0, 300),
    capability_status: {
      sector_rotation: { status: 'not_calculable', reason: 'A point-in-time security sector classification table is not yet present.' },
      manager_skill: { status: 'not_calculable', reason: 'Adjusted daily prices and benchmark returns aligned to SEC acceptance timestamps are required.' },
      backtesting: { status: 'not_calculable', reason: 'No client result is produced until adjusted prices, delistings, corporate actions and transaction costs are available.' },
      other_filings: { status: 'not_integrated', reason: 'Schedule 13D/G, Form 4 and Form ADV remain separate from this 13F evidence graph.' },
    },
  };
}

export async function getInstitutionalDecisionIntelligence({ force = false } = {}) {
  if (!force && cached && Date.now() < cacheExpiresAt) return cached;
  cached = await buildDecisionIntelligence();
  cacheExpiresAt = Date.now() + CACHE_TTL_MS;
  return cached;
}

export function clearInstitutionalDecisionIntelligenceCache() {
  cached = null;
  cacheExpiresAt = 0;
}
