-- Fix signup: Database error saving new user
-- Root cause: auth.users triggers used ON CONFLICT without matching unique constraints
-- (profiles.id, user_index.user_id, subscribers.user_id).

-- 1) Ensure tables + unique targets for ON CONFLICT
CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  display_name text,
  handle text,
  headline text,
  summary text,
  location text,
  industry text,
  website text,
  github text,
  twitter text,
  photo_url text,
  banner_url text,
  is_public boolean DEFAULT true NOT NULL,
  full_name text DEFAULT '' NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS display_name text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS handle text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS headline text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS summary text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS location text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS industry text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS website text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS github text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS twitter text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS photo_url text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS banner_url text;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_public boolean DEFAULT true;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS full_name text DEFAULT '';
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS created_at timestamptz DEFAULT now();
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS updated_at timestamptz DEFAULT now();

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.profiles'::regclass AND contype = 'p'
  ) THEN
    ALTER TABLE public.profiles ADD CONSTRAINT profiles_pkey PRIMARY KEY (id);
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'profiles_pkey: %', SQLERRM;
END $$;

CREATE TABLE IF NOT EXISTS public.user_index (
  user_id uuid PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
  email text,
  created_at timestamptz
);

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conrelid = 'public.user_index'::regclass AND contype = 'p'
  ) THEN
    ALTER TABLE public.user_index ADD CONSTRAINT user_index_pkey PRIMARY KEY (user_id);
  END IF;
EXCEPTION WHEN OTHERS THEN
  RAISE WARNING 'user_index_pkey: %', SQLERRM;
END $$;

-- subscribers.user_id unique so ON CONFLICT (user_id) works (NULLs allowed)
CREATE UNIQUE INDEX IF NOT EXISTS subscribers_user_id_uidx
  ON public.subscribers (user_id)
  WHERE user_id IS NOT NULL;

-- Prefer unique email for claim/insert safety
CREATE UNIQUE INDEX IF NOT EXISTS subscribers_email_lower_uidx
  ON public.subscribers (lower(trim(email)));

-- 2) Soft-fail profile sync
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  meta_name text;
  base_handle text;
  final_handle text;
BEGIN
  meta_name := NULLIF(TRIM(COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name', '')), '');
  base_handle := LOWER(REGEXP_REPLACE(SPLIT_PART(COALESCE(NEW.email, NEW.id::text), '@', 1), '[^a-z0-9_]+', '', 'g'));
  IF base_handle IS NULL OR base_handle = '' THEN
    base_handle := 'investor';
  END IF;
  final_handle := LEFT(base_handle, 24) || '_' || SUBSTRING(REPLACE(NEW.id::text, '-', ''), 1, 6);

  BEGIN
    INSERT INTO public.profiles AS p (id, display_name, full_name, handle, is_public, created_at, updated_at)
    VALUES (
      NEW.id,
      COALESCE(meta_name, SPLIT_PART(COALESCE(NEW.email, 'Investor'), '@', 1)),
      COALESCE(meta_name, ''),
      final_handle,
      true,
      now(),
      now()
    )
    ON CONFLICT (id) DO UPDATE
      SET
        display_name = COALESCE(NULLIF(p.display_name, ''), EXCLUDED.display_name),
        full_name = COALESCE(NULLIF(p.full_name, ''), EXCLUDED.full_name),
        updated_at = now();
  EXCEPTION
    WHEN OTHERS THEN
      RAISE WARNING 'handle_new_user soft-fail: %', SQLERRM;
  END;

  RETURN NEW;
END;
$$;

-- 3) Soft-fail user_index sync (this was aborting signup)
CREATE OR REPLACE FUNCTION public._on_auth_user_created()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  BEGIN
    INSERT INTO public.user_index (user_id, email, created_at)
    VALUES (NEW.id, NEW.email, NEW.created_at)
    ON CONFLICT (user_id) DO UPDATE
      SET email = EXCLUDED.email,
          created_at = COALESCE(public.user_index.created_at, EXCLUDED.created_at);
  EXCEPTION
    WHEN OTHERS THEN
      RAISE WARNING '_on_auth_user_created soft-fail: %', SQLERRM;
  END;
  RETURN NEW;
END;
$$;

-- 4) Soft-fail subscriber sync
CREATE OR REPLACE FUNCTION public.handle_new_user_subscribe()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  BEGIN
    UPDATE public.subscribers
       SET user_id = NEW.id,
           is_active = true
     WHERE user_id IS NULL
       AND lower(trim(email)) = lower(trim(NEW.email));

    IF NOT FOUND THEN
      INSERT INTO public.subscribers (user_id, email, is_active)
      VALUES (NEW.id, NEW.email, true)
      ON CONFLICT DO NOTHING;
    END IF;
  EXCEPTION
    WHEN OTHERS THEN
      RAISE WARNING 'handle_new_user_subscribe soft-fail: %', SQLERRM;
  END;
  RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC;
REVOKE ALL ON FUNCTION public._on_auth_user_created() FROM PUBLIC;
REVOKE ALL ON FUNCTION public.handle_new_user_subscribe() FROM PUBLIC;

GRANT EXECUTE ON FUNCTION public.handle_new_user() TO supabase_auth_admin, postgres, service_role;
GRANT EXECUTE ON FUNCTION public._on_auth_user_created() TO supabase_auth_admin, postgres, service_role;
GRANT EXECUTE ON FUNCTION public.handle_new_user_subscribe() TO supabase_auth_admin, postgres, service_role;

GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT INSERT, UPDATE, SELECT ON TABLE public.profiles TO supabase_auth_admin;
GRANT INSERT, UPDATE, SELECT ON TABLE public.user_index TO supabase_auth_admin;
GRANT INSERT, UPDATE, SELECT ON TABLE public.subscribers TO supabase_auth_admin;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO supabase_auth_admin;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

DROP TRIGGER IF EXISTS _on_auth_user_created ON auth.users;
CREATE TRIGGER _on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public._on_auth_user_created();

DROP TRIGGER IF EXISTS on_auth_user_created_subscribe ON auth.users;
CREATE TRIGGER on_auth_user_created_subscribe
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user_subscribe();

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'profiles' AND policyname = 'Public read public profiles'
  ) THEN
    CREATE POLICY "Public read public profiles"
      ON public.profiles FOR SELECT
      USING (COALESCE(is_public, true) = true OR auth.uid() = id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'profiles' AND policyname = 'Users manage own profile'
  ) THEN
    CREATE POLICY "Users manage own profile"
      ON public.profiles FOR ALL
      TO authenticated
      USING (auth.uid() = id)
      WITH CHECK (auth.uid() = id);
  END IF;
END $$;
