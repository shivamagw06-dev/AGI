export const DEFAULT_SITE_URL = 'https://agarwalglobalinvestments.com';
export const DEFAULT_SHARE_IMAGE_PATH = '/agi-og-cover.png';
export const SITE_NAME = 'Agarwal Global Investments';
export const DEFAULT_SHARE_DESCRIPTION =
  'Institutional-quality market research updated every trading day. Morning briefs, sector analysis, and company updates from Agarwal Global Investments.';

export function siteUrlFromEnv(env = typeof process !== 'undefined' ? process.env : {}) {
  const raw = env?.PUBLIC_SITE_URL || env?.BASE_URL || DEFAULT_SITE_URL;
  return String(raw || DEFAULT_SITE_URL).replace(/\/$/, '');
}

export function sanitizeArticleSlug(value) {
  let raw = String(value || '');
  try {
    raw = decodeURIComponent(raw);
  } catch {
    return '';
  }
  const slug = raw.trim().replace(/^\/+|\/+$/g, '');
  if (!/^[a-z0-9][a-z0-9-]{0,119}$/i.test(slug)) return '';
  return slug;
}

export function firstHttpImageFromHtml(html = '') {
  const match = String(html).match(/<img\b[^>]*\bsrc=["']([^"']+)["']/i);
  const url = String(match?.[1] || '').trim();
  if (/^https:\/\//i.test(url)) return url;
  if (/^http:\/\//i.test(url)) return `https://${url.slice('http://'.length)}`;
  return '';
}

export function absoluteShareImageUrl(url, site = DEFAULT_SITE_URL) {
  const origin = String(site || DEFAULT_SITE_URL).replace(/\/$/, '');
  const fallback = `${origin}${DEFAULT_SHARE_IMAGE_PATH}`;
  const raw = String(url || '').trim();
  if (!raw) return fallback;
  if (/^https:\/\//i.test(raw)) return raw;
  if (/^http:\/\//i.test(raw)) return `https://${raw.slice('http://'.length)}`;
  if (raw.startsWith('//')) return `https:${raw}`;
  if (raw.startsWith('/')) return `${origin}${raw}`;
  return `${origin}/${raw}`;
}

export function imageMimeFromUrl(url) {
  const path = String(url || '').split('?')[0].toLowerCase();
  if (path.endsWith('.jpg') || path.endsWith('.jpeg')) return 'image/jpeg';
  if (path.endsWith('.gif')) return 'image/gif';
  if (path.endsWith('.webp')) return 'image/webp';
  return 'image/png';
}

function asText(value, fallback = '') {
  const text = String(value || '')
    .replace(/\s+/g, ' ')
    .trim();
  return text || fallback;
}

export function buildArticleShareMeta(article = {}, { site } = {}) {
  const origin = String(site || siteUrlFromEnv()).replace(/\/$/, '');
  const slug = sanitizeArticleSlug(article.slug);
  const title = asText(article.title, SITE_NAME);
  const description = asText(
    article.excerpt || article.meta_description,
    DEFAULT_SHARE_DESCRIPTION
  ).slice(0, 200);
  const image = absoluteShareImageUrl(
    article.cover_url ||
      article.coverUrl ||
      article.image ||
      firstHttpImageFromHtml(article.content || article.html || ''),
    origin
  );
  const usesDefaultImage = image.endsWith(DEFAULT_SHARE_IMAGE_PATH);
  const author = asText(
    article.author_name ||
      article.author?.full_name ||
      article.author?.display_name ||
      (typeof article.author === 'string' ? article.author : ''),
    'AGI Research'
  );
  return {
    title,
    pageTitle: slug ? `${title} • AGI` : 'AGI — Agarwal Global Investments',
    description,
    image,
    imageType: imageMimeFromUrl(image),
    imageWidth: usesDefaultImage ? 1200 : null,
    imageHeight: usesDefaultImage ? 630 : null,
    url: slug ? `${origin}/article/${slug}` : `${origin}/`,
    siteName: SITE_NAME,
    type: slug ? 'article' : 'website',
    publishedTime: article.published_at || article.publishedAt || null,
    author,
  };
}

export function escapeHtmlAttr(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/"/g, '&quot;');
}

export function shareMetaTagHtml(meta) {
  const tags = [
    `<meta name="description" content="${escapeHtmlAttr(meta.description)}" />`,
    `<link rel="canonical" href="${escapeHtmlAttr(meta.url)}" />`,
    `<meta property="og:site_name" content="${escapeHtmlAttr(meta.siteName)}" />`,
    `<meta property="og:type" content="${escapeHtmlAttr(meta.type)}" />`,
    `<meta property="og:url" content="${escapeHtmlAttr(meta.url)}" />`,
    `<meta property="og:title" content="${escapeHtmlAttr(meta.title)}" />`,
    `<meta property="og:description" content="${escapeHtmlAttr(meta.description)}" />`,
    `<meta property="og:image" content="${escapeHtmlAttr(meta.image)}" />`,
    `<meta property="og:image:secure_url" content="${escapeHtmlAttr(meta.image)}" />`,
    `<meta property="og:image:type" content="${escapeHtmlAttr(meta.imageType)}" />`,
    `<meta property="og:image:alt" content="${escapeHtmlAttr(meta.title)}" />`,
  ];
  if (meta.imageWidth && meta.imageHeight) {
    tags.push(`<meta property="og:image:width" content="${meta.imageWidth}" />`);
    tags.push(`<meta property="og:image:height" content="${meta.imageHeight}" />`);
  }
  if (meta.publishedTime) {
    tags.push(
      `<meta property="article:published_time" content="${escapeHtmlAttr(meta.publishedTime)}" />`
    );
  }
  if (meta.author) {
    tags.push(`<meta name="author" content="${escapeHtmlAttr(meta.author)}" />`);
    tags.push(`<meta property="article:author" content="${escapeHtmlAttr(meta.author)}" />`);
  }
  tags.push('<meta name="twitter:card" content="summary_large_image" />');
  tags.push(`<meta name="twitter:title" content="${escapeHtmlAttr(meta.title)}" />`);
  tags.push(`<meta name="twitter:description" content="${escapeHtmlAttr(meta.description)}" />`);
  tags.push(`<meta name="twitter:image" content="${escapeHtmlAttr(meta.image)}" />`);
  return tags.join('\n    ');
}

export function injectShareMetaIntoHtml(html, meta) {
  let out = String(html || '');
  if (!/<head[\s>]/i.test(out) || !meta) return out;
  const title = `<title>${escapeHtmlAttr(meta.pageTitle || meta.title)}</title>`;
  if (/<title>[\s\S]*?<\/title>/i.test(out)) {
    out = out.replace(/<title>[\s\S]*?<\/title>/i, title);
  } else {
    out = out.replace(/<head[^>]*>/i, (open) => `${open}\n    ${title}`);
  }
  out = out
    .replace(/<meta\s+name=["']description["'][^>]*>\s*/gi, '')
    .replace(/<link\s+rel=["']canonical["'][^>]*>\s*/gi, '')
    .replace(/<meta\s+property=["']og:[^"']+["'][^>]*>\s*/gi, '')
    .replace(/<meta\s+name=["']twitter:[^"']+["'][^>]*>\s*/gi, '')
    .replace(/<meta\s+property=["']article:[^"']+["'][^>]*>\s*/gi, '');
  return out.replace(/<\/head>/i, `    ${shareMetaTagHtml(meta)}\n  </head>`);
}
