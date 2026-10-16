/**
 * Detect Hostinger deploy mismatch: fresh index.html + stale hashed chunks.
 * When /version.json disagrees with the bundled build id, force one reload.
 */

const LOCAL_BUILD_ID = String(
  (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_BUILD_ID) || ''
).trim();
const RELOAD_KEY = 'agi_build_reload_v1';
const CHUNK_RELOAD_KEY = 'agi_chunk_reload_v1';

export function getLocalBuildId() {
  return LOCAL_BUILD_ID;
}

export async function fetchRemoteBuildVersion() {
  const response = await fetch(`/version.json?t=${Date.now()}`, {
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) return null;
  const data = await response.json().catch(() => null);
  if (!data?.buildId) return null;
  return data;
}

/** Returns true if a reload was triggered. */
export async function checkBuildVersionAndReload() {
  if (!LOCAL_BUILD_ID || typeof window === 'undefined') return false;
  try {
    const remote = await fetchRemoteBuildVersion();
    if (!remote?.buildId || remote.buildId === LOCAL_BUILD_ID) return false;
    if (sessionStorage.getItem(RELOAD_KEY) === remote.buildId) return false;
    sessionStorage.setItem(RELOAD_KEY, remote.buildId);
    console.info(
      `[agi] build mismatch local=${LOCAL_BUILD_ID} remote=${remote.buildId} — reloading once`
    );
    window.location.reload();
    return true;
  } catch {
    return false;
  }
}

export function startBuildVersionWatcher({ intervalMs = 60_000 } = {}) {
  if (typeof window === 'undefined') return () => {};
  void checkBuildVersionAndReload();
  const id = window.setInterval(() => {
    void checkBuildVersionAndReload();
  }, intervalMs);
  return () => window.clearInterval(id);
}

/** One-shot recovery for Vite dynamic import / CSS preload failures after deploy. */
export function reloadOnceForChunkError(message = '') {
  if (typeof window === 'undefined') return false;
  const text = String(message || '');
  const isChunkError =
    /Failed to fetch dynamically imported module|Unable to preload CSS|Importing a module script failed|error loading dynamically imported module/i.test(
      text
    );
  if (!isChunkError) return false;
  const stamp = LOCAL_BUILD_ID || 'unknown';
  if (sessionStorage.getItem(CHUNK_RELOAD_KEY) === stamp) return false;
  sessionStorage.setItem(CHUNK_RELOAD_KEY, stamp);
  console.warn('[agi] chunk/CSS load failure after deploy — reloading once');
  window.location.reload();
  return true;
}
