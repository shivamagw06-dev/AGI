/**
 * Lightweight Node test for Phase 7.4d bootstrap status machine.
 * Run: node --test server/services/upstoxBootstrapEngine.test.js
 */

import { describe, it, before, after } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ub-test-'));
process.env.UPSTOX_BOOTSTRAP_STATE_DIR = tmp;
process.env.UPSTOX_BOOTSTRAP_STATE_PATH = path.join(tmp, 'state.json');

const {
  getUpstoxBootstrapStatus,
  resetUpstoxBootstrap,
  isUpstoxBootstrapRunning,
  shouldPauseAfterFirstWave,
} = await import('../services/upstoxBootstrapEngine.js');

describe('upstoxBootstrapEngine', () => {
  before(async () => {
    await resetUpstoxBootstrap();
  });

  after(() => {
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch { /* ignore */ }
  });

  it('starts idle with empty summary', () => {
    const st = getUpstoxBootstrapStatus();
    assert.equal(st.ok, true);
    assert.equal(st.engine, 'upstox_bootstrap');
    assert.equal(st.status, 'idle');
    assert.equal(st.summary.completed, 0);
    assert.equal(isUpstoxBootstrapRunning(), false);
  });

  it('exposes queue buckets and api health shape', () => {
    const st = getUpstoxBootstrapStatus();
    for (const key of ['PENDING', 'RUNNING', 'SUCCESS', 'FAILED', 'RETRY', 'SKIPPED']) {
      assert.equal(typeof st.queue[key], 'number');
    }
    assert.equal(typeof st.apiHealth.successfulCalls, 'number');
    assert.equal(typeof st.throughput.pauseMs, 'number');
    assert.match(st.nightlySchedulerNote, /full company-equity/i);
    assert.equal(st.waves.firstWaveSize, 1000);
  });

  it('pauses after the first thousand only when more companies remain', () => {
    assert.equal(shouldPauseAfterFirstWave({ attempted: 999, size: 1000, pending: 500 }), false);
    assert.equal(shouldPauseAfterFirstWave({ attempted: 1000, size: 1000, pending: 500 }), true);
    assert.equal(shouldPauseAfterFirstWave({ attempted: 1000, size: 1000, pending: 0, retry: 0 }), false);
  });
});
