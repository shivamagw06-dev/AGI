import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { getCollectionHealth, listRuns } from './institutionalCollectionRuns.js';
import { classifyFiling, applyAmendment, droppedPositions } from './secAmendment.js';

const SEC_ROOT = 'https://www.sec.gov';
const SEC_DATA = 'https://data.sec.gov';
import { scheduleSecRequest, recordThrottled, recordSuccess, parseRetryAfter, SecCircuitOpenError } from './secRateLimiter.js';

const SEC_USER_AGENT = (process.env.SEC_USER_AGENT || 'AGI Institutional Research research@agarwalglobalinvestments.com').trim();
const OPENFIGI_URL = 'https://api.openfigi.com/v3/mapping';
const OPENFIGI_API_KEY = String(process.env.OPENFIGI_API_KEY || '').trim();
const PAGE_SIZE = 1000;
const CONSENSUS_MIN_MANAGERS = 4;
const AUTO_REFRESH_INTERVAL_MS = 24 * 60 * 60 * 1000;
const POST_2022_VALUE_RULE_DATE = '2023-01-03';

export const DEFAULT_MANAGERS = [
  { slug: 'situational-awareness', display_name: 'Situational Awareness', legal_name: 'SITUATIONAL AWARENESS LP', cik: '0002045724', strategy: 'AI and technology concentration', manager_type: 'Investment manager', quality_weight: 1.10, earliest_report_date: '2024-12-31', city: 'San Francisco', state: 'CA', country: 'United States', postal_code: '94107', active: true },
  { slug: 'berkshire-hathaway', display_name: 'Berkshire Hathaway', legal_name: 'BERKSHIRE HATHAWAY INC', cik: '0001067983', strategy: 'Concentrated quality and value', manager_type: 'Holding company', quality_weight: 1.20, earliest_report_date: '2001-03-31', city: 'Omaha', state: 'NE', country: 'United States', postal_code: '68131', active: true },
  { slug: 'duquesne-family-office', display_name: 'Duquesne Family Office', legal_name: 'DUQUESNE FAMILY OFFICE LLC', cik: '0001536411', strategy: 'Macro and concentrated equities', manager_type: 'Family office', quality_weight: 1.15, earliest_report_date: '2011-12-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10019', active: true },
  { slug: 'blackrock', display_name: 'BlackRock', legal_name: 'BLACKROCK INC.', cik: '0001364742', strategy: 'Diversified global asset management', manager_type: 'Asset manager', quality_weight: 0.85, earliest_report_date: '2006-03-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10001', active: true },
  { slug: 'pershing-square', display_name: 'Pershing Square Capital Management', legal_name: 'PERSHING SQUARE CAPITAL MANAGEMENT, L.P.', cik: '0001336528', strategy: 'Concentrated activist', manager_type: 'Investment manager', quality_weight: 1.15, earliest_report_date: '2005-12-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10019', active: true },
  { slug: 'scion-asset-management', display_name: 'Scion Asset Management', legal_name: 'SCION ASSET MANAGEMENT, LLC', cik: '0001649339', strategy: 'Contrarian and special situations', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2015-12-31', city: 'Saratoga', state: 'CA', country: 'United States', postal_code: '95070', active: true },
  { slug: 'tci-fund-management', display_name: 'TCI Fund Management', legal_name: 'TCI FUND MANAGEMENT LTD', cik: '0001647251', strategy: 'Concentrated global activist', manager_type: 'Investment manager', quality_weight: 1.15, earliest_report_date: '2006-03-31', city: 'London', state: '', country: 'United Kingdom', postal_code: 'W1S 2FT', active: true },
  { slug: 'bridgewater-associates', display_name: 'Bridgewater Associates', legal_name: 'BRIDGEWATER ASSOCIATES, LP', cik: '0001350694', strategy: 'Systematic global macro', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2005-12-31', city: 'Westport', state: 'CT', country: 'United States', postal_code: '06880', active: true },
  { slug: 'national-pension-service', display_name: 'National Pension Service', legal_name: 'NATIONAL PENSION SERVICE', cik: '0001608046', strategy: 'Diversified pension allocation', manager_type: 'Pension fund', quality_weight: 0.85, earliest_report_date: '2014-09-30', city: 'Jeonju-si, Jeollabuk-do', state: '', country: 'Korea, Republic of', postal_code: '54870', active: true },
  { slug: 'altimeter-capital', display_name: 'Altimeter Capital Management', legal_name: 'ALTIMETER CAPITAL MANAGEMENT, LP', cik: '0001541617', strategy: 'Technology and growth', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2011-12-31', city: 'Menlo Park', state: 'CA', country: 'United States', postal_code: '94025', active: true },
  { slug: 'atreides-management', display_name: 'Atreides Management', legal_name: 'ATREIDES MANAGEMENT, LP', cik: '0001777813', strategy: 'Technology and thematic equities', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2019-12-31', city: 'Boston', state: 'MA', country: 'United States', postal_code: '02110', active: true },
  { slug: 'renaissance-technologies', display_name: 'Renaissance Technologies', legal_name: 'RENAISSANCE TECHNOLOGIES LLC', cik: '0001037389', strategy: 'Systematic quantitative equities', manager_type: 'Investment manager', quality_weight: 0.95, earliest_report_date: '2001-03-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10022', active: true },
  { slug: 'appaloosa-management', display_name: 'Appaloosa', legal_name: 'APPALOOSA LP', cik: '0001656456', strategy: 'Opportunistic value', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2001-03-31', city: 'Short Hills', state: 'NJ', country: 'United States', postal_code: '07078', active: true },
  { slug: 'nvidia', display_name: 'NVIDIA Corp', legal_name: 'NVIDIA CORP', cik: '0001045810', strategy: 'Corporate investment holdings', manager_type: 'Corporate filer', quality_weight: 0.75, earliest_report_date: '2023-12-31', city: 'Santa Clara', state: 'CA', country: 'United States', postal_code: '95051', active: true },
  { slug: 'himalaya-capital', display_name: 'Himalaya Capital Management', legal_name: 'HIMALAYA CAPITAL MANAGEMENT LLC', cik: '0001709323', strategy: 'Long-term value', manager_type: 'Investment manager', quality_weight: 1.10, earliest_report_date: '2016-12-31', city: 'Seattle', state: 'WA', country: 'United States', postal_code: '98101', active: true },
  { slug: 'coatue-management', display_name: 'Coatue Management', legal_name: 'COATUE MANAGEMENT LLC', cik: '0001135730', strategy: 'Technology and growth', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2001-03-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10019', active: true },
  { slug: 'tiger-global', display_name: 'Tiger Global Management', legal_name: 'TIGER GLOBAL MANAGEMENT LLC', cik: '0001167483', strategy: 'Technology and growth', manager_type: 'Investment manager', quality_weight: 0.95, earliest_report_date: '2001-12-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10019', active: true },
  { slug: 'baker-bros-advisors', display_name: 'Baker Bros Advisors', legal_name: 'BAKER BROS. ADVISORS LP', cik: '0001263508', strategy: 'Healthcare and biotechnology', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2001-12-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10014', active: true },
  { slug: 'baupost-group', display_name: 'The Baupost Group', legal_name: 'BAUPOST GROUP LLC/MA', cik: '0001061768', strategy: 'Deep value and special situations', manager_type: 'Investment manager', quality_weight: 1.15, value_scale_override: 1000, earliest_report_date: '2001-03-31', city: 'Boston', state: 'MA', country: 'United States', postal_code: '02116', active: true },
  { slug: 'citadel-advisors', display_name: 'Citadel Advisors', legal_name: 'CITADEL ADVISORS LLC', cik: '0001423053', strategy: 'Multi-strategy and market neutral', manager_type: 'Investment manager', quality_weight: 0.90, earliest_report_date: '2002-06-30', city: 'Miami', state: 'FL', country: 'United States', postal_code: '33131', active: true },
  { slug: 'whale-rock-capital', display_name: 'Whale Rock Capital Management', legal_name: 'WHALE ROCK CAPITAL MANAGEMENT LLC', cik: '0001387322', strategy: 'Technology and communications', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2006-12-31', city: 'Boston', state: 'MA', country: 'United States', postal_code: '02110', active: true },
  { slug: 'vanguard-group', display_name: 'The Vanguard Group', legal_name: 'VANGUARD GROUP INC', cik: '0000102909', strategy: 'Diversified index and active management', manager_type: 'Asset manager', quality_weight: 0.80, earliest_report_date: '2001-03-31', city: 'Malvern', state: 'PA', country: 'United States', postal_code: '19355', active: true },
  { slug: 'd1-capital-partners', display_name: 'D1 Capital Partners', legal_name: 'D1 CAPITAL PARTNERS L.P.', cik: '0001747057', strategy: 'Global growth and technology', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2018-12-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10019', active: true },
  { slug: 'baillie-gifford', display_name: 'Baillie Gifford & Company', legal_name: 'BAILLIE GIFFORD & CO', cik: '0001088875', strategy: 'Long-duration global growth', manager_type: 'Asset manager', quality_weight: 1.00, earliest_report_date: '2001-03-31', city: 'Edinburgh', state: '', country: 'United Kingdom', postal_code: 'EH3 8RY', active: true },
  { slug: 'lone-pine-capital', display_name: 'Lone Pine Capital', legal_name: 'LONE PINE CAPITAL LLC', cik: '0001061165', strategy: 'Fundamental growth', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2004-12-31', city: 'Greenwich', state: 'CT', country: 'United States', postal_code: '06830', active: true },
  { slug: 'soros-fund-management', display_name: 'Soros Fund Management', legal_name: 'SOROS FUND MANAGEMENT LLC', cik: '0001029160', strategy: 'Global macro and event-driven', manager_type: 'Family office', quality_weight: 1.05, earliest_report_date: '2001-03-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10019', active: true },
  { slug: 'praetorian-pr', display_name: 'Praetorian PR', legal_name: 'PRAETORIAN PR LLC', cik: '0001949877', strategy: 'Contrarian macro equities', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2023-03-31', city: 'Rincon', state: '', country: 'Puerto Rico', postal_code: '00677', active: true },
  { slug: 'dalal-street', display_name: 'Dalal Street', legal_name: 'DALAL STREET, LLC', cik: '0001549575', strategy: 'Concentrated global value', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2004-12-31', city: 'West Lake Hills', state: 'TX', country: 'United States', postal_code: '78746-6496', active: true },
  { slug: 'viking-global', display_name: 'Viking Global Investors', legal_name: 'VIKING GLOBAL INVESTORS LP', cik: '0001103804', strategy: 'Fundamental growth', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2001-03-31', city: 'Stamford', state: 'CT', country: 'United States', postal_code: '06901-6000', active: true },
  { slug: 'alphabet', display_name: 'Alphabet', legal_name: 'ALPHABET INC.', cik: '0001652044', strategy: 'Corporate investment holdings', manager_type: 'Corporate filer', quality_weight: 0.75, earliest_report_date: '2013-12-31', city: 'Mountain View', state: 'CA', country: 'United States', postal_code: '94043', active: true },
  { slug: 'jpmorgan-chase', display_name: 'JPMorgan Chase & Company', legal_name: 'JPMORGAN CHASE & CO', cik: '0000019617', strategy: 'Diversified financial institution', manager_type: 'Bank', quality_weight: 0.80, earliest_report_date: '2001-03-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10017', active: true },
  { slug: 'millennium-management', display_name: 'Millennium Management', legal_name: 'MILLENNIUM MANAGEMENT LLC', cik: '0001273087', strategy: 'Multi-manager multi-strategy', manager_type: 'Investment manager', quality_weight: 0.90, earliest_report_date: '2003-12-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10022', active: true },
  { slug: 'hh-international', display_name: 'H&H International Investment', legal_name: 'H&H INTERNATIONAL INVESTMENT, LLC', cik: '0001759760', strategy: 'Concentrated global equities', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2018-12-31', city: 'Palo Alto', state: 'CA', country: 'United States', postal_code: '94303', active: true },
  { slug: 'third-point', display_name: 'Third Point', legal_name: 'THIRD POINT LLC', cik: '0001040273', strategy: 'Event-driven and activist', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2001-03-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10001', active: true },
  { slug: 'surgocap-partners', display_name: 'Surgocap Partners', legal_name: 'SURGOCAP PARTNERS LP', cik: '0001960830', strategy: 'Healthcare and technology growth', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2023-12-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10011', active: true },
  { slug: 'thiel-macro', display_name: 'Thiel Macro', legal_name: 'THIEL MACRO LLC', cik: '0001562087', strategy: 'Macro and technology', manager_type: 'Family office', quality_weight: 1.00, earliest_report_date: '2014-12-31', city: 'Los Angeles', state: 'CA', country: 'United States', postal_code: '90067', active: true },
  { slug: 'ra-capital', display_name: 'RA Capital Management', legal_name: 'RA CAPITAL MANAGEMENT, L.P.', cik: '0001346824', strategy: 'Healthcare and life sciences', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2007-12-31', city: 'Boston', state: 'MA', country: 'United States', postal_code: '02116', active: true },
  { slug: 'fundsmith', display_name: 'Fundsmith', legal_name: 'FUNDSMITH LLP', cik: '0001569205', strategy: 'High-quality global compounders', manager_type: 'Asset manager', quality_weight: 1.10, earliest_report_date: '2012-12-31', city: 'London', state: '', country: 'United Kingdom', postal_code: 'W1G 0PW', active: true },
  { slug: 'jane-street', display_name: 'Jane Street Group', legal_name: 'JANE STREET GROUP, LLC', cik: '0001595888', strategy: 'Quantitative market making', manager_type: 'Trading firm', quality_weight: 0.80, earliest_report_date: '2014-03-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10281', active: true },
  { slug: 'gates-foundation-trust', display_name: 'Gates Foundation Trust', legal_name: 'BILL & MELINDA GATES FOUNDATION TRUST', cik: '0001166559', strategy: 'Long-term concentrated endowment', manager_type: 'Foundation trust', quality_weight: 1.05, earliest_report_date: '2002-09-30', city: 'Kirkland', state: 'WA', country: 'United States', postal_code: '98033', active: true },
  { slug: 'goldman-sachs-group', display_name: 'Goldman Sachs Group', legal_name: 'GOLDMAN SACHS GROUP INC', cik: '0000886982', strategy: 'Diversified financial institution', manager_type: 'Bank', quality_weight: 0.80, earliest_report_date: '2001-03-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10282', active: true },
  { slug: 'durable-capital', display_name: 'Durable Capital Partners', legal_name: 'DURABLE CAPITAL PARTNERS LP', cik: '0001798849', strategy: 'Long-duration growth', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2019-12-31', city: 'Bethesda', state: 'MD', country: 'United States', postal_code: '20814', active: true },
  { slug: 'value-aligned-research', display_name: 'Value Aligned Research Advisors', legal_name: 'VALUE ALIGNED RESEARCH ADVISORS, LLC', cik: '0001963565', strategy: 'Concentrated value', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2022-12-31', city: 'Princeton', state: 'NJ', country: 'United States', postal_code: '08542', active: true },
  { slug: 'akre-capital', display_name: 'Akre Capital Management', legal_name: 'AKRE CAPITAL MANAGEMENT LLC', cik: '0001112520', strategy: 'Compounding and quality growth', manager_type: 'Investment manager', quality_weight: 1.10, earliest_report_date: '2001-03-31', city: 'Middleburg', state: 'VA', country: 'United States', postal_code: '20117', active: true },
  { slug: 'valley-forge-capital', display_name: 'Valley Forge Capital Management', legal_name: 'VALLEY FORGE CAPITAL MANAGEMENT, LP', cik: '0001697868', strategy: 'Concentrated quality growth', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2016-12-31', city: 'Miami', state: 'FL', country: 'United States', postal_code: '33131', active: true },
  { slug: 'fidelity-investments-money-management', display_name: 'Fidelity Investments Money Management', legal_name: 'FMR LLC', cik: '0000315066', strategy: 'Diversified active asset management', manager_type: 'Asset manager', quality_weight: 0.85, earliest_report_date: '2001-03-31', city: 'Boston', state: 'MA', country: 'United States', postal_code: '02210', active: true },
  { slug: 'maverick-capital', display_name: 'Maverick Capital', legal_name: 'MAVERICK CAPITAL LTD', cik: '0000934639', strategy: 'Fundamental long-short equities', manager_type: 'Investment manager', quality_weight: 1.00, earliest_report_date: '2001-03-31', city: 'Dallas', state: 'TX', country: 'United States', postal_code: '75201', active: true },
  { slug: 'norges-bank', display_name: 'Norges Bank', legal_name: 'NORGES BANK', cik: '0001374170', strategy: 'Sovereign diversified allocation', manager_type: 'Sovereign fund', quality_weight: 0.85, earliest_report_date: '2001-03-31', city: 'Oslo', state: '', country: 'Norway', postal_code: '0107', active: true },
  { slug: 'perceptive-advisors', display_name: 'Perceptive Advisors', legal_name: 'PERCEPTIVE ADVISORS LLC', cik: '0001224962', strategy: 'Healthcare and biotechnology', manager_type: 'Investment manager', quality_weight: 1.05, earliest_report_date: '2001-12-31', city: 'New York', state: 'NY', country: 'United States', postal_code: '10003', active: true },
  { slug: 'aqr-capital', display_name: 'AQR Capital Management', legal_name: 'AQR CAPITAL MANAGEMENT LLC', cik: '0001167557', strategy: 'Systematic factor investing', manager_type: 'Investment manager', quality_weight: 0.90, earliest_report_date: '2001-12-31', city: 'Greenwich', state: 'CT', country: 'United States', postal_code: '06830', active: true },
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

function parseInformationTable(xml, valueScale = 1) {
  const blocks = [...String(xml).matchAll(/<(?:\w+:)?infoTable(?:\s[^>]*)?>([\s\S]*?)<\/(?:\w+:)?infoTable>/gi)];
  return blocks.map((match) => {
    const block = match[1];
    return {
      cusip: xmlValue(block, 'cusip').toUpperCase(),
      issuer_name: xmlValue(block, 'nameOfIssuer'),
      title_of_class: xmlValue(block, 'titleOfClass'),
      value_usd: n(xmlValue(block, 'value')) * valueScale,
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
  return [row.cusip, row.title_of_class || '', row.share_type || 'SH', row.put_call || '']
    .map((value) => String(value).trim().toUpperCase())
    .join('|');
}

function collapseDuplicateRows(rows) {
  const combined = new Map();
  for (const row of rows) {
    const key = filingKey(row);
    const current = combined.get(key);
    if (!current) {
      combined.set(key, {
        ...row,
        value_usd: n(row.value_usd),
        shares: n(row.shares),
        voting_sole: n(row.voting_sole),
        voting_shared: n(row.voting_shared),
        voting_none: n(row.voting_none),
      });
      continue;
    }
    const managerIds = [...new Set([
      ...String(current.other_manager || '').split(','),
      ...String(row.other_manager || '').split(','),
    ].map((value) => value.trim()).filter(Boolean))].sort((a, b) => Number(a) - Number(b));
    combined.set(key, {
      ...current,
      value_usd: n(current.value_usd) + n(row.value_usd),
      shares: n(current.shares) + n(row.shares),
      voting_sole: n(current.voting_sole) + n(row.voting_sole),
      voting_shared: n(current.voting_shared) + n(row.voting_shared),
      voting_none: n(current.voting_none) + n(row.voting_none),
      other_manager: managerIds.join(',') || null,
      investment_discretion: current.investment_discretion === row.investment_discretion
        ? current.investment_discretion
        : 'MULTIPLE',
    });
  }
  return [...combined.values()];
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
    ignoreDuplicates: false,
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

function consensusEligibleLatest(latest) {
  const newestReport = [...latest.values()].map((row) => row.report_date).sort().reverse()[0];
  if (!newestReport) return new Map();
  const cutoff = new Date(`${newestReport}T00:00:00Z`);
  cutoff.setUTCDate(cutoff.getUTCDate() - 200);
  const cutoffDate = cutoff.toISOString().slice(0, 10);
  return new Map([...latest.entries()].filter(([, filing]) => filing.report_date >= cutoffDate));
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
    const activityByManager = new Map();
    for (const row of related) {
      if (!activityByManager.has(row.manager_id)) activityByManager.set(row.manager_id, []);
      activityByManager.get(row.manager_id).push(row);
    }
    const activity = { new: 0, increased: 0, reduced: 0, exited: 0 };
    for (const [managerId, rows] of activityByManager) {
      const netShares = rows.reduce((sum, row) => sum + n(row.share_change), 0);
      const types = new Set(rows.map((row) => row.change_type));
      let type;
      if (!item.owners.has(managerId) && types.has('exited')) type = 'exited';
      else if (types.has('new') && !types.has('reduced') && !types.has('exited')) type = 'new';
      else if (netShares > 0) type = 'increased';
      else if (netShares < 0) type = 'reduced';
      else if (types.has('increased')) type = 'increased';
      else if (types.has('reduced')) type = 'reduced';
      if (type) activity[type] += 1;
    }
    const owners = item.owners.size;
    const breadth = managerCount ? owners / managerCount : 0;
    const consensusReady = managerCount >= CONSENSUS_MIN_MANAGERS;
    const consensusScore = consensusReady ? clamp(breadth * 80 + Math.min(item.aggregate_weight / Math.max(owners, 1), 10) * 2) : null;
    return {
      ...item,
      owners,
      owner_ids: [...item.owners],
      aggregate_weight: Math.round(item.aggregate_weight * 100) / 100,
      consensus_score: consensusScore,
      score_status: consensusReady ? 'available' : 'withheld',
      new_buyers: activity.new,
      increasers: activity.increased,
      reducers: activity.reduced,
      exits: activity.exited,
    };
  }).sort((a, b) => n(b.consensus_score) - n(a.consensus_score) || b.aggregate_weight - a.aggregate_weight);
}

export async function getInstitutionalOverview() {
  const client = db();
  const managerRows = await managers(client);
  const { data: filingRows, error: filingError } = await client.from('institutional_filings').select('*').eq('is_active', true).order('report_date', { ascending: false });
  if (filingError) throw filingError;
  const latest = latestByManager(filingRows || []);
  const consensusLatest = consensusEligibleLatest(latest);
  const filingIds = [...latest.values()].map((row) => row.id);
  const holdings = filingIds.length ? await collect(() => client.from('institutional_holdings').select('*').in('filing_id', filingIds)) : [];
  const changes = filingIds.length ? await collect(() => client.from('holding_changes').select('*').in('filing_id', filingIds)) : [];
  const consensusFilingIds = new Set([...consensusLatest.values()].map((row) => row.id));
  const consensus = aggregateConsensus(
    holdings.filter((row) => consensusFilingIds.has(row.filing_id)),
    changes.filter((row) => consensusFilingIds.has(row.filing_id)),
    consensusLatest.size,
  );
  const fundCards = managerRows.map((manager) => {
    const filing = latest.get(manager.id) || null;
    const owned = filing ? holdings.filter((row) => row.filing_id === filing.id && !row.put_call) : [];
    const filingHistory = (filingRows || [])
      .filter((row) => row.manager_id === manager.id)
      .sort((a, b) => String(a.report_date || '').localeCompare(String(b.report_date || '')))
      .slice(-12)
      .map((row) => ({
        report_date: row.report_date,
        filed_at: row.filed_at,
        total_value_usd: row.total_value_usd,
        holdings_count: row.holdings_count,
      }));
  return {
      ...manager,
      latest_filing: filing,
      filing_history: filingHistory,
      position_count: owned.length,
      top_positions: owned.sort((a, b) => n(b.portfolio_weight) - n(a.portfolio_weight)).slice(0, 3),
      new_positions: filing ? changes.filter((row) => row.filing_id === filing.id && row.change_type === 'new').length : 0,
      exits: filing ? changes.filter((row) => row.filing_id === filing.id && row.change_type === 'exited').length : 0,
    };
  });
  const { data: alerts } = await client.from('institutional_filing_alerts').select('*, institutional_managers(display_name, slug)').order('created_at', { ascending: false }).limit(12);
  // Consensus aggregates across every manager and quarter, so it is precisely
  // the figure that cannot be trusted while some history is repaired and some
  // is not. The surface reports the gate; it does not decide for itself.
  const dataIntegrity = await getRepairStatus();
  return {
    generated_at: new Date().toISOString(),
    data_integrity: dataIntegrity,
    reporting_basis: 'SEC Form 13F, available only after the SEC acceptance timestamp',
    managers: fundCards,
    consensus: consensus.slice(0, 30),
    alerts: alerts || [],
    covered_managers: managerRows.length,
    managers_with_filings: latest.size,
    consensus_managers: consensusLatest.size,
    consensus_ready: consensusLatest.size >= CONSENSUS_MIN_MANAGERS,
    consensus_min_managers: CONSENSUS_MIN_MANAGERS,
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
  const latestIngestedAt = latest?.ingested_at ? new Date(latest.ingested_at).getTime() : 0;
  const freshSignals = (signals || []).filter((row) => {
    const calculatedAt = row?.calculated_at ? new Date(row.calculated_at).getTime() : 0;
    return calculatedAt >= latestIngestedAt;
  });
  return { manager, filings: filings || [], latest_filing: latest, holdings, changes, signals: freshSignals };
}

export async function getInstitutionalStock(rawKey) {
  const client = db();
  const key = decodeURIComponent(String(rawKey || '')).trim().toUpperCase();
  if (!key) return null;
  const managerRows = await managers(client);
  const { data: filingRows, error: filingError } = await client.from('institutional_filings').select('*').eq('is_active', true).order('report_date', { ascending: false });
  if (filingError) throw filingError;
  const latest = latestByManager(filingRows || []);
  const consensusLatest = consensusEligibleLatest(latest);
  const ids = [...consensusLatest.values()].map((row) => row.id);
  if (!ids.length) return { key, owners: [], history: [], manager_count: managerRows.length };
  const holdings = await collect(() => client.from('institutional_holdings').select('*').in('filing_id', ids).or(`ticker.eq.${key},cusip.eq.${key}`));
  const identity = holdings[0] || null;
  if (!identity) return null;
  const allHistory = await collect(() => client.from('institutional_holdings').select('*, institutional_managers(display_name, slug)').or(`ticker.eq.${identity.ticker || key},cusip.eq.${identity.cusip}`).order('report_date', { ascending: false }));
  const managerMap = new Map(managerRows.map((row) => [row.id, row]));
  const owners = holdings.filter((row) => !row.put_call).map((row) => ({ ...row, manager: managerMap.get(row.manager_id), filing: latest.get(row.manager_id) }));
  const { data: changes } = await client.from('holding_changes').select('*').in('filing_id', ids).eq('cusip', identity.cusip);
  const consensusReady = consensusLatest.size >= CONSENSUS_MIN_MANAGERS;
  const consensusScore = consensusReady ? clamp((owners.length / Math.max(consensusLatest.size, 1)) * 80 + Math.min(owners.reduce((sum, row) => sum + n(row.portfolio_weight), 0) / Math.max(owners.length, 1), 10) * 2) : null;
  return {
    key: identity.ticker || identity.cusip,
    ticker: identity.ticker,
    cusip: identity.cusip,
    issuer_name: identity.issuer_name,
    manager_count: consensusLatest.size,
    tracked_manager_count: managerRows.length,
    covered_manager_count: latest.size,
    owner_count: owners.length,
    aggregate_weight: owners.reduce((sum, row) => sum + n(row.portfolio_weight), 0),
    aggregate_value_usd: owners.reduce((sum, row) => sum + n(row.value_usd), 0),
    consensus_score: consensusScore,
    consensus_ready: consensusReady,
    consensus_min_managers: CONSENSUS_MIN_MANAGERS,
    owners: owners.sort((a, b) => n(b.portfolio_weight) - n(a.portfolio_weight)),
    changes: changes || [],
    history: allHistory,
  };
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Retry was already here; pacing was not. Every attempt now queues through the
// process-wide limiter, and a throttle is reported to it rather than absorbed
// locally - EDGAR's limit is per source, so one caller's 429 is every caller's
// problem and must slow all of them down.
async function secFetch(url, asJson = false) {
  let lastError;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      const response = await scheduleSecRequest(() => fetch(url, {
        headers: { Accept: asJson ? 'application/json' : 'application/xml,text/xml,text/plain,*/*', 'User-Agent': SEC_USER_AGENT },
        signal: AbortSignal.timeout(30_000),
      }));
      if (response.ok) {
        recordSuccess();
        return asJson ? response.json() : response.text();
      }
      lastError = new Error(`SEC request failed (${response.status}) for ${url}`);
      // 403 is how EDGAR answers a source it has decided to block, so it counts
      // as pushback exactly like 429 does.
      if (response.status === 429 || response.status === 403) {
        recordThrottled(parseRetryAfter(response.headers.get('retry-after')));
      } else if (response.status < 500) {
        throw lastError;
      }
    } catch (error) {
      // An open circuit is a decision, not a transient failure. Retrying
      // against it is the behaviour the circuit exists to prevent.
      if (error instanceof SecCircuitOpenError) throw error;
      lastError = error;
      if (attempt === 3) break;
    }
    await wait(500 * (2 ** attempt));
  }
  throw lastError || new Error(`SEC request failed for ${url}`);
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
  const names = (index?.directory?.item || [])
    .map((item) => item.name)
    .filter((name) => /\.(xml|txt)$/i.test(name))
    .sort((a, b) => {
      const rank = (name) => /info.*table|form13f.*info/i.test(name) ? 0 : /primary/i.test(name) ? 2 : 1;
      return rank(a) - rank(b);
    });
  const documents = [];
  for (const name of names.slice(0, 12)) {
    const text = await secFetch(`${base}/${name}`);
    documents.push({ name, text });
    if (documents.some((doc) => /<(?:\w+:)?infoTable[\s>]/i.test(doc.text))) break;
  }

  // The cover page, fetched separately and on purpose.
  //
  // The loop above ranks the information table first and stops the moment it
  // has one, so on a filing laid out as [infotable.xml, submission.txt,
  // primary_doc.xml] it downloads exactly one file. That is correct for
  // holdings and wrong for everything else: the cover page is the only place
  // SEC states whether a 13F-HR/A restates the earlier report or adds to it,
  // and it was never being read. Verified against Elliott 0000902664-25-003078
  // and Baupost 0001567619-18-006456, both real restatements, both of which
  // downloaded only the info table.
  //
  // One extra request per filing, and only when the cover page was not already
  // picked up in the documents above.
  let coverPage = documents.find((doc) => /primary_doc\.xml$/i.test(doc.name))?.text || null;
  if (!coverPage && names.some((name) => /primary_doc\.xml$/i.test(name))) {
    try {
      coverPage = await secFetch(`${base}/primary_doc.xml`);
    } catch (error) {
      // Not fatal. An amendment without a readable cover page is escalated for
      // review rather than guessed at, which is handled by the caller.
      console.warn(`[institutional-holdings] cover page unavailable for ${accession}: ${error.message}`);
    }
  }
  // Older filings predate the XML cover page entirely; the full submission text
  // is the only place the metadata can be.
  if (!coverPage) {
    coverPage = documents.find((doc) => /<(?:\w+:)?amendmentType>/i.test(doc.text))?.text || null;
  }

  return { base, documents, coverPage };
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

function preferredFigiCandidate(result) {
  const candidates = (result?.data || []).filter((row) => row?.ticker && row?.marketSector === 'Equity');
  return candidates.sort((a, b) => {
    const score = (row) => (row.exchCode === 'US' ? 20 : 0)
      + (/Common Stock|Depositary Receipt|REIT|ETP/i.test(row.securityType2 || '') ? 10 : 0)
      + (row.compositeFIGI ? 2 : 0);
    return score(b) - score(a);
  })[0] || null;
}

async function openFigiBatch(cusips) {
  const headers = { Accept: 'application/json', 'Content-Type': 'application/json' };
  if (OPENFIGI_API_KEY) headers['X-OPENFIGI-APIKEY'] = OPENFIGI_API_KEY;
  let lastError;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      const response = await fetch(OPENFIGI_URL, {
        method: 'POST',
        headers,
        body: JSON.stringify(cusips.map((cusip) => ({ idType: 'ID_CUSIP', idValue: cusip }))),
        signal: AbortSignal.timeout(30_000),
      });
      if (response.ok) return response.json();
      lastError = new Error(`OpenFIGI mapping failed (${response.status})`);
      if (response.status !== 429 && response.status < 500) throw lastError;
      const resetSeconds = Math.max(1, n(response.headers.get('ratelimit-reset')));
      await wait(resetSeconds * 1000);
    } catch (error) {
      lastError = error;
      if (attempt < 3) await wait(750 * (2 ** attempt));
    }
  }
  throw lastError || new Error('OpenFIGI mapping failed.');
}

async function enrichSecurityIdentifiers(client, limit = 1000) {
  const unresolved = await collect(() => client.from('institutional_holdings').select('cusip,issuer_name,value_usd').is('ticker', null).order('value_usd', { ascending: false }));
  const unique = [];
  const seen = new Set();
  for (const row of unresolved) {
    if (!seen.has(row.cusip)) {
      seen.add(row.cusip);
      unique.push(row);
    }
    if (unique.length >= limit) break;
  }
  const batchSize = OPENFIGI_API_KEY ? 100 : 5;
  const mappings = [];
  const errors = [];
  for (let index = 0; index < unique.length; index += batchSize) {
    const batch = unique.slice(index, index + batchSize);
    try {
      const results = await openFigiBatch(batch.map((row) => row.cusip));
      results.forEach((result, resultIndex) => {
        const source = batch[resultIndex];
        const match = preferredFigiCandidate(result);
        if (source && match) mappings.push({
          cusip: source.cusip,
          ticker: String(match.ticker).trim().toUpperCase(),
          issuer_name: source.issuer_name,
          valid_from: '1900-01-01',
          source: 'openfigi',
          manually_verified: false,
          updated_at: new Date().toISOString(),
        });
      });
    } catch (error) {
      errors.push(error.message);
    }
    if (!OPENFIGI_API_KEY && index + batchSize < unique.length) await wait(2500);
  }
  if (mappings.length) {
    const { error } = await client.from('security_identifier_history').upsert(mappings, { onConflict: 'cusip,valid_from' });
    if (error) throw error;
  }
  return { attempted: unique.length, mapped: mappings.length, unresolved: Math.max(0, unique.length - mappings.length), errors: [...new Set(errors)] };
}

async function mapWithConcurrency(items, concurrency, worker) {
  const output = new Array(items.length);
  let cursor = 0;
  async function run() {
    while (cursor < items.length) {
      const index = cursor;
      cursor += 1;
      output[index] = await worker(items[index], index);
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, items.length) }, run));
  return output;
}

function buildChanges(current, previous, filing) {
  const now = new Map(collapseDuplicateRows(current).filter((row) => !row.put_call).map((row) => [filingKey(row), row]));
  const before = new Map(collapseDuplicateRows(previous).filter((row) => !row.put_call).map((row) => [filingKey(row), row]));
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
  const archive = await filingDocuments(manager.cik, source.accession_number);
  const infoDocument = archive.documents.find((doc) => /<(?:\w+:)?infoTable[\s>]/i.test(doc.text));
  if (!infoDocument) throw new Error(`No 13F information table found in ${source.accession_number}`);
  let rawRows = collapseDuplicateRows(parseInformationTable(infoDocument.text, 1));
  if (!rawRows.length) throw new Error(`The SEC information table was empty for ${source.accession_number}`);
  const ratios = rawRows.filter((row) => row.shares > 0 && row.value_usd > 0 && !row.put_call).map((row) => row.value_usd / row.shares).sort((a, b) => a - b);
  const medianRatio = ratios.length ? ratios[Math.floor(ratios.length / 2)] : null;
  const legacyScaleDetected = ratios.length >= 5 && medianRatio < 1 && ratios.filter((ratio) => ratio < 1).length / ratios.length >= 0.6;
  const valueScale = n(manager.value_scale_override) || (String(source.accepted_at || source.filing_date) < POST_2022_VALUE_RULE_DATE || legacyScaleDetected ? 1000 : 1);
  if (valueScale !== 1) rawRows = rawRows.map((row) => ({ ...row, value_usd: n(row.value_usd) * valueScale }));
  // Amendment handling.
  //
  // What was here tested for a tag SEC does not emit, against documents that
  // did not include the cover page, so every 13F-HR/A ever ingested was
  // classified additional_holdings and merged. A restatement that removed a
  // position therefore left it standing as a phantom holding. See
  // secAmendment.js for the filings this was verified against.
  const classification = classifyFiling(source.form_type, archive.coverPage);
  const amendmentType = classification.amendmentType;
  const { data: previousVersion } = await client.from('institutional_filings').select('*').eq('manager_id', manager.id).eq('report_date', source.report_date).eq('is_active', true).order('filed_at', { ascending: false }).limit(1).maybeSingle();

  const priorVersionRows = previousVersion
    ? await collect(() => client.from('institutional_holdings').select('*').eq('filing_id', previousVersion.id))
    : [];
  const strippedPriorRows = priorVersionRows.map(
    ({ id, filing_id, manager_id, report_date, portfolio_weight, created_at, ...row }) => row,
  );

  // An amendment with no prior version to amend is just a filing.
  const strategy = amendmentType === 'original' || !previousVersion ? 'replace' : classification.strategy;
  const outcome = applyAmendment({
    strategy,
    priorRows: strippedPriorRows,
    amendmentRows: rawRows,
    keyOf: filingKey,
  });
  const removed = strategy === 'replace' && previousVersion
    ? droppedPositions({ priorRows: strippedPriorRows, amendmentRows: rawRows, keyOf: filingKey })
    : [];
  if (removed.length) {
    console.info(`[institutional-holdings] ${source.accession_number} restates ${manager.slug || manager.display_name}: ${removed.length} position(s) removed`);
  }

  // An amendment we could not classify must not silently rewrite the report.
  // The filing is recorded so it is visible, the earlier version stays
  // authoritative, and an operator decides.
  if (strategy === 'review') {
    console.warn(`[institutional-holdings] ${source.accession_number} needs review: ${classification.reviewReason}`);
    await client.from('institutional_filings').upsert({
      manager_id: manager.id,
      accession_number: source.accession_number,
      form_type: source.form_type,
      report_date: source.report_date,
      filed_at: source.accepted_at,
      primary_document: source.primary_document,
      amendment_type: 'unknown',
      is_amendment: true,
      is_active: false,
      needs_review: true,
      review_reason: classification.reviewReason,
      source_url: `${archive.base}/${source.primary_document || infoDocument.name}`,
      holdings_count: rawRows.length,
      ingested_at: new Date().toISOString(),
    }, { onConflict: 'accession_number' });
    return {
      accession_number: source.accession_number,
      status: 'needs_review',
      holdings: 0,
      report_date: source.report_date,
      changes: 0,
      review_reason: classification.reviewReason,
    };
  }

  let rows = strategy === 'merge' ? collapseDuplicateRows(outcome.rows) : outcome.rows;
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

function pastedAccession(value = '') {
  const dashed = String(value).match(/\b\d{10}-\d{2}-\d{6}\b/);
  if (dashed) return dashed[0];
  const compact = String(value).match(/\b\d{18}\b/);
  return compact ? `${compact[0].slice(0, 10)}-${compact[0].slice(10, 12)}-${compact[0].slice(12)}` : null;
}

function stableImportId(value = '') {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) hash = Math.imul(hash ^ value.charCodeAt(index), 16777619);
  return (hash >>> 0).toString(16).padStart(8, '0');
}

function xmlImportValue(xml, names) {
  for (const name of names) {
    const match = String(xml).match(new RegExp(`<(?:\\w+:)?${name}[^>]*>([\\s\\S]*?)<\\/(?:\\w+:)?${name}>`, 'i'));
    if (match) return match[1].replace(/<[^>]+>/g, '').trim();
  }
  return '';
}

function pastedNumber(value) {
  const cleaned = String(value ?? '').replace(/[,$₹%\s]/g, '');
  return /^-?\d+(?:\.\d+)?$/.test(cleaned) ? Number(cleaned) : null;
}

function parsePasted13fTable(text, valueScale) {
  const rows = [];
  for (const rawLine of String(text).split(/\r?\n/)) {
    let cells = rawLine.includes('\t') ? rawLine.split(/\t+/) : rawLine.trim().split(/\s{2,}/);
    cells = cells.map((cell) => cell.trim()).filter(Boolean);
    const cusipIndex = cells.findIndex((cell) => /^[0-9A-Z*@#]{8,9}$/i.test(cell.replace(/\s/g, '')));
    if (cusipIndex < 1) continue;
    const tail = cells.slice(cusipIndex + 1);
    const numeric = tail.map((cell, index) => ({ index, value: pastedNumber(cell) })).filter((item) => item.value !== null);
    if (numeric.length < 2) continue;
    const metadata = tail.slice(numeric[1].index + 1);
    const voting = numeric.slice(-3).map((item) => item.value);
    const putCall = metadata.find((cell) => /^(PUT|CALL)$/i.test(cell));
    rows.push({
      issuer_name: cells[0],
      title_of_class: cells.slice(1, cusipIndex).join(' ') || 'COM',
      cusip: cells[cusipIndex].replace(/\s/g, '').toUpperCase(),
      value_usd: Math.round(numeric[0].value * valueScale),
      shares_or_principal: numeric[1].value,
      share_type: (metadata.find((cell) => /^(SH|PRN)$/i.test(cell)) || 'SH').toUpperCase(),
      put_call: putCall ? putCall.toUpperCase() : null,
      investment_discretion: (metadata.find((cell) => /^(SOLE|SHARED|DEFINED)$/i.test(cell)) || 'SOLE').toUpperCase(),
      other_manager: null,
      voting_authority_sole: voting.length === 3 ? voting[0] : 0,
      voting_authority_shared: voting.length === 3 ? voting[1] : 0,
      voting_authority_none: voting.length === 3 ? voting[2] : 0,
    });
  }
  return collapseDuplicateRows(rows);
}

function submissionImportRows(submissions) {
  const recent = submissions?.filings?.recent || {};
  return (recent.accessionNumber || []).map((accession, index) => ({
    accession_number: accession,
    form_type: recent.form?.[index] || '',
    report_date: recent.reportDate?.[index] || '',
    filed_at: recent.filingDate?.[index] || '',
    accepted_at: recent.acceptanceDateTime?.[index] || recent.filingDate?.[index] || '',
    primary_document: recent.primaryDocument?.[index] || '',
  })).filter((row) => /^13F-(HR|NT)(\/A)?$/.test(row.form_type));
}

async function secImportRows(manager, source) {
  const archive = await filingDocuments(manager.cik, source.accession_number);
  const names = archive.documents.map((document) => document.name)
    .filter((name) => /\.xml$/i.test(name) && name !== source.primary_document)
    .sort((left, right) => Number(/infotable|informationtable/i.test(right)) - Number(/infotable|informationtable/i.test(left)));
  for (const name of names) {
    const response = await scheduleSecRequest(() => fetch(`${archive.base}/${name}`, { headers: { 'User-Agent': SEC_USER_AGENT } }));
    if (!response.ok) continue;
    const scale = source.report_date < POST_2022_VALUE_RULE_DATE ? 1000 : 1;
    const rows = collapseDuplicateRows(parseInformationTable(await response.text(), scale));
    if (rows.length) return { rows, primary_document: name, source_url: `${archive.base}/${name}` };
  }
  throw new Error('This filing has no readable 13F information table. It may be a notice filing.');
}

async function previousImportPortfolio(client, manager, reportDate, submissions) {
  const { data: filing } = await client.from('institutional_filings').select('*').eq('manager_id', manager.id)
    .eq('is_active', true).lt('report_date', reportDate).order('report_date', { ascending: false }).limit(1).maybeSingle();
  if (filing) {
    const { data: rows, error } = await client.from('institutional_holdings').select('*').eq('filing_id', filing.id);
    if (error) throw error;
    return { filing, rows: rows || [], source: null };
  }
  const source = submissionImportRows(submissions).filter((row) => /^13F-HR/.test(row.form_type) && row.report_date < reportDate)
    .sort((left, right) => right.report_date.localeCompare(left.report_date))[0];
  if (!source) return { filing: null, rows: [], source: null };
  const parsed = await secImportRows(manager, source);
  return { filing: source, rows: parsed.rows, source: { ...source, ...parsed } };
}

async function prepareInstitutionalImport(client, payload = {}) {
  const input = String(payload.input || '').trim();
  if (!input) throw new Error('Paste a SEC URL, accession number, XML document, or holdings table.');
  const manager = (await managers(client)).find((item) => item.id === payload.managerId || item.slug === payload.managerId);
  if (!manager) throw new Error('Choose the manager that owns this filing.');
  const submissions = await fetchJson(`${SEC_DATA}/submissions/CIK${cleanCik(manager.cik)}.json`);
  const accession = pastedAccession(input);
  const isXml = /<(?:\w+:)?informationTable\b|<(?:\w+:)?infoTable\b/i.test(input);
  let kind = 'table';
  let source;
  let rows;

  if (accession) {
    kind = 'sec';
    source = submissionImportRows(submissions).find((row) => row.accession_number === accession);
    if (!source) throw new Error('That accession does not belong to the selected manager in SEC EDGAR.');
    if (/^13F-NT/.test(source.form_type)) return { manager, kind, source, rows: [], previous: { rows: [] }, noticeOnly: true };
    const parsed = await secImportRows(manager, source);
    source = { ...source, ...parsed };
    rows = parsed.rows;
  } else {
    const reportDate = isXml ? (xmlImportValue(input, ['periodOfReport', 'reportCalendarOrQuarter']) || payload.reportDate) : payload.reportDate;
    if (!/^\d{4}-\d{2}-\d{2}$/.test(reportDate || '')) throw new Error('Enter the filing report date before analysing this content.');
    kind = isXml ? 'xml' : 'table';
    source = {
      accession_number: `manual-${cleanCik(manager.cik)}-${reportDate}-${stableImportId(input)}`,
      form_type: payload.formType || '13F-HR',
      report_date: reportDate,
      filed_at: new Date().toISOString().slice(0, 10),
      accepted_at: new Date().toISOString(),
      primary_document: isXml ? 'cms-upload.xml' : 'cms-pasted-table',
      source_url: null,
      amendment_type: payload.amendmentType || null,
    };
    const scale = reportDate < POST_2022_VALUE_RULE_DATE ? 1000 : 1;
    rows = isXml ? collapseDuplicateRows(parseInformationTable(input, scale)) : parsePasted13fTable(input, scale);
  }
  if (!rows.length) throw new Error('No valid holdings were detected. Preserve tabs between copied columns, or paste the SEC information-table XML.');
  const mapping = await mappingsFor(client, rows.map((row) => row.cusip));
  rows = rows.map((row) => ({ ...row, ...(mapping.get(row.cusip) || {}) }));
  const totalValue = rows.reduce((sum, row) => sum + n(row.value_usd), 0);
  rows = rows.map((row) => ({ ...row, portfolio_weight: totalValue ? (n(row.value_usd) / totalValue) * 100 : 0 }));
  const previous = await previousImportPortfolio(client, manager, source.report_date, submissions);
  return { manager, kind, source, rows, totalValue, previous, noticeOnly: false };
}

function buildImportPreview(prepared) {
  const { manager, kind, source, rows, totalValue, previous, noticeOnly } = prepared;
  const managerView = { id: manager.id, slug: manager.slug, display_name: manager.display_name, cik: manager.cik };
  if (noticeOnly) return {
    manager: managerView,
    source: { ...source, kind },
    publishable: false,
    warnings: ['13F-NT is a notice filing. It has no holdings information table and cannot update portfolio intelligence.'],
  };
  const changes = buildChanges(rows, previous.rows || [], { id: null, manager_id: manager.id, report_date: source.report_date });
  const top = rows.filter((row) => !row.put_call).sort((a, b) => n(b.portfolio_weight) - n(a.portfolio_weight)).slice(0, 10);
  const concentration = top.reduce((sum, row) => sum + n(row.portfolio_weight), 0);
  const mapped = rows.filter((row) => row.ticker).length;
  const coverage = rows.length ? (mapped / rows.length) * 100 : 0;
  const counts = changes.reduce((result, row) => ({ ...result, [row.change_type]: (result[row.change_type] || 0) + 1 }), {});
  const adds = changes.filter((row) => ['new', 'increased'].includes(row.change_type)).reduce((sum, row) => sum + Math.max(0, n(row.weight_change)), 0);
  const cuts = changes.filter((row) => ['reduced', 'exited'].includes(row.change_type)).reduce((sum, row) => sum + Math.abs(Math.min(0, n(row.weight_change))), 0);
  const accumulation = clamp(Math.round(50 + (adds - cuts) * 2), 0, 100);
  const stance = accumulation >= 66 ? 'Bullish accumulation' : accumulation <= 44 ? 'Defensive reduction' : 'Balanced positioning';
  const warnings = [];
  if (!previous.rows?.length) warnings.push('No earlier portfolio was available, so change intelligence is withheld.');
  if (coverage < 100) warnings.push(`${rows.length - mapped} holding${rows.length - mapped === 1 ? '' : 's'} still require ticker mapping.`);
  if (rows.some((row) => row.put_call)) warnings.push('Options stay separate and are excluded from ordinary-equity concentration.');
  if (kind !== 'sec') warnings.push('Manual source: verify manager, period, units, and amendment treatment against EDGAR before publishing.');
  const label = (row) => row?.ticker || row?.security_name || row?.issuer_name || row?.cusip;
  const newRows = changes.filter((row) => row.change_type === 'new').sort((a, b) => n(b.current_weight) - n(a.current_weight)).slice(0, 3);
  const increased = changes.filter((row) => row.change_type === 'increased').sort((a, b) => n(b.weight_change) - n(a.weight_change)).slice(0, 3);
  const reduced = changes.filter((row) => ['reduced', 'exited'].includes(row.change_type)).sort((a, b) => n(a.weight_change) - n(b.weight_change)).slice(0, 3);
  const bullets = [];
  if (newRows.length) bullets.push(`New disclosed positions: ${newRows.map(label).join(', ')}.`);
  if (increased.length) bullets.push(`Largest disclosed increases: ${increased.map(label).join(', ')}.`);
  if (reduced.length) bullets.push(`Largest disclosed reductions or exits: ${reduced.map(label).join(', ')}.`);
  bullets.push(`Top ten ordinary-equity positions represent ${concentration.toFixed(1)}% of disclosed value.`);
  return {
    manager: managerView,
    source: { ...source, kind },
    publishable: true,
    metrics: { holdings_count: rows.length, total_value_usd: totalValue, mapping_coverage: Number(coverage.toFixed(1)), option_positions: rows.filter((row) => row.put_call).length, previous_report_date: previous.filing?.report_date || null, top10_concentration: Number(concentration.toFixed(2)) },
    scores: { conviction: clamp(Math.round(concentration), 0, 100), accumulation, exit_pressure: clamp(Math.round(cuts * 4), 0, 100), stance, confidence: previous.rows?.length && coverage >= 80 ? 'High' : coverage >= 60 ? 'Medium' : 'Low' },
    activity: { counts, top_changes: [...newRows, ...increased, ...reduced].slice(0, 8) },
    top_positions: top,
    warnings,
    brief: {
      headline: `${manager.display_name}: ${stance.toLowerCase()} in the ${source.report_date} 13F`,
      summary: `${manager.display_name} disclosed ${rows.length} reportable line items worth approximately $${(totalValue / 1e9).toFixed(2)}bn. The evidence-based accumulation score is ${accumulation}/100.`,
      bullets,
      limitations: ['13F is a delayed quarter-end snapshot, not a live portfolio.', 'It omits shorts, cash, most derivatives, and many non-US securities; value is not cost basis or performance.'],
    },
  };
}

function importedHolding(row, filing, manager) {
  return {
    filing_id: filing.id, manager_id: manager.id, report_date: filing.report_date,
    issuer_name: row.issuer_name, title_of_class: row.title_of_class, cusip: row.cusip,
    ticker: row.ticker || null, security_name: row.security_name || null, sector: row.sector || null,
    value_usd: n(row.value_usd), shares_or_principal: n(row.shares_or_principal), share_type: row.share_type || null,
    put_call: row.put_call || null, investment_discretion: row.investment_discretion || null, other_manager: row.other_manager || null,
    voting_authority_sole: n(row.voting_authority_sole), voting_authority_shared: n(row.voting_authority_shared),
    voting_authority_none: n(row.voting_authority_none), portfolio_weight: n(row.portfolio_weight),
  };
}

async function publishPreparedImport(client, prepared, actor) {
  const { manager, source } = prepared;
  let rows = prepared.rows;
  const amendmentType = source.form_type === '13F-HR/A' ? (source.amendment_type || 'restatement') : null;
  if (amendmentType === 'additional_holdings') {
    const { data: version } = await client.from('institutional_filings').select('id').eq('manager_id', manager.id).eq('report_date', source.report_date).eq('is_active', true).limit(1).maybeSingle();
    if (version) {
      const { data: existing } = await client.from('institutional_holdings').select('*').eq('filing_id', version.id);
      rows = collapseDuplicateRows([...(existing || []), ...rows]);
      const total = rows.reduce((sum, row) => sum + n(row.value_usd), 0);
      rows = rows.map((row) => ({ ...row, portfolio_weight: total ? (n(row.value_usd) / total) * 100 : 0 }));
    }
  }
  const filingPayload = {
    manager_id: manager.id, accession_number: source.accession_number, form_type: source.form_type,
    report_date: source.report_date, filed_at: source.filed_at, accepted_at: source.accepted_at,
    primary_document: source.primary_document, source_url: source.source_url,
    total_value_usd: rows.reduce((sum, row) => sum + n(row.value_usd), 0), holdings_count: rows.length,
    is_amendment: source.form_type === '13F-HR/A', amendment_type: amendmentType, is_active: true,
    raw_metadata: { imported_via: 'institutional_cms', approved_by: actor, source_kind: prepared.kind },
  };
  const { data: filing, error } = await client.from('institutional_filings').upsert(filingPayload, { onConflict: 'accession_number' }).select('*').single();
  if (error) throw error;
  await client.from('institutional_filings').update({ is_active: false }).eq('manager_id', manager.id).eq('report_date', source.report_date).neq('id', filing.id);
  await client.from('institutional_holdings').delete().eq('filing_id', filing.id);
  await insertChunks(client, 'institutional_holdings', rows.map((row) => importedHolding(row, filing, manager)));
  const previous = await previousImportPortfolio(client, manager, source.report_date, { filings: { recent: {} } });
  await client.from('institutional_holding_changes').delete().eq('filing_id', filing.id);
  const changes = buildChanges(rows, previous.rows || [], filing);
  await insertChunks(client, 'institutional_holding_changes', changes);
  await createAlerts(client, manager, filing, changes);
  return { filing, changes: changes.length };
}

export async function previewInstitutionalImport(payload) {
  const prepared = await prepareInstitutionalImport(db(), payload);
  prepared.source.amendment_type = payload.amendmentType || prepared.source.amendment_type || null;
  return buildImportPreview(prepared);
}

export async function publishInstitutionalImport(payload) {
  const client = db();
  const prepared = await prepareInstitutionalImport(client, payload);
  prepared.source.amendment_type = payload.amendmentType || prepared.source.amendment_type || null;
  const preview = buildImportPreview(prepared);
  if (!preview.publishable) throw new Error('This filing has no publishable holdings table.');
  if (prepared.previous.source) await ingestFiling(client, prepared.manager, prepared.previous.source);
  const ingestion = prepared.kind === 'sec' ? await ingestFiling(client, prepared.manager, prepared.source) : await publishPreparedImport(client, prepared, payload.actor || 'admin');
  const enrichment = await enrichSecurityIdentifiers(client);
  const signals = await rebuildSignals(client);
  await client.from('institutional_managers').update({ last_refresh_at: new Date().toISOString(), last_refresh_status: 'success', last_refresh_error: null }).eq('id', prepared.manager.id);
  return { ok: true, manager: preview.manager, filing: preview.source, ingestion, enrichment, signals, intelligence: preview.brief };
}

async function rebuildSignals(client) {
  const managerRows = await managers(client);
  const { data: filings, error } = await client.from('institutional_filings').select('*').eq('is_active', true).order('report_date', { ascending: false });
  if (error) throw error;
  const latest = latestByManager(filings || []);
  const consensusLatest = consensusEligibleLatest(latest);
  const ids = [...latest.values()].map((row) => row.id);
  if (!ids.length) return { funds: 0, stocks: 0 };
  const holdings = await collect(() => client.from('institutional_holdings').select('*').in('filing_id', ids));
  const changes = await collect(() => client.from('holding_changes').select('*').in('filing_id', ids));
  const consensusReady = consensusLatest.size >= CONSENSUS_MIN_MANAGERS;
  const consensusFilingIds = new Set([...consensusLatest.values()].map((row) => row.id));
  const consensus = aggregateConsensus(
    holdings.filter((row) => consensusFilingIds.has(row.filing_id)),
    changes.filter((row) => consensusFilingIds.has(row.filing_id)),
    consensusLatest.size,
  );
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
      consensusReady && consensusLatest.has(manager.id) ? signal('consensus', (avgBreadth / Math.max(consensusLatest.size, 1)) * 100, { average_top10_owner_count: avgBreadth, consensus_managers: consensusLatest.size, tracked_managers: managerRows.length }, 'Average ownership breadth across current fund top ten positions.') : null,
    ].filter(Boolean);
    signalRows.push(...scores.map((row) => ({ ...row, scope_type: 'fund', scope_id: manager.id, as_of: filing.report_date })));
  }
  for (const row of consensus.filter(() => consensusReady)) {
    signalRows.push({
      ...signal('consensus', row.consensus_score, { owners: row.owners, consensus_managers: consensusLatest.size, tracked_managers: managerRows.length, aggregate_weight_pct: row.aggregate_weight }, 'Current-manager breadth plus average disclosed portfolio importance.'),
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

async function performInstitutionalRefresh({ managerSlug, quarters = 12 } = {}) {
  const client = db();
  const managerRows = await managers(client);
  const selected = managerSlug && managerSlug !== 'all' ? managerRows.filter((row) => row.slug === managerSlug) : managerRows;
  if (!selected.length) throw new Error('Select a tracked manager.');
  const results = await mapWithConcurrency(selected, 3, async (manager) => {
    await client.from('institutional_managers').update({ last_refresh_at: new Date().toISOString(), last_refresh_status: 'running', last_refresh_error: null }).eq('id', manager.id);
    try {
      const submissions = await secFetch(`${SEC_DATA}/submissions/CIK${cleanCik(manager.cik)}.json`, true);
      const filingRows = recent13fFilings(submissions, quarters);
      if (!filingRows.length) throw new Error('No Form 13F filings were found for this SEC filer.');
      const filings = [];
      for (const filing of filingRows) filings.push(await ingestFiling(client, manager, filing));
      const newestReport = filingRows.map((row) => row.report_date).sort().reverse()[0];
      const staleCutoff = new Date(Date.now() - (240 * 24 * 60 * 60 * 1000)).toISOString().slice(0, 10);
      const status = newestReport < staleCutoff ? 'stale' : 'success';
      await client.from('institutional_managers').update({ last_refresh_at: new Date().toISOString(), last_successful_refresh_at: new Date().toISOString(), last_refresh_status: status, last_refresh_error: status === 'stale' ? `Latest available 13F reports ${newestReport}.` : null }).eq('id', manager.id);
      return { manager: manager.display_name, cik: manager.cik, ok: true, status, latest_report_date: newestReport, filings };
    } catch (error) {
      await client.from('institutional_managers').update({ last_refresh_at: new Date().toISOString(), last_refresh_status: 'error', last_refresh_error: error.message }).eq('id', manager.id);
      return { manager: manager.display_name, cik: manager.cik, ok: false, status: 'error', error: error.message };
    }
  });
  const enrichment = await enrichSecurityIdentifiers(client);
  const scores = await rebuildSignals(client);
  return { ok: results.some((row) => row.ok), refreshed_at: new Date().toISOString(), results, enrichment, scores };
}

let fullRefreshPromise = null;

export function refreshInstitutionalFilings(options = {}) {
  const isFullRefresh = !options.managerSlug || options.managerSlug === 'all';
  if (isFullRefresh && fullRefreshPromise) return fullRefreshPromise;
  const promise = performInstitutionalRefresh(options);
  if (!isFullRefresh) return promise;
  fullRefreshPromise = promise.finally(() => { fullRefreshPromise = null; });
  return fullRefreshPromise;
}

let automationStarted = false;

// Opt-in, not opt-out.
//
// This used to default to on, so every deploy of the web process started an
// unthrottled SEC crawl 15 seconds later: 51 managers x 12 quarters of EDGAR
// requests from a dyno whose job is serving clients, with no rate limiter and
// no coordination between instances. Restart the service three times and three
// crawls run at once, against an endpoint whose Fair Access policy is 10
// requests a second and whose penalty is an IP block.
//
// Collection belongs in a scheduled worker with a real limiter. Until that
// exists, this runs only where someone has deliberately set the flag.
export function startInstitutionalHoldingsAutomation() {
  if (automationStarted || String(process.env.INSTITUTIONAL_AUTO_REFRESH || 'false').toLowerCase() !== 'true') return;
  automationStarted = true;
  const execute = () => refreshInstitutionalFilings({ managerSlug: 'all', quarters: 12 })
    .then((result) => console.info(`[institutional-holdings] automatic refresh complete: ${result.results.filter((row) => row.ok).length}/${result.results.length} managers, ${result.enrichment.mapped} identifiers mapped`))
    .catch((error) => console.error('[institutional-holdings] automatic refresh failed:', error.message));
  const initial = setTimeout(execute, 15_000);
  const recurring = setInterval(execute, AUTO_REFRESH_INTERVAL_MS);
  initial.unref?.();
  recurring.unref?.();
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
  // Collection telemetry. Wrapped because the admin console must still load
  // before the run-records migration has been applied, and because an
  // operations panel failing shut takes the whole CMS page with it - the
  // opposite of what a health display is for.
  let collection = null;
  try {
    collection = { health: await getCollectionHealth(), runs: await listRuns(10) };
  } catch (error) {
    collection = { health: null, runs: [], unavailable: error.message };
  }
  const { data: filings } = await client.from('institutional_filings').select('*, institutional_managers(display_name,slug)').order('filed_at', { ascending: false }).limit(30);
  const { data: alerts } = await client.from('institutional_filing_alerts').select('*, institutional_managers(display_name,slug)').order('created_at', { ascending: false }).limit(50);
  const { data: corrections } = await client.from('institutional_corrections').select('*').order('created_at', { ascending: false }).limit(50);
  return {
    collection,
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

/**
 * Re-ingest one already-known filing straight from SEC.
 *
 * Exists for the amendment remediation job. Every 13F-HR/A ingested before the
 * classification was fixed took the merge branch, so a restatement that removed
 * a position left it in the portfolio. Fixing ingestion forward does not undo
 * that: the stored rows are the merged result, and the amendment's own holdings
 * are not recoverable from them. They have to come back from EDGAR.
 *
 * The whole point is that this re-runs the same ingestFiling every collection
 * uses, rather than a parallel repair implementation that could drift from it.
 * Re-ingesting a manager's filings for one report_date in acceptance order
 * reproduces the correct end state: the original first, then each amendment
 * applied under its real classification.
 */
export async function reingestFiling(filingId) {
  const client = db();
  const { data: filing, error } = await client
    .from('institutional_filings')
    .select('*, institutional_managers(*)')
    .eq('id', filingId)
    .single();
  if (error) throw new Error(error.message);
  if (!filing) throw new Error(`Filing ${filingId} not found`);

  const manager = filing.institutional_managers;
  if (!manager?.cik) throw new Error(`Filing ${filingId} has no manager CIK to fetch against`);

  return ingestFiling(client, manager, {
    accession_number: filing.accession_number,
    form_type: filing.form_type,
    report_date: filing.report_date,
    accepted_at: filing.filed_at,
    primary_document: filing.primary_document,
  });
}

/** Holdings currently stored for a filing, for before/after comparison. */
export async function holdingsForFiling(filingId) {
  const client = db();
  return collect(() => client
    .from('institutional_holdings')
    .select('cusip,ticker,issuer_name,shares,value_usd,put_call')
    .eq('filing_id', filingId));
}

/** Every 13F-HR/A on record, oldest acceptance first, with its manager. */
export async function amendmentFilings() {
  const client = db();
  const { data, error } = await client
    .from('institutional_filings')
    .select('id,accession_number,form_type,report_date,filed_at,manager_id,is_active,amendment_type,institutional_managers(slug,display_name,cik)')
    .like('form_type', '%/A')
    .order('filed_at', { ascending: true });
  if (error) throw new Error(error.message);
  return data || [];
}

/** Active filings for one manager and quarter, in acceptance order. */
export async function filingsForQuarter(managerId, reportDate) {
  const client = db();
  const { data, error } = await client
    .from('institutional_filings')
    .select('id,accession_number,form_type,report_date,filed_at,is_active,amendment_type')
    .eq('manager_id', managerId)
    .eq('report_date', reportDate)
    .order('filed_at', { ascending: true });
  if (error) throw new Error(error.message);
  return data || [];
}

/** Recompute signals after a repair batch. Exported so the job runs it once at the end. */
export async function rebuildInstitutionalSignals() {
  return rebuildSignals(db());
}

/**
 * What re-ingesting a filing would produce, without writing anything.
 *
 * The repair job defaults to a dry run, and a dry run that can only say "this
 * would be reclassified" is not much of a report. This fetches and parses the
 * filing exactly as ingestion would, applies the real classification, and hands
 * back the rows that would result - so the reconciliation report can state
 * which positions would be removed before anything is changed.
 */
export async function previewFilingRepair(filingId) {
  const client = db();
  const { data: filing, error } = await client
    .from('institutional_filings')
    .select('*, institutional_managers(*)')
    .eq('id', filingId)
    .single();
  if (error) throw new Error(error.message);

  const manager = filing?.institutional_managers;
  if (!manager?.cik) throw new Error(`Filing ${filingId} has no manager CIK`);

  const archive = await filingDocuments(manager.cik, filing.accession_number);
  const infoDocument = archive.documents.find((doc) => /<(?:\w+:)?infoTable[\s>]/i.test(doc.text));
  if (!infoDocument) throw new Error(`No 13F information table in ${filing.accession_number}`);

  const amendmentRows = collapseDuplicateRows(parseInformationTable(infoDocument.text, 1));
  const classification = classifyFiling(filing.form_type, archive.coverPage);

  // The version this amendment amends.
  //
  // is_active is deliberately NOT part of this query. Ingesting the amendment
  // made it the active filing and deactivated the report it superseded, so
  // asking for the active one excludes the very filing being looked for. That
  // returned null on every amendment in the database, with two consequences:
  // removals were computed against an empty prior set and always reported
  // zero, and `strategy` fell through to replace regardless of what the cover
  // page said - which would erase valid positions on an additive amendment.
  const { data: previousVersion } = await client.from('institutional_filings').select('*')
    .eq('manager_id', manager.id).eq('report_date', filing.report_date)
    .neq('id', filing.id).lte('filed_at', filing.filed_at)
    .order('filed_at', { ascending: false }).limit(1).maybeSingle();
  const priorRows = previousVersion
    ? (await collect(() => client.from('institutional_holdings').select('*').eq('filing_id', previousVersion.id)))
      .map(({ id, filing_id, manager_id, report_date, portfolio_weight, created_at, ...row }) => row)
    : [];

  const strategy = classification.amendmentType === 'original' || !previousVersion
    ? 'replace'
    : classification.strategy;
  const outcome = applyAmendment({ strategy, priorRows, amendmentRows, keyOf: filingKey });

  // What actually disappears from the portfolio, measured against the rows
  // stored TODAY rather than against the prior version.
  //
  // The stored rows are the merged result the broken classification produced,
  // and they are what a client sees now. Comparing the prior version to the
  // amendment answers a different question and reported zero removals while
  // row counts visibly dropped - JPMorgan 7,756 to 7,499 with "0 removed".
  const currentRows = (await collect(() => client.from('institutional_holdings')
    .select('*').eq('filing_id', filing.id)))
    .map(({ id, filing_id, manager_id, report_date, portfolio_weight, created_at, ...row }) => row);
  const surviving = new Set(outcome.rows.map((row) => filingKey(row)));
  const removed = currentRows.filter((row) => !surviving.has(filingKey(row)));

  return {
    filing,
    manager,
    classification,
    strategy,
    priorRows,
    currentRows,
    amendmentRows,
    resultingRows: outcome.rows,
    removed,
    applied: outcome.applied,
  };
}

/**
 * Take an unclassifiable amendment out of the derived calculations.
 *
 * Recording that a filing needs review is not the same as stopping it counting.
 * An amendment whose type could not be read was ingested under the old merge
 * behaviour, so its rows are the merged result - and while it stays active,
 * consensus, sector weights and change signals keep reading them as though the
 * amendment had been understood.
 *
 * The filing itself is preserved: it is the audit record, and it is what a
 * reviewer resolves against. Only is_active changes, which is the flag every
 * derived surface filters on. The version it superseded is reactivated so the
 * quarter still has exactly one authoritative report rather than none - a
 * quarter with no active filing silently disappears from history, which is a
 * worse failure than the one being fixed.
 */
export async function quarantineAmendment(filingId, reason) {
  const client = db();
  const { data: amendment, error } = await client
    .from('institutional_filings')
    .select('id,manager_id,report_date,accession_number')
    .eq('id', filingId)
    .single();
  if (error) throw new Error(error.message);

  const { error: flagError } = await client
    .from('institutional_filings')
    .update({ is_active: false, needs_review: true, review_reason: reason || 'Amendment type could not be determined.' })
    .eq('id', filingId);
  if (flagError) throw new Error(flagError.message);

  // The most recent filing for this quarter that is not itself quarantined.
  const { data: candidates } = await client
    .from('institutional_filings')
    .select('id,form_type,filed_at,needs_review')
    .eq('manager_id', amendment.manager_id)
    .eq('report_date', amendment.report_date)
    .neq('id', filingId)
    .order('filed_at', { ascending: false });

  const successor = (candidates || []).find((row) => !row.needs_review);
  if (successor) {
    await client.from('institutional_filings').update({ is_active: true }).eq('id', successor.id);
    // Exactly one active version per quarter, or the aggregates double count.
    await client.from('institutional_filings').update({ is_active: false })
      .eq('manager_id', amendment.manager_id)
      .eq('report_date', amendment.report_date)
      .neq('id', successor.id);
  }

  return {
    quarantined: amendment.accession_number,
    reactivated: successor?.id || null,
    orphaned_quarter: !successor,
  };
}

/**
 * Whether derived numbers can currently be trusted as a whole.
 *
 * Repairing amendments quarter by quarter means there is a window in which
 * some of the history has been corrected and some has not, and a consensus
 * figure computed across both is not a figure of anything. Surfaces that
 * aggregate across managers and quarters ask this and say so, rather than
 * publishing a number whose inputs are half repaired.
 *
 * Deliberately conservative: anything unresolved reports as in progress. A gate
 * that reads clear while filings sit unreviewed is a gate that does nothing.
 */
export async function getRepairStatus() {
  const client = db();
  try {
    const [{ count: pendingReview }, { data: lastRun }] = await Promise.all([
      client.from('institutional_filings')
        .select('id', { count: 'exact', head: true })
        .eq('needs_review', true),
      client.from('institutional_amendment_repair_summary')
        .select('*')
        .order('started_at', { ascending: false })
        .limit(1)
        .maybeSingle(),
    ]);

    const run = lastRun || null;
    const failed = Number(run?.filings_failed || 0);
    const needingReview = Number(run?.filings_needing_review || 0);
    const pending = Number(pendingReview || 0);

    // A dry run has repaired nothing, so it never clears the gate on its own.
    const repairApplied = Boolean(run?.applied);
    const incomplete = failed > 0 || needingReview > 0 || pending > 0;

    if (!run) {
      return {
        status: 'not_started',
        clean: false,
        message: 'Historical amendment repair has not run. Aggregate figures may include positions withdrawn by amendments.',
      };
    }
    if (!repairApplied) {
      return {
        status: 'in_progress',
        clean: false,
        message: 'Historical repair in progress. Aggregate figures may mix repaired and unrepaired history.',
        pending_review: pending,
      };
    }
    if (incomplete) {
      return {
        status: 'in_progress',
        clean: false,
        message: 'Historical repair in progress. Some filings could not be repaired or are awaiting review, so aggregate figures may mix repaired and unrepaired history.',
        pending_review: pending,
        failed,
      };
    }
    return {
      status: 'complete',
      clean: true,
      message: null,
      repaired_at: run.finished_at || null,
    };
  } catch (error) {
    // Before the repair migration is applied the tables do not exist. Unknown
    // is not clean: it must not read as a clean bill of health.
    return {
      status: 'unknown',
      clean: false,
      message: 'Repair status is unavailable, so aggregate figures cannot be confirmed as fully repaired.',
      error: error.message,
    };
  }
}
