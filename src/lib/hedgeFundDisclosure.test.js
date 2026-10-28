import test from 'node:test';
import assert from 'node:assert/strict';
import { coverageCounts, filingStatus, latestFilingEvents, secManagerUrl, secPublicationDate } from './hedgeFundDisclosure.js';

test('coverage uses the visible population and preserves unknown service counts', () => {
  assert.deepEqual(coverageCounts({ managers: [{ latest_filing: {} }, {}], covered_managers: 50, consensus_managers: 1 }), { selected: 2, eligible: 1, withFilings: 1 });
  assert.equal(coverageCounts(null).selected, null);
  assert.equal(coverageCounts({ managers: [] }).eligible, null);
});
test('SEC dates retain US publication day across Indian midnight and date-only inputs', () => {
  assert.equal(secPublicationDate('2026-08-14T21:18:08+00:00'), 'Aug 14, 2026');
  assert.equal(secPublicationDate('2026-08-14'), 'Aug 14, 2026');
  assert.equal(secPublicationDate(null), 'Date unavailable');
});
test('notice, historical and failed checks have distinct ownership meaning', () => {
  assert.equal(filingStatus({ last_refresh_status: 'reports_elsewhere' }).label, 'Reports through another filer');
  assert.match(filingStatus({ last_refresh_status: 'stale' }).note, /does not establish a current position/);
  assert.match(filingStatus({ last_refresh_status: 'error' }).note, /does not establish that a newer filing is absent/);
  assert.equal(secManagerUrl('bad'), null);
  assert.match(secManagerUrl('0001336528'), /CIK=1336528/);
});
test('filing feed orders by actual publication rather than ingestion and deduplicates', () => {
  const filing = (id, filed_at, ingested_at) => ({ id, filed_at, ingested_at });
  const older = { latest_filing: filing('a', '2023-11-13', '2026-09-09') };
  const newer = { latest_filing: filing('b', '2026-08-14', '2026-08-15') };
  assert.deepEqual(latestFilingEvents([older, newer, older, { latest_filing: { filed_at: 'invalid' } }]).map(e => e.key), ['b', 'a']);
});
