import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, ExternalLink, Loader2, Radio, Save } from 'lucide-react';
import { getLiveBroadcastSettings, saveLiveBroadcastSetting } from '@/lib/liveDeskBroadcastApi';

const CHANNELS = [
  { id: 'global', label: 'Bloomberg Live', market: 'Global markets' },
  { id: 'india', label: 'NDTV Profit Live', market: 'Indian markets' },
];

export default function BroadcastLinks() {
  const [values, setValues] = useState({ global: '', india: '' });
  const [saved, setSaved] = useState({});
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setMessage(null);
    try {
      const payload = await getLiveBroadcastSettings();
      const next = Object.fromEntries((payload.broadcasts || []).map((row) => [row.id, row.youtubeUrl]));
      setValues((current) => ({ ...current, ...next }));
      setSaved(next);
    } catch (error) {
      setMessage({ tone: 'error', text: error?.message || 'Could not load broadcast links.' });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const save = async (id) => {
    setBusy(id);
    setMessage(null);
    try {
      const payload = await saveLiveBroadcastSetting(id, values[id]);
      const row = payload.broadcast;
      setValues((current) => ({ ...current, [id]: row.youtubeUrl }));
      setSaved((current) => ({ ...current, [id]: row.youtubeUrl }));
      setMessage({ tone: 'ok', text: `${row.title} updated. Live Desk will refresh within about one minute.` });
    } catch (error) {
      setMessage({ tone: 'error', text: error?.message || 'Could not save the broadcast link.' });
    } finally {
      setBusy('');
    }
  };

  return (
    <div className="max-w-4xl p-6 lg:p-8">
      <header className="mb-8">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
          <Radio size={16} /> Live Desk controls
        </div>
        <h1 className="mt-2 text-2xl font-bold text-slate-950">Broadcast links</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
          Paste the current YouTube watch link for each publisher. A channel <code>/live</code> link is also accepted and resolved to its active video before saving.
        </p>
      </header>

      {message ? (
        <div className={`mb-5 flex items-center gap-2 rounded-xl border px-4 py-3 text-sm ${message.tone === 'ok' ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-red-200 bg-red-50 text-red-800'}`}>
          {message.tone === 'ok' ? <CheckCircle2 size={17} /> : null}
          {message.text}
        </div>
      ) : null}

      <div className="space-y-5">
        {CHANNELS.map((channel) => (
          <section key={channel.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-4 flex items-start justify-between gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">{channel.market}</p>
                <h2 className="mt-1 text-lg font-semibold text-slate-950">{channel.label}</h2>
              </div>
              {saved[channel.id] ? (
                <a href={saved[channel.id]} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-sm font-medium text-blue-700 hover:text-blue-900">
                  Open current <ExternalLink size={14} />
                </a>
              ) : null}
            </div>
            <label className="block text-sm font-medium text-slate-700" htmlFor={`broadcast-${channel.id}`}>YouTube URL</label>
            <div className="mt-2 flex flex-col gap-3 sm:flex-row">
              <input
                id={`broadcast-${channel.id}`}
                type="url"
                value={values[channel.id]}
                onChange={(event) => setValues((current) => ({ ...current, [channel.id]: event.target.value }))}
                placeholder="https://www.youtube.com/watch?v=..."
                className="min-w-0 flex-1 rounded-xl border border-slate-300 px-4 py-3 text-sm text-slate-950 outline-none transition focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                disabled={loading || busy === channel.id}
              />
              <button
                type="button"
                onClick={() => save(channel.id)}
                disabled={loading || !!busy || !values[channel.id]?.trim() || values[channel.id] === saved[channel.id]}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-blue-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-800 disabled:cursor-not-allowed disabled:bg-slate-300"
              >
                {busy === channel.id ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save link
              </button>
            </div>
          </section>
        ))}
      </div>

      <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-900">
        Use only the publisher's official YouTube channel. Saving changes the embedded player, not the publisher name or attribution.
      </div>
    </div>
  );
}
