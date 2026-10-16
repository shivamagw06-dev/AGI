-- Fix "Database error saving new user" on signup.
-- Cause: auth.users INSERT trigger failing (usually profiles sync / permissions).
-- Safe to re-run. Soft-fails so Auth signup never rolls back on profile issues.

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
  is_public boolean DEFAULT true,
  full_name text DEFAULT '',
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

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
DROP TRIGGER IF EXISTS on_auth_user_created_profiles ON auth.users;
DROP TRIGGER IF EXISTS handle_new_user ON auth.users;
DROP TRIGGER IF EXISTS create_profile_on_signup ON auth.users;

DROP FUNCTION IF EXISTS public.handle_new_user() CASCADE;
DROP FUNCTION IF EXISTS public.on_auth_user_created() CASCADE;
DROP FUNCTION IF EXISTS public.create_profile_for_user() CASCADE;

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
      -- Never fail auth.users insert because profile sync failed.
      RAISE WARNING 'handle_new_user soft-fail: %', SQLERRM;
  END;

  RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO supabase_auth_admin;
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO postgres;
GRANT EXECUTE ON FUNCTION public.handle_new_user() TO service_role;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT INSERT, UPDATE, SELECT ON TABLE public.profiles TO supabase_auth_admin;

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
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
