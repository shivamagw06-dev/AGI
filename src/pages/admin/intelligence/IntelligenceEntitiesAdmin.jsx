import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchEntities, fetchPlatformStats, entityPublicPath } from '@/lib/intelligencePlatformApi';

const TYPE_FILTERS = [
  { value: '', label: 'All types' },
  { value: 'pe_firm', label: 'Firms' },
  { value: 'fund', label: 'Funds' },
  { value: 'portfolio_company', label: 'Portfolio companies' },
  { value: 'transaction', label: 'Transactions' },
  { value: 'person', label: 'People' },
  { value: 'industry', label: 'Industries' },
  { value: 'news', label: 'News' },
];

export default function IntelligenceEntitiesAdmin() {
  const [stats, setStats] = useState(null);
  const [type, setType] = useState('');
  const [q, setQ] = useState('');
  const [entities, setEntities] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPlatformStats().then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    fetchEntities({ type: type || undefined, q: q || undefined, limit: 100 })
      .then((res) => setEntities(res.entities || []))
      .catch((e) => setError(e.message));
  }, [type, q]);

  return (
    <div className="p-6 lg:p-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Entity Registry</h1>
        <p className="text-slate-500 mt-1">
          Universal entity system — firms, funds, companies, people, and relationships.
        </p>
      </div>

      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-2xl font-bold">{stats.entities?.total || 0}</div>
            <div className="text-sm text-slate-500">Entities</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-2xl font-bold">{stats.relationships?.total || 0}</div>
            <div className="text-sm text-slate-500">Relationships</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-2xl font-bold">{stats.timeline?.total || 0}</div>
            <div className="text-sm text-slate-500">Timeline events</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-2xl font-bold">{stats.entities?.published || 0}</div>
            <div className="text-sm text-slate-500">Published</div>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search entities…"
          className="border border-slate-300 rounded-md px-3 py-2 text-sm min-w-[220px]"
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="border border-slate-300 rounded-md px-3 py-2 text-sm"
        >
          {TYPE_FILTERS.map((f) => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Updated</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {entities.map((entity) => (
              <tr key={entity.id} className="hover:bg-slate-50">
                <td className="px-4 py-3 font-medium text-slate-900">{entity.name}</td>
                <td className="px-4 py-3 text-slate-600">{entity.entity_type.replace(/_/g, ' ')}</td>
                <td className="px-4 py-3">
                  <span className="text-xs uppercase tracking-wide text-slate-500">{entity.status}</span>
                </td>
                <td className="px-4 py-3 text-slate-500">
                  {entity.updated_at ? new Date(entity.updated_at).toLocaleDateString() : '—'}
                </td>
                <td className="px-4 py-3 text-right">
                  <Link
                    to={entityPublicPath(entity)}
                    target="_blank"
                    className="text-[#0b3b60] hover:underline"
                  >
                    View
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
