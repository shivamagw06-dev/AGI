import { useEffect, useState } from 'react';
import { listNewsletterCampaigns } from '@/lib/publishingApi';

export default function CampaignHistory() {
  const [campaigns, setCampaigns] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    listNewsletterCampaigns()
      .then((d) => setCampaigns(d.campaigns || []))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold">Campaign History</h1>
        <p className="text-sm text-slate-500 mt-1">Archive of research distribution sends.</p>
      </div>
      {error && <p className="text-red-600 text-sm">{error}</p>}
      <div className="bg-white border rounded-xl divide-y">
        {campaigns.map((c) => (
          <div key={c.id} className="p-4 flex flex-wrap justify-between gap-3">
            <div>
              <p className="font-medium">{c.name}</p>
              <p className="text-xs text-slate-500 mt-1">{c.status} · {c.segment} · sent {c.stats?.sent ?? 0}</p>
            </div>
            <p className="text-xs text-slate-400">{c.sent_at ? new Date(c.sent_at).toLocaleString() : '—'}</p>
          </div>
        ))}
        {!campaigns.length && <p className="p-4 text-sm text-slate-500">No campaigns yet.</p>}
      </div>
    </div>
  );
}
