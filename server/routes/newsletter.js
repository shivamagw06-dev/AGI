import { Router } from 'express';
import rateLimit from 'express-rate-limit';
import {
  getLetter,
  letterDisplayFrom,
  letterKeyFromSection,
  normalizePreferences,
  selectedLetterNames,
} from '../lib/agiLetters.js';
import { buildArticleEmail, excerptFromHtml } from '../lib/articleEmailTemplate.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const BLOCKED_TEST_DOMAINS = new Set(['example.com', 'example.org', 'example.net', 'test.com']);

function normalizeEmail(value) {
  return String(value || '').trim().toLowerCase();
}

function isSendableEmail(value) {
  const email = normalizeEmail(value);
  if (!EMAIL_RE.test(email)) return false;
  const domain = email.split('@')[1] || '';
  return !BLOCKED_TEST_DOMAINS.has(domain);
}

function siteUrl() {
  return (process.env.PUBLIC_SITE_URL || process.env.BASE_URL || 'https://agarwalglobalinvestments.com').replace(
    /\/$/,
    ''
  );
}

function logoUrl() {
  // Compact email asset at site root (also kept under /public for older deploys).
  return `${siteUrl()}/agi-logo-email.png`;
}

function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

async function getSupabaseAdmin() {
  const { createSupabaseAdmin } = await import('../lib/supabaseAdmin.js');
  const admin = createSupabaseAdmin();
  if (!admin) {
    const err = new Error('Supabase admin credentials unavailable.');
    err.code = 'SUPABASE_ADMIN_MISSING';
    throw err;
  }
  return admin;
}

async function sendWithResend(payload) {
  const key = (process.env.RESEND_API_KEY || '').trim();
  if (!key) {
    const err = new Error('RESEND_API_KEY is not configured.');
    err.code = 'RESEND_MISSING';
    throw err;
  }
  const resp = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  const text = await resp.text().catch(() => '');
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  if (!resp.ok) {
    const err = new Error(json?.message || text.slice(0, 200) || `Resend failed (${resp.status})`);
    err.status = resp.status;
    throw err;
  }
  return json;
}

async function sendBatchWithResend(items) {
  const key = (process.env.RESEND_API_KEY || '').trim();
  if (!key) {
    const err = new Error('RESEND_API_KEY is not configured.');
    err.code = 'RESEND_MISSING';
    throw err;
  }
  const resp = await fetch('https://api.resend.com/emails/batch', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${key}`,
      'Content-Type': 'application/json',
      'x-batch-validation': 'permissive',
    },
    body: JSON.stringify(items),
  });
  const text = await resp.text().catch(() => '');
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = null;
  }
  if (!resp.ok) {
    const err = new Error(json?.message || text.slice(0, 200) || `Resend batch failed (${resp.status})`);
    err.status = resp.status;
    throw err;
  }
  return json;
}

function welcomeHtml(email, preferences = {}) {
  const site = siteUrl();
  const unsub = `${site}/unsubscribe?email=${encodeURIComponent(email)}`;
  const logo = logoUrl();
  const names = selectedLetterNames(preferences);
  const list = names
    .map((name) => `<li style="margin:0 0 6px;">${escapeHtml(name)}</li>`)
    .join('');
  return `<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f7fa;font-family:Arial,sans-serif;color:#18202b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f7fa;padding:28px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:560px;background:#ffffff;border:1px solid #dce1e7;">
        <tr>
          <td style="background:#0d1d33;color:#ffffff;padding:22px 26px;">
            <img src="${escapeHtml(logo)}" alt="Agarwal Global Investments" width="72" height="64" style="display:block;width:72px;height:auto;border:0;" />
            <div style="margin-top:14px;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#d4af37;">Agarwal Global Investments</div>
            <div style="margin-top:8px;font-size:22px;font-weight:700;">Welcome to AGI Letters</div>
          </td>
        </tr>
        <tr>
          <td style="padding:26px;">
            <p style="margin:0 0 14px;font-size:15px;line-height:1.6;">Thanks for subscribing.</p>
            <p style="margin:0 0 10px;font-size:15px;line-height:1.6;color:#445066;">
              You are on:
            </p>
            <ul style="margin:0 0 18px;padding-left:18px;font-size:15px;line-height:1.6;color:#18202b;">
              ${list || '<li>AGI Markets</li>'}
            </ul>
            <p style="margin:0 0 18px;">
              <a href="${escapeHtml(site)}" style="display:inline-block;background:#0d1d33;color:#ffffff;text-decoration:none;padding:12px 18px;font-size:14px;font-weight:700;">
                Visit AGI
              </a>
            </p>
            <p style="margin:0;font-size:12px;line-height:1.6;color:#7b8491;">
              <a href="${escapeHtml(unsub)}" style="color:#274c77;">Unsubscribe</a>
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;
}

export default function createNewsletterRouter() {
  const router = Router();

  const notifyLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 20,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many newsletter notify requests. Try again later.' },
  });

  const welcomeLimiter = rateLimit({
    windowMs: 15 * 60 * 1000,
    max: 40,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: 'Too many welcome email requests. Try again later.' },
  });

  router.get('/health', (_req, res) => {
    res.json({
      ok: true,
      resend: Boolean((process.env.RESEND_API_KEY || '').trim()),
      letters: ['agi_markets', 'agi_morning_brief', 'agi_evening_brief', 'agi_macro'],
      supabaseAdmin: Boolean(
        (process.env.SUPABASE_URL || '').trim() &&
          (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim()
      ),
      testSend: true,
    });
  });

  router.get('/letters', (_req, res) => {
    res.json({
      ok: true,
      letters: [
        {
          key: 'agi_markets',
          name: 'AGI Markets',
          schedule: 'Flagship publication',
          tagline: 'Your market hub for equities, macro, commodities, FX and fixed income.',
        },
        {
          key: 'agi_morning_brief',
          name: 'AGI Morning Brief',
          schedule: '7:00–8:00 AM IST',
          tagline: 'Everything you need before the opening bell.',
        },
        {
          key: 'agi_evening_brief',
          name: 'AGI Evening Brief',
          schedule: '4:30–6:00 PM IST',
          tagline: 'What moved markets today—and why.',
        },
        {
          key: 'agi_macro',
          name: 'AGI Macro',
          schedule: 'Weekly or major events',
          tagline: 'Understanding the forces shaping global markets.',
        },
      ],
    });
  });

  router.post('/welcome', welcomeLimiter, async (req, res) => {
    try {
      const email = String(req.body?.email || '').trim().toLowerCase();
      const preferences = normalizePreferences(req.body?.preferences || null);
      if (!EMAIL_RE.test(email)) {
        return res.status(400).json({ error: 'Valid email is required.' });
      }

      await sendWithResend({
        from: letterDisplayFrom('agi_markets'),
        to: email,
        subject: 'Welcome to AGI Letters',
        html: welcomeHtml(email, preferences),
      });

      // Also send the latest published article (same drip as account signup).
      try {
        const { queueLatestPublishedArticleEmail } = await import(
          '../services/sendLatestArticleEmail.js'
        );
        queueLatestPublishedArticleEmail(email);
      } catch (queueErr) {
        console.warn('[newsletter/welcome] latest-article queue failed', queueErr?.message || queueErr);
      }

      return res.json({ ok: true, preferences });
    } catch (err) {
      console.error('[newsletter/welcome]', err?.message || err);
      if (err?.code === 'RESEND_MISSING') {
        return res.status(503).json({ ok: false, skipped: true, reason: err.message });
      }
      return res.status(500).json({ error: 'Failed to send welcome email.' });
    }
  });

  router.post('/notify-subscribers', notifyLimiter, async (req, res) => {
    try {
      const title = String(req.body?.title || '').trim();
      const slug = String(req.body?.slug || '').trim();
      const section = String(req.body?.section || '').trim();
      const letterKey =
        String(req.body?.newsletterKey || req.body?.letterKey || '').trim() ||
        letterKeyFromSection(section);
      const letter = getLetter(letterKey);
      const summary = String(
        req.body?.summary || req.body?.excerpt || excerptFromHtml(req.body?.body || '')
      ).trim();
      const coverUrl = String(req.body?.coverUrl || req.body?.cover_url || '').trim();
      const author = String(req.body?.author || '').trim();
      const publishedAt = req.body?.publishedAt || req.body?.published_at || new Date().toISOString();
      const words = excerptFromHtml(req.body?.body || '', 100000).split(/\s+/).filter(Boolean).length;
      const readTime = String(req.body?.readTime || req.body?.read_time || `${Math.max(1, Math.ceil(words / 220))} min read`);

      if (!title || !slug) {
        return res.status(400).json({ error: 'title and slug are required.' });
      }

      const testTo = normalizeEmail(req.body?.to || req.body?.testEmail || '');
      let recipients = [];

      if (testTo) {
        if (!isSendableEmail(testTo)) {
          return res.status(400).json({ error: 'Valid test recipient email is required.' });
        }
        recipients = [{ email: testTo, unsubscribeToken: null }];
      } else {
        const admin = await getSupabaseAdmin();
        let list = [];
        let queryError = null;

        const withPrefs = await admin.from('subscribers').select('email, preferences, unsubscribe_token').eq('is_active', true);
        if (withPrefs.error && /preferences|column/i.test(withPrefs.error.message || '')) {
          const fallback = await admin.from('subscribers').select('email').eq('is_active', true);
          list = fallback.data || [];
          queryError = fallback.error;
        } else {
          list = withPrefs.data || [];
          queryError = withPrefs.error;
        }
        if (queryError) throw queryError;

        recipients = (list || [])
          .map((row) => ({
            email: normalizeEmail(row.email),
            preferences: normalizePreferences(row.preferences),
            unsubscribeToken: row.unsubscribe_token || null,
          }))
          .filter((row) => isSendableEmail(row.email) && row.preferences[letter.key]);
      }

      if (!recipients.length) {
        return res.json({
          ok: true,
          sent: 0,
          skipped: true,
          letter: letter.key,
          reason: `No active subscribers for ${letter.name}.`,
        });
      }

      const from = letterDisplayFrom(letter.key);
      const items = recipients.map((row) => {
        const email = buildArticleEmail({
          title,
          summary,
          slug,
          email: row.email,
          letter,
          section,
          unsubscribeToken: row.unsubscribeToken,
          coverUrl,
          author,
          publishedAt,
          readTime,
        });
        return {
          from,
          to: [row.email],
          subject: email.subject,
          html: email.html,
          text: email.text,
        };
      });

      if (testTo || items.length === 1) {
        const item = items[0];
        await sendWithResend({
          from: item.from,
          to: item.to[0],
          subject: item.subject,
          html: item.html,
          text: item.text,
        });
        return res.json({
          ok: true,
          sent: 1,
          test: Boolean(testTo),
          to: item.to[0],
          from,
          letter: letter.key,
          section: section || null,
        });
      }

      let sent = 0;
      for (let i = 0; i < items.length; i += 50) {
        const chunk = items.slice(i, i + 50);
        await sendBatchWithResend(chunk);
        sent += chunk.length;
      }

      return res.json({ ok: true, sent, from, letter: letter.key, section: section || null });
    } catch (err) {
      console.error('[newsletter/notify-subscribers]', err?.message || err);
      if (err?.code === 'RESEND_MISSING' || err?.code === 'SUPABASE_ADMIN_MISSING') {
        return res.status(503).json({ ok: false, skipped: true, reason: err.message });
      }
      return res.status(500).json({ error: 'Failed to notify subscribers.' });
    }
  });

  return router;
}
