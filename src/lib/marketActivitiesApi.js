import { supabase, isSupabaseConfigured } from '@/lib/supabaseClient';

const MAX_BODY = 280;

export function normalizeActivityBody(value = '') {
  return String(value || '').trim().replace(/\s+/g, ' ').slice(0, MAX_BODY);
}

export async function listPublishedMarketActivities({ limit = 12 } = {}) {
  if (!isSupabaseConfigured) return [];
  const { data, error } = await supabase
    .from('market_activities')
    .select('id, body, published, created_at, updated_at')
    .eq('published', true)
    .order('created_at', { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data || [];
}

export async function listMarketActivitiesAdmin({ limit = 50 } = {}) {
  if (!isSupabaseConfigured) return [];
  const { data, error } = await supabase
    .from('market_activities')
    .select('id, body, published, created_at, updated_at, created_by')
    .order('created_at', { ascending: false })
    .limit(limit);
  if (error) throw error;
  return data || [];
}

export async function createMarketActivity({ body, published = true, userId = null } = {}) {
  const cleaned = normalizeActivityBody(body);
  if (!cleaned) throw new Error('Write a short update first.');
  const payload = {
    body: cleaned,
    published: Boolean(published),
    updated_at: new Date().toISOString(),
  };
  if (userId) payload.created_by = userId;
  const { data, error } = await supabase
    .from('market_activities')
    .insert(payload)
    .select('id, body, published, created_at, updated_at, created_by')
    .single();
  if (error) throw error;
  return data;
}

export async function updateMarketActivity(id, patch = {}) {
  if (!id) throw new Error('Missing activity id.');
  const next = { updated_at: new Date().toISOString() };
  if (patch.body != null) {
    const cleaned = normalizeActivityBody(patch.body);
    if (!cleaned) throw new Error('Update text cannot be empty.');
    next.body = cleaned;
  }
  if (patch.published != null) next.published = Boolean(patch.published);
  const { data, error } = await supabase
    .from('market_activities')
    .update(next)
    .eq('id', id)
    .select('id, body, published, created_at, updated_at, created_by')
    .single();
  if (error) throw error;
  return data;
}

export async function deleteMarketActivity(id) {
  if (!id) throw new Error('Missing activity id.');
  const { error } = await supabase.from('market_activities').delete().eq('id', id);
  if (error) throw error;
}
