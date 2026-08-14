import crypto from 'node:crypto';

const DEFAULT_ADMIN_EMAIL = 'shivam.agw06@gmail.com';

function bearer(req) {
  const value = String(req.get('authorization') || '');
  return value.startsWith('Bearer ') ? value.slice(7).trim() : '';
}

function allowedEmails() {
  return new Set(
    `${process.env.ADMIN_EMAILS || ''},${process.env.VITE_ADMIN_EMAILS || ''},${DEFAULT_ADMIN_EMAIL}`
      .split(',').map((value) => value.trim().toLowerCase()).filter(Boolean),
  );
}

export async function requireStrategyLabAdmin(req, res, next) {
  const token = bearer(req);
  const url = String(process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '').replace(/\/$/, '');
  const anonKey = String(process.env.SUPABASE_ANON_KEY || process.env.VITE_SUPABASE_ANON_KEY || '');
  if (!token || !url || !anonKey) {
    return res.status(401).json({ ok: false, error: 'ADMIN_AUTH_REQUIRED' });
  }
  try {
    const response = await fetch(`${url}/auth/v1/user`, {
      headers: { apikey: anonKey, Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(10_000),
    });
    if (!response.ok) return res.status(401).json({ ok: false, error: 'INVALID_ADMIN_SESSION' });
    const user = await response.json();
    const email = String(user?.email || '').toLowerCase();
    const configuredId = String(process.env.ADMIN_USER_ID || process.env.VITE_ADMIN_ID || '');
    const permitted = allowedEmails().has(email) || (configuredId && configuredId === user?.id);
    if (!permitted) return res.status(403).json({ ok: false, error: 'ADMIN_ONLY' });
    req.strategyLabActor = { id: user.id, email, auditHash: crypto.createHash('sha256').update(`${user.id}:${email}`).digest('hex').slice(0, 16) };
    return next();
  } catch (error) {
    return res.status(503).json({ ok: false, error: 'ADMIN_AUTH_UNAVAILABLE', detail: String(error?.message || error).slice(0, 120) });
  }
}
