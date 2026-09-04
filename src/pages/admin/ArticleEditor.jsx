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
import { Eye, Save, Send, ImageIcon, Loader2, Brain, Mail, Radio } from 'lucide-react';
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
  HOMEPAGE_FEATURED_TAG,
  htmlToExcerpt,
  readingTime,
  setHomepageFeaturedArticle,
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
import LiveBadge from '@/components/Article/LiveBadge';
import {
  LIVE_TAG,
  createLiveUpdate,
  formatLiveClock,
  isLiveArticle,
  isMissingLiveColumnError,
  normalizeLiveUpdates,
  withLiveTag,
} from '@/lib/liveArticle';

const AUTOSAVE_MS = 4000;
const EDITOR_SELECT =
  'id, title, slug, section, excerpt, meta_description, content_md, content, cover_url, tags, status, author_id, published_at, is_live, live_updates, live_started_at, live_ended_at, article_type, equity_research';
const EDITOR_SELECT_FALLBACK =
  'id, title, slug, section, excerpt, meta_description, content_md, content, cover_url, tags, status, author_id, published_at, article_type, equity_research';

const initialEquityResearch = () => ({
  company_name: '',
  ticker: '',
  exchange: 'NSE',
  stance: 'neutral',
  report_label: 'Equity Research',
  report_date: new Date().toISOString().slice(0, 10),
  currency: 'INR',
  current_price: '',
  fair_value: '',
  potential_pct: '',
  analyst_name: '',
  analyst_title: 'Equity Research Analyst',
  analyst_contact: '',
  key_data: '',
  thesis: '',
  strengths: '',
  risks: '',
  ipo_scores: {
    business_quality: '',
    financial_quality: '',
    valuation: '',
    governance: '',
    issue_structure: '',
    demand_quality: '',
  },
});

const IPO_SCORE_FIELDS = [
  ['business_quality', 'Business quality', '25%'],
  ['financial_quality', 'Financial quality', '20%'],
  ['valuation', 'Valuation', '20%'],
  ['governance', 'Governance', '15%'],
  ['issue_structure', 'Issue structure', '10%'],
  ['demand_quality', 'Demand quality', '10%'],
];

const researchInputClass =
  'mt-1 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100';

function stripLiveCoverageColumns(payload) {
  const { is_live, live_updates, live_started_at, live_ended_at, ...rest } = payload;
  return rest;
}

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
  const [showAsHomepageLead, setShowAsHomepageLead] = useState(false);
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
  const [originallyPublishedAt, setOriginallyPublishedAt] = useState(null);
  const [isLive, setIsLive] = useState(false);
  const [liveUpdates, setLiveUpdates] = useState([]);
  const [liveStartedAt, setLiveStartedAt] = useState(null);
  const [liveEndedAt, setLiveEndedAt] = useState(null);
  const [updateHeadline, setUpdateHeadline] = useState('');
  const [updateBody, setUpdateBody] = useState('');
  const [articleType, setArticleType] = useState('article');
  const [equityResearch, setEquityResearch] = useState(initialEquityResearch);

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
      let { data, error: loadError } = await supabase
        .from('articles')
        .select(EDITOR_SELECT)
        .eq('slug', editSlug)
        .maybeSingle();

      if (loadError && isMissingLiveColumnError(loadError)) {
        ({ data, error: loadError } = await supabase
          .from('articles')
          .select(EDITOR_SELECT_FALLBACK)
          .eq('slug', editSlug)
          .maybeSingle());
      }

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
      setOriginallyPublishedAt(data.published_at || null);
      setTitle(data.title || '');
      setSlug(data.slug || '');
      setSlugManual(true);
      setMetaDescription(data.meta_description || data.excerpt || '');
      setSection(data.section || '');
      setCoverUrl(data.cover_url || '');
      const loadedTags = Array.isArray(data.tags) ? data.tags : [];
      setTagsInput(
        loadedTags
          .filter(
            (tag) =>
              tag !== HOMEPAGE_LATEST_TAG &&
              tag !== HOMEPAGE_FEATURED_TAG &&
              tag !== LIVE_TAG
          )
          .join(', ')
      );
      setShowInLatest(loadedTags.includes(HOMEPAGE_LATEST_TAG));
      setShowAsHomepageLead(loadedTags.includes(HOMEPAGE_FEATURED_TAG));
      setStatus(data.status || 'draft');
      setIsLive(isLiveArticle(data));
      setLiveUpdates(normalizeLiveUpdates(data.live_updates));
      setLiveStartedAt(data.live_started_at || null);
      setLiveEndedAt(data.live_ended_at || null);
      setArticleType(data.article_type || 'article');
      const savedEquityResearch = data.equity_research && typeof data.equity_research === 'object'
        ? data.equity_research
        : {};
      const equityDefaults = initialEquityResearch();
      setEquityResearch({
        ...equityDefaults,
        ...savedEquityResearch,
        ipo_scores: {
          ...equityDefaults.ipo_scores,
          ...(savedEquityResearch.ipo_scores && typeof savedEquityResearch.ipo_scores === 'object'
            ? savedEquityResearch.ipo_scores
            : {}),
        },
      });

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
      if (articleType === 'equity_research' && !tags.includes('equity-research')) {
        tags.push('equity-research');
      }
      if (section === 'IPOs') {
        if (!tags.some((tag) => tag.toLowerCase() === 'ipo')) tags.push('IPO');
        const tickerTag = String(equityResearch.ticker || '').trim().toUpperCase();
        if (tickerTag && !tags.some((tag) => tag.toUpperCase() === tickerTag)) tags.push(tickerTag);
      }
      if (showInLatest && publishStatus !== 'intelligence') tags.push(HOMEPAGE_LATEST_TAG);
      if (showAsHomepageLead && publishStatus === 'published') tags.push(HOMEPAGE_FEATURED_TAG);
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
        article_type: articleType,
        equity_research:
          articleType === 'equity_research'
            ? Object.fromEntries(
                Object.entries(equityResearch).map(([key, value]) => [
                  key,
                  typeof value === 'string' ? value.trim() : value,
                ])
              )
            : null,
      };
      if (!draftId) {
        payload.author_id = user.id;
      } else if (originalAuthorId) {
        payload.author_id = originalAuthorId;
      } else if (!isAdmin(user)) {
        payload.author_id = user.id;
      }

      if (metaDescription.trim()) payload.meta_description = metaDescription.trim();
      if (publishStatus === 'published' && !originallyPublishedAt) {
        payload.published_at = new Date().toISOString();
      }
      payload.is_live = publishStatus === 'published' ? isLive : false;
      payload.live_updates = liveUpdates;
      payload.live_started_at = isLive ? liveStartedAt || new Date().toISOString() : liveStartedAt;
      payload.live_ended_at = isLive ? null : liveEndedAt;
      payload.tags = withLiveTag(payload.tags, payload.is_live);
      payload.tags = payload.tags.length ? payload.tags : null;
      // Private intelligence notes must never appear as website posts.
      if (publishStatus === 'intelligence') {
        payload.published_at = null;
        payload.tags = Array.from(
          new Set([...(payload.tags || []), 'intelligence-only', 'agi-private'])
        );
      }

      return payload;
    },
    [
      editor,
      tagsInput,
      showInLatest,
      showAsHomepageLead,
      metaDescription,
      user,
      title,
      slug,
      section,
      coverUrl,
      draftId,
      originalAuthorId,
      originallyPublishedAt,
      isLive,
      liveUpdates,
      liveStartedAt,
      liveEndedAt,
      articleType,
      equityResearch,
    ]
  );

  const persist = useCallback(
    async (publishStatus, { silent = false, ingest = false, stayInEditor = false, skipNotify = false, payloadPatch = null } = {}) => {
      if (!editor) return null;
      setSaving(true);
      setError('');

      try {
        if (
          publishStatus === 'published' &&
          articleType === 'equity_research' &&
          (!equityResearch.company_name?.trim() || !equityResearch.ticker?.trim())
        ) {
          throw new Error('Company name and ticker are required before publishing equity research.');
        }

        let articleSlug = slug || (await generateUniqueSlug(title, draftId));
        if (!slugManual) setSlug(articleSlug);

        let payload = { ...buildPayload(publishStatus), slug: articleSlug, ...(payloadPatch || {}) };
        if (payload.is_live === true) {
          payload.tags = withLiveTag(payload.tags, true);
          payload.live_ended_at = null;
          payload.live_started_at = payload.live_started_at || liveStartedAt || new Date().toISOString();
        } else if (payload.is_live === false) {
          payload.tags = withLiveTag(payload.tags, false);
        }
        payload.tags = payload.tags?.length ? payload.tags : null;

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
        if (saveError && isMissingLiveColumnError(saveError)) {
          const fallbackPayload = {
            ...stripLiveCoverageColumns(payload),
            tags: withLiveTag(payload.tags, payload.is_live === true),
          };
          fallbackPayload.tags = fallbackPayload.tags?.length ? fallbackPayload.tags : null;
          result = draftId
            ? await supabase.from('articles').update(fallbackPayload).eq('id', draftId).select('id, slug, status').single()
            : await supabase.from('articles').insert(fallbackPayload).select('id, slug, status').single();
          ({ data, error: saveError } = result);
          if (!saveError) {
            setError(
              'This story is tagged live. Timestamped updates need the live coverage columns in Supabase — run articles_live_coverage.'
            );
          }
        }
        if (saveError) throw saveError;

        setDraftId(data.id);
        setSlug(data.slug);
        setStatus(publishStatus === 'intelligence' ? 'intelligence' : data.status);
        if (publishStatus === 'published' && !originallyPublishedAt) {
          setOriginallyPublishedAt(payload.published_at || new Date().toISOString());
        }
        if (payloadPatch?.live_updates) setLiveUpdates(payloadPatch.live_updates);
        if (payloadPatch?.is_live !== undefined) setIsLive(payloadPatch.is_live);
        if (payloadPatch?.live_started_at) setLiveStartedAt(payloadPatch.live_started_at);
        if (Object.prototype.hasOwnProperty.call(payloadPatch || {}, 'live_ended_at')) {
          setLiveEndedAt(payloadPatch.live_ended_at);
        }
        setLastSaved(new Date());
        dirtyRef.current = false;

        if (publishStatus === 'published' && data?.id) {
          try {
            await setHomepageFeaturedArticle(data.id, { enabled: showAsHomepageLead });
          } catch (pinErr) {
            console.warn('[cms] homepage lead update failed', pinErr);
          }
        }

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
        if (publishStatus === 'published' && notifyOnPublish && !skipNotify) {
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
    [
      editor,
      slug,
      slugManual,
      title,
      draftId,
      buildPayload,
      navigate,
      section,
      tagsInput,
      notifyOnPublish,
      coverUrl,
      showAsHomepageLead,
      user,
      originallyPublishedAt,
      liveStartedAt,
      articleType,
      equityResearch,
    ]
  );

  const startLiveCoverage = useCallback(() => {
    const started = liveStartedAt || new Date().toISOString();
    setIsLive(true);
    setLiveStartedAt(started);
    setLiveEndedAt(null);
    dirtyRef.current = true;
  }, [liveStartedAt]);

  const endLiveCoverage = useCallback(async () => {
    const ended = new Date().toISOString();
    setIsLive(false);
    setLiveEndedAt(ended);
    dirtyRef.current = true;
    if (status !== 'published') return;
    await persist('published', {
      stayInEditor: true,
      skipNotify: true,
      payloadPatch: { is_live: false, live_ended_at: ended },
    });
  }, [persist, status]);

  const postLiveUpdate = useCallback(async () => {
    const headline = updateHeadline.trim();
    const body = updateBody.trim();
    if (!headline && !body) {
      setError('Write an update headline or a few sentences before posting.');
      return;
    }
    const next = [createLiveUpdate({ headline, body }), ...liveUpdates];
    const started = liveStartedAt || new Date().toISOString();
    setLiveUpdates(next);
    setIsLive(true);
    setLiveStartedAt(started);
    setLiveEndedAt(null);
    setUpdateHeadline('');
    setUpdateBody('');
    const firstPublish = status !== 'published';
    const saved = await persist('published', {
      stayInEditor: true,
      ingest: firstPublish,
      skipNotify: true,
      payloadPatch: {
        is_live: true,
        live_updates: next,
        live_started_at: started,
        live_ended_at: null,
      },
    });
    if (saved) setError('');
  }, [updateHeadline, updateBody, liveUpdates, liveStartedAt, status, persist]);

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
        persist(status === 'published' || status === 'intelligence' ? status : 'draft', {
          silent: true,
          skipNotify: true,
          stayInEditor: true,
        });
      }
    }, AUTOSAVE_MS);

    return () => clearInterval(autosaveTimer.current);
  }, [editor, loaded, user, title, persist, status]);

  const html = editor?.getHTML() || '';
  const words = wordCountFromHTML(html);
  const minutes = readingTime(html);

  const updateEquityResearch = (field, value) => {
    setEquityResearch((current) => ({ ...current, [field]: value }));
    dirtyRef.current = true;
  };

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
          {isLive ? <LiveBadge /> : null}
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
            onClick={() =>
              persist('published', {
                ingest: status !== 'published',
                stayInEditor: isLive && status === 'published',
                skipNotify: isLive && status === 'published',
              })
            }
            disabled={saving || !title.trim()}
            title={
              isLive && status === 'published'
                ? 'Saves the continuing story without resetting the original publish time or emailing subscribers'
                : notifyOnPublish
                  ? 'Goes live on the website, emails subscribers, and is studied by AGI Intelligence'
                  : 'Goes live on the website without emailing subscribers'
            }
          >
            <Send size={15} className="mr-1.5" />
            {isLive && status === 'published' ? 'Save live story' : 'Publish to Website'}
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
            {articleType === 'equity_research' && (
              <section className="mx-4 mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="mb-5 flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 pb-4">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">{section === 'IPOs' ? 'IPO research cover sheet' : 'Equity research cover sheet'}</p>
                    <h2 className="mt-1 text-xl font-semibold text-slate-950">{section === 'IPOs' ? 'Issue thesis and intelligence scorecard' : 'Company, stance and valuation snapshot'}</h2>
                    <p className="mt-1 text-sm text-slate-500">These fields create the institutional header and facts panel on the published report.</p>
                  </div>
                  <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-800">Editorial view, not a trade recommendation</span>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <label className="text-sm font-medium text-slate-700 sm:col-span-2">Company name *<input className={researchInputClass} value={equityResearch.company_name} onChange={(e) => updateEquityResearch('company_name', e.target.value)} placeholder="e.g. Reliance Industries Ltd." /></label>
                  <label className="text-sm font-medium text-slate-700">Ticker *<input className={researchInputClass} value={equityResearch.ticker} onChange={(e) => updateEquityResearch('ticker', e.target.value.toUpperCase())} placeholder="RELIANCE" /></label>
                  <label className="text-sm font-medium text-slate-700">Exchange<input className={researchInputClass} value={equityResearch.exchange} onChange={(e) => updateEquityResearch('exchange', e.target.value.toUpperCase())} placeholder="NSE" /></label>
                  <label className="text-sm font-medium text-slate-700">Thesis stance<select className={researchInputClass} value={equityResearch.stance} onChange={(e) => updateEquityResearch('stance', e.target.value)}><option value="bullish">Bullish</option><option value="neutral">Neutral</option><option value="bearish">Bearish</option></select></label>
                  <label className="text-sm font-medium text-slate-700">Report date<input type="date" className={researchInputClass} value={equityResearch.report_date} onChange={(e) => updateEquityResearch('report_date', e.target.value)} /></label>
                  <label className="text-sm font-medium text-slate-700">Report label<input className={researchInputClass} value={equityResearch.report_label} onChange={(e) => updateEquityResearch('report_label', e.target.value)} /></label>
                  <label className="text-sm font-medium text-slate-700">Currency<select className={researchInputClass} value={equityResearch.currency} onChange={(e) => updateEquityResearch('currency', e.target.value)}><option value="INR">INR</option><option value="USD">USD</option><option value="EUR">EUR</option><option value="GBP">GBP</option></select></label>
                  <label className="text-sm font-medium text-slate-700">Reference price<input inputMode="decimal" className={researchInputClass} value={equityResearch.current_price} onChange={(e) => updateEquityResearch('current_price', e.target.value)} placeholder="2,945.50" /></label>
                  <label className="text-sm font-medium text-slate-700">Fair value<input inputMode="decimal" className={researchInputClass} value={equityResearch.fair_value} onChange={(e) => updateEquityResearch('fair_value', e.target.value)} placeholder="3,250.00" /></label>
                  <label className="text-sm font-medium text-slate-700">Implied move<input className={researchInputClass} value={equityResearch.potential_pct} onChange={(e) => updateEquityResearch('potential_pct', e.target.value)} placeholder="+10.3%" /></label>
                  <label className="text-sm font-medium text-slate-700 sm:col-span-2">Analyst name<input className={researchInputClass} value={equityResearch.analyst_name} onChange={(e) => updateEquityResearch('analyst_name', e.target.value)} placeholder="Shivam Agarwal" /></label>
                  <label className="text-sm font-medium text-slate-700">Analyst title<input className={researchInputClass} value={equityResearch.analyst_title} onChange={(e) => updateEquityResearch('analyst_title', e.target.value)} /></label>
                  <label className="text-sm font-medium text-slate-700">Analyst contact<input className={researchInputClass} value={equityResearch.analyst_contact} onChange={(e) => updateEquityResearch('analyst_contact', e.target.value)} placeholder="research@..." /></label>
                  <label className="text-sm font-medium text-slate-700 sm:col-span-2 lg:col-span-4">Key data<textarea className={`${researchInputClass} min-h-28 resize-y`} value={equityResearch.key_data} onChange={(e) => updateEquityResearch('key_data', e.target.value)} placeholder={'Market cap: INR 19.9tn\nEnterprise value: INR 22.1tn\n3m average turnover: INR 9.4bn\nSector: Energy & Retail'} /><span className="mt-1 block text-xs font-normal text-slate-400">Enter one label and value per line.</span></label>
                  {section === 'IPOs' && (
                    <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-4 sm:col-span-2 lg:col-span-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">IPO intelligence inputs</p>
                      <p className="mt-1 text-xs text-slate-500">These fields feed the client IPO page. Enter one evidence-backed strength or risk per line.</p>
                      <div className="mt-4 grid gap-4 lg:grid-cols-2">
                        <label className="text-sm font-medium text-slate-700 lg:col-span-2">Thesis summary<textarea className={`${researchInputClass} min-h-20 resize-y`} value={equityResearch.thesis || ''} onChange={(e) => updateEquityResearch('thesis', e.target.value)} placeholder="State the core investment thesis and what would change it." /></label>
                        <label className="text-sm font-medium text-slate-700">Potential strengths<textarea className={`${researchInputClass} min-h-28 resize-y`} value={equityResearch.strengths || ''} onChange={(e) => updateEquityResearch('strengths', e.target.value)} placeholder={'Revenue visibility supported by...\nMargins can expand because...'} /></label>
                        <label className="text-sm font-medium text-slate-700">Principal risks<textarea className={`${researchInputClass} min-h-28 resize-y`} value={equityResearch.risks || ''} onChange={(e) => updateEquityResearch('risks', e.target.value)} placeholder={'Customer concentration remains...\nOFS-heavy structure limits...'} /></label>
                      </div>
                      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {IPO_SCORE_FIELDS.map(([field, label, weight]) => (
                          <label key={field} className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-600">
                            {label} <span className="font-normal text-slate-400">({weight})</span>
                            <input
                              type="number"
                              min="0"
                              max="100"
                              className={`${researchInputClass} normal-case tracking-normal`}
                              value={equityResearch.ipo_scores?.[field] ?? ''}
                              onChange={(e) => updateEquityResearch('ipo_scores', {
                                ...(equityResearch.ipo_scores || {}),
                                [field]: e.target.value,
                              })}
                              placeholder="0-100"
                            />
                          </label>
                        ))}
                      </div>
                      <p className="mt-3 text-xs text-slate-500">The overall score appears only after at least four pillars have verified evidence. Leave demand quality blank to use live subscription demand.</p>
                    </div>
                  )}
                </div>
              </section>
            )}

            <input
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                dirtyRef.current = true;
              }}
              placeholder={articleType === 'equity_research' ? 'Research headline — e.g. Margin recovery strengthens the medium-term thesis' : 'Headline — e.g. Morning Market Update: Nifty Holds 24,800'}
              className="w-full px-8 pt-8 pb-4 text-3xl md:text-4xl font-bold text-slate-900 bg-white border-b border-slate-100 outline-none placeholder:text-slate-300"
            />

            {isLive ? (
              <div className="mx-4 mt-4 rounded-xl border border-red-200 bg-red-50 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <LiveBadge />
                  <p className="text-sm font-semibold text-red-900">Post a timestamped update</p>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-red-800/80">
                  The headline and original article stay put. Each update appears at the top of the live page with the time it was posted.
                </p>
                <input
                  className="mt-3 w-full rounded-lg border border-red-200 bg-white px-3 py-2 text-sm"
                  placeholder="Update headline (optional)"
                  value={updateHeadline}
                  onChange={(e) => setUpdateHeadline(e.target.value)}
                />
                <textarea
                  className="mt-2 w-full min-h-[88px] rounded-lg border border-red-200 bg-white px-3 py-2 text-sm"
                  placeholder="What just happened…"
                  value={updateBody}
                  onChange={(e) => setUpdateBody(e.target.value)}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    className="bg-[#e1251b] hover:bg-[#c41f17]"
                    onClick={postLiveUpdate}
                    disabled={saving}
                  >
                    Post update
                  </Button>
                  {status === 'published' ? (
                    <Button size="sm" variant="outline" onClick={endLiveCoverage} disabled={saving}>
                      End live coverage
                    </Button>
                  ) : null}
                </div>
                {liveUpdates.length ? (
                  <ol className="mt-4 space-y-3">
                    {liveUpdates.map((update) => (
                      <li key={update.id} className="border-l-2 border-[#e1251b] pl-3">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-red-700">
                          {formatLiveClock(update.at)}
                        </p>
                        {update.headline ? (
                          <p className="mt-0.5 text-sm font-semibold text-slate-900">{update.headline}</p>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                ) : null}
              </div>
            ) : null}

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
            <label className="block text-sm font-medium text-slate-700 mb-1">Article format</label>
            <select
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
              value={articleType}
              onChange={(e) => {
                setArticleType(e.target.value);
                dirtyRef.current = true;
              }}
            >
              <option value="article">Standard article</option>
              <option value="equity_research">Equity research report</option>
            </select>
            <p className="text-xs text-slate-400 mt-1 mb-4">Equity research adds a company cover sheet and thesis stance.</p>
            <label className="block text-sm font-medium text-slate-700 mb-1">Research Desk</label>
            <select
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
              value={section}
              onChange={(e) => {
                const nextSection = e.target.value;
                setSection(nextSection);
                if (nextSection === 'IPOs' && articleType === 'equity_research') {
                  setEquityResearch((current) => ({
                    ...current,
                    report_label: current.report_label === 'Equity Research' ? 'IPO Research' : current.report_label,
                  }));
                }
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
                checked={isLive}
                onChange={(e) => {
                  if (e.target.checked) startLiveCoverage();
                  else if (status === 'published') void endLiveCoverage();
                  else {
                    setIsLive(false);
                    setLiveEndedAt(new Date().toISOString());
                    dirtyRef.current = true;
                  }
                }}
              />
              <span>
                <span className="flex items-center gap-2 text-sm font-semibold text-red-800">
                  <Radio size={14} /> Live continuing story
                </span>
                <span className="mt-1 block text-xs leading-relaxed text-red-700/80">
                  Same URL, red LIVE badge above the headline. Add timestamped updates as news lands. Does not reset the original publish time.
                </span>
              </span>
            </span>
          </label>

          <label className="block rounded-lg border border-blue-200 bg-blue-50 p-3 cursor-pointer">
            <span className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-0.5 h-4 w-4 accent-blue-700"
                checked={showAsHomepageLead}
                onChange={(e) => {
                  setShowAsHomepageLead(e.target.checked);
                  dirtyRef.current = true;
                }}
              />
              <span>
                <span className="block text-sm font-semibold text-blue-800">Show first on homepage</span>
                <span className="mt-1 block text-xs leading-relaxed text-blue-800/80">
                  Makes this the large lead story on the homepage. Only one article can be first.
                </span>
              </span>
            </span>
          </label>

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
        article={{ title, section, metaDescription, coverUrl, status, isLive, liveUpdates }}
        html={html}
      />
    </div>
  );
}
