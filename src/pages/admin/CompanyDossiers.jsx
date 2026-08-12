import { useCallback, useEffect, useState } from 'react';
import { Briefcase, AlertTriangle, RefreshCw } from 'lucide-react';
import {
  getCidDashboard,
  getCidHealth,
  getCidQualityGates,
  getCompanyDossier,
  getCompanyDossierCoverage,
  getCompanyDossierTimeline,
  generateCompanyDossier,
  enrichYfp,
} from '@/lib/intelligenceApi';
import { Button } from '@/components/ui/button';

function Stat({ label, value, hint }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="text-3xl font-bold mt-1 text-slate-900">{value}</p>
      {hint ? <p className="text-xs text-slate-400 mt-1">{hint}</p> : null}
    </div>
  );
}

export default function CompanyDossiers() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [gates, setGates] = useState(null);
  const [selected, setSelected] = useState('HDFCBANK');
  const [dossier, setDossier] = useState(null);
  const [coverage, setCoverage] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, g] = await Promise.all([getCidHealth(), getCidDashboard(), getCidQualityGates()]);
      setHealth(h);
      setDashboard(d);
      setGates(g);
    } catch (err) {
      setError(err?.message || 'Failed to load Company Dossiers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const loadTicker = async (ticker) => {
    setSelected(ticker);
    setBusy(ticker);
    setError('');
    try {
      const [d, c, t] = await Promise.all([
        getCompanyDossier(ticker),
        getCompanyDossierCoverage(ticker),
        getCompanyDossierTimeline(ticker, 40),
      ]);
      setDossier(d);
      setCoverage(c);
      setTimeline(t);
    } catch (err) {
      setError(err?.message || 'Failed to load dossier');
    } finally {
      setBusy('');
    }
  };

  const onEnrichFinancials = async () => {
    setBusy('enrich');
    setError('');
    try {
      await enrichYfp(selected || 'HDFCBANK');
      await loadTicker(selected || 'HDFCBANK');
      await load();
    } catch (err) {
      setError(err?.message || 'Financial enrichment failed');
    } finally {
      setBusy('');
    }
  };

  const onGenerateDossier = async () => {
    const ticker = selected || 'HDFCBANK';
    setBusy('generate');
    setError('');
    try {
      const result = await generateCompanyDossier(ticker, true);
      setDossier(result?.dossier || null);
      await loadTicker(ticker);
      await load();
    } catch (err) {
      setError(err?.message || 'OpenAI dossier generation failed');
    } finally {
      setBusy('');
    }
  };

  const pct = (v) =>
    v == null || Number.isNaN(Number(v)) ? '—' : `${Math.round(Number(v) <= 1 ? Number(v) * 100 : Number(v))}%`;

  const revenueTrend = (dossier?.historical_kpi_trends?.revenue || dossier?.financial_history?.kpi_trends?.revenue || []).slice(0, 6);
  const valuationHist = (dossier?.valuation?.historical || []).slice(-8).reverse();
  const finCov = dossier?.financial_coverage || {};
  const missingFin = [
    ...(finCov?.financial?.missing_financial_fields || []),
    ...(finCov?.valuation?.missing_valuation_fields || []),
    ...((dossier?.financial_statements?.coverage || {}).missing_financial_fields || []),
  ];

  const rows = dashboard?.dossiers || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-indigo-600 font-semibold">
            CID v1.0 · Company Intelligence Dossier
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1 flex items-center gap-2">
            <Briefcase className="h-6 w-6 text-indigo-600" />
            Company Dossiers
          </h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Permanent institutional memory for every tracked company. LEO updates dossiers from verified
            evidence; Ask AGI reasons from the dossier first — never rebuilds from raw APIs.
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={onGenerateDossier} disabled={!!busy || loading || !selected}>
            {busy === 'generate' ? 'Generating…' : 'Generate full dossier'}
          </Button>
          <Button variant="outline" onClick={onEnrichFinancials} disabled={!!busy || loading}>
            {busy === 'enrich' ? 'Enriching…' : 'Enrich Financials'}
          </Button>
          <Button variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Status" value={health?.status ?? '—'} hint={health?.version || 'cid'} />
        <Stat label="Dossiers" value={dashboard?.dossier_count ?? '—'} hint="Living company objects" />
        <Stat
          label="Quality gates"
          value={gates?.passed ? 'Pass' : gates ? 'Review' : '—'}
          hint="Tracked universe"
        />
        <Stat
          label="Institutional"
          value={dashboard?.grade_distribution?.['Institutional Grade'] ?? 0}
          hint="≥90% coverage"
        />
        <Stat
          label="Research / Partial"
          value={
            (dashboard?.grade_distribution?.['Research Grade'] || 0) +
            (dashboard?.grade_distribution?.Partial || 0)
          }
          hint="70–89% / 50–69%"
        />
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-slate-900">Tracked dossiers</h2>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              gates?.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
            }`}
          >
            {gates?.passed ? 'Gates pass' : 'Gates pending'}
          </span>
        </div>
        <div className="overflow-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-slate-500 border-b">
                <th className="py-2">Ticker</th>
                <th>Company</th>
                <th>Sector</th>
                <th>Coverage</th>
                <th>Grade</th>
                <th>Latest filing</th>
                <th>Updated</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.ticker} className="border-b border-slate-50">
                  <td className="py-2 font-medium">{row.ticker}</td>
                  <td>{row.company_name}</td>
                  <td className="text-slate-500">{row.sector_id || row.sector || '—'}</td>
                  <td>{row.coverage_score != null ? `${Math.round(row.coverage_score * 100)}%` : '—'}</td>
                  <td>{row.coverage_grade || '—'}</td>
                  <td className="text-slate-500 max-w-[180px] truncate">
                    {row.latest_filing?.title || row.latest_announcement?.title || '—'}
                  </td>
                  <td className="text-slate-400 text-xs">{row.updated_at ? String(row.updated_at).slice(0, 19) : '—'}</td>
                  <td>
                    <Button size="sm" variant="outline" onClick={() => loadTicker(row.ticker)} disabled={!!busy}>
                      {busy === row.ticker ? '…' : 'Open'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(gates?.checks || {}).map(([key, ok]) => (
            <div key={key} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
      </div>

      {dossier ? (
        <div className="grid gap-6 lg:grid-cols-2">
          {dossier.openai_research ? (
            <section className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-5 space-y-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-[10px] uppercase tracking-[0.2em] text-indigo-600 font-semibold">OpenAI grounded synthesis</p>
                  <h2 className="font-semibold text-slate-900 mt-1">Institutional research dossier</h2>
                </div>
                <p className="text-xs text-slate-400">
                  {dossier.openai_research.model} · {String(dossier.openai_research.generated_at || '').slice(0, 19)}
                </p>
              </div>
              <p className="text-sm text-slate-700 leading-6">{dossier.openai_research.executive_summary}</p>
              <div className="grid gap-3 md:grid-cols-2">
                {Object.entries(dossier.openai_research.sections || {}).map(([name, section]) => (
                  <div key={name} className="border border-slate-100 rounded-lg p-3">
                    <h3 className="text-sm font-semibold text-slate-900 capitalize">{name.replaceAll('_', ' ')}</h3>
                    <p className="text-sm text-slate-600 mt-1">{section.summary || 'Evidence gap.'}</p>
                    <p className="text-xs text-slate-400 mt-2">
                      Evidence: {(section.evidence_ids || []).join(', ') || 'none'} · Confidence {Math.round(Number(section.confidence || 0) * 100)}%
                    </p>
                  </div>
                ))}
              </div>
            </section>
          ) : null}
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
            <h2 className="font-semibold text-slate-900">
              {selected} · {dossier.identity?.company_name || selected}
            </h2>
            <p className="text-sm text-slate-600">{dossier.reasoning_hint || 'Living institutional dossier.'}</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <Stat
                label="Coverage"
                value={coverage?.coverage_score != null ? `${Math.round(coverage.coverage_score * 100)}%` : '—'}
                hint={coverage?.coverage_grade}
              />
              <Stat
                label="Sector KPIs"
                value={(dossier.sector_kpis?.priority_metrics || []).length || '—'}
                hint={(dossier.sector_kpis?.priority_metrics || []).slice(0, 4).join(', ') || '—'}
              />
            </div>
            {(dossier.data_quality_panel || dossier.dvc?.panel) && (
              <div className="rounded-lg border border-emerald-100 bg-emerald-50/40 p-3 space-y-2">
                <h3 className="text-sm font-semibold text-emerald-900">Data Quality Panel (DVC)</h3>
                {(() => {
                  const panel = dossier.data_quality_panel || dossier.dvc?.panel || {};
                  const pct = (v) =>
                    v == null ? '—' : `${Math.round(Number(v) <= 1 ? Number(v) * 100 : Number(v))}%`;
                  return (
                    <div className="grid gap-2 sm:grid-cols-3 text-xs text-slate-700">
                      <div>Research Grade: <strong>{panel.research_grade || '—'}</strong></div>
                      <div>Knowledge Grade: <strong>{panel.knowledge_grade || '—'}</strong></div>
                      <div>Data Grade: <strong>{panel.data_grade || '—'}</strong></div>
                      <div>Coverage: {pct(panel.coverage)}</div>
                      <div>Freshness: {pct(panel.freshness)}</div>
                      <div>Confidence: {pct(panel.confidence)}</div>
                      <div className="sm:col-span-3">
                        Providers: {(panel.provider_sources || []).join(', ') || '—'}
                      </div>
                      <div className="sm:col-span-3">
                        Missing: {(panel.missing_information || []).slice(0, 8).join(', ') || 'None'}
                      </div>
                      <div className="sm:col-span-3">
                        Recommended refresh: {panel.recommended_refresh || '—'}
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
            <div>
              <h3 className="text-sm font-medium text-slate-800 mb-1">Missing evidence</h3>
              <p className="text-sm text-slate-600">
                {(dossier.missing_evidence || coverage?.missing_evidence || []).join(', ') || 'None'}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-800 mb-1">Academy concepts</h3>
              <p className="text-sm text-slate-600">
                {(dossier.finance_academy?.active_concepts || []).slice(0, 10).join(', ') || '—'}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-800 mb-1">Latest</h3>
              <ul className="text-sm text-slate-600 space-y-1">
                <li>Announcement: {dossier.latest_announcement?.title || '—'}</li>
                <li>Filing: {dossier.latest_filing?.title || '—'}</li>
                <li>Presentation: {dossier.latest_presentation?.title || '—'}</li>
              </ul>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
            <h2 className="font-semibold text-slate-900">Evidence timeline</h2>
            <ul className="text-xs text-slate-600 space-y-2 max-h-96 overflow-auto">
              {(timeline?.events || []).map((e, idx) => (
                <li key={`${e.evidence_id}-${idx}`} className="border border-slate-100 rounded-lg p-2">
                  <p className="font-medium text-slate-800">
                    {e.evidence_type} · {e.source_id}
                  </p>
                  <p className="text-slate-500 mt-0.5">{e.title}</p>
                  <p className="text-slate-400 mt-0.5">{e.at ? String(e.at).slice(0, 19) : ''}</p>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3 lg:col-span-2">
            <h2 className="font-semibold text-slate-900">Financial History</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Stat
                label="Financial coverage"
                value={pct(finCov?.financial?.coverage || dossier?.financial_statements?.coverage?.coverage)}
                hint="Statement / field coverage"
              />
              <Stat
                label="Valuation coverage"
                value={pct(finCov?.valuation?.coverage || dossier?.valuation?.coverage?.coverage)}
                hint="Multiples present"
              />
              <Stat
                label="Freshness"
                value={pct(finCov?.financial?.freshness ?? finCov?.valuation?.freshness)}
              />
              <Stat
                label="Confidence"
                value={pct(finCov?.financial?.confidence ?? finCov?.valuation?.confidence)}
              />
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-800 mb-1">Missing financial fields</h3>
              <p className="text-sm text-slate-600">
                {[...new Set(missingFin)].slice(0, 16).join(', ') || 'None listed'}
              </p>
            </div>
            <div className="grid gap-4 lg:grid-cols-2">
              <div>
                <h3 className="text-sm font-medium text-slate-800 mb-2">Revenue history (chart)</h3>
                {revenueTrend.length === 0 ? (
                  <p className="text-sm text-slate-400">No revenue series yet — run Enrich Financials.</p>
                ) : (
                  <div className="flex items-end gap-2 h-28">
                    {revenueTrend
                      .slice()
                      .reverse()
                      .map((p, idx) => {
                        const vals = revenueTrend.map((x) => Number(x.value) || 0);
                        const max = Math.max(...vals, 1);
                        const h = Math.max(8, Math.round((Number(p.value) / max) * 100));
                        return (
                          <div key={`${p.period_end}-${idx}`} className="flex-1 flex flex-col items-center gap-1">
                            <div
                              className="w-full rounded-t bg-indigo-500/80"
                              style={{ height: `${h}%` }}
                              title={`${p.period_end}: ${p.value}`}
                            />
                            <span className="text-[10px] text-slate-400 truncate w-full text-center">
                              {String(p.period_end || '').slice(0, 4)}
                            </span>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
              <div>
                <h3 className="text-sm font-medium text-slate-800 mb-2">Valuation history</h3>
                <ul className="text-xs text-slate-600 space-y-1 max-h-36 overflow-auto">
                  {valuationHist.length === 0 ? (
                    <li className="text-slate-400">No valuation timeline yet.</li>
                  ) : (
                    valuationHist.map((v, idx) => (
                      <li key={`${v.at}-${idx}`} className="border border-slate-100 rounded-lg px-2 py-1 flex justify-between gap-2">
                        <span>
                          PE {v.valuation?.trailing_pe ?? '—'} · EV/EBITDA {v.valuation?.ev_ebitda ?? '—'} · PB{' '}
                          {v.valuation?.price_to_book ?? '—'}
                        </span>
                        <span className="text-slate-400">{v.at ? String(v.at).slice(0, 10) : ''}</span>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-medium text-slate-800 mb-1">Statement versions</h3>
              <p className="text-xs text-slate-500">
                {((dossier.financial_statements?.versions || []).slice(-6) || [])
                  .map((v) => `${v.statement}/${v.period} (${v.row_count || 'n'} rows)`)
                  .join(' · ') || '—'}
              </p>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
