// src/lib/supabaseClient.js
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL?.trim() || '';
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY?.trim() || '';

function looksLikeJwt(value) {
  if (!value) return false;
  return value.split('.').length === 3 && value.length >= 100;
}

const keyLooksValid = looksLikeJwt(supabaseAnonKey);
const urlLooksValid =
  Boolean(supabaseUrl) &&
  !/placeholder\.supabase\.co/i.test(supabaseUrl) &&
  /^https:\/\//i.test(supabaseUrl);

export const isSupabaseConfigured = Boolean(urlLooksValid && keyLooksValid);

if (!isSupabaseConfigured) {
  console.warn(
    'Supabase env vars missing or truncated (VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY). Auth will use branded API fallbacks where possible.'
  );
}

// Placeholders keep the app from crashing when secrets are missing at build time.
export const supabase = createClient(
  urlLooksValid ? supabaseUrl : 'https://placeholder.supabase.co',
  keyLooksValid ? supabaseAnonKey : 'placeholder-anon-key',
  {
    auth: { persistSession: true, detectSessionInUrl: true, autoRefreshToken: true },
  }
);

if (typeof window !== 'undefined') {
  window.supabase = supabase;
}
    