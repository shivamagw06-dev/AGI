require('dotenv').config({ path: require('path').join(__dirname, '.env') });
const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_SERVICE_ROLE;

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error('Missing SUPABASE env vars in server/.env; aborting.');
  process.exit(1);
}

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

(async () => {
  try {
    const payload = { email: 'debug.test+1@example.com', is_active: true, unsubscribe_token: 'debugtoken123' };
    const { data, error } = await supabase.from('subscribers').upsert(payload, { onConflict: ['email'] }).select().single();
    console.log('DATA:', data);
    console.log('ERROR:', error);
  } catch (err) {
    console.error('EXCEPTION:', err);
  } finally {
    process.exit(0);
  }
})();
