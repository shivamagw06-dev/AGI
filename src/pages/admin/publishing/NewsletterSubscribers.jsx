import { useEffect, useState } from 'react';
import { listNewsletterSubscribers } from '@/lib/publishingApi';
import { Button } from '@/components/ui/button';

export default function NewsletterSubscribers() {
  const [q, setQ] = useState('');
  const [source, setSource] = useState('');
  const [status, setStatus] = useState('active');
  const [preference, setPreference] = useState('');
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await listNewsletterSubscribers({
        q: q || undefined,
        source: source || undefined,
        status: status || undefined,
        preference: preference || undefined,
        limit: '200',
      });
      setRows(data.subscribers || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold">Subscribers</h1>
        <p className="text-sm text-slate-500 mt-1">Search by email, name, source, tags, preferences, status.</p>
      </div>

      <div className="flex flex-wrap gap-2 items-end">
        <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="border rounded-lg px-3 py-2 text-sm" value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="">All sources</option>
          {['website_signup', 'newsletter_popup', 'linkedin_campaign', 'csv_upload', 'api', 'referral'].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All status</option>
          <option value="active">active</option>
          <option value="unsubscribed">unsubscribed</option>
          <option value="pending">pending</option>
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={preference} onChange={(e) => setPreference(e.target.value)}>
          <option value="">All preferences</option>
          {['macro_research', 'company_research', 'forecast_updates', 'investment_office_brief', 'weekly_newsletter'].map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <Button onClick={load} disabled={loading}>{loading ? 'Loading…' : 'Search'}</Button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      <p className="text-xs text-slate-500">{total} subscribers</p>

      <div className="bg-white border rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase text-slate-500">
            <tr>
              <th className="px-3 py-2">Email</th>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Source</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Tags</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t">
                <td className="px-3 py-2 font-medium">{r.email}</td>
                <td className="px-3 py-2">{[r.first_name, r.last_name].filter(Boolean).join(' ') || '—'}</td>
                <td className="px-3 py-2">{r.source}</td>
                <td className="px-3 py-2">{r.status}</td>
                <td className="px-3 py-2 text-xs text-slate-500">{(r.tags || []).join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
