#!/usr/bin/env node
/**
 * Writes crawler-visible /article/{slug}/index.html shells so LinkedIn,
 * WhatsApp and X see the cover photo without executing React.
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { firstImageUrlFromHtml, usableCoverUrl } from '../server/lib/articleEmailTemplate.js';
import {
  buildArticleShareMeta,
  injectShareMetaIntoHtml,
  sanitizeArticleSlug,
  siteUrlFromEnv,
} from '../src/lib/articleShareMeta.js';
import { loadHostingerEnv } from './loadHostingerEnv.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
loadHostingerEnv(root);
const SELECT = 'title,slug,excerpt,cover_url,content,published_at';

function readShell() {
  for (const candidate of ['dist/index.html', 'index.html']) {
    const file = path.join(root, candidate);
    if (fs.existsSync(file)) return fs.readFileSync(file, 'utf8');
  }
  return '';
}

async function fetchPublishedArticles() {
  const supabaseUrl = String(process.env.SUPABASE_URL || process.env.VITE_SUPABASE_URL || '')
    .trim()
    .replace(/\/$/, '');
  const key = String(
    process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.VITE_SUPABASE_ANON_KEY || ''
  ).trim();
  if (!supabaseUrl || !key) {
    console.warn('prerender-article-og: missing Supabase credentials; skipping.');
    return [];
  }
  const rows = [];
  const pageSize = 200;
  for (let from = 0; from < 2000; from += pageSize) {
    const to = from + pageSize - 1;
    const url = `${supabaseUrl}/rest/v1/articles?select=${encodeURIComponent(SELECT)}&status=eq.published&slug=not.is.null&order=published_at.desc`;
    const response = await fetch(url, {
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        Accept: 'application/json',
        Range: `${from}-${to}`,
        Prefer: 'count=exact',
      },
    });
    if (!response.ok) {
      throw new Error(`Supabase ${response.status}: ${(await response.text()).slice(0, 180)}`);
    }
    const batch = await response.json();
    if (!Array.isArray(batch) || batch.length === 0) break;
    rows.push(...batch);
    if (batch.length < pageSize) break;
  }
  return rows;
}

function writeShell(slug, html) {
  const rel = path.join('article', slug, 'index.html');
  for (const base of [path.join(root, 'dist'), root]) {
    const dest = path.join(base, rel);
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.writeFileSync(dest, html);
  }
}

const shell = readShell();
if (!shell.includes('<div id="root"')) {
  console.warn('prerender-article-og: SPA shell missing; skipping.');
  process.exit(0);
}

let articles = [];
try {
  articles = await fetchPublishedArticles();
} catch (error) {
  console.warn(`prerender-article-og: ${error.message}`);
  process.exit(0);
}

const site = siteUrlFromEnv();
let written = 0;
for (const article of articles) {
  const slug = sanitizeArticleSlug(article.slug);
  if (!slug) continue;
  const meta = buildArticleShareMeta(
    {
      ...article,
      cover_url: usableCoverUrl(article.cover_url, firstImageUrlFromHtml(article.content || '')),
    },
    { site }
  );
  writeShell(slug, injectShareMetaIntoHtml(shell, meta));
  written += 1;
}

console.log(`prerender-article-og: wrote ${written} article share shells.`);
