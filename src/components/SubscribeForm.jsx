import { useState } from 'react';
import { subscribeNewsletter } from '@/lib/subscribeNewsletter';

export default function SubscribeForm() {
  const [email, setEmail] = useState('');
  const [ok, setOk] = useState(false);
  const [err, setErr] = useState('');

  async function onSubmit(e) {
    e.preventDefault();
    setErr('');
    setOk(false);
    try {
      await subscribeNewsletter(email);
      setOk(true);
      setEmail('');
    } catch (error) {
      setErr(error.message || 'Subscription failed');
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex gap-2">
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="you@example.com"
        className="px-3 py-2 rounded border border-slate-300 w-64"
        required
      />
      <button className="px-4 py-2 rounded bg-amber-500 text-white">Subscribe</button>
      {ok && <span className="text-emerald-600 text-sm">Check your inbox</span>}
      {err && <span className="text-rose-600 text-sm">{err}</span>}
    </form>
  );
}
