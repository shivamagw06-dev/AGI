import { useEffect, useState } from 'react';
import { getNewsletterAnalytics } from '@/lib/publishingApi';

export default function NewsletterAnalytics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    getNewsletterAnalytics()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <p className="p-6 text-red-600">{error}</p>;
  if (!data) return <p className="p-6 text-slate-500">Loading analytics…</p>;

  return (
    <div className="p-6 space-y-8 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold">Campaign Analytics</h1>
        <p className="text-sm text-slate-500 mt-1">Subscribers, growth, opens, clicks, topics.</p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          ['Subscribers', data.subscribers.total],
          ['Open rate', `${data.email.open_rate}%`],
          ['Click rate', `${data.email.click_rate}%`],
          ['Bounce rate', `${data.email.bounce_rate}%`],
        ].map(([label, value]) => (
          <div key={label} className="bg-white border rounded-xl p-4">
            <p className="text-xs uppercase text-slate-400">{label}</p>
            <p className="text-2xl font-semibold mt-2">{value}</p>
          </div>
        ))}
      </div>

      <section className="grid md:grid-cols-2 gap-6">
        <div className="bg-white border rounded-xl p-4">
          <h2 className="font-semibold mb-3">Traffic / source</h2>
          <ul className="space-y-2 text-sm">
            {Object.entries(data.traffic_source || {}).map(([k, v]) => (
              <li key={k} className="flex justify-between border-t pt-2"><span>{k}</span><span className="font-medium">{v}</span></li>
            ))}
          </ul>
        </div>
        <div className="bg-white border rounded-xl p-4">
          <h2 className="font-semibold mb-3">Top topics</h2>
          <ul className="space-y-2 text-sm">
            {(data.top_performing_topics || []).map((t) => (
              <li key={t.topic} className="flex justify-between border-t pt-2"><span>{t.topic}</span><span className="font-medium">{t.count}</span></li>
            ))}
          </ul>
        </div>
      </section>

      <section className="bg-white border rounded-xl p-4">
        <h2 className="font-semibold mb-3">Most read / distributed</h2>
        <ul className="space-y-2 text-sm">
          {(data.most_read_articles || []).map((a) => (
            <li key={a.slug || a.title} className="flex justify-between border-t pt-2 gap-3">
              <span>{a.title}</span>
              <span className="text-slate-500 shrink-0">opens {a.opens} · clicks {a.clicks}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
