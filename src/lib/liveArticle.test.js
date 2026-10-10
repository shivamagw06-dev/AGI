import assert from 'node:assert/strict';
import test from 'node:test';
import {
  createLiveUpdate,
  formatLiveClock,
  hasLiveTag,
  isLiveArticle,
  isMissingLiveColumnError,
  latestLiveTimestamp,
  normalizeLiveUpdates,
  plaintextToHtml,
  withLiveTag,
} from './liveArticle.js';

test('isLiveArticle prefers the is_live flag and stops after coverage ends', () => {
  assert.equal(isLiveArticle({ is_live: true }), true);
  assert.equal(isLiveArticle({ isLive: true, tags: [] }), true);
  assert.equal(isLiveArticle({ is_live: true, live_ended_at: '2026-08-27T08:00:00.000Z' }), false);
  assert.equal(isLiveArticle({ is_live: false, tags: ['live'] }), false);
  assert.equal(isLiveArticle({ tags: ['LIVE'] }), true);
  assert.equal(isLiveArticle({ tags: ['markets'] }), false);
});

test('live tag helpers keep a single live marker', () => {
  assert.equal(hasLiveTag(['markets', 'live']), true);
  assert.deepEqual(withLiveTag(['markets', 'LIVE'], true), ['markets', 'live']);
  assert.deepEqual(withLiveTag(['markets', 'live'], false), ['markets']);
});

test('normalizeLiveUpdates sorts newest first and drops empty rows', () => {
  const updates = normalizeLiveUpdates([
    { id: 'old', at: '2026-08-27T07:00:00.000Z', headline: 'Open', html: '<p>Open</p>' },
    { id: 'new', at: '2026-08-27T08:00:00.000Z', title: 'Close', body: '<p>Close</p>' },
    { id: 'blank' },
  ]);
  assert.equal(updates.length, 2);
  assert.equal(updates[0].id, 'new');
  assert.equal(updates[0].headline, 'Close');
  assert.equal(updates[1].id, 'old');
});

test('latestLiveTimestamp uses the newest update, not the original publish time', () => {
  const article = {
    published_at: '2026-08-26T04:00:00.000Z',
    updated_at: '2026-08-27T06:00:00.000Z',
    live_updates: [
      { id: 'u1', at: '2026-08-27T09:15:00.000Z', html: '<p>Print</p>' },
    ],
  };
  assert.equal(latestLiveTimestamp(article), '2026-08-27T09:15:00.000Z');
});

test('plaintextToHtml escapes markup and splits paragraphs', () => {
  assert.equal(
    plaintextToHtml('Zinc jumped.\n\nSilver <held>.'),
    '<p>Zinc jumped.</p><p>Silver &lt;held&gt;.</p>'
  );
});

test('createLiveUpdate fills html from a plain body', () => {
  const update = createLiveUpdate({
    headline: 'RBI holds',
    body: 'Policy unchanged.',
    at: '2026-08-27T10:00:00.000Z',
    id: 'fixed',
  });
  assert.equal(update.id, 'fixed');
  assert.equal(update.headline, 'RBI holds');
  assert.equal(update.html, '<p>Policy unchanged.</p>');
  assert.equal(update.at, '2026-08-27T10:00:00.000Z');
});

test('formatLiveClock labels India time', () => {
  const clock = formatLiveClock('2026-08-27T07:30:00.000Z');
  assert.match(clock, /27 Aug/i);
  assert.match(clock, /IST/);
});

test('isMissingLiveColumnError detects schema drift', () => {
  assert.equal(isMissingLiveColumnError({ message: 'column articles.is_live does not exist' }), true);
  assert.equal(isMissingLiveColumnError({ message: 'permission denied' }), false);
});
