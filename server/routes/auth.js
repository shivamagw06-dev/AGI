import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import { safeVerificationRedirect } from '../lib/authRedirect.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const GENERIC_VERIFICATION_RESPONSE = {
  ok: true,
  message: 'If an account needs verification, an email will arrive shortly.',
};

function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function brandedVerificationHtml({ fullName, actionLink, siteUrl }) {
  const name = escapeHtml(fullName || 'Investor');
  const link = escapeHtml(actionLink);
  const site = escapeHtml(siteUrl);
  // Prefer compact email asset; fall back to full logo. Root paths work on Hostinger.
  const logo = `${siteUrl.replace(/\/$/, '')}/agi-logo-email.png`;
  return `<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f7fa;font-family:Arial,sans-serif;color:#18202b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f7fa;padding:32px 12px;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border:1px solid #dce1e7;">
          <tr>
            <td style="background:#0d1d33;color:#ffffff;padding:24px 28px;">
              <img src="${escapeHtml(logo)}" alt="Agarwal Global Investments" width="72" height="64" style="display:block;width:72px;height:auto;border:0;" />
              <div style="margin-top:14px;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#d4af37;">Agarwal Global Investments</div>
              <div style="margin-top:10px;font-size:24px;font-weight:700;">Verify your AGI account</div>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;">
              <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">Hello ${name},</p>
              <p style="margin:0 0 18px;font-size:15px;line-height:1.6;color:#445066;">
                Welcome to Agarwal Global Investments. Confirm your email to activate your secure research account.
              </p>
              <p style="margin:0 0 24px;">
                <a href="${link}" style="display:inline-block;background:#0d1d33;color:#ffffff;text-decoration:none;padding:12px 18px;font-size:14px;font-weight:700;">
                  Verify email address
                </a>
              </p>
              <p style="margin:0 0 10px;font-size:13px;line-height:1.6;color:#667085;">
                If the button does not work, copy and paste this link into your browser:
              </p>
              <p style="margin:0 0 18px;font-size:12px;word-break:break-all;color:#274c77;">${link}</p>
              <p style="margin:0;font-size:12px;line-height:1.6;color:#7b8491;">
                This link expires for your security. If you did not create an AGI account, you can ignore this email.
              </p>
            </td>
          </tr>
          <tr>
            <td style="border-top:1px solid #e8edf2;padding:16px 28px;font-size:11px;color:#7b8491;">
              Support: support@agarwalglobalinvestments.com · <a href="${site}" style="color:#274c77;">${site}</a>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>`;
}

function fromCandidates() {
  const configured = [
    process.env.FROM_EMAIL,
    process.env.AUTH_FROM_EMAIL,
    'Agarwal Global Investments <support@agarwalglobalinvestments.com>',
    'AGI Updates <updates@agarwalglobalinvestments.com>',
  ]
    .map((v) => String(v || '').trim())
    .filter(Boolean);
  return [...new Set(configured)];
}

async function sendWithResend({ to, subject, html, from }) {
  const resendKey = (process.env.RESEND_API_KEY || '').trim();
  if (!resendKey) return null;
  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${resendKey}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ from, to, subject, html }),
  });
  const body = await resp.text().catch(() => '');
  if (!resp.ok) {
    const err = new Error(`Resend failed (${resp.status}): ${body.slice(0, 240)}`);
    err.code = 'RESEND_FAILED';
    err.status = resp.status;
    throw err;
  }
  return { provider: 'resend', from };
}

async function sendEmail({ to, subject, html }) {
  const sendgridKey = (process.env.SENDGRID_API_KEY || '').trim();
  if (sendgridKey) {
    const from = fromCandidates()[0];
    const sgMail = (await import('@sendgrid/mail')).default;
    sgMail.setApiKey(sendgridKey);
    await sgMail.send({ to, from, subject, html });
    return { provider: 'sendgrid', from };
  }

  const resendKey = (process.env.RESEND_API_KEY || '').trim();
  if (resendKey) {
    let lastErr = null;
    for (const from of fromCandidates()) {
      try {
        return await sendWithResend({ to, subject, html, from });
      } catch (err) {
        lastErr = err;
        // Try next from-address if domain/sender rejected.
        if (!/resend failed|from|domain|sender/i.test(err?.message || '')) throw err;
      }
    }
    throw lastErr || new Error('Resend send failed.');
  }

  const err = new Error('No email provider configured (SENDGRID_API_KEY or RESEND_API_KEY).');
  err.code = 'EMAIL_PROVIDER_MISSING';
  throw err;
}

async function generateActionLink(admin, email, redirectTo) {
  // Prefer magiclink first — works for existing users without inserting auth.users.
  // `signup` / `invite` create users and currently fail when the profiles trigger is broken.
  const types = ['magiclink', 'recovery', 'signup'];
  let lastError = null;

  for (const type of types) {
    const { data, error } = await admin.auth.admin.generateLink({
      type,
      email,
      options: { redirectTo },
    });
    if (error) {
      lastError = error;
      continue;
    }
    const actionLink = data?.properties?.action_link || data?.action_link || null;
    if (actionLink) return { actionLink, type };
  }

  const err = new Error(lastError?.message || 'Unable to generate verification link.');
  err.code = 'LINK_GENERATION_FAILED';
  throw err;
}

export default function createAuthRouter() {
  const router = Router();

  const authLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 8,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many attempts. Wait a few minutes before trying again.' },
  });
  const emailLimiter = rateLimit({
    windowMs: 30 * 60 * 1000,
    max: 3,
    keyGenerator: (req) => String(req.body?.email || '').trim().toLowerCase() || 'missing-email',
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many attempts. Wait a few minutes before trying again.' },
  });

  router.post('/send-verification', authLimiter, emailLimiter, async (req, res) => {
    try {
      const email = String(req.body?.email || '').trim().toLowerCase();
      const redirectTo = String(req.body?.redirectTo || '').trim();
      const siteUrl = (process.env.PUBLIC_SITE_URL || 'https://agarwalglobalinvestments.com').replace(/\/$/, '');

      if (!EMAIL_RE.test(email)) {
        return res.status(400).json({ error: 'Valid email is required.' });
      }

      const { createSupabaseAdmin } = await import('../lib/supabaseAdmin.js');
      const admin = createSupabaseAdmin();
      if (!admin) {
        console.error('[auth/send-verification] Supabase admin credentials unavailable');
        return res.status(202).json(GENERIC_VERIFICATION_RESPONSE);
      }

      const { error } = await admin.auth.resend({
        type: 'signup',
        email,
        options: { emailRedirectTo: safeVerificationRedirect(redirectTo, siteUrl) },
      });
      if (error) {
        console.warn('[auth/send-verification] Supabase resend rejected', error.message);
      }
      return res.status(202).json(GENERIC_VERIFICATION_RESPONSE);
    } catch (err) {
      console.error('[auth/send-verification]', err?.message || err);
      return res.status(202).json(GENERIC_VERIFICATION_RESPONSE);
    }
  });

  router.get('/health', (_req, res) => {
    res.json({
      ok: true,
      sendgrid: Boolean((process.env.SENDGRID_API_KEY || '').trim()),
      resend: Boolean((process.env.RESEND_API_KEY || '').trim()),
      fromCandidates: fromCandidates(),
      supabaseAdmin: Boolean(
        (process.env.SUPABASE_URL || '').trim() &&
          (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim()
      ),
    });
  });

  return router;
}
