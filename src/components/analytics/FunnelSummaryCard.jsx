import { useMemo } from 'react';
import { getFunnelSummary } from '@/lib/funnelAnalytics';

/** Same-browser funnel snapshot for CMS operators (debug / early signal). */
export default function FunnelSummaryCard() {
  const summary = useMemo(() => getFunnelSummary(), []);
  const c = summary.counts || {};
  const r = summary.rates || {};

  const rows = [
    ['Sessions', c.visitor_session || 0],
    ['Home views', c.public_home || 0],
    ['Article views', c.public_article || 0],
    ['Gated clicks', c.gated_feature_clicked || 0],
    ['Unlock screen', c.unlock_screen || 0],
    ['Signup started', c.signup_started || 0],
    ['Signup completed', c.signup_completed || 0],
    ['Activated', c.first_meaningful_action || 0],
    ['7-day return', c.day7_return || 0],
  ];

  return (
    <section className="mb-8 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wide text-slate-500">Registration funnel</h2>
          <p className="mt-1 text-sm text-slate-600">
            Same-browser early signal. Site-wide totals need GA (`VITE_GA_MEASUREMENT_ID`).
          </p>
        </div>
        <div className="flex gap-3 text-xs text-slate-500">
          <span>Unlock→start {r.unlock_to_signup_start_pct ?? '—'}%</span>
          <span>Start→done {r.signup_start_to_complete_pct ?? '—'}%</span>
          <span>Signup→activate {r.signup_to_activation_pct ?? '—'}%</span>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-9">
        {rows.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-2">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-1 text-lg font-semibold tabular-nums text-slate-900">{value}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
