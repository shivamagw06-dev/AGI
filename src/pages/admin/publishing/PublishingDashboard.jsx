import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listPublishJobs, listNewsletterCampaigns, getNewsletterAnalytics } from '@/lib/publishingApi';
import { Button } from '@/components/ui/button';

export default function PublishingDashboard() {
  const [jobs, setJobs] = useState([]);
  const [campaigns, setCampaigns] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    Promise.all([listPublishJobs(), listNewsletterCampaigns(), getNewsletterAnalytics()])
      .then(([j, c, a]) => {
        if (!active) return;
        setJobs(j.jobs || []);
        setCampaigns(c.campaigns || []);
        setAnalytics(a);
      })
      .catch((err) => active && setError(err.message));
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="p-6 space-y-8 max-w-6xl">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-orange-500 font-semibold">Research Distribution</p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">Publishing Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">One-click publish → website, newsletter, social packs, analytics.</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline"><Link to="/admin/publishing/subscribers">Subscribers</Link></Button>
          <Button asChild variant="outline"><Link to="/admin/publishing/import">Import CSV</Link></Button>
          <Button asChild className="bg-blue-700 hover:bg-blue-800"><Link to="/admin/articles/new">New Research</Link></Button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>}

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          ['Active subscribers', analytics?.subscribers?.active ?? '—'],
          ['Emails sent', analytics?.email?.sent ?? '—'],
          ['Open rate', analytics ? `${analytics.email.open_rate}%` : '—'],
          ['Campaigns', campaigns.length],
        ].map(([label, value]) => (
          <div key={label} className="bg-white border border-slate-200 rounded-xl p-4">
            <p className="text-xs uppercase tracking-wide text-slate-400">{label}</p>
            <p className="text-2xl font-semibold text-slate-900 mt-2">{value}</p>
          </div>
        ))}
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-3">Newsletter queue / recent jobs</h2>
        <div className="bg-white border border-slate-200 rounded-xl divide-y">
          {jobs.length === 0 && <p className="p-4 text-sm text-slate-500">No distribution jobs yet. Publish an article from the editor.</p>}
          {jobs.map((job) => (
            <div key={job.id} className="p-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="font-medium text-slate-900">{job.title}</p>
                <p className="text-xs text-slate-500 mt-1">
                  {job.status} · sent {job.newsletter_sent || 0} · segment {job.segment}
                </p>
              </div>
              <div className="flex flex-wrap gap-2 text-[11px]">
                {Object.entries(job.channels || {}).map(([k, v]) => (
                  <span key={k} className="px-2 py-1 rounded-full bg-slate-100 text-slate-600">
                    {k}: {v?.status || '—'}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">Campaign history</h2>
        <div className="bg-white border border-slate-200 rounded-xl divide-y">
          {campaigns.slice(0, 8).map((c) => (
            <div key={c.id} className="p-4 flex justify-between gap-3 text-sm">
              <div>
                <p className="font-medium">{c.name}</p>
                <p className="text-xs text-slate-500">{c.status} · {c.segment}</p>
              </div>
              <p className="text-xs text-slate-400">{c.sent_at ? new Date(c.sent_at).toLocaleString() : '—'}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
