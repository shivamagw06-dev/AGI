/**
 * The page's data, summarised by fixed rules.
 *
 * No model writes any of this. Each sentence is a template filled from the
 * same endpoint responses the panels render, so every figure in the summary
 * is one a reader can find on the page, and a sentence whose data has not
 * arrived is left out and the section says what it is waiting for. The
 * caveats are rules too: a session priced from last trades, members admitted
 * on the day being summarised, a market value that is the whole company's.
 * They appear when their condition holds and not otherwise.
 *
 * Every line carries the anchor of the panel it came from.
 */

export const LAYER_LABEL = {
  power: 'Power', data_centre: 'Data Centers', semiconductor: 'Semiconductors', infrastructure: 'EPC & Project Delivery',
};
export const SUB_LABEL = {
  generation: 'Generation', transmission: 'Transmission', equipment: 'Equipment',
  developer: 'Developer', operator: 'Operator', hardware: 'Hardware',
  osat: 'OSAT', materials: 'Materials', epc: 'EPC',
};
export const ALL_SUBS = [
  ['power', 'generation'], ['power', 'transmission'], ['power', 'equipment'],
  ['data_centre', 'developer'], ['data_centre', 'operator'], ['data_centre', 'hardware'],
  ['semiconductor', 'osat'], ['semiconductor', 'materials'], ['semiconductor', 'hardware'],
  ['infrastructure', 'epc'],
];

const KIND_PHRASE = {
  order: ['signed order', 'signed orders'],
  operating: ['operating disclosure', 'operating disclosures'],
  capex: ['committed capex filing', 'committed capex filings'],
};

const TESTS = [
  ['revenueCagr3y', 'revenue growth', '% a year over three years', '% a year'],
  ['capexGrowth', 'capex growth', '%', '%'],
  ['capexToSales', 'capex/sales', '%', '%'],
  ['rndToSales', 'R&D/sales', '%', '%'],
];

const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;
const signed = (v, digits = 2) => `${v >= 0 ? '+' : '−'}${Math.abs(v).toFixed(digits)}`;
const pct1 = (fraction) => `${(fraction * 100).toFixed(1)}`;
const listJoin = (items) => (items.length <= 1 ? items.join('')
  : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`);
const byCountDesc = (counts) => Object.entries(counts).sort((a, b) => b[1] - a[1]);

/** ₹ crore, in lakh crore above 1,00,000. */
export function rupeesCr(v) {
  if (v >= 100_000) return `₹${(v / 100_000).toFixed(1)} lakh cr`;
  return `₹${Math.round(v).toLocaleString('en-IN')} cr`;
}

const shareOf = (fraction) => (fraction < 0.01 ? 'under 1%' : `${Math.round(fraction * 100)}%`);

/** YYYY-MM-DD, in IST, of an instant. */
const istDate = (ms) => new Date(ms + 330 * 60_000).toISOString().slice(0, 10);
const istTime = (ms) => new Date(ms + 330 * 60_000).toISOString().slice(11, 16);
const longDate = (iso) => new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-GB', {
  day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
});

const line = (text, href) => ({ text, href });

function basketSection(universe) {
  const members = universe?.members || [];
  if (!members.length) return { pending: 'the universe' };
  const lines = [];
  const kinds = {};
  for (const member of members) {
    for (const one of member.admittedOn || []) kinds[one.kind] = (kinds[one.kind] || 0) + 1;
  }
  const filings = Object.values(kinds).reduce((a, b) => a + b, 0);
  const parts = byCountDesc(kinds).map(([kind, n]) => {
    const [one, many] = KIND_PHRASE[kind] || [kind, kind];
    return plural(n, one, many);
  });
  lines.push(line(`${plural(members.length, 'company', 'companies')} admitted on ${plural(filings, 'filing', 'filings')} of their own: ${listJoin(parts)}. Nothing is admitted on intent or an MoU.`, '#universe'));

  const layers = {};
  for (const member of members) layers[member.layer] = (layers[member.layer] || 0) + 1;
  lines.push(line(`By layer: ${byCountDesc(layers).map(([layer, n]) => `${LAYER_LABEL[layer] || layer} ${n}`).join(', ')}.`, '#universe'));

  const filled = new Set(members.flatMap((m) => (m.subLayers || []).map((s) => `${m.layer}/${s}`)));
  const empty = ALL_SUBS.filter(([layer, sub]) => !filled.has(`${layer}/${sub}`))
    .map(([layer, sub]) => `${LAYER_LABEL[layer]} — ${SUB_LABEL[sub]}`);
  lines.push(line(empty.length
    ? `${ALL_SUBS.length - empty.length} of ${ALL_SUBS.length} sub-layers are filled; ${listJoin(empty)} ${empty.length === 1 ? 'is' : 'are'} empty, with nothing disclosed beyond intent.`
    : `All ${ALL_SUBS.length} sub-layers are filled.`, '#layers'));

  const leads = members.filter((one) => String(one.discoveredVia || '').startsWith('EXTERNAL_LEAD')).length;
  if (leads) {
    lines.push(line(`${members.length - leads} came from AGI's own screen and ${leads} were first read as leads from a reported broker list; all passed the same evidence test.`, '#universe'));
  }

  const candidates = universe?.candidates || [];
  const pending = candidates.filter((one) => one.pendingVerification).map((one) => one.symbol);
  const excluded = (universe?.excluded || []).length;
  lines.push(line(`${plural(candidates.length, 'candidate is', 'candidates are')} held back${pending.length ? ` (${listJoin(pending)} pending verification)` : ''}${excluded ? `, and ${excluded} excluded` : ''}.`, '#refused'));

  const attribution = { SEGMENT_REPORTED: 0, MANAGEMENT_DISCLOSED: 0, NOT_ATTRIBUTABLE: 0, unrecorded: 0 };
  for (const member of members) {
    if (member.attribution in attribution) attribution[member.attribution] += 1;
    else attribution.unrecorded += 1;
  }
  const exposure = [
    attribution.SEGMENT_REPORTED ? `${attribution.SEGMENT_REPORTED} ${attribution.SEGMENT_REPORTED === 1 ? 'reports' : 'report'} data-centre revenue as a segment` : null,
    attribution.MANAGEMENT_DISCLOSED ? `management states it for ${attribution.MANAGEMENT_DISCLOSED}` : null,
    attribution.NOT_ATTRIBUTABLE ? `no filing sizes it for ${attribution.NOT_ATTRIBUTABLE}` : null,
    attribution.unrecorded ? `not yet recorded for ${attribution.unrecorded}` : null,
  ].filter(Boolean);
  lines.push(line(`How much of each business serves AI infrastructure: ${exposure.join('; ')}.`, '#universe'));
  return { lines };
}

function sessionSection(live, universe) {
  const index = live?.index;
  if (!index) return { pending: 'the live basket' };
  if (index.status !== 'ok') {
    return { lines: [line(`The basket is not priced right now: ${index.reason || index.status}.`, '#basket')] };
  }
  const q = live.quality || {};
  const lastTrade = Boolean(q.closed && q.session_last);
  const lines = [];
  const rel = index.relative;
  const verb = index.return_pp >= 0 ? 'rose' : 'fell';
  const opening = lastTrade ? 'In the last session the basket' : 'Today so far the basket';
  lines.push(line(`${opening} ${verb} ${Math.abs(index.return_pp).toFixed(2)}%${rel ? ` against Nifty 50's ${signed(rel.benchmark_return_pp)}%, ${rel.excess_pp >= 0 ? 'ahead' : 'behind'} by ${Math.abs(rel.excess_pp).toFixed(2)}pp` : ''}; ${index.breadth?.advancing ?? 0} of ${index.priced} members rose.`, '#basket'));

  const layers = index.contributions?.byLayer || [];
  if (layers.length) {
    lines.push(line(`By layer: ${[...layers].sort((a, b) => b.contribution_pp - a.contribution_pp)
      .map((one) => `${LAYER_LABEL[one.layer] || one.layer} ${signed(one.contribution_pp)}pp`).join(', ')}.`, '#basket'));
  }
  const names = [...(index.contributions?.byName || [])].filter((one) => Number.isFinite(one.return_pct))
    .sort((a, b) => b.return_pct - a.return_pct);
  if (names.length >= 6) {
    const fmt = (one) => `${one.symbol} ${signed(one.return_pct * 100, 1)}%`;
    lines.push(line(`Leaders: ${names.slice(0, 3).map(fmt).join(', ')}. Laggards: ${names.slice(-3).reverse().map(fmt).join(', ')}.`, '#basket'));
  }

  const caveats = [];
  if (lastTrade && q.last_trade_at) {
    caveats.push(`Priced at each member's last trade, latest ${istTime(Date.parse(q.last_trade_at))} IST; NSE's official close may differ slightly${q.from_candles ? `; ${q.from_candles} from the session's final minute candle while the feed reconnects` : ''}.`);
  }
  if (index.priced < index.total) caveats.push(`${index.total - index.priced} of ${index.total} members are not priced and are left out.`);
  if (index.priceBreak?.length) caveats.push(`Excluded for a corporate action: ${index.priceBreak.map((one) => one.symbol).join(', ')}.`);
  if (index.fallback?.length) caveats.push(`${plural(index.fallback.length, 'member is', 'members are')} on a last-good price, not live.`);

  // Members decided on the session being summarised were not members at its
  // open, so the move is the current basket's, not the record's.
  const sessionDate = lastTrade && q.last_trade_at ? istDate(Date.parse(q.last_trade_at)) : istDate(Date.parse(live.at || Date.now()));
  const sameDay = (universe?.members || []).filter((one) => one.membershipStart && one.membershipStart >= sessionDate).length;
  if (sameDay) {
    caveats.push(`${sameDay} of these members were admitted on ${longDate(sessionDate)}, so this session is the current basket's move, not part of the since-admission record.`);
  }
  return { lines, caveats };
}

function recordSection(history) {
  if (!history) return { pending: 'the since-admission series' };
  const points = history.points || [];
  if (!history.base) return { lines: [line('No membership dates are recorded, so there is no since-admission series.', '#history')] };
  if (points.length < 2) {
    return { lines: [line(`The record starts at the close on ${longDate(history.base)} and has no completed session yet; the first point arrives with the next published daily close.`, '#history')] };
  }
  const last = points[points.length - 1];
  const lines = [line(`Since the close on ${longDate(history.base)}, over ${plural(points.length - 1, 'session', 'sessions')}: the basket ${signed(last.basket - 100)}%, Nifty 50 ${signed(last.benchmark - 100)}%, a gap of ${signed(last.basket - last.benchmark)}pp. ${last.members} members counted in the last session.`, '#history')];
  const caveats = [];
  if (last.missing?.length) caveats.push(`No close for ${last.missing.join(', ')} in the last session.`);
  if (last.excluded?.length) caveats.push(`Left out of the last session for a bonus, split or rights issue: ${last.excluded.join(', ')}.`);
  return { lines, caveats };
}

function sizeSection(marketValue) {
  if (!marketValue) return { pending: 'market values' };
  if (!marketValue.ok) return { lines: [line(`Market value is unavailable: ${marketValue.error || 'no response'}.`, '#value')] };
  const lines = [];
  const total = marketValue.byLayer?.totalCr || 0;
  const groups = marketValue.byLayer?.groups || [];
  lines.push(line(`Combined market value ${rupeesCr(total)} at the ${longDate(marketValue.closeDate)} close: ${groups.map((one) => `${LAYER_LABEL[one.key] || one.key} ${shareOf(one.share)}`).join(', ')}.`, '#value'));
  const top = [...(marketValue.rows || [])].filter((one) => one.marketValueCr != null)
    .sort((a, b) => b.marketValueCr - a.marketValueCr).slice(0, 2);
  if (top.length === 2 && total > 0) {
    const share = (top[0].marketValueCr + top[1].marketValueCr) / total;
    lines.push(line(`${top[0].symbol} and ${top[1].symbol} are ${Math.round(share * 100)}% of it${share >= 0.4 ? ', which is why the basket is equal-weighted rather than weighted by size' : ''}.`, '#value'));
  }
  const caveats = ['This is whole-company value: where listed value with a filed AI-infrastructure link sits, not what the link is worth.'];
  const leftOut = marketValue.byLayer?.leftOut || [];
  if (leftOut.length) caveats.push(`Left out of the totals: ${leftOut.map((one) => one.symbol).join(', ')}.`);
  return { lines, caveats };
}

function intensitySection(stage3) {
  if (!stage3) return { pending: 'the stage 3 inputs' };
  const members = (stage3.rows || []).filter((one) => one.kind === 'member');
  if (!members.length) return { pending: 'the stage 3 inputs' };
  const t = stage3.thresholds || {};
  const lines = [];
  const pass = members.filter((one) => one.verdict === 'PASS').length;
  const medians = TESTS.filter(([key]) => Number.isFinite(t[key]))
    .map(([key, label, unit]) => `${label} ${pct1(t[key])}${unit}`);
  lines.push(line(`${pass} of ${members.length} members are above the group median on at least one test. Medians: ${medians.join('; ')}.`, '#intensity'));
  const highs = TESTS.map(([key, label, , unit]) => {
    const best = members.filter((one) => Number.isFinite(one[key])).sort((a, b) => b[key] - a[key])[0];
    return best ? `${label} ${best.symbol} ${pct1(best[key])}${unit}` : null;
  }).filter(Boolean);
  if (highs.length) lines.push(line(`Highest: ${highs.join('; ')}.`, '#intensity'));
  const below = members.filter((one) => one.verdict === 'BELOW')
    .map((one) => `${one.symbol} (${one.tested.length} of 4 tested)`);
  if (below.length) lines.push(line(`Below the median on every test it could be measured on: ${listJoin(below)}.`, '#intensity'));
  const notScreened = members.filter((one) => one.verdict === 'NOT_SCREENED').map((one) => one.symbol);
  const caveats = ['Context, not a gate: stage 3 removes no one, and the medians are of a group already chosen for exposure.'];
  if (notScreened.length) caveats.push(`Not screened: ${listJoin(notScreened)}.`);
  return { lines, caveats };
}

function tradabilitySection(exitability) {
  if (!exitability) return { pending: 'the liquidity screen' };
  if (!exitability.ok) return { lines: [line(`The liquidity screen is unavailable: ${exitability.error || 'no response'}.`, null)] };
  const sized = exitability.sized || [];
  const policy = exitability.policy || {};
  const target = policy.targetPosition ? policy.targetPosition / 1e7 : null;
  const needs = exitability.minimumAdvtForTarget ? exitability.minimumAdvtForTarget / 1e7 : null;
  const meets = sized.filter((one) => one.meetsTarget).length;
  const lines = [];
  lines.push(line(`${meets} of ${sized.length} members can carry a ${target ? rupeesCr(target) : 'target'} position${needs ? `, which takes ${rupeesCr(needs)} of normal daily turnover to exit in ${policy.exitDays} days at ${Math.round(policy.maxParticipation * 100)}% of volume` : ''}.`, null));
  const short = sized.filter((one) => !one.meetsTarget && !one.exception)
    .sort((a, b) => b.maxExecutablePosition - a.maxExecutablePosition)
    .map((one) => `${one.symbol} ${rupeesCr(one.maxExecutablePosition / 1e7)}`);
  if (short.length) lines.push(line(`Largest executable position below target: ${short.join(', ')}.`, null));
  const excepted = sized.filter((one) => !one.meetsTarget && one.exception)
    .map((one) => `${one.symbol} (${rupeesCr(one.maxExecutablePosition / 1e7)})`);
  const caveats = [];
  if (excepted.length) caveats.push(`Held below target on recorded exceptions: ${listJoin(excepted)}.`);
  return { lines, caveats };
}

function gapsSection({ marketValue }) {
  const lines = [];
  const flagged = (marketValue?.rows || []).filter((one) => one.crossCheck?.within === false).map((one) => one.symbol);
  if (flagged.length) {
    lines.push(line(`P/B × book disagrees with the filed share count by more than 25% for ${plural(flagged.length, 'member', 'members')} (${listJoin(flagged)}) and is not used.`, '#value'));
  }
  lines.push(line('No forward-estimates source is connected, so there are no earnings revisions.', null));
  return { lines };
}

/**
 * The summary: sections in reading order, each with lines (text and source
 * anchor), caveats, or `pending` naming the data it is waiting for.
 */
export function summariseIntelligence({
  universe = null, live = null, history = null, marketValue = null, stage3 = null, exitability = null,
} = {}) {
  return [
    { id: 'basket', title: 'The basket', ...basketSection(universe) },
    { id: 'session', title: live?.quality?.closed && live?.quality?.session_last ? 'Last session' : 'Today', ...sessionSection(live, universe) },
    { id: 'record', title: 'Since admission', ...recordSection(history) },
    { id: 'size', title: 'Size and concentration', ...sizeSection(marketValue) },
    { id: 'intensity', title: 'Investment intensity', ...intensitySection(stage3) },
    { id: 'tradability', title: 'Can it be traded?', ...tradabilitySection(exitability) },
    { id: 'gaps', title: 'Data gaps', ...gapsSection({ marketValue }) },
  ].map((one) => ({ lines: [], caveats: [], ...one }));
}

/** The summary as plain text, for copying. */
export function summaryText(sections) {
  return sections.map((section) => {
    const body = section.pending
      ? [`Waiting for ${section.pending}.`]
      : [...section.lines.map((one) => one.text), ...section.caveats.map((one) => `Note: ${one}`)];
    return [section.title.toUpperCase(), ...body.map((one) => `- ${one}`)].join('\n');
  }).join('\n\n');
}
