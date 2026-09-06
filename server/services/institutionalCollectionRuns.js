/**
 * The record of what collection actually did.
 *
 * Collection used to leave no trace beyond a console line. That is how a
 * collector on the hedge fund desk stopped for 26 days without anyone
 * noticing: nothing recorded when it last succeeded, so nothing could tell
 * "the data has not changed" apart from "the data is not changing any more".
 *
 * Two rules hold everything here together:
 *
 *   The row is written when the run STARTS. A run that dies - killed, timed
 *   out, host restarted - leaves a row stuck in 'running', which is visible.
 *   Writing the row at the end means a run that dies leaves nothing, and
 *   silence reads identically to success.
 *
 *   Nothing is estimated. Every counter comes from something the collector
 *   observed. A number that could not be measured stays null rather than
 *   being filled in with a plausible one, because a plausible number in an
 *   operations dashboard is worse than a blank.
 */

import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

function db() {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Institutional collection run recorder is not configured.');
  return client;
}

/**
 * Next occurrence of a five-field cron expression, in UTC.
 *
 * Deliberately supports only what the collection schedule uses: fixed minute,
 * fixed hour, every day. Anything else returns null rather than guessing, so
 * the CMS shows "unknown" instead of a confidently wrong time. A general cron
 * parser is a dependency and a source of subtle bugs for a field that exists
 * to tell an operator roughly when to look again.
 */
export function nextScheduledAt(expression, from = new Date()) {
  const match = /^(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+\*$/.exec(String(expression || '').trim());
  if (!match) return null;
  const minute = Number(match[1]);
  const hour = Number(match[2]);
  if (minute > 59 || hour > 23) return null;
  const next = new Date(Date.UTC(
    from.getUTCFullYear(), from.getUTCMonth(), from.getUTCDate(), hour, minute, 0, 0,
  ));
  if (next <= from) next.setUTCDate(next.getUTCDate() + 1);
  return next.toISOString();
}

/**
 * Open a run. Returns the row id, or null when the recorder cannot write -
 * collection is more important than its own telemetry, so a failure to record
 * must never stop a run that would otherwise have worked.
 */
export async function startRun({
  trigger = 'schedule',
  host = null,
  managerSlug = null,
  quarters = null,
  scheduleExpression = null,
} = {}) {
  try {
    const { data, error } = await db()
      .from('institutional_collection_runs')
      .insert({
        trigger,
        host,
        manager_slug: managerSlug,
        quarters,
        schedule_expression: scheduleExpression,
        next_scheduled_at: nextScheduledAt(scheduleExpression),
        status: 'running',
      })
      .select('id')
      .single();
    if (error) throw new Error(error.message);
    return data?.id || null;
  } catch (error) {
    console.warn(`[collection-runs] could not open a run record: ${error.message}`);
    return null;
  }
}

/**
 * Close a run.
 *
 * `status` is derived from the work, not passed in as an opinion: a run where
 * nothing succeeded is 'failed' even if it threw no exception, and one where
 * some managers failed is 'partial' rather than 'success'. A dashboard that
 * shows green while half the universe is missing is worse than no dashboard.
 */
export function deriveStatus({ attempted, succeeded, error, aborted }) {
  if (aborted) return 'aborted';
  if (error && !succeeded) return 'failed';
  if (!attempted) return error ? 'failed' : 'success';
  if (!succeeded) return 'failed';
  if (succeeded < attempted) return 'partial';
  return 'success';
}

export async function finishRun(id, summary = {}) {
  if (!id) return false;
  try {
    const { error } = await db()
      .from('institutional_collection_runs')
      .update({
        finished_at: new Date().toISOString(),
        status: summary.status,
        sec_requests: summary.secRequests ?? 0,
        sec_throttled: summary.secThrottled ?? 0,
        sec_throttle_pause_ms: Math.round(summary.secThrottlePauseMs ?? 0),
        sec_paced_wait_ms: Math.round(summary.secPacedWaitMs ?? 0),
        sec_circuit_trips: summary.secCircuitTrips ?? 0,
        managers_attempted: summary.managersAttempted ?? 0,
        managers_succeeded: summary.managersSucceeded ?? 0,
        filings_ingested: summary.filingsIngested ?? 0,
        holdings_rows: summary.holdingsRows ?? 0,
        amendments_detected: summary.amendmentsDetected ?? 0,
        failures: summary.failures ?? [],
        retry_state: summary.retryState ?? null,
        error: summary.error ?? null,
      })
      .eq('id', id);
    if (error) throw new Error(error.message);
    return true;
  } catch (error) {
    console.warn(`[collection-runs] could not close run ${id}: ${error.message}`);
    return false;
  }
}

/**
 * Turn a refresh result into the counters the run record stores.
 *
 * Kept separate from the collector so it can be tested against real result
 * shapes without a database, and so the meaning of each counter lives in one
 * place rather than being reconstructed at each call site.
 */
export function summariseRefresh(result) {
  const rows = Array.isArray(result?.results) ? result.results : [];
  const succeeded = rows.filter((row) => row?.ok);

  // An amendment is a filing whose SEC form type ends in /A. The service
  // already classifies these at ingestion; this only counts what it found.
  const amendments = succeeded.filter((row) => {
    const form = row?.filing?.form_type || '';
    return typeof form === 'string' && form.toUpperCase().endsWith('/A');
  });

  return {
    managersAttempted: rows.length,
    managersSucceeded: succeeded.length,
    filingsIngested: succeeded.filter((row) => row?.ingestion?.status === 'ingested').length,
    holdingsRows: succeeded.reduce((total, row) => total + (Number(row?.ingestion?.holdings) || 0), 0),
    amendmentsDetected: amendments.length,
    failures: rows.filter((row) => !row?.ok).map((row) => ({
      manager: row?.manager?.slug || row?.slug || row?.manager?.display_name || 'unknown',
      error: String(row?.error || 'no reason recorded').slice(0, 500),
    })),
  };
}

export async function getCollectionHealth() {
  const { data, error } = await db()
    .from('institutional_collection_health')
    .select('*')
    .maybeSingle();
  if (error) throw new Error(error.message);
  return data || null;
}

export async function listRuns(limit = 20) {
  const { data, error } = await db()
    .from('institutional_collection_runs')
    .select('*')
    .order('started_at', { ascending: false })
    .limit(Math.min(Math.max(Number(limit) || 20, 1), 100));
  if (error) throw new Error(error.message);
  return data || [];
}
