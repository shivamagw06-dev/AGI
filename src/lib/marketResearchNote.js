import { supabase } from '@/lib/supabaseClient';

export const MARKET_SECTOR_FEATURED_TAG = 'market-sector-featured';
const THEME_PREFIX = 'market-sector-theme:';
const AUTHOR_PREFIX = 'market-sector-author:';

export function noteThemes(tags = []) {
  return (Array.isArray(tags) ? tags : [])
    .filter((tag) => String(tag).startsWith(THEME_PREFIX))
    .map((tag) => String(tag).slice(THEME_PREFIX.length))
    .filter(Boolean);
}

export function noteAuthor(tags = []) {
  const entry = (Array.isArray(tags) ? tags : []).find((tag) => String(tag).startsWith(AUTHOR_PREFIX));
  return entry ? String(entry).slice(AUTHOR_PREFIX.length) : 'AGI Research';
}

export function buildNoteTags({ themes = [], author = '', featured = true, existing = [] } = {}) {
  const retained = (Array.isArray(existing) ? existing : []).filter((tag) => {
    const value = String(tag);
    return value !== MARKET_SECTOR_FEATURED_TAG && !value.startsWith(THEME_PREFIX) && !value.startsWith(AUTHOR_PREFIX);
  });
  const cleanThemes = themes.map((theme) => String(theme).trim()).filter(Boolean).map((theme) => `${THEME_PREFIX}${theme}`);
  if (author.trim()) retained.push(`${AUTHOR_PREFIX}${author.trim()}`);
  if (featured) retained.push(MARKET_SECTOR_FEATURED_TAG);
  return Array.from(new Set([...retained, ...cleanThemes]));
}

export async function getFeaturedMarketResearchNote() {
  const { data, error } = await supabase
    .from('articles')
    .select('id,title,slug,excerpt,meta_description,tags,published_at,created_at')
    .eq('status', 'published')
    .contains('tags', [MARKET_SECTOR_FEATURED_TAG])
    .order('published_at', { ascending: false })
    .limit(1)
    .maybeSingle();
  if (error) throw error;
  return data || null;
}

export async function getMarketResearchNotes() {
  const { data, error } = await supabase
    .from('articles')
    .select('id,title,slug,excerpt,meta_description,content_md,content,tags,status,published_at,created_at,updated_at')
    .contains('tags', [MARKET_SECTOR_FEATURED_TAG])
    .order('updated_at', { ascending: false })
    .limit(20);
  if (error) throw error;
  return data || [];
}
