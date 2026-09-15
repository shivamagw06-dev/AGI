-- AGI PIN auth + trusted device support (profiles extension)
-- Never store plaintext PINs.

ALTER TABLE profiles ADD COLUMN IF NOT EXISTS pin_hash text;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS pin_salt text;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS pin_updated_at timestamptz;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS display_name text;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS notification_prefs jsonb DEFAULT '{
  "morning_note": true,
  "pre_market": true,
  "market_close": true,
  "research": true,
  "macro_reports": false
}'::jsonb;

CREATE TABLE IF NOT EXISTS trusted_devices (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  device_id text NOT NULL,
  label text,
  user_agent text,
  trusted_at timestamptz DEFAULT now(),
  expires_at timestamptz NOT NULL,
  last_active timestamptz DEFAULT now(),
  UNIQUE (user_id, device_id)
);

CREATE INDEX IF NOT EXISTS trusted_devices_user_idx ON trusted_devices (user_id);
CREATE INDEX IF NOT EXISTS trusted_devices_expires_idx ON trusted_devices (expires_at);

ALTER TABLE trusted_devices ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users read own trusted devices" ON trusted_devices;
CREATE POLICY "Users read own trusted devices"
  ON trusted_devices FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users insert own trusted devices" ON trusted_devices;
CREATE POLICY "Users insert own trusted devices"
  ON trusted_devices FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users update own trusted devices" ON trusted_devices;
CREATE POLICY "Users update own trusted devices"
  ON trusted_devices FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users delete own trusted devices" ON trusted_devices;
CREATE POLICY "Users delete own trusted devices"
  ON trusted_devices FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

COMMENT ON COLUMN profiles.pin_hash IS 'PBKDF2 hash of 6-digit PIN — never plaintext';
COMMENT ON TABLE trusted_devices IS 'Browsers trusted for PIN unlock without OTP (default 90 days)';
