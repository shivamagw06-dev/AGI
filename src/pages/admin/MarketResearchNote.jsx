import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, ExternalLink, FileText, Loader2, Plus, Save } from 'lucide-react';
import { supabase } from '@/lib/supabaseClient';
import { useAuth } from '@/contexts/AuthContext';
import { toSlug } from '@/lib/articleUtils';
import {
  MARKET_SECTOR_FEATURED_TAG,
  buildNoteTags,
  getMarketResearchNotes,
  noteAuthor,
  noteThemes,
} from '@/lib/marketResearchNote';

const blank = () => ({
  id: null, title: '', subtitle: '', author: 'AGI Research', date: new Date().toISOString().slice(0, 10),
  summary: '', fullNote: '', themes: '', status: 'draft', featured: true, tags: [], slug: '',
});

function noteDate(note) {
  return String(note.published_at || note.created_at || new Date().toISOString()).slice(0, 10);
}

export default function MarketResearchNote() {
  const { user } = useAuth();
  const [notes, setNotes] = useState([]);
  const [form, setForm] = useState(blank);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    try { setNotes(await getMarketResearchNotes()); }
    catch (err) { setError(err?.message || 'Could not load research notes.'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const select = (note) => {
    setMessage(''); setError('');
    setForm({
      id: note.id, title: note.title || '', subtitle: note.meta_description || '', author: noteAuthor(note.tags),
      date: noteDate(note), summary: note.excerpt || '', fullNote: note.content_md || note.content || '',
      themes: noteThemes(note.tags).join('\n'), status: note.status || 'draft',
      featured: (note.tags || []).includes(MARKET_SECTOR_FEATURED_TAG), tags: note.tags || [], slug: note.slug || '',
    });
  };
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const themes = useMemo(() => form.themes.split('\n').map((item) => item.trim()).filter(Boolean), [form.themes]);

  const save = async (nextStatus = form.status) => {
    setSaving(true); setError(''); setMessage('');
    try {
      if (!form.title.trim()) throw new Error('A title is required.');
      const slug = form.slug || `${toSlug(form.title)}-${form.date.replaceAll('-', '')}`;
      const payload = {
        title: form.title.trim(), slug, section: 'Research Reports', excerpt: form.summary.trim(),
        meta_description: form.subtitle.trim() || form.summary.trim(), content_md: form.fullNote.trim(),
        content: form.fullNote.trim(), status: nextStatus,
        tags: buildNoteTags({ themes, author: form.author, featured: form.featured, existing: form.tags }),
      };
      if (!form.id) payload.author_id = user.id;
      if (nextStatus === 'published') payload.published_at = new Date(`${form.date}T12:00:00+05:30`).toISOString();

      if (nextStatus === 'published' && form.featured) {
        const { data: prior } = await supabase.from('articles').select('id,tags').contains('tags', [MARKET_SECTOR_FEATURED_TAG]);
        await Promise.all((prior || []).filter((item) => item.id !== form.id).map((item) =>
          supabase.from('articles').update({ tags: (item.tags || []).filter((tag) => tag !== MARKET_SECTOR_FEATURED_TAG) }).eq('id', item.id)
        ));
      }
      const result = form.id
        ? await supabase.from('articles').update(payload).eq('id', form.id).select('id,slug,status').single()
        : await supabase.from('articles').insert(payload).select('id,slug,status').single();
      if (result.error) throw result.error;
      setForm((current) => ({ ...current, id: result.data.id, slug: result.data.slug, status: result.data.status }));
      setMessage(nextStatus === 'published' ? 'Published. This is now the featured Sector Intelligence research note.' : 'Draft saved.');
      await load();
    } catch (err) { setError(err?.message || 'Could not save the research note.'); }
    finally { setSaving(false); }
  };

  return (
    <div className="mx-auto max-w-6xl p-6 lg:p-8">
      <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
        <div><p className="text-xs font-bold uppercase tracking-[.18em] text-emerald-700">Market Intelligence</p><h1 className="mt-1 text-3xl font-semibold text-slate-950">AGI Research Note</h1><p className="mt-2 max-w-2xl text-sm text-slate-600">Editorial market commentary for the Sector Intelligence desk. Only the latest published featured note appears to clients.</p></div>
        <button type="button" onClick={() => { setForm(blank()); setMessage(''); setError(''); }} className="inline-flex items-center gap-2 rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white"><Plus size={16} /> New note</button>
      </div>
      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="rounded border border-slate-200 bg-white p-3">
          <p className="px-2 pb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Research notes</p>
          {loading ? <p className="p-3 text-sm text-slate-500">Loading…</p> : notes.length ? notes.map((note) => <button key={note.id} type="button" onClick={() => select(note)} className={`mb-1 w-full rounded p-3 text-left hover:bg-slate-50 ${form.id === note.id ? 'bg-blue-50 ring-1 ring-blue-200' : ''}`}><span className="block text-sm font-semibold text-slate-900">{note.title}</span><span className="mt-1 block text-xs text-slate-500">{note.status} · {noteDate(note)}</span></button>) : <p className="p-3 text-sm text-slate-500">No sector research notes yet.</p>}
        </aside>
        <section className="rounded border border-slate-200 bg-white p-5 shadow-sm">
          {error ? <p className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</p> : null}
          {message ? <p className="mb-4 flex items-center gap-2 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"><CheckCircle2 size={16} /> {message}</p> : null}
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="sm:col-span-2 text-sm font-medium text-slate-800">Title<input value={form.title} onChange={(e) => update('title', e.target.value)} placeholder="Indian Equities: Valuation Dispersion Is Creating a More Selective Market" className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
            <label className="sm:col-span-2 text-sm font-medium text-slate-800">Subtitle<input value={form.subtitle} onChange={(e) => update('subtitle', e.target.value)} placeholder="A short context line shown in the research note." className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
            <label className="text-sm font-medium text-slate-800">Date<input type="date" value={form.date} onChange={(e) => update('date', e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
            <label className="text-sm font-medium text-slate-800">Author<input value={form.author} onChange={(e) => update('author', e.target.value)} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
            <label className="sm:col-span-2 text-sm font-medium text-slate-800">Short summary<textarea value={form.summary} onChange={(e) => update('summary', e.target.value)} rows={3} placeholder="The 2–4 sentence editorial summary shown to clients." className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
            <label className="sm:col-span-2 text-sm font-medium text-slate-800">Full research note<textarea value={form.fullNote} onChange={(e) => update('fullNote', e.target.value)} rows={12} placeholder="Write the full AGI research note. It opens via Read Full Note." className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm" /></label>
            <label className="sm:col-span-2 text-sm font-medium text-slate-800">Key themes <span className="font-normal text-slate-500">(one per line, optional)</span><textarea value={form.themes} onChange={(e) => update('themes', e.target.value)} rows={4} placeholder={'Industrials valuation has normalised\nMaterials remain below historical ranges'} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm" /></label>
          </div>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
            <label className="flex items-center gap-2 text-sm font-medium text-slate-800"><input type="checkbox" checked={form.featured} onChange={(e) => update('featured', e.target.checked)} /> Featured on Sector Intelligence</label>
            <div className="flex gap-2"><button type="button" disabled={saving} onClick={() => save('draft')} className="inline-flex items-center gap-2 rounded border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700"><Save size={15} /> Save draft</button><button type="button" disabled={saving} onClick={() => save('published')} className="inline-flex items-center gap-2 rounded bg-emerald-700 px-3 py-2 text-sm font-semibold text-white">{saving ? <Loader2 className="animate-spin" size={15} /> : <FileText size={15} />} Publish note</button></div>
          </div>
          {form.slug && form.status === 'published' ? <Link to={`/article/${form.slug}`} target="_blank" className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-blue-700">View public note <ExternalLink size={14} /></Link> : null}
        </section>
      </div>
    </div>
  );
}
