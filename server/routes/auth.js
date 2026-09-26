import { Router } from 'express';
import rateLimit from 'express-rate-limit';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function brandedEmailShell({ title, greeting, bodyHtml, ctaLabel, actionLink, siteUrl }) {
  const name = escapeHtml(greeting || 'Investor');
  const link = escapeHtml(actionLink);
  const site = escapeHtml(siteUrl);
  const heading = escapeHtml(title);
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
              <div style="margin-top:10px;font-size:24px;font-weight:700;">${heading}</div>
            </td>
          </tr>
          <tr>
            <td style="padding:28px;">
              <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">Hello ${name},</p>
              ${bodyHtml}
              <p style="margin:0 0 24px;">
                <a href="${link}" style="display:inline-block;background:#0d1d33;color:#ffffff;text-decoration:none;padding:12px 18px;font-size:14px;font-weight:700;">
                  ${escapeHtml(ctaLabel)}
                </a>
              </p>
              <p style="margin:0 0 10px;font-size:13px;line-height:1.6;color:#667085;">
                If the button does not work, copy and paste this link into your browser:
              </p>
              <p style="margin:0 0 18px;font-size:12px;word-break:break-all;color:#274c77;">${link}</p>
              <p style="margin:0;font-size:12px;line-height:1.6;color:#7b8491;">
                This link expires for your security. If you did not request this, you can ignore this email.
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

function brandedVerificationHtml({ fullName, actionLink, siteUrl }) {
  return brandedEmailShell({
    title: 'Verify your AGI account',
    greeting: fullName || 'Investor',
    bodyHtml: `<p style="margin:0 0 18px;font-size:15px;line-height:1.6;color:#445066;">
                Welcome to Agarwal Global Investments. Confirm your email to activate your secure research account.
              </p>`,
    ctaLabel: 'Verify email address',
    actionLink,
    siteUrl,
  });
}

function brandedResetHtml({ fullName, actionLink, siteUrl }) {
  return brandedEmailShell({
    title: 'Reset your AGI password',
    greeting: fullName || 'Investor',
    bodyHtml: `<p style="margin:0 0 18px;font-size:15px;line-height:1.6;color:#445066;">
                We received a request to reset the password for your Agarwal Global Investments account.
              </p>`,
    ctaLabel: 'Reset password',
    actionLink,
    siteUrl,
  });
}

function isStrongPassword(password = '') {
  const value = String(password);
  return (
    value.length >= 8 &&
    /[A-Z]/.test(value) &&
    /[a-z]/.test(value) &&
    /\d/.test(value)
  );
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

async function generateActionLink(admin, email, redirectTo, preferredTypes = null) {
  // Prefer magiclink first for existing users — avoids insert paths when possible.
  // After admin.createUser, prefer signup then magiclink.
  const types = preferredTypes || ['magiclink', 'recovery', 'signup'];
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

async function sendBrandedAuthEmail({
  admin,
  email,
  fullName,
  redirectTo,
  siteUrl,
  subject,
  htmlBuilder,
  preferredTypes,
}) {
  const { actionLink, type } = await generateActionLink(
    admin,
    email,
    redirectTo || `${siteUrl}/verify-email`,
    preferredTypes
  );
  const sent = await sendEmail({
    to: email,
    subject,
    html: htmlBuilder({ fullName, actionLink, siteUrl }),
  });
  return { ...sent, linkType: type, actionLink };
}

export default function createAuthRouter() {
  const router = Router();

  const authLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 20,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many auth email requests. Try again later.' },
  });

  router.post('/send-verification', authLimiter, async (req, res) => {
    try {
      const email = String(req.body?.email || '').trim().toLowerCase();
      const fullName = String(req.body?.fullName || '').trim();
      const redirectTo = String(req.body?.redirectTo || '').trim();
      const siteUrl = (process.env.PUBLIC_SITE_URL || 'https://agarwalglobalinvestments.com').replace(
        /\/$/,
        ''
      );

      if (!EMAIL_RE.test(email)) {
        return res.status(400).json({ error: 'Valid email is required.' });
      }

      const { createSupabaseAdmin } = await import('../lib/supabaseAdmin.js');
      const admin = createSupabaseAdmin();
      if (!admin) {
        return res.status(503).json({
          ok: false,
          skipped: true,
          reason: 'Supabase admin credentials unavailable; relying on default Auth email.',
        });
      }

      try {
        const sent = await sendBrandedAuthEmail({
          admin,
          email,
          fullName,
          redirectTo: redirectTo || `${siteUrl}/verify-email`,
          siteUrl,
          subject: 'Verify your Agarwal Global Investments account',
          htmlBuilder: brandedVerificationHtml,
          preferredTypes: ['magiclink', 'signup', 'recovery'],
        });
        return res.json({
          ok: true,
          provider: sent.provider,
          from: sent.from,
          linkType: sent.linkType,
        });
      } catch (mailErr) {
        if (mailErr?.code === 'EMAIL_PROVIDER_MISSING') {
          return res.status(503).json({
            ok: false,
            skipped: true,
            reason: mailErr.message,
            note: 'Configure RESEND_API_KEY on Render, and/or Supabase custom SMTP.',
          });
        }
        return res.status(502).json({
          error: 'Email provider rejected the message.',
          detail: mailErr?.message || String(mailErr),
        });
      }
    } catch (err) {
      console.error('[auth/send-verification]', err?.message || err);
      return res.status(500).json({
        error: 'Failed to send verification email.',
        detail: err?.message || String(err),
      });
    }
  });

  /**
   * Create account via service role (bypasses broken Supabase SMTP on /auth/v1/signup),
   * then send AGI branded verification email through Resend/SendGrid.
   */
  router.post('/signup', authLimiter, async (req, res) => {
    try {
      const email = String(req.body?.email || '').trim().toLowerCase();
      const password = String(req.body?.password || '');
      const fullName = String(req.body?.fullName || '').trim();
      const mobile = String(req.body?.mobile || '').trim();
      const redirectTo = String(req.body?.redirectTo || '').trim();
      const siteUrl = (process.env.PUBLIC_SITE_URL || 'https://agarwalglobalinvestments.com').replace(
        /\/$/,
        ''
      );

      if (!EMAIL_RE.test(email)) {
        return res.status(400).json({ error: 'Valid email is required.' });
      }
      if (!fullName || fullName.length < 2) {
        return res.status(400).json({ error: 'Enter your full name.' });
      }
      if (!isStrongPassword(password)) {
        return res.status(400).json({
          error: 'Use 8+ characters with upper, lower, and a number.',
        });
      }

      const { createSupabaseAdmin } = await import('../lib/supabaseAdmin.js');
      const admin = createSupabaseAdmin();
      if (!admin) {
        return res.status(503).json({
          error: 'Authentication service is not configured on the API.',
          detail: 'Missing SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY.',
        });
      }

      let created = false;
      let user = null;
      const { data: createdData, error: createError } = await admin.auth.admin.createUser({
        email,
        password,
        email_confirm: false,
        user_metadata: {
          full_name: fullName,
          mobile: mobile || null,
          onboarding_complete: false,
        },
      });

      if (createError) {
        const msg = String(createError.message || '');
        const already =
          /already|registered|exists/i.test(msg) || createError.status === 422;
        if (!already) {
          console.error('[auth/signup] createUser', createError);
          return res.status(400).json({
            error: 'Unable to create your account.',
            detail: msg,
          });
        }
        // Existing account: still send verification so the user can finish setup.
        try {
          const existing = await admin.auth.admin.getUserByEmail(email);
          user = existing?.data?.user || null;
        } catch {
          user = null;
        }
      } else {
        created = true;
        user = createdData?.user || null;
      }

      try {
        const sent = await sendBrandedAuthEmail({
          admin,
          email,
          fullName,
          redirectTo: redirectTo || `${siteUrl}/verify-email`,
          siteUrl,
          subject: 'Verify your Agarwal Global Investments account',
          htmlBuilder: brandedVerificationHtml,
          preferredTypes: created
            ? ['signup', 'magiclink', 'recovery']
            : ['magiclink', 'signup', 'recovery'],
        });
        // New accounts are auto-added to subscribers by DB trigger; also send
        // the latest published article so they see your research immediately.
        if (created) {
          try {
            const { queueLatestPublishedArticleEmail } = await import(
              '../services/sendLatestArticleEmail.js'
            );
            queueLatestPublishedArticleEmail(email, admin);
          } catch (queueErr) {
            console.warn('[auth/signup] latest-article queue failed', queueErr?.message || queueErr);
          }
        }
        return res.status(created ? 201 : 200).json({
          ok: true,
          created,
          alreadyExists: !created,
          email,
          userId: user?.id || null,
          provider: sent.provider,
          from: sent.from,
          linkType: sent.linkType,
          message: created
            ? 'Account created. Check your email to verify, then sign in.'
            : 'An account with this email already exists. We sent a verification link if the address is registered.',
        });
      } catch (mailErr) {
        if (created) {
          try {
            const { queueLatestPublishedArticleEmail } = await import(
              '../services/sendLatestArticleEmail.js'
            );
            queueLatestPublishedArticleEmail(email, admin);
          } catch (queueErr) {
            console.warn('[auth/signup] latest-article queue failed', queueErr?.message || queueErr);
          }
          return res.status(201).json({
            ok: true,
            created: true,
            email,
            userId: user?.id || null,
            emailDelivery: 'failed',
            message:
              'Account created, but the verification email could not be sent. Use Resend verification on the login page.',
            detail: mailErr?.message || String(mailErr),
          });
        }
        return res.status(502).json({
          error: 'Unable to send verification email.',
          detail: mailErr?.message || String(mailErr),
        });
      }
    } catch (err) {
      console.error('[auth/signup]', err?.message || err);
      return res.status(500).json({
        error: 'Failed to create account.',
        detail: err?.message || String(err),
      });
    }
  });

  router.post('/send-password-reset', authLimiter, async (req, res) => {
    try {
      const email = String(req.body?.email || '').trim().toLowerCase();
      const redirectTo = String(req.body?.redirectTo || '').trim();
      const siteUrl = (process.env.PUBLIC_SITE_URL || 'https://agarwalglobalinvestments.com').replace(
        /\/$/,
        ''
      );

      if (!EMAIL_RE.test(email)) {
        return res.status(400).json({ error: 'Valid email is required.' });
      }

      const { createSupabaseAdmin } = await import('../lib/supabaseAdmin.js');
      const admin = createSupabaseAdmin();
      if (!admin) {
        return res.status(503).json({
          ok: false,
          skipped: true,
          reason: 'Supabase admin credentials unavailable.',
        });
      }

      // Always return a generic success to avoid email enumeration, after attempting send.
      try {
        const sent = await sendBrandedAuthEmail({
          admin,
          email,
          fullName: '',
          redirectTo: redirectTo || `${siteUrl}/reset-password`,
          siteUrl,
          subject: 'Reset your Agarwal Global Investments password',
          htmlBuilder: brandedResetHtml,
          preferredTypes: ['recovery'],
        });
        return res.json({
          ok: true,
          provider: sent.provider,
          from: sent.from,
          linkType: sent.linkType,
        });
      } catch (mailErr) {
        // Do not reveal whether the account exists.
        console.warn('[auth/send-password-reset]', mailErr?.message || mailErr);
        return res.json({
          ok: true,
          provider: 'none',
          message: 'If an account exists for that email, a reset link will arrive shortly.',
        });
      }
    } catch (err) {
      console.error('[auth/send-password-reset]', err?.message || err);
      return res.status(500).json({
        error: 'Failed to process password reset.',
        detail: err?.message || String(err),
      });
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
      routes: ['signup', 'send-verification', 'send-password-reset', 'health'],
    });
  });

  return router;
}
