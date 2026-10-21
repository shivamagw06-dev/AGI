import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  buildKocDegradedAudit,
  buildKocDegradedHealth,
  buildKocDegradedOverview,
} from '../services/kocDegraded.js';

describe('kocDegraded', () => {
  it('builds health shell', () => {
    const h = buildKocDegradedHealth('timeout');
    assert.equal(h.degraded, true);
    assert.equal(h.ok, false);
    assert.match(h.error, /timeout/);
    assert.equal(h.workstream_id, 'KOC-01');
  });

  it('builds overview shell the UI can render', () => {
    const d = buildKocDegradedOverview({ scope: 'TOP20', detail: 'aborted' });
    assert.equal(d.ok, true);
    assert.equal(d.degraded, true);
    assert.equal(d.endpoint, 'overview');
    assert.ok(Array.isArray(d.coverage_table));
    assert.equal(d.coverage_table.length, 0);
    assert.equal(d.missing_inbox.count, 0);
    assert.equal(d.kpis.koc_status, 'Degraded');
    assert.equal(d.system_health.bar.koc.status, 'Degraded');
  });

  it('builds empty audit', () => {
    const a = buildKocDegradedAudit({ limit: 10, detail: 'down' });
    assert.equal(a.degraded, true);
    assert.deepEqual(a.events, []);
  });
});
