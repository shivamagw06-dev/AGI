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
// Re-exported so callers have one import for the whole concern, while the pure
// half stays reachable without a database driver.
import { nextScheduledAt, deriveStatus, summariseRefresh } from './collectionRunSummary.js';

export { nextScheduledAt, deriveStatus, summariseRefresh };

function db() {
  const client = createSupabaseAdmin();
  if (!client) throw new Error('Institutional collection run recorder is not configured.');
  return client;
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
