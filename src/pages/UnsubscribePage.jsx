import { useMemo, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { newsletterUnsubscribe, newsletterPreferences } from '@/lib/publishingApi';
import { Button } from '@/components/ui/button';

const PREFS = [
  ['daily_market_brief', 'Daily Market Brief'],
  ['weekly_newsletter', 'Weekly Newsletter'],
  ['macro_research', 'Macro Research'],
  ['company_research', 'Company Research'],
  ['sector_reports', 'Sector Reports'],
  ['forecast_updates', 'Forecast Updates'],
  ['investment_office_brief', 'Investment Office Brief'],
  ['product_updates', 'Product Updates'],
];

export default function UnsubscribePage() {
  const [params] = useSearchParams();
  const emailParam = params.get('email') || '';
  const tokenParam = params.get('token') || '';
  const [email, setEmail] = useState(emailParam);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [prefs, setPrefs] = useState(() => Object.fromEntries(PREFS.map(([k]) => [k, true])));
  const hasToken = useMemo(() => Boolean(tokenParam), [tokenParam]);

  async function onUnsubscribe() {
    setError('');
    try {
      await newsletterUnsubscribe({ email, token: tokenParam || undefined });
      setMessage('You have been unsubscribed. You will not receive further research emails.');
    } catch (err) {
      setError(err.message);
    }
  }

  async function onSavePrefs() {
    setError('');
    try {
      await newsletterPreferences({ email, token: tokenParam || undefined, preferences: prefs });
      setMessage('Preferences updated.');
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-16">
      <div className="mx-auto max-w-lg bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
        <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400 font-semibold">AGI Research</p>
        <h1 className="text-2xl font-bold mt-2 text-slate-900">Email preferences</h1>
        <p className="text-sm text-slate-500 mt-2">Update topics or unsubscribe. We never email unsubscribed addresses.</p>

        <label className="block mt-6 text-sm">
          Email
          <input
            className="mt-1 w-full border rounded-lg px-3 py-2"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={hasToken && Boolean(emailParam)}
          />
        </label>

        <div className="mt-6 space-y-2">
          {PREFS.map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={Boolean(prefs[key])}
                onChange={(e) => setPrefs((p) => ({ ...p, [key]: e.target.checked }))}
              />
              {label}
            </label>
          ))}
        </div>

        <div className="mt-6 flex flex-wrap gap-2">
          <Button className="bg-blue-700 hover:bg-blue-800" onClick={onSavePrefs}>Save preferences</Button>
          <Button variant="outline" onClick={onUnsubscribe}>Unsubscribe all</Button>
        </div>

        {message && <p className="mt-4 text-sm text-green-700">{message}</p>}
        {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

        <p className="mt-8 text-xs text-slate-400">
          <Link to="/privacy" className="underline">Privacy</Link> · Research distribution only — not spam marketing.
        </p>
      </div>
    </div>
  );
}
