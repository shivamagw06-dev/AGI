/**
 * Ported from vitest to node:test.
 *
 * This file and three others imported vitest, which is not a dependency of
 * this repo and has no config in it. They could not run at all, and nothing
 * ran them: there was no npm test script, and the 138 other test files use
 * node:test. Ported rather than adding a runner, so one command runs the suite.
 */
import test, { describe, mock } from 'node:test';
import assert from 'node:assert/strict';
import {
  defaultLiveDeskBroadcasts,
  normalizeYoutubeVideoUrl,
  resolveYoutubeVideoUrl,
} from './liveDeskBroadcastService.js';

describe('live desk broadcast links', () => {
  test('normalizes supported YouTube watch and short links', () => {
    assert.equal(normalizeYoutubeVideoUrl('https://www.youtube.com/watch?v=QB5BNdBFujE'), 'QB5BNdBFujE');
    assert.equal(normalizeYoutubeVideoUrl('https://youtu.be/EN-N1xhtBqU'), 'EN-N1xhtBqU');
  });

  test('rejects non-YouTube and malformed links', () => {
    assert.throws(() => normalizeYoutubeVideoUrl('https://example.com/watch?v=QB5BNdBFujE'), /Only official/);
    assert.throws(() => normalizeYoutubeVideoUrl('https://www.youtube.com/watch?v=short'), /does not identify/);
  });

  test('resolves a channel live URL to the current video', async () => {
    const fetchImpl = mock.fn(async () => ({
      ok: true,
      url: 'https://www.youtube.com/watch?v=QB5BNdBFujE',
    }));
    const resolved = await resolveYoutubeVideoUrl('https://www.youtube.com/channel/UCIALMKvObZNtJ6AmdCLP7Lg/live', fetchImpl);
    assert.equal(resolved, 'QB5BNdBFujE');
    // Once, not merely at least once: resolving a live URL twice would mean
    // the channel is fetched again for a video it already found.
    assert.equal(fetchImpl.mock.callCount(), 1);
  });

  test('ships usable defaults for both desk slots', () => {
    assert.deepEqual(defaultLiveDeskBroadcasts().map((row) => row.id), ['global', 'india']);
    assert.equal(defaultLiveDeskBroadcasts().every((row) => row.embedUrl.includes('/embed/')), true);
  });
});
