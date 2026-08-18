import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import Link from '@tiptap/extension-link';
import Highlight from '@tiptap/extension-highlight';
import TextAlign from '@tiptap/extension-text-align';
import { TextStyle } from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import HorizontalRule from '@tiptap/extension-horizontal-rule';
import { Table } from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import { Eye, Save, Send, ImageIcon, Loader2, Brain, Mail } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/contexts/AuthContext';
import useCategories from '@/hooks/useCategories';
import EditorToolbar from '@/components/editor/EditorToolbar';
import ArticlePreview from '@/components/editor/ArticlePreview';
import { CustomImage } from '@/extensions/CustomImage';
import { IframeEmbed } from '@/extensions/IframeEmbed';
import {
  generateUniqueSlug,
  HOMEPAGE_LATEST_TAG,
  htmlToExcerpt,
  readingTime,
  toSlug,
  wordCountFromHTML,
} from '@/lib/articleUtils';
import { ingestArticleToIntelligence } from '@/lib/cmsIntelligence';
import { notifySubscribers } from '@/lib/newsletterClient';
import { normalizeArticleSection } from '@/lib/articleSections';
import { RESEARCH_DESK_SECTIONS } from '@/lib/deskSections';
import { canEditArticle, isAdmin } from '@/lib/adminAuth';
import { Button } from '@/components/ui/button';
import { insertImageAtPosition, uploadArticleImage } from '@/lib/articleImageUpload';

const AUTOSAVE_MS = 4000;

function toEmbedUrl(raw) {
  const url = raw.trim();
  if (!url) return null;
  const yt = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([\w-]+)/);
  if (yt) return `https://www.youtube.com/embed/${yt[1]}`;
  if (/vimeo\.com\/(\d+)/.test(url)) return url.replace('vimeo.com/', 'player.vimeo.com/video/');
  return url;
}

export default function ArticleEditor() {
  const { slug: editSlugParam } = useParams();
  const editSlug = editSlugParam ? decodeURIComponent(editSlugParam) : '';
  const navigate = useNavigate();
  const { user } = useAuth();
  const { categories, loading: categoriesLoading } = useCategories();

  const [title, setTitle] = useState('');
  const [slug, setSlug] = useState('');
  const [slugManual, setSlugManual] = useState(false);
  const [metaDescription, setMetaDescription] = useState('');
  const [section, setSection] = useState('Indian Market');
  const [tagsInput, setTagsInput] = useState('');
  const [showInLatest, setShowInLatest] = useState(false);
  const [coverUrl, setCoverUrl] = useState('');
  const [draftId, setDraftId] = useState(null);
  const [status, setStatus] = useState('draft');
  const [saving, setSaving] = useState(false);
  const [notifying, setNotifying] = useState(false);
  const [notifyOnPublish, setNotifyOnPublish] = useState(true);
  const [lastSaved, setLastSaved] = useState(null);
  const [error, setError] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [inlineImageUploading, setInlineImageUploading] = useState(false);
  const [loaded, setLoaded] = useState(!editSlug);
  const [originalAuthorId, setOriginalAuthorId] = useState(null);

  const pendingContentRef = useRef('');
  const autosaveTimer = useRef(null);
  const dirtyRef = useRef(false);

  const extensions = useMemo(
    () => [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      Placeholder.configure({ placeholder: 'Start writing your research or market update…' }),
      Link.configure({ openOnClick: false, autolink: true }),
      CustomImage,
      IframeEmbed,
      Highlight,
      TextStyle,
      Color,
      HorizontalRule,
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    []
  );

  const editor = useEditor({
    extensions,
    content: '<p></p>',
    editorProps: {
      attributes: {
        class:
          'article-editor-content article-prose prose prose-lg max-w-none min-h-[420px] px-8 py-6 focus:outline-none',
      },
    },
    onUpdate: () => {
      dirtyRef.current = true;
    },
  });

  useEffect(() => {
    if (!section) setSection('Indian Market');
  }, [section]);

  useEffect(() => {
    if (!slugManual && title) setSlug(toSlug(title));
  }, [title, slugManual]);

  useEffect(() => {
    if (!editSlug || !user) return;
    let mounted = true;

    (async () => {
      const { data, error: loadError } = await supabase
        .from('articles')
        .select(
          'id, title, slug, section, excerpt, meta_description, content_md, content, cover_url, tags, status, author_id'
        )
        .eq('slug', editSlug)
        .maybeSingle();

      if (!mounted) return;
      if (loadError || !data) {
        setError('Article not found.');
        setLoaded(true);
        return;
      }

      if (!canEditArticle(user, data)) {
        setError('You can only edit articles you uploaded.');
        setLoaded(true);
        return;
      }

      setDraftId(data.id);
      setOriginalAuthorId(data.author_id || user.id);
      setTitle(data.title || '');
      setSlug(data.slug || '');
      setSlugManual(true);
      setMetaDescription(data.meta_description || data.excerpt || '');
      setSection(data.section || '');
      setCoverUrl(data.cover_url || '');
      const loadedTags = Array.isArray(data.tags) ? data.tags : [];
      setTagsInput(loadedTags.filter((tag) => tag !== HOMEPAGE_LATEST_TAG).join(', '));
      setShowInLatest(loadedTags.includes(HOMEPAGE_LATEST_TAG));
      setStatus(data.status || 'draft');

      const html = data.content_md || data.content || '';
      if (editor) editor.commands.setContent(html, false);
      else pendingContentRef.current = html;

      setLoaded(true);
    })();

    return () => {
      mounted = false;
    };
  }, [editSlug, user, editor]);

  useEffect(() => {
    if (editor && pendingContentRef.current) {
      editor.commands.setContent(pendingContentRef.current, false);
      pendingContentRef.current = '';
    }
  }, [editor]);

  const uploadFile = useCallback(
    async (bucket, file) => uploadArticleImage({ userId: user?.id, file, bucket }),
    [user?.id]
  );

  const insertImageFile = useCallback(
    async (file, insertionPosition) => {
      if (!editor || !file || inlineImageUploading) return;
      if (!file.type?.startsWith('image/')) {
        setError('Only image files can be inserted into the article body.');
        return;
      }
      const position = insertionPosition ?? editor.state.selection.anchor;
      try {
        setInlineImageUploading(true);
        setError('');
        const url = await uploadFile('images', file);
        insertImageAtPosition(editor, position, { url, alt: file.name });
        dirtyRef.current = true;
      } catch (err) {
        setError(err?.message || 'Image upload failed');
      } finally {
        setInlineImageUploading(false);
      }
    },
    [editor, inlineImageUploading, uploadFile]
  );

  const insertImage = useCallback(async () => {
    if (!editor || inlineImageUploading) return;
    const insertionPosition = editor.state.selection.anchor;
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (file) await insertImageFile(file, insertionPosition);
    };
    input.click();
  }, [editor, inlineImageUploading, insertImageFile]);

  useEffect(() => {
    if (!editor) return;
    const view = editor.view;
    if (!view?.dom) return;

    const dropHandler = (event) => {
      const files = event.dataTransfer?.files;
      if (!files?.length) return;
      const imageFiles = Array.from(files).filter((file) => file.type.startsWith('image/'));
      if (!imageFiles.length) return;
      event.preventDefault();
      const coords = { left: event.clientX, top: event.clientY };
      const pos = view.posAtCoords(coords)?.pos ?? editor.state.selection.anchor;
      void (async () => {
        for (const file of imageFiles) {
          // eslint-disable-next-line no-await-in-loop
          await insertImageFile(file, pos);
        }
      })();
    };

    const pasteHandler = (event) => {
      const files = event.clipboardData?.files;
      if (!files?.length) return;
      const imageFiles = Array.from(files).filter((file) => file.type.startsWith('image/'));
      if (!imageFiles.length) return;
      event.preventDefault();
      const position = editor.state.selection.anchor;
      void (async () => {
        for (const file of imageFiles) {
          // eslint-disable-next-line no-await-in-loop
          await insertImageFile(file, position);
        }
      })();
    };

    view.dom.addEventListener('drop', dropHandler);
    view.dom.addEventListener('paste', pasteHandler);
    return () => {
      view.dom.removeEventListener('drop', dropHandler);
      view.dom.removeEventListener('paste', pasteHandler);
    };
  }, [editor, insertImageFile]);

  const insertVideo = useCallback(() => {
    const raw = window.prompt('Paste YouTube, Vimeo, or embed URL');
    const src = toEmbedUrl(raw || '');
    if (!src || !editor) return;
    editor.chain().focus().setIframeEmbed({ src, title: 'Video embed', height: 420 }).run();
  }, [editor]);

  const insertChart = useCallback(() => {
    const raw = window.prompt('Paste TradingView or chart embed URL');
    if (!raw?.trim() || !editor) return;
    editor.chain().focus().setIframeEmbed({ src: raw.trim(), title: 'Chart embed', height: 480 }).run();
  }, [editor]);

  const chooseCover = useCallback(async () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = 'image/*';
    input.onchange = async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const url = await uploadFile('covers', file);
        setCoverUrl(url);
        dirtyRef.current = true;
      } catch (err) {
        setError(err?.message || 'Cover upload failed');
      }
    };
    input.click();
  }, [uploadFile]);

  const buildPayload = useCallback(
    (publishStatus) => {
      const html = editor?.getHTML() || '';
      const tags = tagsInput.split(',').map((t) => t.trim()).filter(Boolean);
      if (showInLatest && publishStatus !== 'intelligence') tags.push(HOMEPAGE_LATEST_TAG);
      const excerpt = metaDescription.trim() || htmlToExcerpt(html, 320);
      const safeSection = normalizeArticleSection(section, {
        forIntelligence: publishStatus === 'intelligence',
      });

      const payload = {
        // Keep original uploader on edit; set author only when creating.
        title: title.trim() || 'Untitled',
        slug: slug || toSlug(title) || `draft-${Date.now()}`,
        section: safeSection,
        excerpt,
        content_md: html,
        content: html,
        cover_url: coverUrl || null,
        tags: tags.length ? tags : null,
        status: publishStatus,
      };
      if (!draftId) {
        payload.author_id = user.id;
      } else if (originalAuthorId) {
        payload.author_id = originalAuthorId;
      } else if (!isAdmin(user)) {
        payload.author_id = user.id;
      }

      if (metaDescription.trim()) payload.meta_description = metaDescription.trim();
      if (publishStatus === 'published') payload.published_at = new Date().toISOString();
      // Private intelligence notes must never appear as website posts.
      if (publishStatus === 'intelligence') {
        payload.published_at = null;
        payload.tags = Array.from(
          new Set([...(payload.tags || []), 'intelligence-only', 'agi-private'])
        );
      }

      return payload;
    },
    [editor, tagsInput, showInLatest, metaDescription, user, title, slug, section, coverUrl, draftId, originalAuthorId]
  );

  const persist = useCallback(
    async (publishStatus, { silent = false, ingest = false, stayInEditor = false } = {}) => {
      if (!editor) return null;
      setSaving(true);
      setError('');

      try {
        let articleSlug = slug || (await generateUniqueSlug(title, draftId));
        if (!slugManual) setSlug(articleSlug);

        let payload = { ...buildPayload(publishStatus), slug: articleSlug };

        let result;
        if (draftId) {
          let updateQuery = supabase.from('articles').update(payload).eq('id', draftId);
          if (!isAdmin(user)) {
            updateQuery = updateQuery.eq('author_id', user.id);
          }
          result = await updateQuery.select('id, slug, status').single();
        } else {
          result = await supabase.from('articles').insert(payload).select('id, slug, status').single();
        }

        let { data, error: saveError } = result;

        // Older schemas may not allow the intelligence status yet — keep content saved as draft metadata.
        if (saveError && publishStatus === 'intelligence' && /status|check|constraint/i.test(saveError.message || '')) {
          const fallbackPayload = {
            ...payload,
            status: 'draft',
            section: normalizeArticleSection(payload.section || section, { forIntelligence: true }),
            tags: Array.from(new Set([...(payload.tags || []), 'intelligence-only', 'agi-private'])),
          };
          if (draftId) {
            let fallbackUpdate = supabase.from('articles').update(fallbackPayload).eq('id', draftId);
            if (!isAdmin(user)) fallbackUpdate = fallbackUpdate.eq('author_id', user.id);
            result = await fallbackUpdate.select('id, slug, status').single();
          } else {
            result = await supabase
              .from('articles')
              .insert(fallbackPayload)
              .select('id, slug, status')
              .single();
          }
          ({ data, error: saveError } = result);
          if (!saveError) {
            setError('Saved for intelligence. Run the CMS migration to enable status=intelligence in Supabase.');
          }
        }

        // Section value not in DB check constraint — coerce to a known-safe section and retry once.
        if (saveError && /articles_section_allowed|section_allowed/i.test(saveError.message || '')) {
          const fallbackPayload = {
            ...payload,
            section: publishStatus === 'intelligence' ? 'Intelligence' : 'Research Reports',
          };
          result = draftId
            ? await supabase.from('articles').update(fallbackPayload).eq('id', draftId).select('id, slug, status').single()
            : await supabase.from('articles').insert(fallbackPayload).select('id, slug, status').single();
          ({ data, error: saveError } = result);
          if (!saveError) {
            setSection(fallbackPayload.section);
            setError(
              `Section was adjusted to "${fallbackPayload.section}" because the database section list needs updating. Run the latest CMS section migration in Supabase.`
            );
          }
        }

        if (saveError?.message?.includes('meta_description')) {
          const { meta_description, ...fallbackPayload } = payload;
          result = draftId
            ? await supabase.from('articles').update(fallbackPayload).eq('id', draftId).select('id, slug, status').single()
            : await supabase.from('articles').insert(fallbackPayload).select('id, slug, status').single();
          ({ data, error: saveError } = result);
        }
        if (saveError) throw saveError;

        setDraftId(data.id);
        setSlug(data.slug);
        setStatus(publishStatus === 'intelligence' ? 'intelligence' : data.status);
        setLastSaved(new Date());
        dirtyRef.current = false;

        let ingestResult = null;
        let ingestError = null;
        if (ingest) {
          try {
            ingestResult = await ingestArticleToIntelligence({
              title: title.trim(),
              contentHtml: editor.getHTML(),
              slug: data.slug,
              articleId: data.id,
              section: payload.section || section,
              tags: tagsInput.split(',').map((t) => t.trim()).filter(Boolean),
              status: publishStatus,
              destination: publishStatus === 'published' ? 'website' : 'intelligence',
              onAttempt: ({ phase, label, attempt, maxAttempts }) => {
                if (label) {
                  setError(label);
                } else if (phase === 'enqueue' || phase === 'queued') {
                  setError('Creating intelligence ingest job…');
                } else if (phase === 'waking') {
                  setError('Waking intelligence engine…');
                } else if (phase === 'processing') {
                  setError('Ingesting into institutional memory…');
                } else if (phase === 'retry') {
                  setError(`Worker retrying ingest (${attempt}/${maxAttempts})…`);
                }
              },
            });

            if (ingestResult?.id || ingestResult?.document_id) {
              const docId = ingestResult.document_id || ingestResult.id;
              // Avoid treating job_id as document id
              if (docId && !String(docId).startsWith('job_')) {
                const learnedAt = new Date().toISOString();
                try {
                  await supabase
                    .from('articles')
                    .update({
                      intelligence_document_id: docId,
                      intelligence_ingested_at: learnedAt,
                      last_learned_at: learnedAt,
                      learn_status: 'learned',
                      last_learn_error: null,
                    })
                    .eq('id', data.id);
                } catch {
                  /* optional columns may be missing until migration */
                }
              }
            } else if (ingestResult?.queued || ingestResult?.pending || ingestResult?.poll_timeout) {
              try {
                await supabase
                  .from('articles')
                  .update({
                    learn_status: 'pending',
                    last_learn_error: ingestResult?.job_id
                      ? `Queued job ${ingestResult.job_id}`
                      : 'Queued for background ingest',
                  })
                  .eq('id', data.id);
              } catch {
                /* optional */
              }
            }
            setError('');
          } catch (err) {
            // Article is already saved — do not fail the whole CMS action on engine cold-start.
            ingestError = err?.message || 'Intelligence ingest failed';
            console.warn('[cms] intelligence ingest failed', err);
          }
        }

        let notifyResult = null;
        if (publishStatus === 'published' && notifyOnPublish) {
          const html = editor.getHTML();
          notifyResult = await notifySubscribers({
            title: title.trim(),
            slug: data.slug,
            summary: htmlToExcerpt(html, 280),
            body: html,
            section,
            coverUrl,
          });
        }

        if (!silent && publishStatus === 'published' && !stayInEditor) {
          if (!notifyOnPublish) {
            alert('Published to website. Subscribers were not emailed.');
          } else if (notifyResult?.ok && notifyResult?.sent > 0) {
            alert(
              `Published to ${notifyResult.letter || 'letter'}. Notified ${notifyResult.sent} subscriber${
                notifyResult.sent === 1 ? '' : 's'
              }.`
            );
          } else if (notifyResult && !notifyResult.ok && !notifyResult.skipped) {
            alert('Published to website, but subscriber email notify failed. Check Resend / Render env.');
          }
          navigate(`/article/${data.slug}`);
        } else if (!silent && publishStatus === 'intelligence') {
          if (ingestError) {
            alert(
              `Saved for Intelligence, but ingest job failed (${ingestError}). ` +
                `Your draft is safe. The worker will not ask you to click again for the same version — edit and re-send only if you change the article.`
            );
          } else if (ingestResult?.poll_timeout || (ingestResult?.pending && !ingestResult?.document_id)) {
            alert(
              'Saved for Intelligence. Job is still running in the background (engine may be waking). No need to click Send again.'
            );
          } else if (ingestResult?.document_id) {
            alert('Sent to AGI Intelligence only. This will not appear on the public website.');
          } else {
            alert(
              'Saved for Intelligence and queued. Ingest continues in the background — no need to click Send again.'
            );
          }
        } else if (!silent && ingest && publishStatus === 'published' && stayInEditor) {
          const notifyNote = !notifyOnPublish
            ? ' Subscribers were not emailed.'
            : notifyResult?.ok && notifyResult?.sent > 0
              ? ` Notified ${notifyResult.sent} subscribers.`
              : '';
          const ingestNote = ingestError
            ? ` Intelligence ingest failed (${ingestError}).`
            : ingestResult?.document_id
              ? ' Ingested into AGI Intelligence.'
              : ' Intelligence ingest queued (background worker).';
          alert(`Published to website.${ingestNote}${notifyNote}`);
        }

        if (ingestError && !silent) {
          setError(ingestError);
        }

        return { ...data, ingestResult, notifyResult, ingestError };
      } catch (err) {
        const msg = err?.message || 'Save failed';
        setError(msg);
        if (!silent) alert(msg);
        return null;
      } finally {
        setSaving(false);
      }
    },
    [editor, slug, slugManual, title, draftId, buildPayload, navigate, section, tagsInput, notifyOnPublish, coverUrl]
  );

  const notifyNow = useCallback(async () => {
    if (!editor || notifying) return;
    if (status !== 'published' || !slug) {
      alert('Publish to the website first — the email links to the live article.');
      return;
    }
    if (!window.confirm(`Email "${title.trim()}" to every active subscriber of this letter?`)) return;

    setNotifying(true);
    try {
      const body = editor.getHTML();
      const result = await notifySubscribers({
        title: title.trim(),
        slug,
        summary: htmlToExcerpt(body, 280),
        body,
        section,
        coverUrl,
      });

      if (result?.ok && result?.sent > 0) {
        alert(`Sent to ${result.sent} subscriber${result.sent === 1 ? '' : 's'} (${result.letter || 'letter'}).`);
      } else if (result?.ok) {
        alert(result.reason || 'No matching subscribers for this letter.');
      } else {
        alert(`Notify failed: ${result?.reason || result?.error || 'unknown error'}`);
      }
    } finally {
      setNotifying(false);
    }
  }, [editor, notifying, status, slug, title, section]);

  useEffect(() => {
    if (!editor || !loaded || !user) return;

    autosaveTimer.current = setInterval(() => {
      if (dirtyRef.current && title.trim()) {
        persist('draft', { silent: true });
      }
    }, AUTOSAVE_MS);

    return () => clearInterval(autosaveTimer.current);
  }, [editor, loaded, user, title, persist]);

  const html = editor?.getHTML() || '';
  const words = wordCountFromHTML(html);
  const minutes = readingTime(html);

  if (!loaded) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        <Loader2 className="animate-spin mr-2" size={20} /> Loading editor…
      </div>
    );
  }

  if (editSlug && error && !draftId) {
    return (
      <div className="flex flex-col items-center justify-center h-72 px-6 text-center">
        <p className="text-lg font-semibold text-slate-900 mb-2">Cannot open editor</p>
        <p className="text-slate-500 mb-6 max-w-md">{error}</p>
        <Button onClick={() => navigate('/admin/articles')} className="bg-blue-700 hover:bg-blue-800">
          Back to My Articles
        </Button>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Top bar */}
      <div className="shrink-0 bg-white border-b border-slate-200 px-6 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3 text-sm text-slate-500">
          <span
            className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
              status === 'published'
                ? 'bg-green-100 text-green-700'
                : status === 'intelligence'
                  ? 'bg-violet-100 text-violet-700'
                  : 'bg-amber-100 text-amber-700'
            }`}
          >
            {status === 'intelligence' ? 'intelligence only' : status}
          </span>
          {saving ? (
            <span className="flex items-center gap-1"><Loader2 size={14} className="animate-spin" /> Saving…</span>
          ) : lastSaved ? (
            <span>Saved {lastSaved.toLocaleTimeString()}</span>
          ) : (
            <span>Auto-save enabled</span>
          )}
          <span>· {words} words · {minutes} min read</span>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setPreviewOpen(true)}>
            <Eye size={15} className="mr-1.5" /> Preview
          </Button>
          <Button variant="outline" size="sm" onClick={() => persist('draft')} disabled={saving}>
            <Save size={15} className="mr-1.5" /> Save Draft
          </Button>
          <label
            className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-medium text-slate-700"
            title="If checked, Publish to Website also emails active subscribers"
          >
            <input
              type="checkbox"
              className="h-3.5 w-3.5 accent-blue-700"
              checked={notifyOnPublish}
              onChange={(event) => setNotifyOnPublish(event.target.checked)}
            />
            Notify subscribers
          </label>
          <Button
            size="sm"
            className="bg-blue-700 hover:bg-blue-800"
            onClick={() => persist('published', { ingest: true })}
            disabled={saving || !title.trim()}
            title={
              notifyOnPublish
                ? 'Goes live on the website, emails subscribers, and is studied by AGI Intelligence'
                : 'Goes live on the website without emailing subscribers'
            }
          >
            <Send size={15} className="mr-1.5" /> Publish to Website
          </Button>
          <Button
            size="sm"
            className="bg-violet-700 hover:bg-violet-800"
            onClick={() => persist('intelligence', { ingest: true, stayInEditor: true })}
            disabled={saving || !title.trim()}
            title="Private — AGI studies this. Not shown on the public website."
          >
            <Brain size={15} className="mr-1.5" /> Send to Intelligence
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={notifyNow}
            disabled={notifying || saving || status !== 'published' || !slug}
            title={
              status === 'published'
                ? 'Email this live article to subscribers of its letter'
                : 'Available once the article is published'
            }
          >
            {notifying ? (
              <Loader2 size={15} className="mr-1.5 animate-spin" />
            ) : (
              <Mail size={15} className="mr-1.5" />
            )}
            Notify Subscribers
          </Button>
        </div>
      </div>

      <div className="mx-6 mt-3 grid gap-2 md:grid-cols-2 text-xs text-slate-600">
        <div className="rounded-lg border border-blue-100 bg-blue-50 px-3 py-2">
          <p className="font-semibold text-blue-800">1) Publish to Website</p>
          <p>
            Daily public articles (about 3–4/day). Live on Research pages and also ingested for Ask AGI.
            Uncheck <span className="font-semibold">Notify subscribers</span> to publish without emailing, or use
            Notify Subscribers later.
          </p>
        </div>
        <div className="rounded-lg border border-violet-100 bg-violet-50 px-3 py-2">
          <p className="font-semibold text-violet-800">2) Send to Intelligence</p>
          <p>Paste private research/notes for AGI to study. Not published on the website.</p>
        </div>
      </div>

      {error && (
        <div className="mx-6 mt-4 px-4 py-3 rounded-lg bg-red-50 text-red-700 text-sm border border-red-200">{error}</div>
      )}

      <div className="flex-1 flex overflow-hidden">
        {/* Editor column */}
        <div className="flex-1 overflow-y-auto bg-slate-50">
          {/* Cover */}
          <div className="bg-white border-b border-slate-200">
            {coverUrl ? (
              <div className="relative group agi-cover agi-cover--editor">
                <img src={coverUrl} alt="Cover" />
                <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                  <Button size="sm" variant="secondary" onClick={chooseCover}>Change</Button>
                  <Button size="sm" variant="secondary" onClick={() => setCoverUrl('')}>Remove</Button>
                </div>
              </div>
            ) : (
              <button
                type="button"
                onClick={chooseCover}
                className="w-full h-40 flex flex-col items-center justify-center gap-2 text-slate-400 hover:bg-slate-50 transition-colors border-b border-dashed border-slate-200"
              >
                <ImageIcon size={24} />
                <span className="text-sm">Add featured image</span>
              </button>
            )}
          </div>

          <div className="max-w-4xl mx-auto">
            <input
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                dirtyRef.current = true;
              }}
              placeholder="Headline — e.g. Morning Market Update: Nifty Holds 24,800"
              className="w-full px-8 pt-8 pb-4 text-3xl md:text-4xl font-bold text-slate-900 bg-white border-b border-slate-100 outline-none placeholder:text-slate-300"
            />

            <div className="bg-white border border-slate-200 rounded-b-xl shadow-sm mx-4 mb-8 overflow-hidden">
              <EditorToolbar
                editor={editor}
                onInsertImage={insertImage}
                onInsertVideo={insertVideo}
                onInsertChart={insertChart}
                imageUploading={inlineImageUploading}
              />
              {inlineImageUploading && (
                <div className="border-b border-blue-100 bg-blue-50 px-4 py-2 text-sm text-blue-700" role="status">
                  Uploading image at the cursor — you can also paste or drag images into the editor.
                </div>
              )}
              <EditorContent editor={editor} />
            </div>
          </div>
        </div>

        {/* SEO sidebar */}
        <aside className="w-80 shrink-0 bg-white border-l border-slate-200 overflow-y-auto p-5 space-y-5">
          <div>
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-3">Publishing</h3>
            <label className="block text-sm font-medium text-slate-700 mb-1">Research Desk</label>
            <select
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
              value={section}
              onChange={(e) => {
                setSection(e.target.value);
                dirtyRef.current = true;
              }}
            >
              {RESEARCH_DESK_SECTIONS.map((deskSection) => (
                <option key={deskSection} value={deskSection}>{deskSection}</option>
              ))}
            </select>
            <p className="text-xs text-slate-400 mt-1">
              Choose which homepage desk this research belongs to.
            </p>
          </div>

          <label className="block rounded-lg border border-red-200 bg-red-50 p-3 cursor-pointer">
            <span className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-red-600"
                checked={showInLatest}
                onChange={(e) => {
                  setShowInLatest(e.target.checked);
                  dirtyRef.current = true;
                }}
              />
              <span>
                <span className="block text-sm font-semibold text-red-800">Show in Homepage Latest</span>
                <span className="mt-1 block text-xs leading-relaxed text-red-700/80">
                  Adds this headline to the manually curated Latest rail after it is published.
                </span>
              </span>
            </span>
          </label>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">URL Slug</label>
            <input
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-mono"
              value={slug}
              onChange={(e) => {
                setSlug(toSlug(e.target.value));
                setSlugManual(true);
                dirtyRef.current = true;
              }}
            />
            <p className="text-xs text-slate-400 mt-1">/article/{slug || '…'}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Meta Description</label>
            <textarea
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm resize-none"
              rows={3}
              maxLength={160}
              placeholder="SEO summary (160 chars max)"
              value={metaDescription}
              onChange={(e) => {
                setMetaDescription(e.target.value);
                dirtyRef.current = true;
              }}
            />
            <p className="text-xs text-slate-400 mt-1">{metaDescription.length}/160</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Tags</label>
            <input
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
              placeholder="nifty, rbi, banking"
              value={tagsInput}
              onChange={(e) => {
                setTagsInput(e.target.value);
                dirtyRef.current = true;
              }}
            />
            <p className="text-xs text-slate-400 mt-1">Comma-separated</p>
          </div>

          <div className="pt-4 border-t border-slate-100">
            <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-2">SEO Preview</h3>
            <div className="rounded-lg border border-slate-200 p-3 bg-slate-50">
              <p className="text-blue-700 text-sm font-medium line-clamp-1">{title || 'Article Title'}</p>
              <p className="text-green-700 text-xs mt-0.5 truncate">agarwalglobalinvestments.com/article/{slug || '…'}</p>
              <p className="text-slate-600 text-xs mt-1 line-clamp-2">
                {metaDescription || htmlToExcerpt(html, 120) || 'Meta description will appear here.'}
              </p>
            </div>
          </div>
        </aside>
      </div>

      <ArticlePreview
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        article={{ title, section, metaDescription, coverUrl, status }}
        html={html}
      />
    </div>
  );
}
