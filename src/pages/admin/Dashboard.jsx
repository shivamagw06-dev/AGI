import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, FileText, Eye, Pencil, Trash2, Clock, Brain, Pin } from 'lucide-react';
import useArticlesAdmin from '@/hooks/useArticlesAdmin';
import { formatArticleDate, hasHomepageFeaturedTag, setHomepageFeaturedArticle } from '@/lib/articleUtils';
import { getCmsLearningStatus, learnCmsArticles } from '@/lib/intelligenceApi';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';
import { Button } from '@/components/ui/button';

export default function AdminDashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const admin = isAdmin(user);
  const { articles, loading, deleteArticle, reload, stats } = useArticlesAdmin();
  const [cmsLearn, setCmsLearn] = useState(null);
  const [learnBusy, setLearnBusy] = useState(false);
  const [learnMsg, setLearnMsg] = useState('');
  const [pinningId, setPinningId] = useState(null);

  const refreshLearn = useCallback(async () => {
    try {
      setCmsLearn(await getCmsLearningStatus(10));
    } catch {
      setCmsLearn(null);
    }
  }, []);

  useEffect(() => {
    refreshLearn();
  }, [refreshLearn]);

  const handlePinHomepage = async (article) => {
    if (article.status !== 'published') {
      alert('Publish the article first, then you can show it first on the homepage.');
      return;
    }
    const already = hasHomepageFeaturedTag(article);
    setPinningId(article.id);
    try {
      await setHomepageFeaturedArticle(article.id, { enabled: !already });
      await reload();
    } catch (err) {
      alert(err.message || 'Could not update homepage lead.');
    } finally {
      setPinningId(null);
    }
  };

  const handleDelete = async (id, title) => {
    if (!window.confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
      await deleteArticle(id);
    } catch (err) {
      alert(err.message || 'Delete failed');
    }
  };

  const handleLearnArticles = async () => {
    setLearnBusy(true);
    setLearnMsg('');
    try {
      const result = await learnCmsArticles({
        only_unlearned: true,
        limit: 200,
        compound: true,
      });
      setLearnMsg(
        `Intelligence learned ${result?.learned ?? 0} article(s) on ${result?.learning_date || '—'}` +
          (result?.failed ? ` (${result.failed} failed)` : '') +
          '.'
      );
      await refreshLearn();
    } catch (err) {
      setLearnMsg(err?.message || 'Learning run failed');
    } finally {
      setLearnBusy(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-7xl">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{admin ? 'Dashboard' : 'My Articles'}</h1>
          <p className="text-slate-500 mt-1">
            {admin
              ? 'Manage research articles and market updates. Use Show first to pick the homepage lead story.'
              : 'Edit and manage articles you uploaded'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {admin ? (
            <Button
              variant="outline"
              disabled={learnBusy}
              onClick={handleLearnArticles}
              className="border-slate-300"
            >
              <Brain size={16} className="mr-2" />
              {learnBusy ? 'Intelligence reading…' : 'Ask intelligence to learn articles'}
            </Button>
          ) : null}
          <Button onClick={() => navigate('/admin/articles/new')} className="bg-blue-700 hover:bg-blue-800">
            <Plus size={16} className="mr-2" />
            New Article
          </Button>
        </div>
      </div>

      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
        <p className="font-semibold text-slate-900">
          {admin ? 'Two CMS destinations' : 'Edit your uploads anytime'}
        </p>
        <p className="mt-1">
          {admin ? (
            <>
              <span className="font-semibold text-blue-700">Publish to Website</span> — live public research.
              {' '}
              <span className="font-semibold text-violet-700">Send to Intelligence</span> — private notes for Ask AGI only (not on the website).
            </>
          ) : (
            <>
              Open any article below with <span className="font-semibold text-blue-700">Edit</span> to update
              title, body, cover, or publish status. You can only change articles you uploaded.
            </>
          )}
        </p>
        {admin ? (
          <p className="mt-2 text-slate-500">
            Learning calendar today: {cmsLearn?.today || '—'} · pending unread:{' '}
            {cmsLearn?.pending_count ?? '—'} · last dates:{' '}
            {(cmsLearn?.learning_calendar || [])
              .slice(0, 3)
              .map((d) => `${d.learning_date} (${d.learned})`)
              .join(' · ') || 'none yet'}
          </p>
        ) : null}
        {learnMsg ? <p className="mt-2 text-emerald-800">{learnMsg}</p> : null}
      </div>

      <div className="grid sm:grid-cols-4 gap-4 mb-8">
        {[
          ['Total', stats.total, 'text-slate-900'],
          ['Website', stats.published, 'text-green-600'],
          ['Intelligence', stats.intelligence, 'text-violet-700'],
          ['Drafts', stats.drafts, 'text-amber-600'],
        ].map(([label, value, color]) => (
          <div key={label} className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-sm text-slate-500">{label}</p>
            <p className={`text-3xl font-bold mt-1 ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-2">
          <FileText size={18} className="text-slate-400" />
          <h2 className="font-semibold text-slate-900">{admin ? 'Recent Articles' : 'Your uploaded articles'}</h2>
        </div>

        {loading ? (
          <p className="p-8 text-center text-slate-400">Loading articles…</p>
        ) : articles.length === 0 ? (
          <div className="p-12 text-center">
            <p className="text-slate-500 mb-4">
              {admin
                ? 'No articles yet. Write your first market update or research report.'
                : 'You have not uploaded any articles yet.'}
            </p>
            <Button onClick={() => navigate('/admin/articles/new')} className="bg-blue-700 hover:bg-blue-800">
              {admin ? 'Create First Article' : 'Upload / Write Article'}
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-500 uppercase text-xs tracking-wide">
                <tr>
                  <th className="text-left px-5 py-3 font-medium">Title</th>
                  <th className="text-left px-5 py-3 font-medium">Category</th>
                  <th className="text-left px-5 py-3 font-medium">Status</th>
                  <th className="text-left px-5 py-3 font-medium">Homepage</th>
                  <th className="text-left px-5 py-3 font-medium">Date</th>
                  <th className="text-left px-5 py-3 font-medium">Learned</th>
                  <th className="text-right px-5 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {articles.map((article) => (
                  <tr key={article.id} className="hover:bg-slate-50/80">
                    <td className="px-5 py-4">
                      <p className="font-medium text-slate-900 line-clamp-1">{article.title}</p>
                      <p className="text-xs text-slate-400 mt-0.5">/{article.slug}</p>
                    </td>
                    <td className="px-5 py-4 text-slate-600">{article.section || '—'}</td>
                    <td className="px-5 py-4">
                      <span
                        className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                          article.status === 'published'
                            ? 'bg-green-100 text-green-700'
                            : article.status === 'intelligence' || (article.tags || []).includes('intelligence-only')
                              ? 'bg-violet-100 text-violet-700'
                              : 'bg-amber-100 text-amber-700'
                        }`}
                      >
                        {article.status === 'intelligence' || (article.tags || []).includes('intelligence-only')
                          ? 'intelligence'
                          : article.status}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      {article.status === 'published' ? (
                        <button
                          type="button"
                          onClick={() => handlePinHomepage(article)}
                          disabled={pinningId === article.id}
                          className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-semibold ${
                            hasHomepageFeaturedTag(article)
                              ? 'bg-blue-700 text-white hover:bg-blue-800'
                              : 'text-slate-600 hover:bg-blue-50 hover:text-blue-700'
                          }`}
                          title={
                            hasHomepageFeaturedTag(article)
                              ? 'This article is first on the homepage. Click to unpin.'
                              : 'Show this article first on the homepage'
                          }
                        >
                          <Pin size={13} />
                          {hasHomepageFeaturedTag(article) ? 'On homepage' : 'Show first'}
                        </button>
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      )}
                    </td>
                    <td className="px-5 py-4 text-slate-500 whitespace-nowrap">
                      <span className="flex items-center gap-1">
                        <Clock size={13} />
                        {formatArticleDate(article.published_at || article.created_at)}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-slate-500 whitespace-nowrap text-xs">
                      {article.last_learned_at
                        ? formatArticleDate(article.last_learned_at)
                        : article.status === 'published' || article.status === 'intelligence'
                          ? 'not yet'
                          : '—'}
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center justify-end gap-2">
                        {article.status === 'published' && (
                          <Link
                            to={`/article/${article.slug}`}
                            target="_blank"
                            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-600 hover:text-blue-700 hover:bg-blue-50"
                            title="View"
                          >
                            <Eye size={14} />
                            View
                          </Link>
                        )}
                        <button
                          type="button"
                          onClick={() => navigate(`/admin/articles/edit/${encodeURIComponent(article.slug)}`)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-semibold text-white bg-blue-700 hover:bg-blue-800"
                          title="Edit article"
                        >
                          <Pencil size={14} />
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(article.id, article.title)}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium text-slate-500 hover:text-red-700 hover:bg-red-50"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
