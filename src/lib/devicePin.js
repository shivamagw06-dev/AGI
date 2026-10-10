/**
 * Device PIN unlock for an already-authenticated Supabase session.
 * PIN never replaces password auth; it only gates a trusted browser session.
 */

const STORAGE_PREFIX = 'agi.devicePin.v1';
const UNLOCK_PREFIX = 'agi.pinUnlocked.v1';

function storageKey(userId) {
  return `${STORAGE_PREFIX}:${userId}`;
}

function unlockKey(userId) {
  return `${UNLOCK_PREFIX}:${userId}`;
}

async function sha256Hex(value) {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function randomSalt() {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return [...bytes].map((b) => b.toString(16).padStart(2, '0')).join('');
}

export function isValidPin(pin, { length = 4 } = {}) {
  return new RegExp(`^\\d{${length}}$`).test(String(pin || ''));
}

export function getPinConfig(userId) {
  if (!userId || typeof localStorage === 'undefined') return null;
  try {
    const raw = localStorage.getItem(storageKey(userId));
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function hasPin(userId) {
  const cfg = getPinConfig(userId);
  return Boolean(cfg?.hash && cfg?.salt);
}

export function isPinUnlocked(userId) {
  if (!userId || typeof sessionStorage === 'undefined') return false;
  return sessionStorage.getItem(unlockKey(userId)) === '1';
}

export function markPinUnlocked(userId) {
  if (!userId || typeof sessionStorage === 'undefined') return;
  sessionStorage.setItem(unlockKey(userId), '1');
}

export function clearPinUnlock(userId) {
  if (!userId || typeof sessionStorage === 'undefined') return;
  sessionStorage.removeItem(unlockKey(userId));
}

export async function setDevicePin(userId, pin, { length = 4 } = {}) {
  if (!userId) throw new Error('Missing user');
  if (!isValidPin(pin, { length })) throw new Error(`PIN must be ${length} digits`);
  const salt = randomSalt();
  const hash = await sha256Hex(`${salt}:${pin}:${userId}`);
  const payload = {
    salt,
    hash,
    length,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  localStorage.setItem(storageKey(userId), JSON.stringify(payload));
  markPinUnlocked(userId);
  return payload;
}

export async function verifyDevicePin(userId, pin) {
  const cfg = getPinConfig(userId);
  if (!cfg?.hash || !cfg?.salt) return false;
  const hash = await sha256Hex(`${cfg.salt}:${pin}:${userId}`);
  const ok = hash === cfg.hash;
  if (ok) markPinUnlocked(userId);
  return ok;
}

export function disableDevicePin(userId) {
  if (!userId || typeof localStorage === 'undefined') return;
  localStorage.removeItem(storageKey(userId));
  clearPinUnlock(userId);
}

export function shouldChallengePin(user) {
  if (!user?.id) return false;
  if (!hasPin(user.id)) return false;
  if (isPinUnlocked(user.id)) return false;
  return true;
}
