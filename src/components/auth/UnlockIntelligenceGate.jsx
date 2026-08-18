import { Link, useLocation } from 'react-router-dom';
import { BrainCircuit, Check, Lock, Sparkles } from 'lucide-react';
import {
  UNLOCK_BENEFITS,
  buildLoginUrl,
  getFeatureCopy,
  getFeatureForPath,
} from '@/lib/accessPolicy';

/**
 * Progressive registration wall — sells AGI intelligence instead of a bare login redirect.
 * Remembers returnTo via LoginPage ?next=.
 */
export default function UnlockIntelligenceGate({ feature: featureProp, returnTo: returnToProp }) {
  const location = useLocation();
  const returnTo = returnToProp || `${location.pathname}${location.search || ''}` || '/';
  const feature = featureProp || getFeatureForPath(location.pathname) || 'intelligence';
  const copy = getFeatureCopy(feature);
  const signupUrl = buildLoginUrl({ returnTo, mode: 'signup' });
  const signinUrl = buildLoginUrl({ returnTo, mode: 'signin' });

  return (
    <div className="relative min-h-[calc(100vh-4rem)] overflow-hidden bg-[#070f16] text-[#eef4f7]">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            'radial-gradient(ellipse at 20% 10%, rgba(59,130,246,0.22), transparent 45%), radial-gradient(ellipse at 80% 0%, rgba(16,185,129,0.12), transparent 40%), linear-gradient(rgba(120,150,170,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(120,150,170,0.05) 1px, transparent 1px)',
          backgroundSize: 'auto, auto, 40px 40px, 40px 40px',
        }}
      />

      {/* Soft preview silhouette */}
      <div className="pointer-events-none absolute inset-x-0 top-24 mx-auto hidden max-w-6xl px-6 opacity-30 blur-[2px] lg:block" aria-hidden>
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-40 rounded-xl border border-white/10 bg-white/5 p-4">
              <div className="h-3 w-24 rounded bg-white/20" />
              <div className="mt-4 h-8 w-32 rounded bg-white/15" />
              <div className="mt-6 h-2 w-full rounded bg-white/10" />
              <div className="mt-2 h-2 w-[80%] rounded bg-white/10" />
              <div className="mt-2 h-2 w-[60%] rounded bg-white/10" />
            </div>
          ))}
        </div>
      </div>

      <div className="relative z-10 mx-auto flex min-h-[calc(100vh-4rem)] max-w-3xl flex-col justify-center px-4 py-12 sm:px-6">
        <div className="rounded-2xl border border-white/10 bg-[#0b1620]/95 p-6 shadow-[0_30px_80px_rgba(0,0,0,0.45)] backdrop-blur-md sm:p-10">
          <div className="mb-6 flex items-center gap-3">
            <span className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/15 text-blue-300 ring-1 ring-blue-400/30">
              <BrainCircuit className="h-5 w-5" />
            </span>
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-blue-300">{copy.eyebrow}</p>
              <p className="mt-0.5 flex items-center gap-1.5 text-xs text-slate-400">
                <Lock className="h-3.5 w-3.5" /> Free account required
              </p>
            </div>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">{copy.title}</h1>
          <p className="mt-3 text-[15px] leading-relaxed text-slate-300">{copy.blurb}</p>

          <p className="mt-8 text-[11px] font-bold uppercase tracking-[0.14em] text-emerald-300/90">
            Unlock AGI Intelligence
          </p>
          <ul className="mt-3 space-y-2.5">
            {UNLOCK_BENEFITS.map((item) => (
              <li key={item} className="flex items-start gap-2.5 text-sm text-slate-200">
                <span className="mt-0.5 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full bg-emerald-500/15 text-emerald-300">
                  <Check className="h-3.5 w-3.5" strokeWidth={2.5} />
                </span>
                {item}
              </li>
            ))}
          </ul>

          <div className="mt-8 space-y-3">
            <Link
              to={signupUrl}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#3b82f6] px-4 py-3.5 text-sm font-bold text-white hover:bg-[#2563eb]"
            >
              <Sparkles className="h-4 w-4" />
              Continue with Email
            </Link>
            <Link
              to={`${signupUrl}&oauth=google`}
              className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/15 bg-white px-4 py-3.5 text-sm font-bold text-[#111827] hover:bg-slate-100"
            >
              Continue with Google
            </Link>
          </div>

          <p className="mt-4 text-center text-xs text-slate-400">
            Free account · Takes less than a minute
          </p>
          <p className="mt-2 text-center text-sm text-slate-400">
            Already have an account?{' '}
            <Link to={signinUrl} className="font-semibold text-blue-300 hover:text-blue-200">
              Sign in
            </Link>
          </p>

          <div className="mt-8 border-t border-white/10 pt-5 text-center text-xs text-slate-500">
            Still browsing?{' '}
            <Link to="/" className="text-slate-300 underline-offset-2 hover:underline">
              Back to Home
            </Link>
            {' · '}
            <Link to="/research" className="text-slate-300 underline-offset-2 hover:underline">
              Read research articles
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
