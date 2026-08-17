/**
 * Send the newest published CMS article to one email (signup / welcome drip).
 * Fire-and-forget safe: never throws to callers; logs and returns a result object.
 */
import {
  getLetter,
  letterDisplayFrom,
  letterKeyFromSection,
} from '../lib/agiLetters.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function siteUrl() {
  return (process.env.PUBLIC_SITE_URL || process.env.BASE_URL || 'https://agarwalglobalinvestments.com').replace(
    /\/$/,
    ''
  );
}

function logoUrl() {
  return `${siteUrl()}/agi-logo-email.png`;
}

function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function excerptFromHtml(html = '', maxChars = 280) {
  const txt = String(html)
    .replace(/<\/?[^>]+(>|$)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (txt.length <= maxChars) return txt;
  return `${txt.slice(0, maxChars).trim()}…`;
}

function articleHtml({ title, summary, slug, email, letter }) {
  const site = siteUrl();
  const url = `${site}/article/${encodeURIComponent(slug)}`;
  const unsub = `${site}/unsubscribe?email=${encodeURIComponent(email)}`;
  const logo = logoUrl();
  return `<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f5f7fa;font-family:Arial,sans-serif;color:#18202b;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f7fa;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" style="max-width:640px;background:#ffffff;border:1px solid #e6ebf2;">
        <tr>
          <td style="padding:20px 24px;border-bottom:1px solid #eef2f7;">
            <img src="${escapeHtml(logo)}" alt="AGI" width="120" style="display:block;border:0;" />
          </td>
        </tr>
        <tr>
          <td style="padding:24px;">
            <p style="margin:0 0 8px;font-size:12px;letter-spacing:0.08em;text-transform:uppercase;color:#7b8491;">
              ${escapeHtml(letter?.name || 'AGI Markets')}
            </p>
            <h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;color:#0d1d33;">
              ${escapeHtml(title)}
            </h1>
            <p style="margin:0 0 20px;font-size:15px;line-height:1.6;color:#3a4553;">
              ${escapeHtml(summary || '')}
            </p>
            <p style="margin:0 0 18px;">
              <a href="${escapeHtml(url)}" style="display:inline-block;background:#0d1d33;color:#ffffff;text-decoration:none;padding:12px 18px;font-size:14px;font-weight:700;">
                Read the brief
              </a>
            </p>
            <p style="margin:0;font-size:12px;line-height:1.6;color:#7b8491;">
              You received this because you joined AGI.
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

export async function fetchLatestPublishedArticle(admin) {
  const { data, error } = await admin
    .from('articles')
    .select('id, title, slug, excerpt, section, content, published_at')
    .eq('status', 'published')
    .order('published_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  return data || null;
}

/**
 * @param {object} opts
 * @param {string} opts.email
 * @param {import('@supabase/supabase-js').SupabaseClient} [opts.admin]
 * @returns {Promise<{ ok: boolean, skipped?: boolean, reason?: string, article?: { title: string, slug: string } }>}
 */
export async function sendLatestPublishedArticleEmail({ email, admin: adminArg } = {}) {
  const normalized = String(email || '').trim().toLowerCase();
  if (!EMAIL_RE.test(normalized)) {
    return { ok: false, skipped: true, reason: 'invalid_email' };
  }

  try {
    let admin = adminArg;
    if (!admin) {
      const { createSupabaseAdmin } = await import('../lib/supabaseAdmin.js');
      admin = createSupabaseAdmin();
    }
    if (!admin) {
      return { ok: false, skipped: true, reason: 'supabase_admin_missing' };
    }

    const article = await fetchLatestPublishedArticle(admin);
    if (!article?.slug || !article?.title) {
      return { ok: false, skipped: true, reason: 'no_published_article' };
    }

    const letterKey = letterKeyFromSection(article.section);
    const letter = getLetter(letterKey);
    const summary = String(
      article.excerpt || excerptFromHtml(article.content || '')
    ).trim();

    await sendWithResend({
      from: letterDisplayFrom(letter.key),
      to: normalized,
      subject: `${letter.name}: ${article.title}`,
      html: articleHtml({
        title: article.title,
        summary,
        slug: article.slug,
        email: normalized,
        letter,
      }),
    });

    return {
      ok: true,
      article: { title: article.title, slug: article.slug, letter: letter.key },
    };
  } catch (err) {
    console.error('[sendLatestPublishedArticleEmail]', err?.message || err);
    return {
      ok: false,
      skipped: true,
      reason: err?.code || err?.message || 'send_failed',
    };
  }
}

/** Non-blocking wrapper for signup / welcome paths. */
export function queueLatestPublishedArticleEmail(email, admin) {
  void sendLatestPublishedArticleEmail({ email, admin }).then((result) => {
    if (!result.ok) {
      console.warn('[signup-latest-article]', result.reason || 'skipped', email);
    } else {
      console.info('[signup-latest-article] sent', result.article?.slug, email);
    }
  });
}
