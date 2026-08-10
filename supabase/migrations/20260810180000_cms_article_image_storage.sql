-- CMS article inline images + cover photos (Supabase Storage)
-- Buckets: images (inline body), covers (featured hero)

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('images', 'images', true, 10485760, array['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif']),
  ('covers', 'covers', true, 15728640, array['image/jpeg', 'image/png', 'image/webp', 'image/gif', 'image/avif'])
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Authenticated authors upload into their own folder: {user_id}/*
drop policy if exists "cms_images_auth_insert_own" on storage.objects;
create policy "cms_images_auth_insert_own"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'images'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "cms_images_auth_update_own" on storage.objects;
create policy "cms_images_auth_update_own"
  on storage.objects for update to authenticated
  using (
    bucket_id = 'images'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "cms_covers_auth_insert_own" on storage.objects;
create policy "cms_covers_auth_insert_own"
  on storage.objects for insert to authenticated
  with check (
    bucket_id = 'covers'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

drop policy if exists "cms_covers_auth_update_own" on storage.objects;
create policy "cms_covers_auth_update_own"
  on storage.objects for update to authenticated
  using (
    bucket_id = 'covers'
    and (storage.foldername(name))[1] = auth.uid()::text
  );

-- Public read for published article HTML <img src="...">
drop policy if exists "cms_images_public_read" on storage.objects;
create policy "cms_images_public_read"
  on storage.objects for select to public
  using (bucket_id in ('images', 'covers'));
