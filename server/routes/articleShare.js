import { Router } from 'express';
import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import {
  buildArticleShareMeta,
  injectShareMetaIntoHtml,
  sanitizeArticleSlug,
  siteUrlFromEnv,
} from '../../src/lib/articleShareMeta.js';

const ARTICLE_SELECT = 'id, title, slug, excerpt, cover_url, content, published_at, status';

function supabaseRestConfig() {
  const supabaseUrl = String(process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '')
    .trim()
    .replace(/\/$/, '');
  const key = String(
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.VITE_SUPABASE_ANON_KEY || ''
  ).trim();
  if (!supabaseUrl || !key) return null;
  return { supabaseUrl, key };
}

async function fetchPublishedArticle(slug) {
  const admin = createSupabaseAdmin();
  if (admin) {
    const { data, error } = await admin
      .from('articles')
      .select(ARTICLE_SELECT)
      .eq('slug', slug)
      .eq('status', 'published')
      .maybeSingle();
    if (error) throw error;
    return data || null;
  }

  const rest = supabaseRestConfig();
  if (!rest) return null;
  const url = `${rest.supabaseUrl}/rest/v1/articles?select=${encodeURIComponent(ARTICLE_SELECT)}&slug=eq.${encodeURIComponent(slug)}&status=eq.published&limit=1`;
  const response = await fetch(url, {
    headers: {
      apikey: rest.key,
      Authorization: `Bearer ${rest.key}`,
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    const err = new Error(detail.slice(0, 180) || `Supabase article lookup failed (${response.status})`);
    err.status = response.status;
    throw err;
  }
  const rows = await response.json();
  return Array.isArray(rows) && rows[0] ? rows[0] : null;
}

export function articleToSharePayload(article, { site } = {}) {
  return buildArticleShareMeta(article, { site: site || siteUrlFromEnv() });
}

export default function createArticleShareRouter() {
  const router = Router();

  router.get('/article-share/:slug', async (req, res) => {
    const slug = sanitizeArticleSlug(req.params.slug);
    if (!slug) return res.status(400).json({ error: 'Invalid article slug' });
    try {
      const article = await fetchPublishedArticle(slug);
      if (!article) return res.status(404).json({ error: 'Article not found' });
      const meta = articleToSharePayload(article);
      res.set('Cache-Control', 'public, max-age=120, s-maxage=300');
      return res.json(meta);
    } catch (error) {
      return res.status(error.status && error.status < 500 ? error.status : 503).json({
        error: 'Article share metadata unavailable',
        detail: error.message,
      });
    }
  });

  router.get('/article-share/:slug/html', async (req, res) => {
    const slug = sanitizeArticleSlug(req.params.slug);
    if (!slug) return res.status(400).type('html').send('Invalid article');
    try {
      const article = await fetchPublishedArticle(slug);
      const meta = articleToSharePayload(
        article || { title: 'AGI — Agarwal Global Investments', slug: '' }
      );
      const shell = `<!doctype html><html lang="en"><head><meta charset="UTF-8" /><title></title></head><body></body></html>`;
      res.set('Cache-Control', 'public, max-age=120, s-maxage=300');
      res.type('html').send(injectShareMetaIntoHtml(shell, meta));
    } catch (error) {
      return res.status(503).type('html').send('Share preview unavailable');
    }
  });

  return router;
}
