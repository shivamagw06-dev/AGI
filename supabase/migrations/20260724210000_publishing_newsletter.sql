-- AGI Publishing & Newsletter Platform
-- Extends existing subscribers / articles — does NOT replace CMS article storage.

-- Extended subscriber profile (additive columns on existing subscribers table)
CREATE TABLE IF NOT EXISTS subscribers (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email text UNIQUE NOT NULL,
  first_name text,
  last_name text,
  source text DEFAULT 'website',
  status text DEFAULT 'active' CHECK (status IN ('active', 'unsubscribed', 'bounced', 'pending')),
  verified boolean DEFAULT false,
  preferences jsonb DEFAULT '{}'::jsonb,
  tags text[] DEFAULT '{}',
  is_active boolean DEFAULT true,
  unsubscribe_token text UNIQUE,
  created_at timestamptz DEFAULT now(),
  last_opened timestamptz,
  last_clicked timestamptz,
  last_email_sent timestamptz,
  user_id uuid
);

ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS first_name text;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_name text;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS source text DEFAULT 'website';
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS status text DEFAULT 'active';
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS verified boolean DEFAULT false;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS preferences jsonb DEFAULT '{}'::jsonb;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS tags text[] DEFAULT '{}';
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_opened timestamptz;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_clicked timestamptz;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS last_email_sent timestamptz;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS unsubscribe_token text;
ALTER TABLE subscribers ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true;

CREATE UNIQUE INDEX IF NOT EXISTS subscribers_email_unique_idx ON subscribers (lower(email));
CREATE INDEX IF NOT EXISTS subscribers_source_idx ON subscribers (source);
CREATE INDEX IF NOT EXISTS subscribers_status_idx ON subscribers (status);
CREATE INDEX IF NOT EXISTS subscribers_tags_gin ON subscribers USING gin (tags);

-- CSV / campaign imports
CREATE TABLE IF NOT EXISTS newsletter_imports (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source text NOT NULL,
  filename text,
  imported integer DEFAULT 0,
  skipped integer DEFAULT 0,
  duplicates integer DEFAULT 0,
  errors integer DEFAULT 0,
  preview jsonb DEFAULT '[]'::jsonb,
  created_at timestamptz DEFAULT now(),
  created_by text
);

-- Publish distribution jobs (one-click publish archive)
CREATE TABLE IF NOT EXISTS publish_jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  article_id text,
  article_slug text,
  title text,
  status text DEFAULT 'queued',
  channels jsonb DEFAULT '{}'::jsonb,
  channel_content jsonb DEFAULT '{}'::jsonb,
  newsletter_sent integer DEFAULT 0,
  newsletter_failed integer DEFAULT 0,
  segment text DEFAULT 'all',
  analytics jsonb DEFAULT '{}'::jsonb,
  error text,
  created_at timestamptz DEFAULT now(),
  completed_at timestamptz
);

-- Email send events for analytics
CREATE TABLE IF NOT EXISTS newsletter_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id uuid REFERENCES publish_jobs(id) ON DELETE SET NULL,
  subscriber_id uuid,
  email text,
  event_type text NOT NULL, -- sent | open | click | bounce | unsubscribe
  meta jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS newsletter_events_type_idx ON newsletter_events (event_type);
CREATE INDEX IF NOT EXISTS newsletter_events_job_idx ON newsletter_events (job_id);

-- Campaign history / newsletter queue
CREATE TABLE IF NOT EXISTS newsletter_campaigns (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text,
  subject text,
  segment text DEFAULT 'all',
  status text DEFAULT 'draft', -- draft | queued | sending | sent | failed
  article_id text,
  article_slug text,
  html_preview text,
  stats jsonb DEFAULT '{}'::jsonb,
  scheduled_at timestamptz,
  sent_at timestamptz,
  created_at timestamptz DEFAULT now()
);

COMMENT ON TABLE publish_jobs IS 'AGI Research Distribution Engine — one-click publish archive';
COMMENT ON TABLE subscribers IS 'Newsletter subscribers — extended for preferences, tags, sources';
