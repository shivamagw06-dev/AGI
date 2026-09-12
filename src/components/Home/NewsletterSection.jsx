import { useMemo, useState } from 'react';
import { Check, Loader2 } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { subscribeNewsletter } from '@/lib/subscribeNewsletter';
import { AGI_LETTERS, defaultLetterPreferences } from '@/config/agiLetters';

export default function NewsletterSection({ initialSelected = null, variant = 'full' }) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();
  const minimal = variant === 'minimal';

  const initialPrefs = useMemo(
    () => defaultLetterPreferences(initialSelected),
    [initialSelected]
  );
  const [prefs, setPrefs] = useState(initialPrefs);

  const toggle = (key) => {
    setPrefs((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      if (!Object.values(next).some(Boolean)) next.agi_markets = true;
      return next;
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await subscribeNewsletter(email, { preferences: prefs, source: 'homepage' });
      toast({
        title: 'Subscribed to AGI Letters',
        description: 'Check your inbox for a welcome email from updates@agarwalglobalinvestments.com.',
      });
      setEmail('');
    } catch (err) {
      toast({ title: 'Subscription failed', description: err.message, variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  if (minimal) {
    return (
      <section id="newsletter" className="border-t border-[#e8eaee] bg-white py-12 md:py-16" aria-labelledby="agi-letters-heading">
        <div className="mx-auto max-w-[1680px] px-4 sm:px-6 lg:px-8 text-center">
          <div className="mx-auto max-w-[720px]">
          <h2 id="agi-letters-heading" className="font-serif text-3xl md:text-4xl font-bold text-[#111111]">
            Stay Ahead of the Market.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-[#555555]">
            Receive institutional-quality research and market intelligence directly in your inbox.
          </p>
          <form onSubmit={handleSubmit} className="mx-auto mt-8 flex max-w-lg flex-col gap-3 sm:flex-row">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              disabled={loading}
              className="min-h-[48px] flex-1 rounded-md border border-[#d5d8de] px-4 text-sm focus:border-[#111111] focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="inline-flex min-h-[48px] items-center justify-center rounded-md bg-[#0b1f33] px-6 text-sm font-bold text-white hover:bg-[#163353] disabled:opacity-60"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Subscribing…
                </>
              ) : (
                'Subscribe'
              )}
            </button>
          </form>
          <p className="mt-4 text-[11px] text-[#767676]">
            Free · Unsubscribe anytime · updates@agarwalglobalinvestments.com
          </p>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section id="newsletter" className="py-12 border-t border-[#dddddd] bg-[#fafafa]" aria-labelledby="agi-letters-heading">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start border border-[#dddddd] bg-white p-6 md:p-10">
          <div>
            <p className="text-[11px] font-bold uppercase tracking-wider text-[#5d6470]">Institutional Morning Brief</p>
            <h2 id="agi-letters-heading" className="mt-2 text-2xl font-bold text-[#111111]">
              Subscribe to AGI research
            </h2>
            <p className="mt-2 text-sm text-[#555555] max-w-xl">
              Receive Morning Research, Post Market Research, Global Brief, Macro Updates and IPO Notes.
            </p>

            <div className="mt-6 space-y-4">
              {AGI_LETTERS.map((letter) => (
                <div key={letter.key} className="border-b border-[#eeeeee] pb-4 last:border-0 last:pb-0">
                  <div className="flex items-baseline justify-between gap-3">
                    <h3 className="text-sm font-bold text-[#111111]">{letter.name}</h3>
                    <span className="text-[11px] font-semibold text-[#767676] whitespace-nowrap">
                      {letter.schedule}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-[#444444]">{letter.tagline}</p>
                </div>
              ))}
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              {AGI_LETTERS.map((letter) => (
                <label
                  key={letter.key}
                  className={`flex cursor-pointer items-start gap-3 border px-3 py-3 transition-colors ${
                    prefs[letter.key]
                      ? 'border-[#111111] bg-[#fafafa]'
                      : 'border-[#dddddd] hover:border-[#999999]'
                  }`}
                >
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={Boolean(prefs[letter.key])}
                    onChange={() => toggle(letter.key)}
                  />
                  <span className="min-w-0">
                    <span className="block text-sm font-bold text-[#111111]">{letter.name}</span>
                    <span className="block text-xs text-[#767676] mt-0.5">{letter.schedule}</span>
                  </span>
                  {prefs[letter.key] ? <Check className="ml-auto mt-0.5 h-4 w-4 text-[#008001] shrink-0" /> : null}
                </label>
              ))}
            </div>

            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              disabled={loading}
              className="w-full border border-[#cccccc] px-4 py-3 text-sm focus:border-[#111111] focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#111111] text-white text-sm font-bold py-3 hover:bg-[#333333] transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" /> Subscribing…
                </>
              ) : (
                'Subscribe to selected letters'
              )}
            </button>
            <p className="text-[10px] text-[#767676]">
              Free · Unsubscribe anytime · Sent from updates@agarwalglobalinvestments.com
            </p>
          </form>
        </div>
      </div>
    </section>
  );
}
