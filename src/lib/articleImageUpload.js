import { supabase, isSupabaseConfigured } from '@/lib/supabaseClient';

function sanitizeFilename(name = 'image') {
  const base = String(name).split(/[/\\]/).pop() || 'image';
  const parts = base.split('.');
  const ext = parts.length > 1 ? parts.pop().toLowerCase().replace(/[^a-z0-9]/g, '') : 'jpg';
  const stem = parts.join('.').toLowerCase().replace(/[^a-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '') || 'image';
  return `${stem.slice(0, 80)}.${ext || 'jpg'}`;
}

export async function uploadArticleImage({ userId, file, bucket = 'images' }) {
  if (!file) throw new Error('No image file selected.');
  if (!isSupabaseConfigured) {
    throw new Error('Image upload is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY on the website build.');
  }
  if (!userId) throw new Error('Sign in to upload images into your article.');

  const safeName = sanitizeFilename(file.name);
  const path = `${userId}/${Date.now()}-${safeName}`;
  const { error: uploadError } = await supabase.storage.from(bucket).upload(path, file, {
    cacheControl: '3600',
    upsert: false,
    contentType: file.type || 'image/jpeg',
  });
  if (uploadError) {
    const message = uploadError.message || 'Storage upload failed';
    if (/bucket not found/i.test(message)) {
      throw new Error('The images storage bucket is missing in Supabase. Create a public bucket named "images".');
    }
    if (/policy|permission|denied|unauthorized/i.test(message)) {
      throw new Error('Storage permission denied. Ask an admin to allow authenticated uploads to the images bucket.');
    }
    throw new Error(message);
  }

  const { data } = supabase.storage.from(bucket).getPublicUrl(path);
  if (!data?.publicUrl) throw new Error('Upload succeeded but no public URL was returned.');
  return data.publicUrl;
}

export function insertImageAtPosition(editor, position, { url, alt = '' }) {
  if (!editor || !url) return false;
  const safePosition = Math.max(0, Math.min(Number(position) || 0, editor.state.doc.content.size));
  return editor
    .chain()
    .focus()
    .insertContentAt(safePosition, {
      type: 'image',
      attrs: { src: url, alt, size: 'full', align: 'center' },
    })
    .run();
}
