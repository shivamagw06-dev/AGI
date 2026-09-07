// src/components/WriteArticle.jsx
import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import ImageExtension from '@tiptap/extension-image';
import Link from '@tiptap/extension-link';
import { supabase } from '@/lib/supabaseClient';
import apiFetch from '../utils/apiFetch'; // <-- fixed: top-level import

// --- config
const STORAGE_BUCKET_COVERS = 'covers';
const STORAGE_BUCKET_IMAGES = 'images';
const LOCAL_DRAFT_PREFIX = 'agib:draft:';

// --- map between UI keys (kebab-case) and DB labels (title-case)
const SECTION_LABEL_MAP = {
  'live-articles': 'Live Articles',
  'research-notes': 'Research Notes',
  'deal-tracker': 'Deal Tracker',
  'markets': 'Markets',
  'opinions-editorials': 'Opinions & Editorials',
  'uncategorized': 'Uncategorized',
};
function toDbSectionLabel(key) {
  return SECTION_LABEL_MAP[key] ?? key;
}

// --- small UI helper
function ToolbarButton({ label, onClick, title, className = '' }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title || label}
      className={`px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 focus:outline-none text-sm ${className}`}
    >
      {label}
    </button>
  );
}

// dedupe helper for tiptap extensions
function dedupeExtensions(exts = []) {
  const seen = new Set();
  const out = [];
  for (const e of exts) {
    const name = e?.name ?? (e?.constructor && e.constructor.name) ?? String(e);
    if (!seen.has(name)) {
      seen.add(name);
      out.push(e);
    }
  }
  return out;
}

// small helper to make excerpt from HTML
function htmlToExcerpt(html = '', max = 300) {
  const plain = String(html).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
  return plain.length > max ? plain.slice(0, max).trim() + '…' : plain;
}

export default function WriteArticle() {
  const navigate = useNavigate();

  // --- states
  const [title, setTitle] = useState(() => localStorage.getItem(`${LOCAL_DRAFT_PREFIX}title`) || '');
  const [tags, setTags] = useState(() => {
    try {
      const raw = localStorage.getItem(`${LOCAL_DRAFT_PREFIX}tags`);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });
  const [section, setSection] = useState(() => localStorage.getItem(`${LOCAL_DRAFT_PREFIX}section`) || 'live-articles');

  // cover
  const [coverFile, setCoverFile] = useState(null);
  const [coverPreview, setCoverPreview] = useState(() => localStorage.getItem(`${LOCAL_DRAFT_PREFIX}coverPreview`) || '');
  const [coverPublicUrl, setCoverPublicUrl] = useState(() => localStorage.getItem(`${LOCAL_DRAFT_PREFIX}coverPublicUrl`) || '');
  const [coverUploading, setCoverUploading] = useState(false);

  const [coverHeight, setCoverHeight] = useState(() => Number(localStorage.getItem(`${LOCAL_DRAFT_PREFIX}coverHeight`)) || 320);
  const [coverPosX, setCoverPosX] = useState(() => Number(localStorage.getItem(`${LOCAL_DRAFT_PREFIX}coverPosX`)) || 50);
  const [coverFitMode, setCoverFitMode] = useState(() => localStorage.getItem(`${LOCAL_DRAFT_PREFIX}coverFitMode`) || 'fill'); // 'fill'|'contain'|'compact'
  const [coverZoom, setCoverZoom] = useState(() => Number(localStorage.getItem(`${LOCAL_DRAFT_PREFIX}coverZoom`)) || 100);

  // sections & options
  const [sectionsSelected, setSectionsSelected] = useState(() => {
    try {
      const raw = localStorage.getItem(`${LOCAL_DRAFT_PREFIX}sectionsSelected`);
      return raw ? JSON.parse(raw) : ['live-articles'];
    } catch {
      return ['live-articles'];
    }
  });
  const [lockImageSize, setLockImageSize] = useState(() => {
    try {
      const r = localStorage.getItem(`${LOCAL_DRAFT_PREFIX}lockImageSize`);
      return r ? JSON.parse(r) : true;
    } catch {
      return true;
    }
  });

  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);

  // selected image (to show inline toolbar)
  const [selectedImageAttrsState, setSelectedImageAttrsState] = useState(null);

  // TipTap extensions computed + deduped
  const extensions = useMemo(
    () =>
      dedupeExtensions([
        StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
        Placeholder.configure({ placeholder: 'Write your article. Use the image button to insert visuals.' }),
        ImageExtension.configure({ inline: false, allowBase64: false }),
        Link.configure({ openOnClick: true }),
      ]),
    []
  );

  // --- TipTap editor
  const editor = useEditor({
    extensions,
    content: localStorage.getItem(`${LOCAL_DRAFT_PREFIX}content`) || '<p></p>',
    editorProps: {
      attributes: {
        class: 'prose lg:prose-lg focus:outline-none dark:prose-invert',
      },
    },
  });

  // --- autosave debounced
  useEffect(() => {
    if (!editor) return;
    let t;
    const save = () => {
      try {
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}content`, editor.getHTML());
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}title`, title);
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}tags`, JSON.stringify(tags));
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}section`, section);
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPreview`, coverPreview || '');
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPublicUrl`, coverPublicUrl || '');
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverHeight`, String(coverHeight));
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPosX`, String(coverPosX));
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverFitMode`, coverFitMode);
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverZoom`, String(coverZoom));
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}sectionsSelected`, JSON.stringify(sectionsSelected));
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}lockImageSize`, JSON.stringify(lockImageSize));
      } catch (e) {
        console.warn('Autosave failed', e);
      }
    };
    const handler = () => {
      clearTimeout(t);
      t = setTimeout(save, 700);
    };
    editor.on('update', handler);
    editor.on('selectionUpdate', handler);
    return () => {
      clearTimeout(t);
      editor.off('update', handler);
      editor.off('selectionUpdate', handler);
    };
  }, [editor, title, tags, section, coverPreview, coverPublicUrl, coverHeight, coverPosX, coverFitMode, coverZoom, sectionsSelected, lockImageSize]);

  // --- upload helper (returns public URL)
  const uploadToBucket = useCallback(async (bucket, file) => {
    if (!file) return null;
    const ext = file.name.split('.').pop();
    const path = `${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`;

    const { data: uploadData, error: uploadError } = await supabase.storage.from(bucket).upload(path, file, { cacheControl: '3600', upsert: false });
    if (uploadError) {
      console.error('Supabase upload error', uploadError);
      throw uploadError;
    }

    try {
      const urlRes = await supabase.storage.from(bucket).getPublicUrl(path);
      const publicUrl =
        urlRes?.data?.publicUrl ?? urlRes?.data?.publicURL ?? urlRes?.publicUrl ?? urlRes?.publicURL ?? urlRes?.public_url ?? null;
      return publicUrl;
    } catch (err) {
      console.warn('getPublicUrl returned an unexpected shape', err);
      const fallback = supabase.storage.from(bucket).getPublicUrl(path);
      const publicUrl =
        fallback?.data?.publicUrl ?? fallback?.data?.publicURL ?? fallback?.publicUrl ?? fallback?.publicURL ?? fallback?.public_url ?? null;
      return publicUrl;
    }
  }, []);

  // --- cover change: immediate preview + upload
  const onCoverChange = async (e) => {
    const file = e.target.files?.[0] || null;
    if (!file) return;
    setCoverFile(file);

    try {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setCoverPreview(ev.target.result);
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPreview`, ev.target.result);
      };
      reader.readAsDataURL(file);
    } catch (err) {
      console.warn('Preview generation failed', err);
    }

    setCoverUploading(true);
    setError(null);
    try {
      const publicUrl = await uploadToBucket(STORAGE_BUCKET_COVERS, file);
      if (publicUrl) {
        setCoverPublicUrl(publicUrl);
        setCoverPreview(publicUrl);
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPublicUrl`, publicUrl);
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPreview`, publicUrl);
      }
    } catch (err) {
      console.error('Cover upload failed', err);
      setError(err?.message || 'Cover upload failed');
    } finally {
      setCoverUploading(false);
      e.target.value = '';
    }
  };

  // --- remove cover locally (doesn't delete from storage)
  const removeCover = () => {
    setCoverFile(null);
    setCoverPreview('');
    setCoverPublicUrl('');
    localStorage.removeItem(`${LOCAL_DRAFT_PREFIX}coverPreview`);
    localStorage.removeItem(`${LOCAL_DRAFT_PREFIX}coverPublicUrl`);
  };

  // --- insert inline image: upload & insert node (stable callback)
  const handleInsertImage = useCallback(
    async (file) => {
      if (!editor || !file) return;
      setError(null);
      try {
        const url = await uploadToBucket(STORAGE_BUCKET_IMAGES, file);
        if (!url) throw new Error('Image upload returned no URL');

        const style = lockImageSize ? 'max-width:800px;width:100%;height:auto;' : 'width:100%;';
        editor.chain().focus().setImage({ src: url, alt: file.name, title: file.name, style, 'data-mode': 'full' }).run();
        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}content`, editor.getHTML());
      } catch (e) {
        console.error('Insert image failed', e);
        setError(e?.message || 'Image upload failed');
      }
    },
    [editor, lockImageSize, uploadToBucket]
  );

  const onInsertImageChange = (e) => {
    const f = e.target.files?.[0] || null;
    if (f) handleInsertImage(f);
    e.target.value = '';
  };

  // --- drag & paste support for inline images
  useEffect(() => {
    if (!editor) return;
    const view = editor.view;
    if (!view) return;

    const dropHandler = (event) => {
      const dt = event.dataTransfer;
      if (dt && dt.files && dt.files.length) {
        event.preventDefault();
        Array.from(dt.files).forEach((file) => {
          if (file.type.startsWith('image/')) handleInsertImage(file);
        });
      }
    };
    const pasteHandler = (event) => {
      const clipboard = event.clipboardData;
      if (clipboard && clipboard.files && clipboard.files.length) {
        Array.from(clipboard.files).forEach((file) => {
          if (file.type.startsWith('image/')) handleInsertImage(file);
        });
      }
    };

    view.dom.addEventListener('drop', dropHandler);
    view.dom.addEventListener('paste', pasteHandler);
    return () => {
      view.dom.removeEventListener('drop', dropHandler);
      view.dom.removeEventListener('paste', pasteHandler);
    };
  }, [editor, handleInsertImage, lockImageSize]);

  // --- selected image helpers (used by toolbar)
  const selectedImageAttrs = () => {
    if (!editor) return null;
    const { node } = editor.state.selection;
    if (node && node.type?.name === 'image') return node.attrs || null;
    try {
      const { $from } = editor.state.selection;
      const nodeAfter = $from.nodeAfter;
      if (nodeAfter && nodeAfter.type?.name === 'image') return nodeAfter.attrs || null;
    } catch {
      // ignore
    }
    return null;
  };

  // Keep local state for showing toolbar
  useEffect(() => {
    if (!editor) return;
    const update = () => {
      setSelectedImageAttrsState(selectedImageAttrs());
    };
    editor.on('selectionUpdate', update);
    editor.on('update', update);
    update();
    return () => {
      editor.off('selectionUpdate', update);
      editor.off('update', update);
    };
  }, [editor]);

  const updateSelectedImage = (attrsUpdate) => {
    if (!editor) return;
    const attrs = selectedImageAttrs();
    if (attrs && attrs.src) {
      editor.chain().focus().updateAttributes('image', { ...attrs, ...attrsUpdate }).run();
      localStorage.setItem(`${LOCAL_DRAFT_PREFIX}content`, editor.getHTML());
      setSelectedImageAttrsState({ ...attrs, ...attrsUpdate });
      return;
    }
    // fallback: find last image and update
    const json = editor.getJSON();
    let lastImage = null;
    const walk = (node) => {
      if (!node) return;
      if (node.type === 'image') lastImage = node;
      if (node.content) node.content.forEach(walk);
    };
    walk(json);
    if (lastImage?.attrs?.src) {
      editor.chain().focus().updateAttributes('image', { ...lastImage.attrs, ...attrsUpdate }).run();
      localStorage.setItem(`${LOCAL_DRAFT_PREFIX}content`, editor.getHTML());
    }
  };

  const setSelectedImageMode = (mode) => {
    if (mode === 'full')
      updateSelectedImage({
        style: lockImageSize ? 'max-width:800px;width:100%;height:auto;' : 'width:100%;',
        'data-mode': 'full',
      });
    else if (mode === 'center')
      updateSelectedImage({
        style: (lockImageSize ? 'max-width:800px;' : '') + 'display:block;margin-left:auto;margin-right:auto;width:75%;height:auto;',
        'data-mode': 'center',
      });
    else if (mode === 'compact')
      updateSelectedImage({
        style: 'width:300px;height:auto;display:block;margin-left:auto;margin-right:0;float:left;margin-right:16px;',
        'data-mode': 'compact',
      });
  };

  const setSelectedImageWidth = (p) => {
    const base = lockImageSize ? 'max-width:800px;' : '';
    updateSelectedImage({ style: `${base}width:${p}%;height:auto;` });
  };

  const removeSelectedImage = () => {
    if (!editor) return;
    const node = editor.state.selection.node;
    if (node && node.type?.name === 'image') {
      editor.chain().focus().deleteSelection().run();
      localStorage.setItem(`${LOCAL_DRAFT_PREFIX}content`, editor.getHTML());
      setSelectedImageAttrsState(null);
      return;
    }
    // fallback remove last image
    const json = editor.getJSON();
    let removed = false;
    const walkAndRemove = (node) => {
      if (!node || removed) return node;
      if (node.type === 'image') {
        removed = true;
        return null;
      }
      if (node.content) {
        const newContent = node.content.map(walkAndRemove).filter(Boolean);
        return { ...node, content: newContent };
      }
      return node;
    };
    const out = walkAndRemove(json);
    if (removed) {
      editor.commands.setContent(out);
      localStorage.setItem(`${LOCAL_DRAFT_PREFIX}content`, editor.getHTML());
      setSelectedImageAttrsState(null);
    }
  };

  const toggleLockImageSize = () => {
    const next = !lockImageSize;
    setLockImageSize(next);
    localStorage.setItem(`${LOCAL_DRAFT_PREFIX}lockImageSize`, JSON.stringify(next));
    if (next) updateSelectedImage({ style: 'max-width:800px;width:100%;height:auto;' });
  };

  // --- publish/save
  const publish = async (status = 'draft') => {
    setIsSaving(true);
    setError(null);
    try {
      const html = editor ? editor.getHTML() : '';

      // prefer public url else preview
      let cover_url = coverPublicUrl || coverPreview || null;

      // if have a local file but not public url, upload now
      if (coverFile && !coverPublicUrl) {
        try {
          const uploaded = await uploadToBucket(STORAGE_BUCKET_COVERS, coverFile);
          if (uploaded) {
            cover_url = uploaded;
            setCoverPublicUrl(uploaded);
            localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPublicUrl`, uploaded);
            localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPreview`, uploaded);
          }
        } catch (e) {
          console.warn('Cover upload during publish failed', e);
        }
      }

      // compute sections to publish (UI keys)
      const payloadSectionsKeys = Array.from(
        new Set([...(sectionsSelected && sectionsSelected.length ? sectionsSelected : [section || 'live-articles']), 'live-articles'])
      );

      // convert UI keys to DB labels
      const payloadSectionsLabels = payloadSectionsKeys.map((k) => toDbSectionLabel(k));
      // pick last chosen label as main section (keeps previous behavior)
      const payloadSectionLabel = payloadSectionsLabels[payloadSectionsLabels.length - 1] || toDbSectionLabel('live-articles');

      const { data: userData, error: userErr } = await supabase.auth.getUser();
      if (userErr) console.warn('supabase.auth.getUser error', userErr);
      const user = userData?.user ?? null;

      // create excerpt from html (plain text)
      const excerpt = htmlToExcerpt(html, 320);

      const payload = {
        title: title || 'Untitled',
        content: html,
        content_md: html,
        excerpt,
        status,
        cover_url,
        cover_height: coverHeight,
        cover_pos_x: coverPosX,
        tags: tags.length ? tags : null,
        sections: payloadSectionsLabels,
        section: payloadSectionLabel,
        author_id: user?.id ?? null,
        author: user?.email ?? null,
      };

      const { data, error: insertError } = await supabase.from('articles').insert(payload).select('id,slug').single();
      if (insertError) {
        console.error('Insert error', insertError);
        throw insertError;
      }

      // If published, notify subscribers (best-effort; don't fail overall publish)
      if (status === 'published') {
        try {
          await apiFetch('/api/notify-subscribers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              articleId: data?.id ?? null,
              title: payload.title,
              slug: data?.slug ?? data?.id,
              body: html,
              excerpt,
              section: payloadSectionLabel,
              coverUrl: cover_url,
              author: user?.user_metadata?.full_name || user?.email || 'AGI Research Desk',
              publishedAt: new Date().toISOString(),
            }),
          });
        } catch (notifyErr) {
          // log and continue
          console.warn('Failed to notify subscribers', notifyErr);
        }
      }

      // clear local storage
      [
        'content',
        'title',
        'tags',
        'coverPreview',
        'coverPublicUrl',
        'section',
        'coverHeight',
        'coverPosX',
        'coverFitMode',
        'coverZoom',
        'sectionsSelected',
        'lockImageSize',
      ].forEach((k) => localStorage.removeItem(`${LOCAL_DRAFT_PREFIX}${k}`));

      const slug = data?.slug || data?.id;
      if (status === 'published') navigate(`/article/${slug}`);
      else {
        setIsSaving(false);
      }
    } catch (e) {
      console.error('Publish failed', e);
      setError(e?.message || String(e));
      setIsSaving(false);
    }
  };

  // --- tag helpers
  const addTag = (raw) => {
    const t = raw.trim().toLowerCase();
    if (!t) return;
    if (tags.includes(t)) return;
    const next = [...tags, t].slice(0, 6);
    setTags(next);
    localStorage.setItem(`${LOCAL_DRAFT_PREFIX}tags`, JSON.stringify(next));
  };
  const removeTag = (t) => {
    const next = tags.filter((x) => x !== t);
    setTags(next);
    localStorage.setItem(`${LOCAL_DRAFT_PREFIX}tags`, JSON.stringify(next));
  };

  // --- link helper
  const addLink = () => {
    if (!editor) return;
    const url = window.prompt('Enter URL (https://...)');
    if (!url) return;
    editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run();
  };

  const canPublish = useMemo(() => !!title.trim() && editor && editor.getText().trim().length > 50 && !coverUploading, [title, editor, coverUploading]);

  // --- UI render
  return (
    <div className="max-w-5xl mx-auto px-4 md:px-6 py-10">
      <div className="bg-white dark:bg-gray-900 rounded-lg overflow-hidden shadow-sm">
        {/* COVER */}
        <div className="relative bg-gray-50 dark:bg-gray-800 border-b">
          {coverPreview ? (
            <div className="w-full relative overflow-hidden" style={{ height: coverFitMode === 'compact' ? 120 : `${coverHeight}px` }}>
              <img
                src={coverPreview}
                alt="cover"
                className="w-full h-full object-center transition-transform"
                style={{
                  objectFit: coverFitMode === 'contain' ? 'contain' : 'cover',
                  objectPosition: `${coverPosX}% center`,
                  transform: `scale(${coverFitMode === 'fill' ? coverZoom / 100 : 1})`,
                }}
              />

              {coverUploading && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/30">
                  <div className="bg-white dark:bg-gray-800 px-3 py-2 rounded shadow text-sm">Uploading cover...</div>
                </div>
              )}
            </div>
          ) : (
            <div className="w-full h-80 flex items-center justify-center text-gray-400 dark:text-gray-400">
              <div className="text-center">
                <div className="mb-3 text-lg md:text-2xl text-gray-700 dark:text-gray-200">Add a cover image to your article</div>
                <label className="inline-flex items-center gap-2 cursor-pointer">
                  <input type="file" accept="image/*" onChange={onCoverChange} className="hidden" />
                  <span className="px-4 py-2 rounded-full border text-sm bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200">Upload cover</span>
                </label>
              </div>
            </div>
          )}

          <div className="absolute right-4 bottom-4 flex gap-2">
            <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200">Draft</span>
          </div>
        </div>

        {/* HEADER */}
        <div className="p-6">
          <input
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              localStorage.setItem(`${LOCAL_DRAFT_PREFIX}title`, e.target.value);
            }}
            placeholder="Write a compelling headline..."
            className="w-full text-4xl md:text-5xl font-extrabold outline-none placeholder-gray-400 dark:placeholder-gray-500 mb-4 text-gray-900 dark:text-gray-100"
          />

          <div className="mb-4 flex items-start justify-between gap-4">
            <div className="flex-1 flex items-center gap-2 bg-white dark:bg-gray-800 rounded-md px-2 py-1 shadow-sm">
              <ToolbarButton label="B" onClick={() => editor?.chain().focus().toggleBold().run()} title="Bold" />
              <ToolbarButton label="I" onClick={() => editor?.chain().focus().toggleItalic().run()} title="Italic" />
              <ToolbarButton label="H1" onClick={() => editor?.chain().focus().toggleHeading({ level: 1 }).run()} title="H1" />
              <ToolbarButton label="H2" onClick={() => editor?.chain().focus().toggleHeading({ level: 2 }).run()} title="H2" />
              <ToolbarButton label="•" onClick={() => editor?.chain().focus().toggleBulletList().run()} title="Bullet list" />
              <ToolbarButton label="1." onClick={() => editor?.chain().focus().toggleOrderedList().run()} title="Numbered list" />
              <ToolbarButton label="❝" onClick={() => editor?.chain().focus().toggleBlockquote().run()} title="Quote" />
              <ToolbarButton label="</>" onClick={() => editor?.chain().focus().toggleCodeBlock().run()} title="Code block" />
              <ToolbarButton label="Link" onClick={addLink} title="Insert link" />
              <label className="cursor-pointer ml-1 inline-flex items-center">
                <input type="file" accept="image/*" onChange={onInsertImageChange} className="hidden" />
                <span className="px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800">Image</span>
              </label>
            </div>

            <div className="flex flex-col items-end gap-2">
              <div className="flex items-center gap-3">
                <div className="mr-2">
                  <div className="text-sm font-medium mb-1 text-gray-700 dark:text-gray-200">Post to</div>
                  <div className="flex gap-2 items-center flex-wrap text-gray-700 dark:text-gray-200 text-sm">
                    {['live-articles', 'research-notes', 'deal-tracker', 'markets', 'opinions-editorials', 'uncategorized'].map((c) => {
                      const label =
                        c === 'live-articles'
                          ? 'Live Articles'
                          : c === 'research-notes'
                          ? 'Research Notes'
                          : c === 'deal-tracker'
                          ? 'Deal Tracker'
                          : c === 'markets'
                          ? 'Markets'
                          : c === 'opinions-editorials'
                          ? 'Opinions & Editorials'
                          : 'Other';
                      return (
                        <label key={c} className="inline-flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={sectionsSelected.includes(c)}
                            onChange={(e) => {
                              let next = [];
                              if (e.target.checked) next = Array.from(new Set([...sectionsSelected, c]));
                              else next = sectionsSelected.filter((x) => x !== c);
                              if (!next.includes('live-articles')) next = ['live-articles', ...next];
                              setSectionsSelected(next);
                              localStorage.setItem(`${LOCAL_DRAFT_PREFIX}sectionsSelected`, JSON.stringify(next));
                            }}
                            disabled={c === 'live-articles'}
                          />
                          <span>{label}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>

                <input
                  type="text"
                  placeholder="Add a tag and press Enter (e.g. macro, deals)"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      addTag(e.target.value);
                      e.target.value = '';
                    }
                  }}
                  className="border rounded-md px-3 py-2 text-sm text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-800"
                />
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => publish('draft')}
                  disabled={isSaving || coverUploading}
                  className="px-4 py-2 rounded-md border hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-60 text-gray-800 dark:text-gray-100"
                >
                  Save draft
                </button>

                <button onClick={() => publish('published')} disabled={!canPublish || isSaving} className="px-4 py-2 rounded-md bg-blue-600 text-white font-medium disabled:opacity-60">
                  {isSaving ? 'Saving...' : coverUploading ? 'Uploading cover...' : 'Publish'}
                </button>
              </div>
            </div>
          </div>

          {/* Editor */}
          <div>
            <EditorContent editor={editor} />
          </div>

          {/* Inline image toolbar (linked to selected image) */}
          {selectedImageAttrsState && (
            <div className="mt-4 border-t pt-4">
              <div className="flex items-center gap-3">
                <div className="text-sm text-gray-700 dark:text-gray-200">Selected image:</div>
                <div className="flex gap-2">
                  <button onClick={() => setSelectedImageMode('full')} className="px-2 py-1 rounded border text-sm">
                    Full
                  </button>
                  <button onClick={() => setSelectedImageMode('center')} className="px-2 py-1 rounded border text-sm">
                    Center
                  </button>
                  <button onClick={() => setSelectedImageMode('compact')} className="px-2 py-1 rounded border text-sm">
                    Compact
                  </button>
                </div>

                <div className="flex gap-2 ml-4">
                  {[25, 50, 75, 100].map((p) => (
                    <button key={p} onClick={() => setSelectedImageWidth(p)} className="px-2 py-1 rounded border text-sm">
                      {p}%
                    </button>
                  ))}
                </div>

                <div className="ml-4">
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={lockImageSize} onChange={toggleLockImageSize} />
                    <span className="text-sm">Lock image size</span>
                  </label>
                </div>

                <div className="ml-auto">
                  <button onClick={removeSelectedImage} className="px-3 py-1 rounded border text-sm text-red-600 dark:text-red-400">
                    Remove
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Image sizing + cover controls */}
          <div className="mt-6 border-t pt-4 grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
            <div className="col-span-2 space-y-2">
              <div className="flex items-center gap-4">
                <div>
                  <label className="block text-sm text-gray-700 dark:text-gray-200">Cover height (px)</label>
                  <input
                    type="range"
                    min={120}
                    max={600}
                    value={coverHeight}
                    onChange={(e) => {
                      const v = Number(e.target.value);
                      setCoverHeight(v);
                      localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverHeight`, String(v));
                    }}
                    disabled={coverFitMode === 'compact'}
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-700 dark:text-gray-200">Fit mode</label>
                  <select
                    value={coverFitMode}
                    onChange={(e) => {
                      setCoverFitMode(e.target.value);
                      localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverFitMode`, e.target.value);
                    }}
                    className="border rounded px-2 py-1"
                  >
                    <option value="fill">Fill (cover)</option>
                    <option value="contain">Fit (contain)</option>
                    <option value="compact">Compact (minimized)</option>
                  </select>
                </div>

                {coverFitMode === 'fill' && (
                  <div>
                    <label className="block text-sm text-gray-700 dark:text-gray-200">Zoom (%)</label>
                    <input
                      type="range"
                      min={100}
                      max={150}
                      value={coverZoom}
                      onChange={(e) => {
                        const v = Number(e.target.value);
                        setCoverZoom(v);
                        localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverZoom`, String(v));
                      }}
                    />
                  </div>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm text-gray-700 dark:text-gray-200">Cover focus (X %)</label>
              <input
                type="range"
                min={0}
                max={100}
                value={coverPosX}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setCoverPosX(v);
                  localStorage.setItem(`${LOCAL_DRAFT_PREFIX}coverPosX`, String(v));
                }}
              />
            </div>

            <div className="col-span-3 flex gap-2">
              <label className="inline-flex items-center">
                <input type="file" accept="image/*" onChange={onCoverChange} className="hidden" />
                <span className="px-3 py-1 rounded border bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200">Change cover</span>
              </label>

              <button type="button" className="px-3 py-1 rounded border bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200" onClick={removeCover}>
                Remove cover
              </button>

              <button type="button" onClick={() => window.open('/sections/opinions-editorials', '_blank')} className="ml-auto px-3 py-1 rounded border bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200">
                Preview in Opinions
              </button>
            </div>
          </div>

          {/* Right-side preview (desktop) */}
          <div className="mt-6 hidden lg:block">
            <div className="border rounded-xl p-4 bg-white dark:bg-gray-800">
              <h4 className="font-semibold text-gray-800 dark:text-gray-100">Article preview</h4>
              <p className="text-sm mt-2 text-gray-600 dark:text-gray-300">Live preview of metadata & cover</p>

              <div className="mt-4">
                {coverPreview ? (
                  <img src={coverPreview} alt="cover preview" className="w-full rounded-lg object-cover h-40" style={{ objectPosition: `${coverPosX}% center` }} />
                ) : (
                  <div className="w-full h-40 rounded-lg bg-gray-100 dark:bg-gray-700 flex items-center justify-center text-sm text-gray-400 dark:text-gray-300">Cover preview</div>
                )}
              </div>

              <div className="mt-3">
                <div className="text-sm font-medium text-gray-800 dark:text-gray-100">Title</div>
                <div className="text-sm text-gray-700 dark:text-gray-200 truncate">{title || '—'}</div>
              </div>

              <div className="mt-3">
                <div className="text-sm font-medium text-gray-800 dark:text-gray-100">Tags</div>
                <div className="flex gap-2 mt-2 flex-wrap">{tags.map((t) => (<span key={t} className="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-800 dark:text-gray-100">#{t}</span>))}</div>
              </div>
            </div>
          </div>

          {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">Error: {error}</p>}
        </div>
      </div>
    </div>
  );
}
