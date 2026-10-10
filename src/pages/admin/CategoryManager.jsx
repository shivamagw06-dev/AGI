import { useState } from 'react';
import { Plus, Trash2, ChevronUp, ChevronDown, Database } from 'lucide-react';
import useCategories from '@/hooks/useCategories';
import { toSlug } from '@/lib/articleUtils';
import { Button } from '@/components/ui/button';

export default function CategoryManager() {
  const { categories, loading, source, saveCategory, deleteCategory, reorderCategory, seedDefaults } =
    useCategories();
  const [form, setForm] = useState({ name: '', description: '' });
  const [saving, setSaving] = useState(false);

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      await saveCategory({
        name: form.name.trim(),
        slug: toSlug(form.name),
        description: form.description.trim(),
        sort_order: categories.length + 1,
      });
      setForm({ name: '', description: '' });
    } catch (err) {
      alert(err.message || 'Failed to save category');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 lg:p-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Categories</h1>
        <p className="text-slate-500 mt-1">
          Organize articles by topic. Categories appear on the homepage and filter public articles.
        </p>
        {source === 'local' && (
          <div className="mt-4 flex items-start gap-3 p-4 rounded-lg bg-amber-50 border border-amber-200 text-sm text-amber-800">
            <Database size={18} className="shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Using local categories</p>
              <p className="mt-1 text-amber-700">
                Run <code className="bg-amber-100 px-1 rounded">supabase/migrations/001_cms_setup.sql</code> in
                Supabase SQL Editor for persistent category storage, then click Seed Defaults.
              </p>
              <Button size="sm" variant="outline" className="mt-2" onClick={seedDefaults}>
                Seed Defaults
              </Button>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleAdd} className="bg-white rounded-xl border border-slate-200 p-5 mb-6">
        <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Plus size={18} /> Add Category
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm"
            placeholder="Category name"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            required
          />
          <input
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm"
            placeholder="Description (optional)"
            value={form.description}
            onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
          />
        </div>
        <Button type="submit" disabled={saving} className="mt-4 bg-blue-700 hover:bg-blue-800">
          {saving ? 'Saving…' : 'Add Category'}
        </Button>
      </form>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {loading ? (
          <p className="p-8 text-center text-slate-400">Loading…</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {categories.map((cat) => (
              <li key={cat.id} className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50">
                <div className="flex flex-col gap-0.5">
                  <button type="button" onClick={() => reorderCategory(cat.id, 'up')} className="text-slate-300 hover:text-slate-600">
                    <ChevronUp size={14} />
                  </button>
                  <button type="button" onClick={() => reorderCategory(cat.id, 'down')} className="text-slate-300 hover:text-slate-600">
                    <ChevronDown size={14} />
                  </button>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-slate-900">{cat.name}</p>
                  <p className="text-xs text-slate-400">/{cat.slug}</p>
                  {cat.description && <p className="text-sm text-slate-500 mt-0.5">{cat.description}</p>}
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm(`Remove "${cat.name}"?`)) deleteCategory(cat.id);
                  }}
                  className="p-2 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded-md"
                >
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
