import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

const SEC_ROOT = 'https://www.sec.gov';
const SEC_DATA = 'https://data.sec.gov';
const SEC_USER_AGENT = (process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();
const PAGE_SIZE = 1000;

export const DEFAULT_MANAGERS = [
  { slug: 'berkshire-hathaway', display_name: 'Berkshire Hathaway', legal_name: 'BERKSHIRE HATHAWAY INC', cik: '0001067983', strategy: 'Concentrated quality and value', quality_weight: 1.20, active: true },
  { slug: 'pershing-square', display_name: 'Pershing Square', legal_name: 'PERSHING SQUARE CAPITAL MANAGEMENT, L.P.', cik: '0001336528', strategy: 'Concentrated activist', quality_weight: 1.15, active: true },
  { slug: 'appaloosa-management', display_name: 'Appaloosa Management', legal_name: 'APPALOOSA LP', cik: '0001656456', strategy: 'Opportunistic value', quality_weight: 1.05, active: true },
  { slug: 'baupost-group', display_name: 'Baupost Group', legal_name: 'BAUPOST GROUP LLC/MA', cik: '0001061768', strategy: 'Deep value and special situations', quality_weight: 1.15, active: true },
  { slug: 'third-point', display_name: 'Third Point', legal_name: 'THIRD POINT LLC', cik: '0001040273', strategy: 'Event-driven and activist', quality_weight: 1.05, active: true },
  { slug: 'greenlight-capital', display_name: 'Greenlight Capital', legal_name: 'GREENLIGHT CAPITAL INC', cik: '0001079114', strategy: 'Value-oriented long/short', quality_weight: 1.00, active: true },
  { slug: 'coatue-management', display_name: 'Coatue Management', legal_name: 'COATUE MANAGEMENT LLC', cik: '0001135730', strategy: 'Technology and growth', quality_weight: 1.00, active: true },
  { slug: 'viking-global', display_name: 'Viking Global', legal_name: 'VIKING GLOBAL INVESTORS LP', cik: '0001103804', strategy: 'Fundamental growth', quality_weight: 1.05, active: true },
  { slug: 'lone-pine-capital', display_name: 'Lone Pine Capital', legal_name: 'LONE PINE CAPITAL LLC', cik: '0001061165', strategy: 'Fundamental growth', quality_weight: 1.00, active: true },
  { slug: 'tiger-global', display_name: 'Tiger Global Management', legal_name: 'TIGER GLOBAL MANAGEMENT LLC', cik: '0001167483', strategy: 'Technology and growth', quality_weight: 0.95, active: true },
];

function db() {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Institutional Holdings database is not configured.');
  return client;
}

function cleanCik(value) {
  return String(value || '').replace(/\D/g, '').padStart(10, '0').slice(-10);
}

function n(value) {
  const parsed = Number(String(value ?? '').replace(/,/g, '').trim());
  return Number.isFinite(parsed) ? parsed : 0;
}

function clamp(value) {
  return Math.max(0, Math.min(100, Math.round(n(value) * 10) / 10));
}

function decodeXml(value = '') {
  return String(value)
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, '$1')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").trim();
}

function xmlValue(block, tag) {
  const match = String(block).match(new RegExp(`<(?:\\w+:)?${tag}(?:\\s[^>]*)?>([\\s\\S]*?)<\\/(?:\\w+:)?${tag}>`, 'i'));
  return decodeXml(match?.[1] || '').replace(/<[^>]+>/g, '').trim();
}

function parseInformationTable(xml) {
  const blocks = [...String(xml).matchAll(/<(?:\w+:)?infoTable(?:\s[^>]*)?>([\s\S]*?)<\/(?:\w+:)?infoTable>/gi)];
  return blocks.map((match) => {
    const block = match[1];
    return {
      cusip: xmlValue(block, 'cusip').toUpperCase(),
      issuer_name: xmlValue(block, 'nameOfIssuer'),
      title_of_class: xmlValue(block, 'titleOfClass'),
      value_usd: n(xmlValue(block, 'value')) * 1000,
      shares: n(xmlValue(block, 'sshPrnamt')),
      share_type: xmlValue(block, 'sshPrnamtType'),
      put_call: xmlValue(block, 'putCall').toUpperCase() || null,
      investment_discretion: xmlValue(block, 'investmentDiscretion').toUpperCase() || null,
      other_manager: xmlValue(block, 'otherManager') || null,
      voting_sole: n(xmlValue(block, 'Sole')),
      voting_shared: n(xmlValue(block, 'Shared')),
      voting_none: n(xmlValue(block, 'None')),
    };
  }).filter((row) => row.cusip && row.issuer_name);
}

function filingKey(row) {
  return `${row.cusip}|${row.title_of_class || ''}|${row.put_call || ''}|${row.investment_discretion || ''}`;
}

async function collect(factory, pageSize = PAGE_SIZE) {
  const rows = [];
  for (let from = 0; ; from += pageSize) {
    const { data, error } = await factory().range(from, from + pageSize - 1);
    if (error) throw error;
    rows.push(...(data || []));
    if (!data || data.length < pageSize) break;
  }
  return rows;
}

async function seedManagers(client) {
  const { error } = await client.from('institutional_managers').upsert(DEFAULT_MANAGERS, {
    onConflict: 'cik',
    ignoreDuplicates: true,
  });
  if (error) throw error;
}

async function managers(client) {
  await seedManagers(client);
  const { data, error } = await client.from('institutional_managers').select('*').eq('active', true).order('display_name');
  if (error) throw error;
  return data || [];
}

function latestByManager(filings) {
  const map = new Map();
  for (const filing of filings || []) {
    const current = map.get(filing.manager_id);
    if (!current || `${filing.report_date}|${filing.filed_at}` > `${current.report_date}|${current.filed_at}`) map.set(filing.manager_id, filing);
  }
  return map;
}

function securityKey(row) {
  return row.ticker || row.cusip;
}

function scoreLabel(type, score) {
  if (type === 'exit_pressure') return score >= 67 ? 'Elevated' : score >= 34 ? 'Moderate' : 'Low';
  if (type === 'consensus') return score >= 67 ? 'Broad' : score >= 34 ? 'Selective' : 'Sparse';
  return score >= 67 ? 'High' : score >= 34 ? 'Moderate' : 'Low';
}

function signal(type, score, components, explanation) {
  const value = clamp(score);
  return { signal_type: type, score: value, label: scoreLabel(type, value), components, explanation };
}

function aggregateConsensus(latestHoldings, changes, managerCount) {
  const changeMap = new Map();
  for (const row of changes) {
    const key = row.ticker || row.cusip;
    if (!changeMap.has(key)) changeMap.set(key, []);
    changeMap.get(key).push(row);
  }
  const map = new Map();
  for (const row of latestHoldings.filter((item) => !item.put_call)) {
    const key = securityKey(row);
    if (!map.has(key)) map.set(key, { key, cusip: row.cusip, ticker: row.ticker, issuer_name: row.issuer_name, owners: new Set(), aggregate_weight: 0, aggregate_value_usd: 0 });
    const item = map.get(key);
    item.owners.add(row.manager_id);
    item.aggregate_weight += n(row.portfolio_weight);
    item.aggregate_value_usd += n(row.value_usd);
  }
  return [...map.values()].map((item) => {
    const related = changeMap.get(item.key) || changeMap.get(item.cusip) || [];
    const owners = item.owners.size;
    const breadth = managerCount ? owners / managerCount : 0;
    const consensusScore = clamp(breadth * 80 + Math.min(item.aggregate_weight / Math.max(owners, 1), 10) * 2);
    return {
      ...item,
      owners,
      owner_ids: [...item.owners],
      aggregate_weight: Math.round(item.aggregate_weight * 100) / 100,
      consensus_score: consensusScore,
      new_buyers: related.filter((row) => row.change_type === 'new').length,
      increasers: related.filter((row) => row.change_type === 'increased').length,
      reducers: related.filter((row) => row.change_type === 'reduced').length,
      exits: related.filter((row) => row.change_type === 'exited').length,
    };
  }).sort((a, b) => b.consensus_score - a.consensus_score || b.aggregate_weight - a.aggregate_weight);
}

export async function getInstitutionalOverview() {
  const client = db();
  const managerRows = await managers(client);
  const { data: filingRows, error: filingError } = await client.from('institutional_filings').select('*').eq('is_active', true).order('report_date', { ascending: false });
  if (filingError) throw filingError;
  const latest = latestByManager(filingRows || []);
  const filingIds = [...latest.values()].map((row) => row.id);
  const holdings = filingIds.length ? await collect(() => client.from('institutional_holdings').select('*').in('filing_id', filingIds)) : [];
  const changes = filingIds.length ? await collect(() => client.from('holding_changes').select('*').in('filing_id', filingIds)) : [];
  const consensus = aggregateConsensus(holdings, changes, managerRows.length);
  const fundCards = managerRows.map((manager) => {
    const filing = latest.get(manager.id) || null;
    const owned = filing ? holdings.filter((row) => row.filing_id === filing.id && !row.put_call) : [];
    return {
      ...manager,
      latest_filing: filing,
      position_count: owned.length,
      top_positions: owned.sort((a, b) => n(b.portfolio_weight) - n(a.portfolio_weight)).slice(0, 3),
      new_positions: filing ? changes.filter((row) => row.filing_id === filing.id && row.change_type === 'new').length : 0,
      exits: filing ? changes.filter((row) => row.filing_id === filing.id && row.change_type === 'exited').length : 0,
    };
  });
  const { data: alerts } = await client.from('institutional_filing_alerts').select('*, institutional_managers(display_name, slug)').order('created_at', { ascending: false }).limit(12);
  return {
    generated_at: new Date().toISOString(),
    reporting_basis: 'SEC Form 13F, available only after the SEC acceptance timestamp',
    managers: fundCards,
    consensus: consensus.slice(0, 30),
    alerts: alerts || [],
    covered_managers: managerRows.length,
    managers_with_filings: latest.size,
    latest_report_date: [...latest.values()].map((row) => row.report_date).sort().reverse()[0] || null,
  };
}

export async function getInstitutionalFund(slug) {
  const client = db();
  await seedManagers(client);
  const { data: manager, error: managerError } = await client.from('institutional_managers').select('*').eq('slug', slug).maybeSingle();
  if (managerError) throw managerError;
  if (!manager) return null;
  const { data: filings, error: filingError } = await client.from('institutional_filings').select('*').eq('manager_id', manager.id).eq('is_active', true).order('report_date', { ascending: false }).order('filed_at', { ascending: false }).limit(16);
  if (filingError) throw filingError;
  const latest = filings?.[0] || null;
  const holdings = latest ? await collect(() => client.from('institutional_holdings').select('*').eq('filing_id', latest.id).order('portfolio_weight', { ascending: false })) : [];
  const changes = latest ? await collect(() => client.from('holding_changes').select('*').eq('filing_id', latest.id).order('current_weight', { ascending: false })) : [];
  const { data: signals } = latest ? await client.from('institutional_signals').select('*').eq('scope_type', 'fund').eq('scope_id', manager.id).eq('as_of', latest.report_date).order('signal_type') : { data: [] };
  return { manager, filings: filings || [], latest_filing: latest, holdings, changes, signals: signals || [] };
}

export async function getInstitutionalStock(rawKey) {
  const client = db();
  const key = decodeURIComponent(String(rawKey || '')).trim().toUpperCase();
  if (!key) return null;
  const managerRows = await managers(client);
  const { data: filingRows, error: filingError } = await client.from('institutional_filings').select('*').eq('is_active', true).order('report_date', { ascending: false });
  if (filingError) throw filingError;
  const latest = latestByManager(filingRows || []);
  const ids = [...latest.values()].map((row) => row.id);
  if (!ids.length) return { key, owners: [], history: [], manager_count: managerRows.length };
  const holdings = await collect(() => client.from('institutional_holdings').select('*').in('filing_id', ids).or(`ticker.eq.${key},cusip.eq.${key}`));
  const identity = holdings[0] || null;
  if (!identity) return null;
  const allHistory = await collect(() => client.from('institutional_holdings').select('*, institutional_managers(display_name, slug)').or(`ticker.eq.${identity.ticker || key},cusip.eq.${identity.cusip}`).order('report_date', { ascending: false }));
  const managerMap = new Map(managerRows.map((row) => [row.id, row]));
  const owners = holdings.filter((row) => !row.put_call).map((row) => ({ ...row, manager: managerMap.get(row.manager_id), filing: latest.get(row.manager_id) }));
  const { data: changes } = await client.from('holding_changes').select('*').in('filing_id', ids).eq('cusip', identity.cusip);
  const consensusScore = clamp((owners.length / Math.max(managerRows.length, 1)) * 80 + Math.min(owners.reduce((sum, row) => sum + n(row.portfolio_weight), 0) / Math.max(owners.length, 1), 10) * 2);
  return {
    key: identity.ticker || identity.cusip,
    ticker: identity.ticker,
    cusip: identity.cusip,
    issuer_name: identity.issuer_name,
    manager_count: managerRows.length,
    owner_count: owners.length,
    aggregate_weight: owners.reduce((sum, row) => sum + n(row.portfolio_weight), 0),
    aggregate_value_usd: owners.reduce((sum, row) => sum + n(row.value_usd), 0),
    consensus_score: consensusScore,
    owners: owners.sort((a, b) => n(b.portfolio_weight) - n(a.portfolio_weight)),
    changes: changes || [],
    history: allHistory,
  };
}

async function secFetch(url, asJson = false) {
  const response = await fetch(url, {
    headers: { Accept: asJson ? 'application/json' : 'application/xml,text/xml,text/plain,*/*', 'User-Agent': SEC_USER_AGENT },
    signal: AbortSignal.timeout(25_000),
  });
  if (!response.ok) throw new Error(`SEC request failed (${response.status}) for ${url}`);
  return asJson ? response.json() : response.text();
}

function recent13fFilings(submissions, quarters) {
  const recent = submissions?.filings?.recent || {};
  const forms = recent.form || [];
  const rows = forms.map((form, index) => ({
    form_type: form,
    accession_number: recent.accessionNumber?.[index],
    report_date: recent.reportDate?.[index],
    filing_date: recent.filingDate?.[index],
    accepted_at: recent.acceptanceDateTime?.[index] || `${recent.filingDate?.[index]}T00:00:00Z`,
    primary_document: recent.primaryDocument?.[index] || '',
  })).filter((row) => ['13F-HR', '13F-HR/A'].includes(row.form_type) && row.report_date && row.accession_number);
  const periods = [...new Set(rows.map((row) => row.report_date))].sort().reverse().slice(0, Math.max(1, Math.min(n(quarters) || 4, 16)));
  return rows.filter((row) => periods.includes(row.report_date)).sort((a, b) => String(a.accepted_at).localeCompare(String(b.accepted_at)));
}

async function filingDocuments(cik, accession) {
  const compactCik = String(Number(cleanCik(cik)));
  const compactAccession = accession.replace(/-/g, '');
  const base = `${SEC_ROOT}/Archives/edgar/data/${compactCik}/${compactAccession}`;
  const index = await secFetch(`${base}/index.json`, true);
  const names = (index?.directory?.item || []).map((item) => item.name).filter((name) => /\.(xml|txt)$/i.test(name));
  const documents = [];
  for (const name of names.slice(0, 12)) {
    const text = await secFetch(`${base}/${name}`);
    documents.push({ name, text });
    if (documents.some((doc) => /<(?:\w+:)?infoTable[\s>]/i.test(doc.text))) break;
  }
  return { base, documents };
}

async function mappingsFor(client, cusips) {
  if (!cusips.length) return new Map();
  const rows = [];
  for (let index = 0; index < cusips.length; index += 400) {
    const { data, error } = await client.from('security_identifier_history').select('*').in('cusip', cusips.slice(index, index + 400)).order('valid_from', { ascending: false });
    if (error) throw error;
    rows.push(...(data || []));
  }
  const map = new Map();
  for (const row of rows) if (!map.has(row.cusip)) map.set(row.cusip, row);
  return map;
}

function buildChanges(current, previous, filing) {
  const now = new Map(current.filter((row) => !row.put_call).map((row) => [filingKey(row), row]));
  const before = new Map(previous.filter((row) => !row.put_call).map((row) => [filingKey(row), row]));
  const output = [];
  for (const key of new Set([...now.keys(), ...before.keys()])) {
    const currentRow = now.get(key);
    const previousRow = before.get(key);
    const currentShares = n(currentRow?.shares);
    const previousShares = n(previousRow?.shares);
    const delta = currentShares - previousShares;
    let type = null;
    if (currentRow && !previousRow) type = 'new';
    else if (!currentRow && previousRow) type = 'exited';
    else if (Math.abs(delta) > Math.max(1, previousShares * 0.001)) type = delta > 0 ? 'increased' : 'reduced';
    if (!type) continue;
    const row = currentRow || previousRow;
    output.push({
      filing_id: filing.id,
      manager_id: filing.manager_id,
      report_date: filing.report_date,
      cusip: row.cusip,
      ticker: row.ticker,
      issuer_name: row.issuer_name,
      change_type: type,
      current_shares: currentShares,
      previous_shares: previousShares,
      share_change: delta,
      share_change_pct: previousShares ? (delta / previousShares) * 100 : null,
      current_weight: n(currentRow?.portfolio_weight),
      previous_weight: n(previousRow?.portfolio_weight),
      weight_change: n(currentRow?.portfolio_weight) - n(previousRow?.portfolio_weight),
    });
  }
  return output;
}

async function insertChunks(client, table, rows, size = 500) {
  for (let index = 0; index < rows.length; index += size) {
    const { error } = await client.from(table).insert(rows.slice(index, index + size));
    if (error) throw error;
  }
}

async function createAlerts(client, manager, filing, changes) {
  const alerts = [{
    filing_id: filing.id,
    manager_id: manager.id,
    alert_type: 'filing_received',
    severity: filing.is_amendment ? 'notable' : 'info',
    title: `${manager.display_name} filed ${filing.form_type}`,
    body: `Portfolio for ${filing.report_date} became public on ${String(filing.filed_at).slice(0, 10)} with ${filing.holdings_count} disclosed lines.`,
  }];
  for (const row of changes.filter((item) => ['new', 'exited'].includes(item.change_type) && Math.max(item.current_weight, item.previous_weight) >= 1).slice(0, 12)) {
    alerts.push({
      filing_id: filing.id,
      manager_id: manager.id,
      alert_type: row.change_type,
      severity: Math.max(row.current_weight, row.previous_weight) >= 3 ? 'high' : 'notable',
      title: `${manager.display_name} ${row.change_type === 'new' ? 'opened' : 'exited'} ${row.ticker || row.issuer_name}`,
      body: `${row.change_type === 'new' ? 'New position' : 'Reported exit'} representing ${Math.max(row.current_weight, row.previous_weight).toFixed(2)}% of the comparable disclosed portfolio.`,
      security_key: row.ticker || row.cusip,
    });
  }
  const { error } = await client.from('institutional_filing_alerts').upsert(alerts, { onConflict: 'filing_id,alert_type,title', ignoreDuplicates: true });
  if (error) throw error;
}

async function ingestFiling(client, manager, source) {
  const { data: existing } = await client.from('institutional_filings').select('*').eq('accession_number', source.accession_number).maybeSingle();
  if (existing?.holdings_count > 0) return { accession_number: source.accession_number, status: 'already_ingested', holdings: existing.holdings_count };
  const archive = await filingDocuments(manager.cik, source.accession_number);
  const infoDocument = archive.documents.find((doc) => /<(?:\w+:)?infoTable[\s>]/i.test(doc.text));
  if (!infoDocument) throw new Error(`No 13F information table found in ${source.accession_number}`);
  const rawRows = parseInformationTable(infoDocument.text);
  if (!rawRows.length) throw new Error(`The SEC information table was empty for ${source.accession_number}`);
  const combined = archive.documents.map((doc) => doc.text).join('\n');
  const isRestatement = /<(?:\w+:)?isRestatement>\s*true\s*</i.test(combined);
  const amendmentType = source.form_type === '13F-HR' ? 'original' : isRestatement ? 'restatement' : 'additional_holdings';
  const { data: previousVersion } = await client.from('institutional_filings').select('*').eq('manager_id', manager.id).eq('report_date', source.report_date).eq('is_active', true).order('filed_at', { ascending: false }).limit(1).maybeSingle();
  let rows = rawRows;
  if (source.form_type === '13F-HR/A' && !isRestatement && previousVersion) {
    const priorVersionRows = await collect(() => client.from('institutional_holdings').select('*').eq('filing_id', previousVersion.id));
    const merged = new Map(priorVersionRows.map((row) => [filingKey(row), row]));
    for (const row of rawRows) merged.set(filingKey(row), row);
    rows = [...merged.values()].map(({ id, filing_id, manager_id, report_date, portfolio_weight, created_at, ...row }) => row);
  }
  const identifierMap = await mappingsFor(client, [...new Set(rows.map((row) => row.cusip))]);
  const totalValue = rows.reduce((sum, row) => sum + n(row.value_usd), 0);
  rows = rows.map((row) => ({
    ...row,
    ticker: identifierMap.get(row.cusip)?.ticker || row.ticker || null,
    manager_id: manager.id,
    report_date: source.report_date,
    portfolio_weight: totalValue ? (n(row.value_usd) / totalValue) * 100 : 0,
  }));
  const filingPayload = {
    manager_id: manager.id,
    accession_number: source.accession_number,
    form_type: source.form_type,
    report_date: source.report_date,
    filed_at: source.accepted_at,
    primary_document: source.primary_document,
    amendment_type: amendmentType,
    is_amendment: source.form_type.endsWith('/A'),
    is_active: true,
    source_url: `${archive.base}/${source.primary_document || infoDocument.name}`,
    holdings_count: rows.length,
    total_value_usd: totalValue,
    ingested_at: new Date().toISOString(),
  };
  const { data: filing, error: filingError } = await client.from('institutional_filings').upsert(filingPayload, { onConflict: 'accession_number' }).select().single();
  if (filingError) throw filingError;
  await client.from('institutional_filings').update({ is_active: false }).eq('manager_id', manager.id).eq('report_date', source.report_date).neq('id', filing.id);
  await client.from('institutional_holdings').delete().eq('filing_id', filing.id);
  await insertChunks(client, 'institutional_holdings', rows.map((row) => ({ ...row, filing_id: filing.id })));
  const { data: priorFiling } = await client.from('institutional_filings').select('*').eq('manager_id', manager.id).eq('is_active', true).lt('report_date', source.report_date).order('report_date', { ascending: false }).order('filed_at', { ascending: false }).limit(1).maybeSingle();
  const previousRows = priorFiling ? await collect(() => client.from('institutional_holdings').select('*').eq('filing_id', priorFiling.id)) : [];
  const changes = buildChanges(rows, previousRows, filing);
  await client.from('holding_changes').delete().eq('filing_id', filing.id);
  if (changes.length) await insertChunks(client, 'holding_changes', changes);
  await createAlerts(client, manager, filing, changes);
  return { accession_number: filing.accession_number, status: 'ingested', holdings: rows.length, report_date: filing.report_date, changes: changes.length };
}

async function rebuildSignals(client) {
  const managerRows = await managers(client);
  const { data: filings, error } = await client.from('institutional_filings').select('*').eq('is_active', true).order('report_date', { ascending: false });
  if (error) throw error;
  const latest = latestByManager(filings || []);
  const ids = [...latest.values()].map((row) => row.id);
  if (!ids.length) return { funds: 0, stocks: 0 };
  const holdings = await collect(() => client.from('institutional_holdings').select('*').in('filing_id', ids));
  const changes = await collect(() => client.from('holding_changes').select('*').in('filing_id', ids));
  const consensus = aggregateConsensus(holdings, changes, managerRows.length);
  const breadth = new Map(consensus.map((row) => [row.cusip, row.owners]));
  const signalRows = [];
  for (const manager of managerRows) {
    const filing = latest.get(manager.id);
    if (!filing) continue;
    const owned = holdings.filter((row) => row.filing_id === filing.id && !row.put_call).sort((a, b) => n(b.portfolio_weight) - n(a.portfolio_weight));
    const activity = changes.filter((row) => row.filing_id === filing.id);
    const top10 = owned.slice(0, 10).reduce((sum, row) => sum + n(row.portfolio_weight), 0);
    const accumulationWeight = activity.filter((row) => ['new', 'increased'].includes(row.change_type)).reduce((sum, row) => sum + Math.max(0, n(row.weight_change)), 0);
    const newWeight = activity.filter((row) => row.change_type === 'new').reduce((sum, row) => sum + n(row.current_weight), 0);
    const exitWeight = activity.filter((row) => ['exited', 'reduced'].includes(row.change_type)).reduce((sum, row) => sum + Math.max(0, -n(row.weight_change)), 0);
    const avgBreadth = owned.slice(0, 10).length ? owned.slice(0, 10).reduce((sum, row) => sum + n(breadth.get(row.cusip)), 0) / owned.slice(0, 10).length : 0;
    const scores = [
      signal('conviction', top10, { top_10_weight_pct: top10, positions: owned.length }, 'Top-10 disclosed portfolio concentration, capped at 100.'),
      signal('accumulation', accumulationWeight * 4, { positive_weight_change_pct: accumulationWeight }, 'Positive weight added through new and increased positions, scaled against 25%.'),
      signal('new_idea', newWeight * 8, { new_position_weight_pct: newWeight }, 'Current portfolio weight represented by newly disclosed positions, scaled against 12.5%.'),
      signal('exit_pressure', exitWeight * 4, { reduced_or_exited_weight_pct: exitWeight }, 'Portfolio weight removed through reductions and exits, scaled against 25%.'),
      signal('consensus', (avgBreadth / Math.max(managerRows.length, 1)) * 100, { average_top10_owner_count: avgBreadth, tracked_managers: managerRows.length }, 'Average ownership breadth across the fund top ten positions.'),
    ];
    signalRows.push(...scores.map((row) => ({ ...row, scope_type: 'fund', scope_id: manager.id, as_of: filing.report_date })));
  }
  for (const row of consensus) {
    signalRows.push({
      ...signal('consensus', row.consensus_score, { owners: row.owners, tracked_managers: managerRows.length, aggregate_weight_pct: row.aggregate_weight }, 'Tracked-manager breadth plus average disclosed portfolio importance.'),
      scope_type: 'stock', scope_id: row.cusip, as_of: [...latest.values()].map((item) => item.report_date).sort().reverse()[0],
    });
  }
  await client.from('institutional_signals').delete().in('scope_type', ['fund', 'stock']);
  if (signalRows.length) {
    const { error: insertError } = await client.from('institutional_signals').upsert(signalRows, { onConflict: 'scope_type,scope_id,as_of,signal_type' });
    if (insertError) throw insertError;
  }
  return { funds: latest.size, stocks: consensus.length };
}

export async function refreshInstitutionalFilings({ managerSlug, quarters = 4 } = {}) {
  const client = db();
  const managerRows = await managers(client);
  const selected = managerSlug && managerSlug !== 'all' ? managerRows.filter((row) => row.slug === managerSlug) : managerRows;
  if (!selected.length) throw new Error('Select a tracked manager.');
  const results = [];
  for (const manager of selected) {
    try {
      const submissions = await secFetch(`${SEC_DATA}/submissions/CIK${cleanCik(manager.cik)}.json`, true);
      const filingRows = recent13fFilings(submissions, quarters);
      const filings = [];
      for (const filing of filingRows) filings.push(await ingestFiling(client, manager, filing));
      results.push({ manager: manager.display_name, cik: manager.cik, ok: true, filings });
    } catch (error) {
      results.push({ manager: manager.display_name, cik: manager.cik, ok: false, error: error.message });
    }
  }
  const scores = await rebuildSignals(client);
  return { ok: results.some((row) => row.ok), refreshed_at: new Date().toISOString(), results, scores };
}

export async function getInstitutionalAdmin() {
  const client = db();
  const managerRows = await managers(client);
  const unresolved = await collect(() => client.from('institutional_holdings').select('cusip,issuer_name,report_date,value_usd').is('ticker', null).order('value_usd', { ascending: false }));
  const unresolvedMap = new Map();
  for (const row of unresolved) {
    if (!unresolvedMap.has(row.cusip)) unresolvedMap.set(row.cusip, { ...row, observations: 0 });
    unresolvedMap.get(row.cusip).observations += 1;
  }
  const { data: filings } = await client.from('institutional_filings').select('*, institutional_managers(display_name,slug)').order('filed_at', { ascending: false }).limit(30);
  const { data: alerts } = await client.from('institutional_filing_alerts').select('*, institutional_managers(display_name,slug)').order('created_at', { ascending: false }).limit(50);
  const { data: corrections } = await client.from('institutional_corrections').select('*').order('created_at', { ascending: false }).limit(50);
  return {
    managers: managerRows,
    filings: filings || [],
    alerts: alerts || [],
    corrections: corrections || [],
    unresolved: [...unresolvedMap.values()].slice(0, 100),
    sec_user_agent_configured: Boolean(process.env.SEC_USER_AGENT),
  };
}

export async function saveSecurityMapping({ cusip, ticker, issuer_name, reason, actor } = {}) {
  const client = db();
  const cleanCusip = String(cusip || '').trim().toUpperCase();
  const cleanTicker = String(ticker || '').trim().toUpperCase();
  if (!cleanCusip || !cleanTicker) throw new Error('CUSIP and ticker are required.');
  const { data: previous } = await client.from('security_identifier_history').select('*').eq('cusip', cleanCusip).order('valid_from', { ascending: false }).limit(1).maybeSingle();
  const { error } = await client.from('security_identifier_history').upsert({ cusip: cleanCusip, ticker: cleanTicker, issuer_name: issuer_name || previous?.issuer_name || null, valid_from: '1900-01-01', source: 'manual_cms', manually_verified: true, updated_at: new Date().toISOString() }, { onConflict: 'cusip,valid_from' });
  if (error) throw error;
  await client.from('institutional_holdings').update({ ticker: cleanTicker }).eq('cusip', cleanCusip);
  await client.from('holding_changes').update({ ticker: cleanTicker }).eq('cusip', cleanCusip);
  await client.from('institutional_corrections').insert({ entity_type: 'security', entity_key: cleanCusip, field_name: 'ticker', old_value: previous?.ticker || null, new_value: cleanTicker, reason: reason || null, actor: actor || 'admin' });
  await rebuildSignals(client);
  return { ok: true, cusip: cleanCusip, ticker: cleanTicker };
}

export async function updateInstitutionalManager(id, changes = {}, actor = 'admin') {
  const client = db();
  const allowed = ['display_name', 'legal_name', 'cik', 'strategy', 'quality_weight', 'active'];
  const patch = Object.fromEntries(allowed.filter((key) => changes[key] !== undefined).map((key) => [key, key === 'cik' ? cleanCik(changes[key]) : changes[key]]));
  const { data: previous, error: previousError } = await client.from('institutional_managers').select('*').eq('id', id).single();
  if (previousError) throw previousError;
  const { data, error } = await client.from('institutional_managers').update({ ...patch, updated_at: new Date().toISOString() }).eq('id', id).select().single();
  if (error) throw error;
  const corrections = Object.entries(patch).filter(([key, value]) => String(previous[key] ?? '') !== String(value ?? '')).map(([key, value]) => ({ entity_type: 'manager', entity_key: previous.slug, field_name: key, old_value: String(previous[key] ?? ''), new_value: String(value ?? ''), reason: changes.reason || null, actor }));
  if (corrections.length) await client.from('institutional_corrections').insert(corrections);
  return data;
}

export async function markInstitutionalAlert(id, isRead = true) {
  const client = db();
  const { data, error } = await client.from('institutional_filing_alerts').update({ is_read: Boolean(isRead) }).eq('id', id).select().single();
  if (error) throw error;
  return data;
}
