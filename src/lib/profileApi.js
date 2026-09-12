// src/lib/profileApi.js
import { supabase } from './supabaseClient';

/* ---------------------------
   AUTH HELPERS
----------------------------*/
export async function getSession() {
  const { data, error } = await supabase.auth.getSession();
  if (error) throw error;
  return data.session ?? null;
}

export async function ensureSignedIn() {
  const session = await getSession();
  if (!session) throw new Error('Not authenticated');
  return session.user;
}

/* ---------------------------
   PROFILE
----------------------------*/
export async function getMyProfile() {
  const user = await ensureSignedIn();

  // maybeSingle -> returns null instead of throwing when row doesn't exist (avoids 406)
  const { data, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('id', user.id)
    .maybeSingle();

  if (error) throw error;
  return data; // may be null if profile not created yet
}

export async function upsertMyProfile(payload) {
  const user = await ensureSignedIn();
  const row = { id: user.id, ...payload };

  // after upsert we expect exactly one row; SELECT is okay if your RLS allows reading own row
  const { data, error } = await supabase
    .from('profiles')
    .upsert(row, { onConflict: 'id' })
    .select()
    .single();

  if (error) throw error;
  return data;
}

/**
 * Check if a handle is unique (case-insensitive).
 * Pass currentId to ignore your own row during edits.
 */
export async function checkHandleUnique(handle, currentId = null) {
  const trimmed = (handle ?? '').trim();
  if (!trimmed) return false;

  let query = supabase
    .from('profiles')
    .select('id', { count: 'exact', head: true })
    .ilike('handle', trimmed); // case-insensitive equality

  if (currentId) query = query.neq('id', currentId);

  const { error, count } = await query;
  if (error) throw error;
  return (count ?? 0) === 0;
}

/* ---------------------------
   STORAGE HELPERS
----------------------------*/
async function uploadTo(bucket, file, userId, name) {
  if (!file) throw new Error('No file provided');
  const parts = String(file.name || '').split('.');
  const ext = parts.length > 1 ? parts.pop() : 'bin';
  const path = `${userId}/${name}.${ext}`;

  // Upsert to overwrite previous upload
  const { error: upErr } = await supabase.storage.from(bucket).upload(path, file, { upsert: true });
  if (upErr) throw upErr;

  const { data, error: urlErr } = await supabase.storage.from(bucket).getPublicUrl(path);
  if (urlErr) throw urlErr;
  return data.publicUrl;
}

export async function uploadAvatar(file) {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  return uploadTo('avatars', file, user.id, 'avatar');
}

export async function uploadBanner(file) {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error) throw error;
  return uploadTo('banners', file, user.id, 'banner');
}

/* ---------------------------
   SECTIONS CRUD
----------------------------*/
export const sections = {
  experiences: 'experiences',
  educations: 'educations',
  certifications: 'certifications',
  projects: 'projects',
};

export async function listSection(table, userId) {
  const { data, error } = await supabase
    .from(table)
    .select('*')
    .eq('user_id', userId)
    .order('start_date', { ascending: false })
    .order('end_year', { ascending: false, nullsFirst: false });

  if (error) throw error;
  return data ?? [];
}

export async function addSection(table, payload) {
  const user = await ensureSignedIn();
  const row = { ...payload, user_id: user.id };

  // If your SELECT policy doesn't allow return, drop .select().single()
  const { data, error } = await supabase.from(table).insert(row).select().single();
  if (error) throw error;
  return data;
}

export async function updateSection(table, id, patch) {
  const { data, error } = await supabase.from(table).update(patch).eq('id', id).select().single();
  if (error) throw error;
  return data;
}

export async function deleteSection(table, id) {
  const { error } = await supabase.from(table).delete().eq('id', id);
  if (error) throw error;
  return true;
}

/* ---------------------------
   PUBLIC PROFILE BY HANDLE
----------------------------*/
export async function getPublicProfileByHandle(handle) {
  const { data: profile, error } = await supabase
    .from('profiles')
    .select('*')
    .eq('handle', handle)
    .eq('is_public', true)
    .maybeSingle(); // avoid 406 when not found

  if (error) throw error;
  if (!profile) return null;

  const userId = profile.id;

  const [{ data: skills, error: skillsErr }, exp, edu, certs, projs] = await Promise.all([
    supabase
      .from('user_skills')
      .select('endorsement_count, skills(name), skill_id')
      .eq('user_id', userId),
    listSection('experiences', userId),
    listSection('educations', userId),
    listSection('certifications', userId),
    listSection('projects', userId),
  ]);

  if (skillsErr) throw skillsErr;

  return {
    profile,
    experiences: exp,
    educations: edu,
    certifications: certs,
    projects: projs,
    skills: skills ?? [],
  };
}

/* ---------------------------
   OPTIONAL: claim legacy subscriber row after sign-in
   (keeps subscribers.user_id filled when email existed before)
----------------------------*/
export function wireAuthSubscriptionClaim() {
  supabase.auth.onAuthStateChange(async (event, session) => {
    if (event === 'SIGNED_IN' && session?.user) {
      await supabase
        .from('subscribers')
        .update({ user_id: session.user.id, is_active: true })
        .is('user_id', null)
        .eq('email', session.user.email)
        .select()
        .single()
        .catch(() => {});
    }
  });
}
