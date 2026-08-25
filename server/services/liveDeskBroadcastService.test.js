import { describe, expect, it, vi } from 'vitest';
import {
  defaultLiveDeskBroadcasts,
  normalizeYoutubeVideoUrl,
  resolveYoutubeVideoUrl,
} from './liveDeskBroadcastService.js';

describe('live desk broadcast links', () => {
  it('normalizes supported YouTube watch and short links', () => {
    expect(normalizeYoutubeVideoUrl('https://www.youtube.com/watch?v=QB5BNdBFujE')).toBe('QB5BNdBFujE');
    expect(normalizeYoutubeVideoUrl('https://youtu.be/EN-N1xhtBqU')).toBe('EN-N1xhtBqU');
  });

  it('rejects non-YouTube and malformed links', () => {
    expect(() => normalizeYoutubeVideoUrl('https://example.com/watch?v=QB5BNdBFujE')).toThrow(/Only official/);
    expect(() => normalizeYoutubeVideoUrl('https://www.youtube.com/watch?v=short')).toThrow(/does not identify/);
  });

  it('resolves a channel live URL to the current video', async () => {
    const fetchImpl = vi.fn().mockResolvedValue({
      ok: true,
      url: 'https://www.youtube.com/watch?v=QB5BNdBFujE',
    });
    await expect(resolveYoutubeVideoUrl('https://www.youtube.com/channel/UCIALMKvObZNtJ6AmdCLP7Lg/live', fetchImpl)).resolves.toBe('QB5BNdBFujE');
    expect(fetchImpl).toHaveBeenCalledOnce();
  });

  it('ships usable defaults for both desk slots', () => {
    expect(defaultLiveDeskBroadcasts().map((row) => row.id)).toEqual(['global', 'india']);
    expect(defaultLiveDeskBroadcasts().every((row) => row.embedUrl.includes('/embed/'))).toBe(true);
  });
});
