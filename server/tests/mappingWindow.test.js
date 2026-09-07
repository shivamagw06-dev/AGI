import test from 'node:test';
import assert from 'node:assert/strict';
import { windowsOverlap, conflictingOwner, proposedWindow } from '../services/mappingWindow.js';

test('two share classes trading at the same time are a real conflict', () => {
  // Carnival Corp (143658300) and Carnival plc (G2004J103) trade together as
  // CCL and CUK. Giving CCL to both puts one company's price on the other's
  // position - the failure this check exists to stop.
  const owners = [{ cusip: 'G2004J103', valid_from: '2023-09-30', valid_to: null }];
  const clash = conflictingOwner(owners, '143658300', { from: '2023-09-30', to: '2026-06-30' });
  assert.equal(clash?.cusip, 'G2004J103');
});

test('a ticker that moved to a new CUSIP is not a conflict', () => {
  // The old identifier stops being reported when the new one starts. Each
  // owns the ticker for the stretch it actually described.
  const owners = [{ cusip: '438516205', valid_from: '2025-12-31', valid_to: null }];
  assert.equal(conflictingOwner(owners, '438516106', { from: '2023-09-30', to: '2025-09-30' }), null);
});

test('windows that touch at the boundary are a handover, not a clash', () => {
  // Ends are exclusive, so a window ending exactly where another begins does
  // not overlap it - which is the shape a real succession takes.
  assert.equal(windowsOverlap({ from: '2023-01-01', to: '2024-06-30' }, { from: '2024-07-01', to: null }), false);
  assert.equal(windowsOverlap({ from: '2023-01-01', to: '2024-06-30' }, { from: '2024-06-30', to: null }), false);
  // One day of genuine overlap is still a clash.
  assert.equal(windowsOverlap({ from: '2023-01-01', to: '2024-07-01' }, { from: '2024-06-30', to: null }), true);
});

test('an open-ended window runs to the end of time', () => {
  // This is why a proposal must bound itself: claiming forever would block
  // whatever security takes the symbol over next.
  assert.equal(windowsOverlap({ from: '2023-01-01', to: null }, { from: '2030-01-01', to: null }), true);
});

test('a mapping does not conflict with itself', () => {
  const owners = [{ cusip: 'AAA', valid_from: '2023-01-01', valid_to: null }];
  assert.equal(conflictingOwner(owners, 'AAA', { from: '2023-01-01', to: null }), null);
});

test('a position still held claims an open window; one that stopped does not', () => {
  const current = proposedWindow({ earliest: '2023-09-30', latest: '2026-06-30' }, '2026-06-30');
  assert.deepEqual(current, { from: '2023-09-30', to: null });

  // The day after the last report date held. Ending on that date itself would
  // stop one day before covering it, because the end is exclusive.
  const ended = proposedWindow({ earliest: '2023-09-30', latest: '2024-09-30' }, '2026-06-30');
  assert.deepEqual(ended, { from: '2023-09-30', to: '2024-10-01' });
});

test('a security held in a single quarter still gets a real window', () => {
  // This threw: valid_to equal to valid_from violates the table's
  // security_identifier_validity_ordered check, which requires to > from.
  const one = proposedWindow({ earliest: '2026-03-31', latest: '2026-03-31' }, '2026-06-30');
  assert.deepEqual(one, { from: '2026-03-31', to: '2026-04-01' });
  assert.ok(one.to > one.from, 'the table requires valid_to > valid_from');
});

test('a month or year boundary does not produce an impossible date', () => {
  assert.equal(proposedWindow({ earliest: '2024-01-01', latest: '2024-12-31' }, '2026-06-30').to, '2025-01-01');
  assert.equal(proposedWindow({ earliest: '2024-01-01', latest: '2024-02-29' }, '2026-06-30').to, '2024-03-01');
});

test('a stopped position does not block its successor', () => {
  // The whole point: bound the old window, and the new CUSIP can take the
  // ticker from the date it starts.
  const old = proposedWindow({ earliest: '2023-09-30', latest: '2025-09-30' }, '2026-06-30');
  const owners = [{ cusip: 'OLD', valid_from: old.from, valid_to: old.to }];
  assert.equal(conflictingOwner(owners, 'NEW', { from: '2025-12-31', to: null }), null);
});
