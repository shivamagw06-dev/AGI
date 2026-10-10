import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchCmsDashboard } from '@/lib/intelligenceCmsApi';

function Stat({ label, value, to }) {
  const inner = (
    <div className="bg-white border border-slate-200 rounded-lg p-5">
      <div className="text-2xl font-bold text-slate-900">{value}</div>
      <div className="text-sm text-slate-500 mt-1">{label}</div>
    </div>
  );
  return to ? <Link to={to} className="block hover:border-[#0b3b60] border border-transparent rounded-lg">{inner}</Link> : inner;
}

export default function IntelligenceDashboard() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCmsDashboard()
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="p-6 lg:p-8 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Intelligence CMS</h1>
        <p className="text-slate-500 mt-1">
          Knowledge graph → Intelligence CMS → Editorial pages → API → Website
        </p>
      </div>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {stats && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Stat label="Drafts" value={stats.drafts} to="/admin/intelligence/valuation-monitor?status=draft" />
            <Stat label="In review" value={stats.review} to="/admin/intelligence/valuation-monitor?status=review" />
            <Stat label="Published today" value={stats.publishedToday} />
            <Stat label="Scheduled" value={stats.scheduled} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8">
            <Stat label="AI drafts awaiting review" value={stats.aiDraftsAwaitingReview} />
            <Stat label="Missing metadata" value={stats.missingMetadata} />
            <Stat label="Broken relationships" value={stats.brokenRelationships} />
            <Stat label="Total records" value={stats.totalRecords} />
          </div>

          <section className="bg-white border border-slate-200 rounded-lg p-5">
            <h2 className="font-semibold text-slate-900 mb-4">Recently edited</h2>
            <ul className="divide-y divide-slate-100">
              {stats.recentlyEdited.map((r) => (
                <li key={r.id} className="py-3 flex justify-between gap-4 text-sm">
                  <span className="font-medium truncate">{r.data?.company || r.data?.name || r.data?.title || r.id}</span>
                  <span className="text-slate-400 shrink-0">{r.module} · {r.status}</span>
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
