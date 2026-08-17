/**
 * Send the newest published CMS article to one email (signup / welcome drip).
 * Fire-and-forget safe: never throws to callers; logs and returns a result object.
 */
import {
  getLetter,
  letterDisplayFrom,
  letterKeyFromSection,
} from '../lib/agiLetters.js';
import { buildArticleEmail, excerptFromHtml } from '../lib/articleEmailTemplate.js';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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
    const emailContent = buildArticleEmail({
      title: article.title,
      summary,
      slug: article.slug,
      email: normalized,
      letter,
      section: article.section,
      publishedAt: article.published_at,
    });

    await sendWithResend({
      from: letterDisplayFrom(letter.key),
      to: normalized,
      subject: emailContent.subject,
      html: emailContent.html,
      text: emailContent.text,
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
