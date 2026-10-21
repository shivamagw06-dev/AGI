/**
 * AGI PIN + trusted-device helpers.
 * PIN is never stored in plaintext — only salted hashes.
 */

const PIN_KEY = 'agi_pin_vault_v1';
const TRUST_KEY = 'agi_trusted_device_v1';
const UNLOCK_KEY = 'agi_session_unlocked_v1';
const LAST_EMAIL_KEY = 'agi_last_email_v1';

function toHex(buffer) {
  return [...new Uint8Array(buffer)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

function randomSalt(bytes = 16) {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return toHex(arr);
}

export async function hashPin(pin, salt) {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey('raw', enc.encode(String(pin)), 'PBKDF2', false, [
    'deriveBits',
  ]);
  const bits = await crypto.subtle.deriveBits(
    {
      name: 'PBKDF2',
      salt: enc.encode(String(salt)),
      iterations: 120_000,
      hash: 'SHA-256',
    },
    keyMaterial,
    256,
  );
  return toHex(bits);
}

export async function createPinRecord(pin) {
  const normalized = String(pin || '').replace(/\D/g, '');
  if (!/^\d{6}$/.test(normalized)) {
    throw new Error('PIN must be exactly 6 digits');
  }
  if (/^(\d)\1{5}$/.test(normalized) || normalized === '123456' || normalized === '000000') {
    throw new Error('Choose a stronger PIN (avoid repeats or sequences)');
  }
  const salt = randomSalt();
  const hash = await hashPin(normalized, salt);
  return { hash, salt, updated_at: new Date().toISOString() };
}

export async function verifyPinRecord(pin, record) {
  if (!record?.hash || !record?.salt) return false;
  const normalized = String(pin || '').replace(/\D/g, '');
  if (!/^\d{6}$/.test(normalized)) return false;
  const hash = await hashPin(normalized, record.salt);
  return hash === record.hash;
}

export function getDeviceId() {
  const key = 'agi_device_id_v1';
  let id = localStorage.getItem(key);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(key, id);
  }
  return id;
}

export function rememberEmail(email) {
  if (email) localStorage.setItem(LAST_EMAIL_KEY, String(email).trim().toLowerCase());
}

export function getRememberedEmail() {
  return localStorage.getItem(LAST_EMAIL_KEY) || '';
}

export function saveLocalPinVault(userId, record) {
  const vault = JSON.parse(localStorage.getItem(PIN_KEY) || '{}');
  vault[userId] = {
    hash: record.hash,
    salt: record.salt,
    updated_at: record.updated_at || new Date().toISOString(),
  };
  localStorage.setItem(PIN_KEY, JSON.stringify(vault));
}

export function getLocalPinVault(userId) {
  const vault = JSON.parse(localStorage.getItem(PIN_KEY) || '{}');
  return vault[userId] || null;
}

export function clearLocalPinVault(userId) {
  const vault = JSON.parse(localStorage.getItem(PIN_KEY) || '{}');
  delete vault[userId];
  localStorage.setItem(PIN_KEY, JSON.stringify(vault));
}

/** Trust this browser for N days (default 90). */
export function trustDevice(userId, email, days = 90) {
  const expiresAt = Date.now() + days * 24 * 60 * 60 * 1000;
  const payload = {
    userId,
    email: String(email || '').toLowerCase(),
    deviceId: getDeviceId(),
    trustedAt: new Date().toISOString(),
    expiresAt,
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent.slice(0, 180) : '',
    label: detectDeviceLabel(),
  };
  localStorage.setItem(TRUST_KEY, JSON.stringify(payload));
  return payload;
}

export function getTrustedDevice() {
  try {
    const raw = JSON.parse(localStorage.getItem(TRUST_KEY) || 'null');
    if (!raw?.userId || !raw?.expiresAt) return null;
    if (Date.now() > Number(raw.expiresAt)) {
      localStorage.removeItem(TRUST_KEY);
      return null;
    }
    if (raw.deviceId && raw.deviceId !== getDeviceId()) return null;
    return raw;
  } catch {
    return null;
  }
}

export function clearTrustedDevice() {
  localStorage.removeItem(TRUST_KEY);
}

export function setUnlocked(userId) {
  sessionStorage.setItem(UNLOCK_KEY, JSON.stringify({ userId, at: Date.now() }));
}

export function clearUnlocked() {
  sessionStorage.removeItem(UNLOCK_KEY);
}

export function isUnlocked(userId) {
  try {
    const raw = JSON.parse(sessionStorage.getItem(UNLOCK_KEY) || 'null');
    return Boolean(raw && raw.userId === userId);
  } catch {
    return false;
  }
}

function detectDeviceLabel() {
  if (typeof navigator === 'undefined') return 'Browser';
  const ua = navigator.userAgent;
  let browser = 'Browser';
  if (ua.includes('Edg/')) browser = 'Edge';
  else if (ua.includes('Chrome/')) browser = 'Chrome';
  else if (ua.includes('Safari/') && !ua.includes('Chrome')) browser = 'Safari';
  else if (ua.includes('Firefox/')) browser = 'Firefox';

  let os = 'Device';
  if (ua.includes('Mac')) os = 'Mac';
  else if (ua.includes('Windows')) os = 'Windows';
  else if (ua.includes('iPhone')) os = 'iPhone';
  else if (ua.includes('Android')) os = 'Android';
  else if (ua.includes('Linux')) os = 'Linux';

  return `${os} · ${browser}`;
}

export function listLocalDevices(userId) {
  const trusted = getTrustedDevice();
  if (!trusted || trusted.userId !== userId) return [];
  return [
    {
      id: trusted.deviceId,
      label: trusted.label || 'This browser',
      last_active: trusted.trustedAt,
      current: true,
      expires_at: new Date(trusted.expiresAt).toISOString(),
    },
  ];
}
