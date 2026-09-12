import { supabase } from '@/lib/supabaseClient';
import { sendWelcomeEmail } from '@/lib/newsletterClient';
import { defaultLetterPreferences } from '@/config/agiLetters';

/**
 * Insert/upsert subscriber with AGI letter preferences and send welcome email.
 */
export async function subscribeNewsletter(
  email,
  { userId = null, preferences = null, source = 'website' } = {}
) {
  const value = String(email || '').trim().toLowerCase();
  if (!value) throw new Error('Email is required.');

  const prefs = defaultLetterPreferences(
    preferences && typeof preferences === 'object'
      ? Object.keys(preferences).filter((key) => preferences[key])
      : null
  );

  const row = {
    email: value,
    is_active: true,
    preferences: prefs,
    source,
    updated_at: new Date().toISOString(),
    ...(userId ? { user_id: userId } : {}),
  };

  let result = await supabase.from('subscribers').upsert(row, { onConflict: 'email' });

  // Older schemas may not have preferences/source yet — retry without them.
  if (result.error && /preferences|source|updated_at|column/i.test(result.error.message || '')) {
    const { preferences: _p, source: _s, updated_at: _u, ...legacyRow } = row;
    result = await supabase.from('subscribers').upsert(legacyRow, { onConflict: 'email' });
  }

  if (result.error) {
    const insert = await supabase.from('subscribers').insert(row);
    if (insert.error && /preferences|source|updated_at|column/i.test(insert.error.message || '')) {
      const { preferences: _p, source: _s, updated_at: _u, ...legacyRow } = row;
      const legacyInsert = await supabase.from('subscribers').insert(legacyRow);
      if (legacyInsert.error && !/duplicate|unique/i.test(legacyInsert.error.message || '')) {
        throw new Error(legacyInsert.error.message || 'Subscription failed.');
      }
      if (legacyInsert.error && /duplicate|unique/i.test(legacyInsert.error.message || '')) {
        throw new Error('This email is already subscribed.');
      }
    } else if (insert.error && !/duplicate|unique/i.test(insert.error.message || '')) {
      throw new Error(insert.error.message || 'Subscription failed.');
    } else if (insert.error && /duplicate|unique/i.test(insert.error.message || '')) {
      throw new Error('This email is already subscribed.');
    }
  }

  const welcome = await sendWelcomeEmail(value, prefs);
  return { email: value, preferences: prefs, welcome };
}
