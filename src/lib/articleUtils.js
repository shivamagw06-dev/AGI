import { supabase } from '@/lib/supabaseClient';

export const HOMEPAGE_LATEST_TAG = 'homepage:latest';

export function toSlug(str = '') {
  return (str || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 120);
}

export async function generateUniqueSlug(title, excludeId = null) {
  const base = toSlug(title) || 'untitled';
  let candidate = base;
  let i = 1;

  while (true) {
    let query = supabase.from('articles').select('id').eq('slug', candidate);
    if (excludeId) query = query.neq('id', excludeId);
    const { data, error } = await query.maybeSingle();

    if (error) return `${base}-${Date.now()}`;
    if (!data) return candidate;
    candidate = `${base}-${i++}`;
  }
}

export function htmlToExcerpt(html = '', max = 160) {
  const plain = String(html).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  return plain.length > max ? `${plain.slice(0, max).trim()}…` : plain;
}

export function wordCountFromHTML(html = '') {
  const text = html.replace(/<[^>]*>/g, ' ');
  return text.split(/\s+/).filter(Boolean).length;
}

export function readingTime(html = '') {
  return Math.max(1, Math.round(wordCountFromHTML(html) / 200));
}

export function formatArticleDate(dateString) {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatRelativePublishedDate(dateString) {
  if (!dateString) return 'Recently published';

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return 'Recently published';

  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const startOfPublishDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const dayDiff = Math.round((startOfToday - startOfPublishDay) / (1000 * 60 * 60 * 24));

  if (dayDiff === 0) return 'Published today';
  if (dayDiff === 1) return 'Published yesterday';
  if (dayDiff < 7) return `Published ${dayDiff} days ago`;

  return date.toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/** Reuters-style relative time e.g. "17 min ago" */
export function formatTimeAgo(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return '';

  const sec = Math.floor((Date.now() - date.getTime()) / 1000);
  if (sec < 60) return 'Just now';
  const mins = Math.floor(sec / 60);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return '1 day ago';
  if (days < 7) return `${days} days ago`;
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
}

export function estimateReadTimeFromExcerpt(text = '') {
  const words = (text || '').split(/\s+/).filter(Boolean).length;
  const mins = Math.max(3, Math.round(words / 200));
  return `${mins} min read`;
}

const DEFAULT_COVER =
  'https://images.unsplash.com/photo-1595872018818-97555653a011?auto=format&fit=crop&w=1200&q=80';

export function mapArticleForCard(row) {
  if (!row) return null;
  return {
    id: row.id,
    title: row.title,
    slug: row.slug,
    excerpt: row.excerpt,
    coverUrl: row.cover_url || DEFAULT_COVER,
    image: row.cover_url || DEFAULT_COVER,
    category:
      row.section ||
      (Array.isArray(row.tags) && row.tags.length ? row.tags[0] : 'Research'),
    tags: row.tags,
    section: row.section,
    date: row.published_at,
    publishedLabel: formatRelativePublishedDate(row.published_at),
    readTime: estimateReadTimeFromExcerpt(row.excerpt),
  };
}
