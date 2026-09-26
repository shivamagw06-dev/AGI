// src/components/NewArticle.jsx
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { supabase } from '@/lib/supabaseClient.js';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { EditorContent, useEditor } from '@tiptap/react';

/* ---------- TipTap v3 extensions ---------- */
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Link from '@tiptap/extension-link';
import Highlight from '@tiptap/extension-highlight';
import TextAlign from '@tiptap/extension-text-align';
import { TextStyle } from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';

/* ---------- Lowlight ---------- */
import { lowlight } from 'lowlight/lib/core.js';
import javascript from 'highlight.js/lib/languages/javascript';
import xml from 'highlight.js/lib/languages/xml';
import jsonLang from 'highlight.js/lib/languages/json';
lowlight.registerLanguage('javascript', javascript);
lowlight.registerLanguage('xml', xml);
lowlight.registerLanguage('json', jsonLang);

/* ---------- Custom Image Extension ---------- */
import { CustomImage } from '@/extensions/CustomImage';

/* ============================================================ */

const ADMIN_ID = 'c56e4d07-273c-49c9-86a5-a4445e687ece';

const SECTIONS = [
  'Live Articles',
  'Research Notes',
  'Deal Tracker',
  'Markets Dashboard',
  'Opinions & Editorials',
  'Events & Webinars',
];

/* ----------------- Helpers ----------------- */
function toSlug(str = '') {
  return (str || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 120);
}

async function generateUniqueSlug(title) {
  const base = toSlug(title) || 'untitled';
  let candidate = base;
  let i = 1;
  try {
    while (true) {
      const { data, error } = await supabase
        .from('articles')
        .select('id')
        .eq('slug', candidate)
        .maybeSingle();
      if (error) {
        // Log and return fallback slug
        console.warn('generateUniqueSlug supabase error:', error);
        return `${base}-${Date.now()}`;
      }
      if (!data) return candidate;
      candidate = `${base}-${i++}`;
    }
  } catch (err) {
    console.error('generateUniqueSlug failed:', err);
    return `${base}-${Date.now()}`;
  }
}

function wordCountFromHTML(html = '') {
  const text = html.replace(/<[^>]*>/g, ' ');
  return text.split(/\s+/).filter(Boolean).length;
}

function readingTime(html = '') {
  return Math.max(3, Math.round(wordCountFromHTML(html) / 200));
}

/* ============================================================ */
/* ------------------- COMPONENT START ------------------------- */
/* ============================================================ */

export default function NewArticle() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const editSlug = decodeURIComponent(searchParams.get('edit') || '');

  /* ---------- STATE ---------- */
  const [title, setTitle] = useState('');
  const [section, setSection] = useState('Live Articles');
  const [excerpt, setExcerpt] = useState('');
  const [coverUrl, setCoverUrl] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [draftId, setDraftId] = useState(null);
  const [publishNow, setPublishNow] = useState(false);
  const [errorText, setErrorText] = useState('');
  const [slug, setSlug] = useState('');

  /* ---------- TipTap Editor ---------- */
  const editor = useEditor({
    extensions: [
      // disable starter-kit link to avoid duplicate 'link' extension warning
      StarterKit.configure({ history: true, codeBlock: false, link: false }),
      Placeholder.configure({ placeholder: 'Start writing…' }),
      Link.configure({ openOnClick: false, autolink: true }),
      CustomImage,
      Highlight,
      TextStyle,
      Color,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      CodeBlockLowlight.configure({ lowlight }),
    ],
    content: '',
    autofocus: true,
  });

  /* ---------- Access Control ---------- */
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <p className="text-lg font-medium">Please log in to write an article.</p>
      </div>
    );
  }

  if (user.id !== ADMIN_ID) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
        <p className="text-lg font-medium">
          Access denied — only authorized authors can write articles.
        </p>
      </div>
    );
  }

  /* ---------- Load Existing Article ---------- */
  useEffect(() => {
    if (!user || !editor || !editSlug) return;
    let mounted = true;

    (async () => {
      try {
        const { data, error } = await supabase
          .from('articles')
          .select(
            'id, title, slug, section, excerpt, content_md, cover_url, tags, status'
          )
          .eq('slug', editSlug)
          .eq('author_id', user.id)
          .maybeSingle();

        if (error) {
          console.error('Load article error:', error);
          if (mounted) setErrorText('Failed to load article.');
          return;
        }

        if (data && mounted) {
          setDraftId(data.id);
          setSlug(data.slug);
          setTitle(data.title || '');
          setSection(data.section || 'Live Articles');
          setExcerpt(data.excerpt || '');
          setCoverUrl(data.cover_url || '');
          setTagsInput(Array.isArray(data.tags) ? data.tags.join(', ') : '');
          // Use content markdown as HTML / set content for editor
          editor.commands.setContent(data.content_md || '', { emitUpdate: false });
        }
      } catch (err) {
        console.error('Load article exception:', err);
        if (mounted) setErrorText('Failed to load article.');
      }
    })();

    return () => {
      mounted = false;
    };
  }, [editSlug, user, editor]);

  /* ---------- Upload Helpers ---------- */
  async function uploadToBucket(bucket, file) {
    const path = `${user.id}/${Date.now()}-${file.name}`;
    try {
      const { error } = await supabase.storage.from(bucket).upload(path, file, {
        cacheControl: '3600',
        upsert: false,
      });
      if (error) throw error;
      const { data } = supabase.storage.from(bucket).getPublicUrl(path);
      return data.publicUrl;
    } catch (err) {
      console.error('uploadToBucket error:', err);
      throw new Error(err?.message || 'Upload failed');
    }
  }

  async function chooseCover() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const url = await uploadToBucket('covers', file);
        setCoverUrl(url);
      } catch (e) {
        console.error('Cover upload failed:', e);
        alert('Cover upload failed: ' + (e?.message || e));
      }
    };
    input.click();
  }

  /* ---------- Toolbar helpers (LinkedIn like) ---------- */
  function insertImageInEditor(fileUrl) {
    if (!editor) return;
    // rely on CustomImage extension; most image extensions expose 'setImage' command
    if (editor.chain) editor.chain().focus().setImage({ src: fileUrl }).run();
  }

  async function chooseImageForEditor() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const url = await uploadToBucket('images', file);
        insertImageInEditor(url);
      } catch (e) {
        console.error('Image upload failed:', e);
        alert('Image upload failed: ' + (e?.message || e));
      }
    };
    input.click();
  }

  function promptForLink() {
    const url = prompt('Enter URL (include https://)');
    if (!url) return;
    // If the user has selection, set link on selection, otherwise insert linked text
    if (!editor) return;
    if (editor.state.selection && !editor.state.selection.empty) {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
    } else {
      const text = prompt('Link text (optional)') || url;
      editor.chain().focus().insertContent({ type: 'text', text }).setLink({ href: url }).run();
    }
  }

  function toggleHeading(level = 1) {
    if (!editor) return;
    editor.chain().focus().toggleHeading({ level }).run();
  }

  /* ---------- Save Draft ---------- */
  async function saveDraft() {
    const html = editor?.getHTML() || '';
    const tags = tagsInput.split(',').map((t) => t.trim()).filter(Boolean);
    const draftSlug = slug || toSlug(title) || `untitled-${Date.now()}`;

    const payload = {
      author_id: user.id,
      title,
      slug: draftSlug,
      section,
      excerpt,
      content_md: html,
      cover_url: coverUrl || null,
      tags,
      status: 'draft',
    };

    setSaving(true);
    setErrorText('');
    try {
      let result;
      if (draftId) {
        result = await supabase
          .from('articles')
          .update(payload)
          .eq('id', draftId)
          .select('id, slug')
          .maybeSingle();
      } else {
        result = await supabase
          .from('articles')
          .insert([payload])
          .select('id, slug')
          .maybeSingle();
      }

      const { data, error } = result || {};
      if (error) {
        console.error('Save draft supabase error:', error);
        const msg = error?.message || JSON.stringify(error);
        setErrorText(`Save failed: ${msg}`);
        return;
      }
      if (!data) {
        setErrorText('Save failed: no data returned from server.');
        return;
      }

      setDraftId(data.id);
      setSlug(data.slug);
      setErrorText('');
    } catch (err) {
      console.error('Save draft error:', err);
      const msg = err?.message || JSON.stringify(err);
      setErrorText(`Save failed: ${msg}`);
    } finally {
      setSaving(false);
    }
  }

  /* ---------- Publish ---------- */
  async function publishArticle(e) {
    e.preventDefault();
    setErrorText('');
    const html = (editor?.getHTML() || '').trim();
    if (!title || !excerpt || !html || html === '<p></p>') {
      setErrorText('Title, excerpt, and content are required.');
      return;
    }

    let articleSlug = slug;
    if (!articleSlug) {
      articleSlug = await generateUniqueSlug(title);
      setSlug(articleSlug);
    }

    const tags = tagsInput.split(',').map((t) => t.trim()).filter(Boolean);

    const record = {
      id: draftId ?? undefined,
      author_id: user.id,
      title,
      slug: articleSlug,
      section,
      excerpt,
      content_md: html,
      cover_url: coverUrl || null,
      tags,
      status: publishNow ? 'published' : 'draft',
      published_at: publishNow ? new Date().toISOString() : null,
    };

    setSaving(true);
    try {
      const { data, error } = await supabase
        .from('articles')
        .upsert(record)
        .select('id, slug, status')
        .maybeSingle();

      if (error) {
        console.error('Publish supabase error:', error);
        const msg = error?.message || JSON.stringify(error);
        setErrorText(`Publish failed: ${msg}`);
        return;
      }
      if (!data) {
        setErrorText('Publish failed: no data returned from server.');
        return;
      }

      if (data?.status === 'published') {
        navigate(`/article/${data.slug}`);
      } else {
        // saved as draft
        setDraftId(data.id);
        setSlug(data.slug);
        alert('Draft saved. Toggle “Publish immediately” to publish.');
      }
    } catch (err) {
      console.error('Publish error:', err);
      const msg = err?.message || JSON.stringify(err);
      setErrorText(`Publish failed: ${msg}`);
    } finally {
      setSaving(false);
    }
  }

  /* ---------- Derived ---------- */
  const html = editor?.getHTML() || '';
  const minutes = useMemo(() => readingTime(html), [html]);
  const words = useMemo(() => wordCountFromHTML(html), [html]);

  /* ---------- Render ---------- */
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">
          {editSlug ? 'Edit Article' : 'Write a New Article'}
        </h1>

        {/* COVER UPLOAD */}
        <div className="mb-6">
          {coverUrl ? (
            <div>
              <img src={coverUrl} alt="Cover" className="w-full rounded-xl border" />
              <div className="mt-3 flex gap-2">
                <Button variant="outline" onClick={chooseCover}>Change cover</Button>
                <Button variant="ghost" onClick={() => setCoverUrl('')}>Remove</Button>
              </div>
            </div>
          ) : (
            <div
              className="w-full h-52 rounded-xl border border-dashed flex items-center justify-center cursor-pointer bg-white"
              onClick={chooseCover}
            >
              <span className="text-sm text-gray-500">Add a cover image (click to upload)</span>
            </div>
          )}
        </div>

        {/* META FIELDS */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Title</label>
            <input
              className="w-full p-3 rounded-lg border bg-white text-black"
              placeholder="Compelling headline…"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Section</label>
            <select
              className="w-full p-3 rounded-lg border bg-white text-black"
              value={section}
              onChange={(e) => setSection(e.target.value)}
            >
              {SECTIONS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Tags</label>
            <input
              className="w-full p-3 rounded-lg border bg-white text-black"
              placeholder="private equity, m&a, markets"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
            />
          </div>
          <div className="md:col-span-2">
            <label className="block text-sm font-medium mb-1">Excerpt</label>
            <input
              className="w-full p-3 rounded-lg border bg-white text-black"
              placeholder="1–2 sentence summary"
              value={excerpt}
              onChange={(e) => setExcerpt(e.target.value)}
            />
          </div>
        </div>

        {/* LINKEDIN-LIKE TOOLBAR */}
        <div className="flex items-center gap-2 mb-3 bg-white p-3 rounded-full shadow-sm">
          <select
            value={editor?.isActive('heading') ? 'Heading' : 'Paragraph'}
            onChange={(e) => {
              if (e.target.value === 'Heading') toggleHeading(1);
              else editor?.chain().focus().setParagraph().run();
            }}
            className="px-2 py-1 rounded"
          >
            <option>Paragraph</option>
            <option>Heading</option>
          </select>

          <button
            type="button"
            onClick={() => editor?.chain().focus().toggleBold().run()}
            className="px-2 py-1 rounded"
            title="Bold"
          >
            B
          </button>

          <button
            type="button"
            onClick={() => editor?.chain().focus().toggleItalic().run()}
            className="px-2 py-1 rounded"
            title="Italic"
          >
            I
          </button>

          <button
            type="button"
            onClick={() => editor?.chain().focus().toggleBulletList().run()}
            className="px-2 py-1 rounded"
            title="Bulleted list"
          >
            • List
          </button>

          <button
            type="button"
            onClick={() => editor?.chain().focus().toggleOrderedList().run()}
            className="px-2 py-1 rounded"
            title="Numbered list"
          >
            1. List
          </button>

          <button
            type="button"
            onClick={() => editor?.chain().focus().toggleBlockquote().run()}
            className="px-2 py-1 rounded"
            title="Quote"
          >
            “ ”
          </button>

          <button
            type="button"
            onClick={() => editor?.chain().focus().toggleCodeBlock().run()}
            className="px-2 py-1 rounded"
            title="Code block"
          >
            {'</>'}
          </button>

          <button
            type="button"
            onClick={promptForLink}
            className="px-2 py-1 rounded"
            title="Add link"
          >
            🔗
          </button>

          <button
            type="button"
            onClick={chooseImageForEditor}
            className="px-2 py-1 rounded ml-2"
            title="Insert image"
          >
            🖼️
          </button>

          <div className="ml-auto text-sm text-gray-500">
            {minutes} min · {words} words
          </div>
        </div>

        {/* EDITOR */}
        <div className="bg-white text-black border rounded-xl p-5 min-h-[360px] shadow-sm">
          {editor ? (
            <EditorContent editor={editor} className="tiptap" />
          ) : (
            <div className="text-gray-500 text-center py-10">Loading editor…</div>
          )}
        </div>

        {errorText && <p className="mt-3 text-sm text-red-600">{errorText}</p>}

        {/* FOOTER */}
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Button variant="outline" onClick={saveDraft} disabled={saving}>
            {saving ? 'Saving…' : 'Save draft'}
          </Button>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={publishNow}
              onChange={(e) => setPublishNow(e.target.checked)}
            />
            Publish immediately
          </label>
          <Button onClick={publishArticle} disabled={saving}>
            {saving ? 'Publishing…' : 'Save / Publish'}
          </Button>
        </div>
      </div>
    </div>
  );
}
