/**
 * Shared Supabase admin client for Node 20+.
 * supabase-js Realtime expects a WebSocket constructor; Node has none natively,
 * so we pass `ws` as the realtime transport to avoid:
 * "Node.js detected but native WebSocket not found"
 */
import { createClient } from '@supabase/supabase-js';
import ws from 'ws';

export function getSupabaseAdminCredentials() {
  const supabaseUrl = (
    process.env.SUPABASE_URL ||
    process.env.VITE_SUPABASE_URL ||
    ''
  ).trim();
  const serviceKey = (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!supabaseUrl || !serviceKey) return null;
  return { supabaseUrl, serviceKey };
}

export function createSupabaseAdmin() {
  const creds = getSupabaseAdminCredentials();
  if (!creds) return null;
  return createClient(creds.supabaseUrl, creds.serviceKey, {
    auth: { autoRefreshToken: false, persistSession: false },
    realtime: { transport: ws },
  });
}
