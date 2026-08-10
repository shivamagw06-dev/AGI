// src/components/ArticlePage.jsx
import React, { useEffect, useMemo, useState, useCallback, Suspense, lazy } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import DOMPurify from 'dompurify';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';

const ArticleKnowledgePanel = lazy(() => import('@/components/Article/ArticleKnowledgePanel'));

function readingTimeFromHTML(html = '') {
  const text = String(html).replace(/<[^>]*>/g, ' ');
  const words = text.split(/\s+/).filter(Boolean).length;
  return Math.max(3, Math.round(words / 200));
}

// -----------------------------
// Comments (LinkedIn-style)
// -----------------------------
function timeAgo(date) {
  if (!date) return '';
  const d = typeof date === 'string' ? new Date(date) : date;
  const s = Math.floor((Date.now() - d.getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const day = Math.floor(h / 24);
  if (day < 7) return `${day}d ago`;
  return d.toLocaleDateString();
}

function CommentInput({ placeholder = 'Add a comment…', onSubmit, submitting }) {
  const [value, setValue] = useState('');
  const [count, setCount] = useState(0);

  const handleChange = (e) => {
    const v = e.target.value;
    setValue(v);
    setCount(v.trim().length);
  };

  const handleSend = async () => {
    const v = value.trim();
    if (!v) return;
    await onSubmit(v);
    setValue('');
    setCount(0);
  };

  return (
    <div className="w-full border rounded-xl p-3 bg-card">
      <textarea
        className="w-full resize-y min-h-[64px] bg-transparent focus:outline-none text-sm"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        maxLength={2000}
      />
      <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
        <span>{count}/2000</span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => { setValue(''); setCount(0); }} disabled={submitting || !count}>
            Clear
          </Button>
          <Button size="sm" onClick={handleSend} disabled={submitting || !count}>
            {submitting ? 'Posting…' : 'Post'}
          </Button>
        </div>
      </div>
    </div>
  );
}

function CommentItem({ comment, profile, currentUserId, onReply, onLikeToggle, onDelete, children }) {
  const you = currentUserId === comment.user_id;
  return (
    <div className="flex gap-3">
      <div className="w-9 h-9 rounded-full overflow-hidden bg-gray-100 shrink-0">
        {profile?.photo_url ? (
          <img src={profile.photo_url} alt={profile.display_name || 'user'} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-xs text-gray-400">
            {(profile?.display_name || 'U').slice(0, 1)}
          </div>
        )}
      </div>
      <div className="flex-1">
        <div className="bg-accent/40 border rounded-2xl px-3 py-2">
          <div className="text-sm font-medium">
            {profile?.display_name || profile?.full_name || 'User'}
            <span className="ml-2 text-xs text-muted-foreground">{timeAgo(comment.created_at)}</span>
          </div>
          <div className="mt-1 text-sm whitespace-pre-wrap break-words">{comment.content}</div>
        </div>
        <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
          <button className="hover:underline" onClick={() => onLikeToggle(comment)}>
            {comment.viewer_liked ? 'Unlike' : 'Like'}{comment.likes_count ? ` • ${comment.likes_count}` : ''}
          </button>
          <button className="hover:underline" onClick={() => onReply(comment)}>Reply</button>
          {you && (
            <button className="hover:underline text-red-600" onClick={() => onDelete(comment)}>Delete</button>
          )}
        </div>
        {/* Children (replies) */}
        {children && <div className="mt-3 pl-6 border-l">{children}</div>}
      </div>
    </div>
  );
}

function buildTree(comments) {
  const map = new Map();
  comments.forEach((c) => map.set(c.id, { ...c, children: [] }));
  const roots = [];
  map.forEach((node) => {
    if (node.parent_id && map.has(node.parent_id)) {
      map.get(node.parent_id).children.push(node);
    } else {
      roots.push(node);
    }
  });
  return roots;
}

function Comments({ articleId }) {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [replyingTo, setReplyingTo] = useState(null);
  const [error, setError] = useState(null);

  const [comments, setComments] = useState([]); // flat list
  const [profiles, setProfiles] = useState({}); // user_id -> profile

  // FIX: functional update to avoid stale closure
  const fetchProfiles = useCallback(async (userIds) => {
    const unique = Array.from(new Set(userIds.filter(Boolean)));
    if (!unique.length) return;
    const { data, error } = await supabase
      .from('profiles')
      .select('id, display_name, full_name, handle, photo_url')
      .in('id', unique);
    if (!error && data) {
      setProfiles(prev => {
        const next = { ...prev };
        data.forEach((p) => { next[p.id] = p; });
        return next;
      });
    }
  }, []);

  const load = useCallback(async () => {
    if (!articleId) return;
    setLoading(true);
    setError(null);
    try {
      // 1) Get comments for this article
      const { data: rows, error: cErr } = await supabase
        .from('article_comments')
        .select('id, article_id, user_id, content, parent_id, created_at')
        .eq('article_id', articleId)
        .order('created_at', { ascending: true });
      if (cErr) throw cErr;

      const ids = rows?.map((r) => r.id) || [];
      const userIds = rows?.map((r) => r.user_id) || [];

      // 2) Fetch likes to compute counts & viewer state
      let counts = {};
      let viewer = new Set();
      if (ids.length) {
        const { data: likes, error: lErr } = await supabase
          .from('comment_likes')
          .select('comment_id, user_id')
          .in('comment_id', ids);
        if (!lErr && likes) {
          likes.forEach((lk) => {
            counts[lk.comment_id] = (counts[lk.comment_id] || 0) + 1;
            if (lk.user_id === user?.id) viewer.add(lk.comment_id);
          });
        }
      }

      const merged = (rows || []).map((r) => ({
        ...r,
        likes_count: counts[r.id] || 0,
        viewer_liked: viewer.has(r.id),
      }));

      setComments(merged);
      await fetchProfiles(userIds);
    } catch (err) {
      console.error('Comments load error', err);
      setError('Failed to load comments.');
    } finally {
      setLoading(false);
    }
  }, [articleId, user?.id, fetchProfiles]);

  useEffect(() => { load(); }, [load]);

  // Realtime updates
  useEffect(() => {
    if (!articleId) return;
    const channel = supabase.channel(`comments:${articleId}`)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'article_comments', filter: `article_id=eq.${articleId}` }, load)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'comment_likes' }, load)
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [articleId, load]);

  const requireLogin = () => {
    if (!user?.id) {
      const next = typeof window !== 'undefined' ? window.location.pathname : '/';
      navigate(`/login?next=${encodeURIComponent(next)}`);
      return true;
    }
    return false;
  };

  const handlePost = async (content, parentId = null) => {
    if (requireLogin()) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        article_id: articleId,
        user_id: user.id,
        content: content.trim().slice(0, 2000),
        parent_id: parentId,
        created_at: new Date().toISOString(),
      };
      const { error } = await supabase.from('article_comments').insert(payload);
      if (error) throw error;
      setReplyingTo(null);
      await load(); // fallback even with realtime
    } catch (err) {
      console.error('Post comment error', err);
      setError('Could not post comment.');
    } finally {
      setSubmitting(false);
    }
  };

  // FIX: optimistic toggle for instant feedback
  const handleLikeToggle = async (comment) => {
    if (requireLogin()) return;

    // optimistic update
    setComments(prev => prev.map(c =>
      c.id === comment.id
        ? { ...c, viewer_liked: !c.viewer_liked, likes_count: c.viewer_liked ? Math.max(0, c.likes_count - 1) : c.likes_count + 1 }
        : c
    ));

    try {
      if (comment.viewer_liked) {
        const { error } = await supabase
          .from('comment_likes')
          .delete()
          .eq('comment_id', comment.id)
          .eq('user_id', user.id);
        if (error) throw error;
      } else {
        const { error } = await supabase
          .from('comment_likes')
          .insert({ comment_id: comment.id, user_id: user.id, created_at: new Date().toISOString() });
        if (error) throw error;
      }
    } catch (err) {
      console.error('Toggle like error', err);
      setError('Could not update like.');
      // revert on failure
      setComments(prev => prev.map(c =>
        c.id === comment.id
          ? { ...c, viewer_liked: comment.viewer_liked, likes_count: comment.likes_count }
          : c
      ));
    }
  };

  const handleDelete = async (comment) => {
    if (requireLogin()) return;
    if (comment.user_id !== user.id) return;
    if (!window.confirm('Delete this comment?')) return;
    try {
      const { error } = await supabase
        .from('article_comments')
        .delete()
        .eq('id', comment.id)
        .eq('user_id', user.id);
      if (error) throw error;
      // remove locally (realtime will also update)
      setComments(prev => prev.filter(c => c.id !== comment.id && c.parent_id !== comment.id));
    } catch (err) {
      console.error('Delete comment error', err);
      setError('Could not delete comment.');
    }
  };

  const tree = useMemo(() => buildTree(comments), [comments]);

  return (
    <section className="mt-12">
      <h2 className="text-lg font-semibold">Comments</h2>
      <p className="text-sm text-muted-foreground mb-3">Join the conversation — be respectful and on-topic.</p>

      {/* New top-level comment */}
      <CommentInput onSubmit={(v) => handlePost(v, null)} submitting={submitting} />

      {error && <div className="mt-3 text-sm text-red-600">{error}</div>}

      {/* List */}
      <div className="mt-6 space-y-6">
        {loading && <div className="text-sm text-muted-foreground">Loading comments…</div>}
        {!loading && tree.length === 0 && (
          <div className="text-sm text-muted-foreground">Be the first to comment.</div>
        )}
        {!loading && tree.map((c) => (
          <div key={c.id}>
            <CommentItem
              comment={c}
              profile={profiles[c.user_id]}
              currentUserId={user?.id}
              onReply={(cm) => setReplyingTo(cm)}
              onLikeToggle={handleLikeToggle}
              onDelete={handleDelete}
            >
              {/* Replies */}
              {c.children?.length > 0 && (
                <div className="space-y-4">
                  {c.children.map((r) => (
                    <CommentItem
                      key={r.id}
                      comment={r}
                      profile={profiles[r.user_id]}
                      currentUserId={user?.id}
                      onReply={(cm) => setReplyingTo(cm)}
                      onLikeToggle={handleLikeToggle}
                      onDelete={handleDelete}
                    />
                  ))}
                </div>
              )}

              {/* Reply box */}
              {replyingTo?.id === c.id && (
                <div className="mt-3">
                  <CommentInput
                    placeholder={`Reply to ${profiles[c.user_id]?.display_name || 'comment'}…`}
                    onSubmit={(v) => handlePost(v, c.id)}
                    submitting={submitting}
                  />
                  <div className="mt-2">
                    <Button variant="ghost" size="sm" onClick={() => setReplyingTo(null)}>Cancel</Button>
                  </div>
                </div>
              )}
            </CommentItem>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ArticlePage() {
  const { slug: rawSlug } = useParams();
  const slug = decodeURIComponent((rawSlug || '').trim());
  const { user } = useAuth();
  const navigate = useNavigate();

  const [article, setArticle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [author, setAuthor] = useState(null);

  // subscription states
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [checkingSubscription, setCheckingSubscription] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // UI messages
  const [message, setMessage] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);

  // --- Fetch article (published; if author is current user allow draft)
  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setMessage(null);
      setErrorMessage(null);

      try {
        const baseSelect =
          'id, title, slug, section, excerpt, cover_url, content, content_md, tags, status, published_at, author_id, created_at';

        let { data, error } = await supabase
          .from('articles')
          .select(baseSelect)
          .eq('slug', slug)
          .eq('status', 'published')
          .maybeSingle();

        // if not found and user is the author, allow them to view their draft
        if ((!data || error) && user?.id) {
          const { data: authorData, error: authorErr } = await supabase
            .from('articles')
            .select(baseSelect)
            .eq('slug', slug)
            .eq('author_id', user.id)
            .maybeSingle();

          if (authorErr) {
            console.warn('Author fetch error for draft fallback', authorErr);
          }

          if (authorData) data = authorData;
        }

        if (mounted) {
          setArticle(data || null);
        }
      } catch (err) {
        console.error('Article fetch error', err);
        if (mounted) setErrorMessage('Failed to load article.');
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [slug, user?.id]);

  // --- Fetch author profile once we have article
  useEffect(() => {
    let mounted = true;
    (async () => {
      setAuthor(null);
      if (!article?.author_id) return;

      try {
        const { data: aData, error } = await supabase
          .from('profiles') // your table
          .select('id, full_name, display_name, handle, photo_url, is_public')
          .eq('id', article.author_id)
          .maybeSingle();

        if (error) {
          console.warn('Author lookup error', error);
        } else if (mounted) {
          setAuthor(aData || null);
        }
      } catch (err) {
        console.error('Author fetch failed', err);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [article?.author_id]);

  // --- Check subscription status (subscriber -> author)
  useEffect(() => {
    let mounted = true;
    (async () => {
      setIsSubscribed(false);
      setCheckingSubscription(false);
      if (!user?.id || !article?.author_id) return;

      setCheckingSubscription(true);

      try {
        const { data: subData, error } = await supabase
          .from('subscriptions')
          .select('id')
          .eq('subscriber_id', user.id)
          .eq('author_id', article.author_id)
          .maybeSingle();

        if (error) {
          console.warn('Subscription check error', error);
        } else if (mounted) {
          setIsSubscribed(!!subData);
        }
      } catch (err) {
        console.error('Subscription check failed', err);
      } finally {
        if (mounted) setCheckingSubscription(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [user?.id, article?.author_id]);

  const htmlToUse = article ? (article.content ?? article.content_md ?? '') : '';
  const minutes = useMemo(() => readingTimeFromHTML(htmlToUse), [htmlToUse]);

  // delete article (author only)
  async function deleteArticle() {
    if (!article) return;
    const ok = window.confirm('Delete this article? This cannot be undone.');
    if (!ok) return;

    try {
      const { error } = await supabase
        .from('articles')
        .delete()
        .eq('id', article.id)
        .eq('author_id', user?.id);

      if (error) throw error;
      navigate('/');
    } catch (err) {
      console.error('Delete failed', err);
      setErrorMessage('Delete failed: ' + (err.message || 'unknown error'));
    }
  }

  // subscribe / unsubscribe toggle
  async function handleSubscribeToggle() {
    if (!user?.id) {
      const next = typeof window !== 'undefined' ? window.location.pathname : `/article/${article?.slug}`;
      navigate(`/login?next=${encodeURIComponent(next)}`);
      return;
    }

    if (!article?.author_id) {
      setErrorMessage('Unable to subscribe to this author.');
      return;
    }

    if (user.id === article.author_id) {
      setMessage('You are the author of this article.');
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);
    setMessage(null);

    try {
      if (!isSubscribed) {
        const payload = {
          subscriber_id: user.id,
          author_id: article.author_id,
          created_at: new Date().toISOString()
        };

        const { error } = await supabase
          .from('subscriptions')
          .insert(payload)
          .select()
          .maybeSingle();

        if (error) throw error;
        setIsSubscribed(true);
        setMessage('Subscribed successfully.');
      } else {
        const { error } = await supabase
          .from('subscriptions')
          .delete()
          .eq('subscriber_id', user.id)
          .eq('author_id', article.author_id);

        if (error) throw error;
        setIsSubscribed(false);
        setMessage('Unsubscribed.');
      }
    } catch (err) {
      console.error('Subscription action error', err);
      setErrorMessage('Subscription action failed: ' + (err.message || 'unknown error'));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-10">
        <p className="text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (!article) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-10">
        <p className="mb-4 font-semibold">Article not found</p>
        <p className="text-sm text-muted-foreground mb-4">
          Tried slug: <code>{slug}</code>
        </p>
        <Button onClick={() => navigate('/')}>Go Home</Button>
      </div>
    );
  }

  const pubDate = article.published_at ?? article.created_at;
  const isoPubDate = pubDate ? new Date(pubDate).toISOString() : null;
  const niceDate = pubDate
    ? new Date(pubDate).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : '';

  const shareUrl =
    typeof window !== 'undefined'
      ? window.location.href
      : `https://agarwalglobalinvestments.com/article/${article.slug}`;

  const title = article.title || 'Article';
  const description =
    article.excerpt ||
    (htmlToUse ? String(htmlToUse).replace(/<[^>]*>/g, ' ').slice(0, 160) : 'AGI article');
  const image = article.cover_url || 'https://agarwalglobalinvestments.com/assets/og-image.png';
  const siteName = 'Agarwal Global Investments';
  const canonical = `https://agarwalglobalinvestments.com/article/${article.slug}`;

  const sanitizedHtml = DOMPurify.sanitize(htmlToUse);

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': canonical
    },
    headline: title,
    image: [image],
    datePublished: isoPubDate,
    author: {
      '@type': 'Person',
      name: author?.full_name || author?.display_name || 'Author'
    },
    publisher: {
      '@type': 'Organization',
      name: siteName,
      logo: {
        '@type': 'ImageObject',
        url: 'https://agarwalglobalinvestments.com/assets/logo.png'
      }
    },
    description
  };

  return (
    <div className="min-h-screen bg-background">
      <Helmet>
        <title>{title} • AGI</title>
        <meta name="description" content={description} />
        <link rel="canonical" href={canonical} />
        <meta property="og:site_name" content={siteName} />
        <meta property="og:type" content="article" />
        <meta property="og:url" content={shareUrl} />
        <meta property="og:title" content={`${title} | ${siteName}`} />
        <meta property="og:description" content={description} />
        <meta property="og:image" content={image} />
        {isoPubDate && <meta property="article:published_time" content={isoPubDate} />}
        {Array.isArray(article.tags) &&
          article.tags.map((t, i) => <meta key={i} property="article:tag" content={t} />)}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={`${title} | ${siteName}`} />
        <meta name="twitter:description" content={description} />
        <meta name="twitter:image" content={image} />
        {image && <meta property="og:image:alt" content={title} />}
        <script type="application/ld+json">{JSON.stringify(jsonLd)}</script>
      </Helmet>

      <main className="article-page-shell mx-auto w-full max-w-[90rem] px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
        <header className="article-page-header mx-auto w-full max-w-6xl">
          <Link to="/" className="text-sm text-muted-foreground hover:text-foreground">
          ← Back
          </Link>

        <h1 className="mt-3 text-3xl md:text-4xl font-extrabold tracking-tight leading-tight">
          {article.title}
        </h1>

        {/* author + subscribe */}
        <div className="mt-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full overflow-hidden bg-gray-100">
              {author?.photo_url ? (
                <img src={author.photo_url} alt={author.full_name || 'author'} className="w-full h-full object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-sm text-gray-400">
                  {author?.display_name ? author.display_name[0] : 'A'}
                </div>
              )}
            </div>

            <div className="text-sm">
              <div className="font-medium text-foreground">
                {author?.full_name || author?.display_name || author?.handle || 'Author'}
              </div>
              <div className="text-muted-foreground text-xs">
                {author?.handle ? `@${author.handle}` : ''}
              </div>
            </div>
          </div>

          <div>
            {article.author_id !== user?.id && (
              <div>
                <Button
                  onClick={handleSubscribeToggle}
                  disabled={checkingSubscription || submitting}
                  className="bg-yellow-500 hover:bg-yellow-600 text-white text-sm px-3 py-1 rounded-full"
                >
                  {checkingSubscription || submitting
                    ? 'Please wait...'
                    : isSubscribed
                    ? 'Unsubscribe'
                    : 'Subscribe'}
                </Button>
              </div>
            )}

            {article.author_id === user?.id && (
              <div className="text-sm text-muted-foreground">You are the author</div>
            )}
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-muted-foreground">
          <span>{niceDate}</span>
          <span>•</span>
          <span>{minutes} min read</span>

          {Array.isArray(article.tags) && article.tags.length > 0 && (
            <>
              <span>•</span>
              <div className="flex flex-wrap gap-2">
                {article.tags.map((t, i) => (
                  <span key={i} className="rounded-full bg-accent px-2 py-0.5 text-xs text-foreground">
                    #{t}
                  </span>
                ))}
              </div>
            </>
          )}

          {article.status === 'draft' && (
            <>
              <span>•</span>
              <span className="text-orange-500">Draft</span>
            </>
          )}
        </div>

        </header>

        {image && (
          <div className="agi-cover agi-cover--article mx-auto mt-6 w-full max-w-[90rem]">
            <img src={image} alt="" />
          </div>
        )}

        <article
          className="article-prose prose prose-lg prose-neutral dark:prose-invert mx-auto mt-8 w-full max-w-5xl prose-h1:font-extrabold prose-h2:font-bold prose-p:leading-7"
          dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
        />

        <div className="article-page-footer mx-auto w-full max-w-5xl">
          {message && <div className="mt-6 text-sm text-green-700">{message}</div>}
          {errorMessage && <div className="mt-6 text-sm text-red-600">{errorMessage}</div>}

        <div className="mt-10 flex flex-wrap gap-3">
          <Button
            variant="outline"
            onClick={() =>
              window.open(
                `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(shareUrl)}`,
                '_blank'
              )
            }
          >
            Share on LinkedIn
          </Button>

          <Button
            variant="outline"
            onClick={() =>
              window.open(
                `https://twitter.com/intent/tweet?url=${encodeURIComponent(shareUrl)}&text=${encodeURIComponent(title)}`,
                '_blank'
              )
            }
          >
            Share on X
          </Button>

          <Button variant="outline" onClick={() => navigator.clipboard.writeText(shareUrl)}>
            Copy link
          </Button>

          {user?.id === article.author_id && (
            <>
              <Button variant="outline" onClick={() => navigate(`/admin/articles/edit/${encodeURIComponent(article.slug)}`)}>
                Edit
              </Button>
              <Button variant="destructive" onClick={deleteArticle}>
                Delete
              </Button>
            </>
          )}
        </div>

        <Suspense fallback={null}>
          <ArticleKnowledgePanel
            researchId={article.research_id || article.rms_id || null}
            ticker={(Array.isArray(article.tickers) && article.tickers[0]) || null}
            title={article.title}
          />
        </Suspense>

        {/* ----------------------------- */}
        {/* Comments Section */}
        {/* ----------------------------- */}
        <Comments articleId={article.id} />
        </div>
      </main>
    </div>
  );
}
