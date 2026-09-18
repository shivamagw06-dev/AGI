#!/usr/bin/env node
/**
 * Stage 1 of the AI enablers screen, over every NSE equity.
 *
 * Fetches each company's Upstox profile, nominates from its own business
 * description, and stores one row per company in ai_enabler_universe_pass.
 * Nomination picks what to read for evidence; it admits nothing.
 *
 * Resumable: re-running with the same --run id skips companies already
 * stored. Paced under Upstox's limits (250/min, 1,800 per 30 min by default),
 * so a full pass takes a little over an hour.
 *
 * Run from the Render shell (which opens in ~/project/src/server), detached
 * so it survives the shell closing:
 *   nohup node scripts/aiEnablersUniversePass.mjs > /tmp/universe-pass.log 2>&1 &
 *   tail -f /tmp/universe-pass.log
 *
 * A deploy restarts the instance and kills it; re-run the same command after
 * and it resumes. --summary prints the stored run without fetching anything.
 * --renominate re-scores a stored run's descriptions under the current rules,
 * without fetching, and writes only the rows whose outcome moved.
 *
 * Reads EQUITY_L.csv (main board) and, when present, SME_EQUITY_L.csv (NSE
 * Emerge) from the repo root.
 */
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { getFundamentals, isUpstoxConfigured } from '../providers/upstox.js';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import {
  PacedLimiter, parseEquityList, readUniversePass, renominate, runUniversePass, summariseUniversePass,
  UNIVERSE_PASS_TABLE,
} from '../services/aiEnablersUniversePass.js';

const EQUITY_LIST = fileURLToPath(new URL('../../EQUITY_L.csv', import.meta.url));
const SME_LIST = fileURLToPath(new URL('../../SME_EQUITY_L.csv', import.meta.url));
const UNIVERSE = fileURLToPath(new URL('../config/india-ai-enablers.universe.json', import.meta.url));

const arg = (name) => {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : null;
};
const istToday = () => new Date(Date.now() + 330 * 60_000).toISOString().slice(0, 10);

function print(summary, runId) {
  console.log(`\nrun ${runId}: ${summary.recorded} of ${summary.listed} listed recorded`
    + `${summary.complete ? '' : ' (INCOMPLETE - re-run to resume)'}`);
  console.log(`coverage ${(summary.coverage * 100).toFixed(1)}% of ${summary.addressable} addressable -> ${summary.status}`);
  console.log('dispositions', summary.dispositions);
  console.log('boards', summary.byBoard);
  console.log('reading tiers (1 strong, 2 contractor, 3 incidental)', summary.byTier);
  console.log('\nnominated per sub-layer (a company can sit in more than one):');
  for (const [sub, n] of Object.entries(summary.bySubLayer).sort((a, b) => b[1] - a[1])) {
    console.log(`  ${sub.padEnd(34)} ${String(n).padStart(4)}`);
  }
  console.log(`\nrecall against known qualifiers: ${summary.recall.nominated} of ${summary.recall.reference}`);
  for (const miss of summary.recall.missed) {
    console.log(`  MISSED ${miss.symbol.padEnd(12)} ${miss.kind.padEnd(9)} ${miss.disposition}`);
  }
}

async function main() {
  const db = createSupabaseAdmin();
  if (!db) throw new Error('Supabase service role is not configured on this instance.');
  const runId = arg('run') || istToday();
  const main = parseEquityList(await readFile(EQUITY_LIST, 'utf8'), { board: 'main' });
  const sme = existsSync(SME_LIST) ? parseEquityList(await readFile(SME_LIST, 'utf8'), { board: 'sme' }) : [];
  // A symbol on both lists (a migration from Emerge) is read once, as main board.
  const onMain = new Set(main.map((one) => one.symbol));
  const companies = [...main, ...sme.filter((one) => !onMain.has(one.symbol))];
  console.log(`lists: ${main.length} main board, ${sme.length} SME${existsSync(SME_LIST) ? '' : ' (SME_EQUITY_L.csv not found)'}`);
  const universe = JSON.parse(await readFile(UNIVERSE, 'utf8'));
  const reference = [
    ...(universe.members || []).map((one) => ({ symbol: one.symbol, kind: 'member' })),
    ...(universe.candidates || []).map((one) => ({ symbol: one.symbol, kind: 'candidate' })),
  ];

  if (process.argv.includes('--renominate')) {
    const changed = renominate(await readUniversePass(db, runId));
    for (let i = 0; i < changed.length; i += 200) {
      const { error } = await db.from(UNIVERSE_PASS_TABLE).upsert(changed.slice(i, i + 200), { onConflict: 'run_id,symbol' });
      if (error) throw new Error(`writing ${UNIVERSE_PASS_TABLE}: ${error.message}`);
    }
    console.log(`re-scored run ${runId}: ${changed.length} outcomes changed`);
  } else if (!process.argv.includes('--summary')) {
    if (!isUpstoxConfigured()) throw new Error('Upstox is not configured; set UPSTOX_ACCESS_TOKEN.');
    const done = new Set((await readUniversePass(db, runId)).map((one) => one.symbol));
    console.log(`run ${runId}: ${companies.length} listed, ${done.size} already stored, `
      + `${companies.length - done.size} to fetch`);
    const started = Date.now();
    await runUniversePass({
      companies,
      runId,
      done,
      limiter: new PacedLimiter({
        perMinute: Number(process.env.UNIVERSE_PASS_PER_MINUTE || 250),
        perWindow: Number(process.env.UNIVERSE_PASS_PER_30MIN || 1_800),
      }),
      fetchProfile: (isin) => getFundamentals(isin, 'profile', {}),
      save: async (rows) => {
        const { error } = await db.from(UNIVERSE_PASS_TABLE).upsert(rows, { onConflict: 'run_id,symbol' });
        if (error) throw new Error(`writing ${UNIVERSE_PASS_TABLE}: ${error.message}`);
      },
      onProgress: ({ processed }) => {
        if (processed % 100 === 0) {
          const mins = ((Date.now() - started) / 60_000).toFixed(1);
          console.log(`  ${done.size + processed} / ${companies.length}  (${mins} min)`);
        }
      },
    });
  }

  print(summariseUniversePass(await readUniversePass(db, runId), { reference, listed: companies.length }), runId);
}

main().catch((error) => {
  console.error(error?.stack || String(error));
  process.exitCode = 1;
});
