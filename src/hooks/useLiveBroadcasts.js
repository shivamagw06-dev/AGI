import { useCallback, useEffect, useState } from 'react';
import apiFetch from '@/utils/apiFetch';
import { BROADCASTS } from '@/lib/liveDeskConfig';

const REFRESH_MS = 60_000;

function mergeOverrides(rows) {
  const overrides = new Map((Array.isArray(rows) ? rows : []).map((row) => [row?.id, row]));
  return BROADCASTS.map((broadcast) => {
    const override = overrides.get(broadcast.id);
    if (!override?.embedUrl || !override?.youtubeUrl) return broadcast;
    return {
      ...broadcast,
      embedUrl: override.embedUrl,
      externalUrl: override.youtubeUrl,
      updatedAt: override.updatedAt || null,
    };
  });
}

export default function useLiveBroadcasts() {
  const [broadcasts, setBroadcasts] = useState(BROADCASTS);

  const load = useCallback(async () => {
    try {
      const response = await apiFetch('/api/market/live-broadcasts', {
        headers: { Accept: 'application/json' },
        cache: 'no-store',
      });
      if (!response.ok) return;
      const payload = await response.json();
      if (payload?.ok) setBroadcasts(mergeOverrides(payload.broadcasts));
    } catch {
      // Compiled defaults keep both cards usable during backend outages.
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, REFRESH_MS);
    return () => clearInterval(timer);
  }, [load]);

  return broadcasts;
}
