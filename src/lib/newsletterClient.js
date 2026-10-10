import { API_ORIGIN } from '@/config';

function apiBase() {
  return String(API_ORIGIN || '').replace(/\/$/, '');
}

/** Best-effort welcome email after newsletter signup. */
export async function sendWelcomeEmail(email, preferences = null) {
  const value = String(email || '').trim();
  if (!value) return { ok: false, skipped: true };
  const base = apiBase();
  if (!base) return { ok: false, skipped: true, reason: 'API origin missing' };

  try {
    const resp = await fetch(`${base}/api/newsletter/welcome`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: value, preferences }),
    });
    const data = await resp.json().catch(() => ({}));
    return { ok: resp.ok, ...data };
  } catch (err) {
    return { ok: false, error: err?.message || 'welcome email failed' };
  }
}

/** Best-effort new-article blast to matching letter subscribers. */
export async function notifySubscribers({
  title,
  slug,
  summary,
  excerpt,
  body,
  section,
  newsletterKey,
  letterKey,
  coverUrl,
} = {}) {
  const base = apiBase();
  if (!base) return { ok: false, skipped: true, reason: 'API origin missing' };

  try {
    const resp = await fetch(`${base}/api/newsletter/notify-subscribers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        slug,
        summary,
        excerpt,
        body,
        section,
        newsletterKey,
        letterKey,
        coverUrl,
      }),
    });
    const data = await resp.json().catch(() => ({}));
    return { ok: resp.ok, ...data };
  } catch (err) {
    return { ok: false, error: err?.message || 'notify failed' };
  }
}
