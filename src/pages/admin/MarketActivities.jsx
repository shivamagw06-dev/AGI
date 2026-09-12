import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Activity, ExternalLink, Pencil, Plus, Trash2 } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';
import {
  createMarketActivity,
  deleteMarketActivity,
  listMarketActivitiesAdmin,
  normalizeActivityBody,
  updateMarketActivity,
} from '@/lib/marketActivitiesApi';
import { Button } from '@/components/ui/button';

const MAX_LEN = 280;

function formatWhen(value) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('en-IN');
  } catch {
    return '—';
  }
}

export default function MarketActivities() {
  const { user } = useAuth();
  const admin = isAdmin(user);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [body, setBody] = useState('');
  const [published, setPublished] = useState(true);
  const [editingId, setEditingId] = useState(null);
  const [message, setMessage] = useState('');

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await listMarketActivitiesAdmin({ limit: 50 }));
    } catch (err) {
      setMessage(err?.message || 'Could not load activities.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  if (!admin) {
    return (
      <div className="p-6 lg:p-8 max-w-3xl">
        <h1 className="text-2xl font-bold text-slate-900">Activities</h1>
        <p className="mt-2 text-slate-500">Only admins can post Market Intelligence activities.</p>
      </div>
    );
  }

  const resetForm = () => {
    setBody('');
    setPublished(true);
    setEditingId(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const cleaned = normalizeActivityBody(body);
    if (!cleaned) {
      setMessage('Write a 1–2 line update first.');
      return;
    }
    setSaving(true);
    setMessage('');
    try {
      if (editingId) {
        await updateMarketActivity(editingId, { body: cleaned, published });
        setMessage('Activity updated.');
      } else {
        await createMarketActivity({ body: cleaned, published, userId: user?.id });
        setMessage('Activity published to Market Intelligence.');
      }
      resetForm();
      await reload();
    } catch (err) {
      setMessage(err?.message || 'Save failed.');
    } finally {
      setSaving(false);
    }
  };

  const startEdit = (item) => {
    setEditingId(item.id);
    setBody(item.body || '');
    setPublished(item.published !== false);
    setMessage('');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleDelete = async (item) => {
    if (!window.confirm('Delete this activity?')) return;
    try {
      await deleteMarketActivity(item.id);
      if (editingId === item.id) resetForm();
      await reload();
      setMessage('Activity deleted.');
    } catch (err) {
      setMessage(err?.message || 'Delete failed.');
    }
  };

  const handleTogglePublish = async (item) => {
    try {
      await updateMarketActivity(item.id, { published: !item.published });
      await reload();
    } catch (err) {
      setMessage(err?.message || 'Could not update publish state.');
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-3xl">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Activity size={22} /> Activities
          </h1>
          <p className="text-slate-500 mt-1">
            Post 1–2 line desk updates. They appear in the Activities box on Market Intelligence.
          </p>
        </div>
        <Link
          to="/market-intelligence"
          className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-700 hover:underline"
        >
          View live page <ExternalLink size={14} />
        </Link>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="font-semibold text-slate-900 mb-3 flex items-center gap-2">
          {editingId ? <Pencil size={16} /> : <Plus size={16} />}
          {editingId ? 'Edit update' : 'New update'}
        </h2>
        <textarea
          className="w-full min-h-[96px] border border-slate-200 rounded-lg px-3 py-2 text-sm leading-relaxed"
          placeholder="e.g. Pre-market: Nifty futures soft; watch banking names into open."
          value={body}
          maxLength={MAX_LEN}
          onChange={(e) => setBody(e.target.value)}
          required
        />
        <div className="mt-2 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500">
          <label className="inline-flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={published}
              onChange={(e) => setPublished(e.target.checked)}
              className="rounded border-slate-300"
            />
            Show on Market Intelligence
          </label>
          <span>
            {normalizeActivityBody(body).length}/{MAX_LEN}
          </span>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          <Button type="submit" disabled={saving} className="bg-blue-700 hover:bg-blue-800">
            {saving ? 'Saving…' : editingId ? 'Save changes' : 'Post activity'}
          </Button>
          {editingId ? (
            <Button type="button" variant="outline" onClick={resetForm}>
              Cancel edit
            </Button>
          ) : null}
        </div>
        {message ? <p className="mt-3 text-sm text-slate-600">{message}</p> : null}
      </form>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-900">Recent activities</h2>
        </div>
        {loading ? (
          <p className="p-5 text-sm text-slate-500">Loading…</p>
        ) : !items.length ? (
          <p className="p-5 text-sm text-slate-500">No activities yet. Post your first update above.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {items.map((item) => (
              <li key={item.id} className="px-5 py-4 flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-slate-900 leading-snug">{item.body}</p>
                  <p className="mt-1 text-[11px] text-slate-500">
                    {formatWhen(item.created_at)}
                    {' · '}
                    <span className={item.published ? 'text-emerald-700' : 'text-amber-700'}>
                      {item.published ? 'Live' : 'Hidden'}
                    </span>
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => startEdit(item)}>
                    Edit
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleTogglePublish(item)}>
                    {item.published ? 'Hide' : 'Show'}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-red-700 border-red-200"
                    onClick={() => handleDelete(item)}
                  >
                    <Trash2 size={14} />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
