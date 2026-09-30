#!/usr/bin/env node
/**
 * What the screen would see, before any threshold is chosen.
 *
 * Read-only. Fetches daily candles for the current universe, prints the
 * liquidity distribution, and shows what Stage 2 would do at a few candidate
 * floors. Writes nothing: the point is to look at the spread first and set
 * the thresholds afterwards, rather than the other way round.
 *
 * Run from the Render shell (which opens in ~/project/src/server):
 *   node scripts/aiEnablersScreenReport.mjs
 */
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { getHistoricalCandles, isUpstoxConfigured } from '../providers/upstox.js';
import { liquidityForUniverse } from '../services/aiEnablersLiquidity.js';
import { distribution, stageTwo } from '../services/aiEnablersScreen.js';

const UNIVERSE = fileURLToPath(new URL('../config/india-ai-enablers.universe.json', import.meta.url));
const crore = (value) => (value === null ? '        -' : (value / 1e7).toFixed(2).padStart(9));

async function main() {
  if (!isUpstoxConfigured()) {
    console.error('Upstox is not configured. This script only reads; it needs UPSTOX_ACCESS_TOKEN.');
    process.exitCode = 1;
    return;
  }
  const universe = JSON.parse(await readFile(UNIVERSE, 'utf8'));
  const members = (universe.members || []).filter((one) => one.admitted !== false);
  const today = new Date().toISOString().slice(0, 10);
  const from = new Date(Date.now() - 200 * 24 * 3600 * 1000).toISOString().slice(0, 10);

  console.log(`universe ${universe.version} (${universe.status}) - ${members.length} admitted members`);
  console.log(`daily candles ${from} .. ${today}\n`);

  const liquidity = await liquidityForUniverse(universe, {
    fetchCandles: getHistoricalCandles, to: today, from, sessions: 120,
  });

  console.log('symbol        sessions   avg daily volume   median turnover (Rs cr)   last close');
  console.log('-'.repeat(84));
  const rows = [];
  for (const member of members) {
    const one = liquidity.bySymbol[member.symbol];
    if (!one) continue;
    console.log(
      `${member.symbol.padEnd(12)} ${String(one.sessions).padStart(8)}   `
      + `${one.averageDailyVolume === null ? '-'.padStart(16) : one.averageDailyVolume.toLocaleString('en-IN').padStart(16)}   `
      + `${crore(one.medianDailyTurnover).padStart(23)}   `
      + `${one.lastClose === null ? '-' : one.lastClose}`
      + `${one.reason ? `   [${one.reason}]` : ''}`,
    );
    rows.push({ symbol: member.symbol, medianDailyTurnover: one.medianDailyTurnover });
  }
  for (const failure of liquidity.failures) {
    console.log(`${failure.symbol.padEnd(12)} ${'-'.padStart(8)}   ${failure.error}`);
  }

  const spread = distribution(rows, (one) => one.medianDailyTurnover);
  console.log('\nmedian daily turnover, Rs crore');
  console.log(`  min ${crore(spread.min)}   p25 ${crore(spread.p25)}   median ${crore(spread.median)}`
    + `   p75 ${crore(spread.p75)}   max ${crore(spread.max)}   (missing ${spread.missing})`);

  console.log('\nwhat Stage 2 would admit at each turnover floor:');
  for (const floorCrore of [1, 5, 10, 25, 50]) {
    const screened = stageTwo(
      members.map((member) => ({
        symbol: member.symbol,
        // Size is deliberately left out: free float is not in the universe
        // yet, so a size floor here would screen on a number we do not have.
        freeFloatMarketCap: 1,
        medianDailyTurnover: liquidity.bySymbol[member.symbol]?.medianDailyTurnover ?? null,
      })),
      { minMedianDailyTurnover: floorCrore * 1e7 },
    );
    console.log(`  >= Rs ${String(floorCrore).padStart(3)} cr/day: `
      + `${String(screened.passed.length).padStart(2)} pass, `
      + `${String(screened.failed.length).padStart(2)} fail, `
      + `${String(screened.unscreened.length).padStart(2)} unscreened   `
      + `[${screened.passed.map((one) => one.symbol).join(', ')}]`);
  }

  console.log('\nStage 2 needs free-float market cap, which the universe does not carry.');
  console.log('Until it does, size cannot be screened and cap-weighting refuses by design.');
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
