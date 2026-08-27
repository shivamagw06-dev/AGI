/**
 * Email provider abstraction — Resend preferred.
 * Postmark / Brevo / SES can be added without changing business logic.
 */

function providerName() {
  return (process.env.EMAIL_PROVIDER || 'resend').toLowerCase();
}

export function getEmailFrom() {
  return (
    process.env.NEWSLETTER_FROM_EMAIL ||
    process.env.FROM_EMAIL ||
    'AGI Research <updates@agarwalglobalinvestments.com>'
  );
}

async function sendViaResend({ to, subject, html, text, tags }) {
  const apiKey = process.env.RESEND_API_KEY || process.env.re_RESEND_API_KEY;
  if (!apiKey) {
    return { ok: false, provider: 'resend', error: 'RESEND_API_KEY missing', dryRun: true };
  }
  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      from: getEmailFrom(),
      to: Array.isArray(to) ? to : [to],
      subject,
      html,
      text,
      tags,
    }),
  });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    return { ok: false, provider: 'resend', error: body?.message || `HTTP ${resp.status}`, body };
  }
  return { ok: true, provider: 'resend', id: body.id, body };
}

async function sendViaStub({ to, subject }) {
  return {
    ok: true,
    provider: 'stub',
    dryRun: true,
    id: `stub_${Date.now()}`,
    to,
    subject,
  };
}

/**
 * Send one email. Returns { ok, provider, id?, error?, dryRun? }
 */
export async function sendEmail(message) {
  const name = providerName();
  if (name === 'stub' || process.env.NEWSLETTER_DRY_RUN === '1') {
    return sendViaStub(message);
  }
  if (name === 'resend') {
    const result = await sendViaResend(message);
    if (result.dryRun || (!result.ok && result.error?.includes('missing'))) {
      return sendViaStub(message);
    }
    return result;
  }
  // Future: postmark | brevo | ses
  return sendViaStub({ ...message, note: `Provider ${name} not implemented — stubbed` });
}

export async function sendBulk(messages, { concurrency = 5 } = {}) {
  const results = [];
  for (let i = 0; i < messages.length; i += concurrency) {
    const chunk = messages.slice(i, i + concurrency);
    const part = await Promise.all(chunk.map((m) => sendEmail(m)));
    results.push(...part);
  }
  return results;
}
