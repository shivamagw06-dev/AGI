import { useCallback, useEffect, useMemo, useState } from 'react';
import { GraduationCap, Network, RefreshCw, AlertTriangle, ShieldAlert } from 'lucide-react';
import {
  getAcademyAccounting,
  getAcademyCausalModels,
  getAcademyCompletion,
  getAcademyCorporateFinance,
  getAcademyDashboard,
  getAcademyExams,
  getAcademyHealth,
  getAcademyBooksDashboard,
  getAcademyBooksIngestionReport,
  getAcademyBooksQualityGates,
  ingestAcademyBooksLibrary,
  getAcademyProduction,
  getAcademyProductionAb,
  getAcademyProductionQualityGates,
  getAcademyQuality,
  getAcademyRedFlags,
  getSifDashboard,
  getSifQualityGates,
  scoreAcademyEarningsQuality,
  teachAcademyConcept,
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

export default function FinanceAcademy() {
  const [health, setHealth] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [quality, setQuality] = useState(null);
  const [exams, setExams] = useState(null);
  const [completion, setCompletion] = useState(null);
  const [causal, setCausal] = useState(null);
  const [redFlags, setRedFlags] = useState(null);
  const [eq, setEq] = useState(null);
  const [accounting, setAccounting] = useState(null);
  const [acf, setAcf] = useState(null);
  const [production, setProduction] = useState(null);
  const [ab, setAb] = useState(null);
  const [gates, setGates] = useState(null);
  const [sifDash, setSifDash] = useState(null);
  const [sifGates, setSifGates] = useState(null);
  const [booksDash, setBooksDash] = useState(null);
  const [booksGates, setBooksGates] = useState(null);
  const [booksReport, setBooksReport] = useState(null);
  const [courseFilter, setCourseFilter] = useState('all');
  const [conceptId, setConceptId] = useState('capital_allocation');
  const [lesson, setLesson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [h, d, q, e, c, cm, rf, ac, cf, prod, abRes, g, sd, sg, bd, bg, br] = await Promise.all([
        getAcademyHealth(),
        getAcademyDashboard(),
        getAcademyQuality(),
        getAcademyExams(),
        getAcademyCompletion(),
        getAcademyCausalModels(),
        getAcademyRedFlags(),
        getAcademyAccounting(),
        getAcademyCorporateFinance(),
        getAcademyProduction(),
        getAcademyProductionAb(),
        getAcademyProductionQualityGates(),
        getSifDashboard(),
        getSifQualityGates(),
        getAcademyBooksDashboard().catch(() => null),
        getAcademyBooksQualityGates().catch(() => null),
        getAcademyBooksIngestionReport().catch(() => null),
      ]);
      setHealth(h);
      setDashboard(d);
      setQuality(q);
      setExams(e);
      setCompletion(c);
      setCausal(cm);
      setRedFlags(rf);
      setAccounting(ac);
      setAcf(cf);
      setProduction(prod);
      setAb(abRes);
      setGates(g);
      setSifDash(sd);
      setSifGates(sg);
      setBooksDash(bd);
      setBooksGates(bg);
      setBooksReport(br);
    } catch (err) {
      setError(err?.message || 'Failed to load Finance Academy');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const concepts = useMemo(() => {
    const rows = dashboard?.concepts || [];
    if (courseFilter === 'all') return rows;
    return rows.filter((c) => c.course_id === courseFilter || (c.tags || []).includes(`course:${courseFilter}`));
  }, [dashboard, courseFilter]);

  useEffect(() => {
    if (concepts.length && !concepts.find((c) => c.id === conceptId)) {
      setConceptId(concepts[0].id);
    }
  }, [concepts, conceptId]);

  const onTeach = async (e) => {
    e?.preventDefault?.();
    setBusy('teach');
    setError('');
    try {
      const result = await teachAcademyConcept(conceptId.trim() || 'earnings_quality');
      setLesson(result);
    } catch (err) {
      setError(err?.message || 'Teach failed');
    } finally {
      setBusy('');
    }
  };

  const onScoreEq = async () => {
    setBusy('eq');
    setError('');
    try {
      const result = await scoreAcademyEarningsQuality({
        net_income: 100,
        cfo: 70,
        assets: 1000,
        revenue_quality: 0.55,
        exceptionals_pct_ebit: 0.12,
        aggressive_accounting: false,
      });
      setEq(result);
    } catch (err) {
      setError(err?.message || 'EQ score failed');
    } finally {
      setBusy('');
    }
  };

  const examSuite = exams?.suite || completion?.exam_suite || {};
  const courses = health?.courses || dashboard?.courses || [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-[10px] uppercase tracking-[0.2em] text-emerald-600 font-semibold">
            Finance Academy · FAPI v1.0
          </p>
          <h1 className="text-2xl font-bold text-slate-900 mt-1">AGI Finance Academy</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Multi-course institutional curriculum actively wired into production reasoning (CAE → Academy →
            IIE/VE/IRP → Ask AGI). Not a summariser. Not a new engine.
          </p>
        </div>
        <Button variant="outline" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <AlertTriangle className="h-4 w-4 mt-0.5" />
          <span>{error}</span>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Stat label="Courses" value={health?.course_count ?? courses.length ?? '—'} hint="Economics + Accounting + ACF" />
        <Stat label="Concepts" value={health?.concept_count ?? '—'} hint="Canonical objects" />
        <Stat
          label="Quality"
          value={quality?.passed ? 'Pass' : quality ? 'Review' : '—'}
          hint={`${quality?.publishable ?? 0} publishable`}
        />
        <Stat
          label="Exams"
          value={examSuite.complete ? 'Pass' : examSuite.total != null ? `${examSuite.passed}/${examSuite.total}` : '—'}
          hint="Understanding tests"
        />
        <Stat label="Red flags" value={redFlags?.count ?? '—'} hint="Accounting warning library" />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          variant={courseFilter === 'all' ? 'default' : 'outline'}
          size="sm"
          onClick={() => setCourseFilter('all')}
        >
          All courses
        </Button>
        {(courses || []).map((c) => (
          <Button
            key={c.course_id || c.title}
            variant={courseFilter === c.course_id ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCourseFilter(c.course_id)}
          >
            {c.title?.includes('Corporate Finance')
              ? 'Corporate Finance'
              : c.title?.includes('Accounting')
                ? 'Accounting'
                : c.title?.includes('Economics')
                  ? 'Economics'
                  : c.title}
          </Button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-emerald-600" />
            <h2 className="font-semibold text-slate-900">Teach a concept</h2>
          </div>
          <form onSubmit={onTeach} className="flex flex-wrap gap-2">
            <select
              className="border border-slate-200 rounded-lg px-3 py-2 text-sm min-w-[240px]"
              value={conceptId}
              onChange={(ev) => setConceptId(ev.target.value)}
            >
              {concepts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.concept}
                </option>
              ))}
            </select>
            <Button type="submit" disabled={busy === 'teach'}>
              {busy === 'teach' ? 'Teaching…' : 'Teach'}
            </Button>
          </form>
          {lesson ? (
            <div className="text-sm space-y-2 text-slate-700">
              <p>
                <span className="font-medium text-slate-900">What it is: </span>
                {lesson.what_it_is}
              </p>
              {lesson.business_meaning ? (
                <p>
                  <span className="font-medium text-slate-900">Business meaning: </span>
                  {lesson.business_meaning}
                </p>
              ) : null}
              <p>
                <span className="font-medium text-slate-900">Investor lens: </span>
                {(lesson.how_investors_should_think || []).slice(0, 2).join(' · ')}
              </p>
              <p className="text-xs text-slate-400">{lesson.teaching_rule}</p>
            </div>
          ) : null}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-emerald-600" />
            <h2 className="font-semibold text-slate-900">Earnings quality</h2>
          </div>
          <p className="text-sm text-slate-500">
            Investor EQ score methodology from Minimalist Accounting — cash conversion, accruals, revenue
            quality, one-offs, policy stability.
          </p>
          <Button onClick={onScoreEq} disabled={busy === 'eq'}>
            {busy === 'eq' ? 'Scoring…' : 'Run sample EQ score'}
          </Button>
          {eq ? (
            <div className="text-sm text-slate-700 space-y-1">
              <p>
                Score <span className="font-semibold text-slate-900">{eq.score}</span> ({eq.label})
              </p>
              <p className="text-xs text-slate-500">
                MOS guidance: {eq.valuation_guidance?.margin_of_safety} · Multiple:{' '}
                {eq.valuation_guidance?.multiple}
              </p>
            </div>
          ) : null}
          <p className="text-xs text-slate-400">
            Accounting: {accounting?.course?.title || 'Minimalist Accounting'} · ACF:{' '}
            {acf?.course?.title || 'Applied Corporate Finance'} · Core spread: {acf?.core_spread || 'roic_wacc_spread'}
          </p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
        <div className="flex items-center gap-2">
          <Network className="h-5 w-5 text-emerald-600" />
          <h2 className="font-semibold text-slate-900">Causal models</h2>
        </div>
        <ul className="space-y-3 text-sm text-slate-700 max-h-72 overflow-auto">
          {(causal?.models || []).map((m) => (
            <li key={m.model_id} className="border-b border-slate-100 pb-2">
              <p className="font-medium text-slate-900">{m.name}</p>
              <p className="text-xs text-slate-500 mt-1">{(m.chain || []).join(' → ')}</p>
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold text-slate-900">Production usage (FAPI)</h2>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              gates?.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
            }`}
          >
            {gates?.passed ? 'Quality gates pass' : 'Quality gates pending'}
          </span>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Influenced answers"
            value={production?.usage?.influenced_answers ?? '—'}
            hint={`Rate ${production?.usage?.influence_rate ?? '—'}`}
          />
          <Stat
            label="Finance queries"
            value={production?.usage?.finance_queries ?? '—'}
            hint={`${production?.usage?.bypassed ?? 0} bypassed`}
          />
          <Stat
            label="Engines consuming"
            value={Object.keys(production?.engine_consumption || {}).length || '—'}
            hint={Object.keys(production?.engine_consumption || {}).join(', ') || 'none yet'}
          />
          <Stat
            label="A/B improvement"
            value={ab?.material_improvement ? 'Yes' : ab ? 'No' : '—'}
            hint={`Δ WACC ${ab?.deltas?.wacc_delta ?? '—'}`}
          />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <h3 className="text-sm font-medium text-slate-800 mb-2">Most retrieved concepts</h3>
            <ul className="text-sm text-slate-600 space-y-1 max-h-40 overflow-auto">
              {(production?.most_retrieved_concepts || []).slice(0, 12).map((row) => (
                <li key={row.concept_id} className="flex justify-between border-b border-slate-100 py-1">
                  <span>{row.concept_id}</span>
                  <span className="text-slate-400">{row.count}</span>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-medium text-slate-800 mb-2">Unused concepts (sample)</h3>
            <p className="text-xs text-slate-500 mb-2">
              {(production?.unused_concepts || []).slice(0, 16).join(', ') || '—'}
            </p>
            <h3 className="text-sm font-medium text-slate-800 mb-2 mt-4">Recent reasoning traces</h3>
            <ul className="text-xs text-slate-600 space-y-2 max-h-36 overflow-auto">
              {(production?.reasoning_traces || []).slice(0, 6).map((t, idx) => (
                <li key={`${t.ts}-${idx}`} className="border border-slate-100 rounded-lg p-2">
                  <p className="font-medium text-slate-800">
                    {t.engine} · {(t.concept_ids || []).slice(0, 4).join(', ')}
                  </p>
                  <p className="text-slate-500 mt-0.5">{t.query}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
        <div>
          <h3 className="text-sm font-medium text-slate-800 mb-2">Gate checks</h3>
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
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold text-slate-900">Sector Intelligence (SIF)</h2>
          <span
            className={`text-xs font-semibold px-2 py-1 rounded-full ${
              sifGates?.passed ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
            }`}
          >
            {sifGates?.passed ? 'SIF gates pass' : 'SIF gates pending'}
          </span>
        </div>
        <p className="text-sm text-slate-500">
          Additive sector frameworks that teach when/how to apply Finance Academy concepts. Not a new engine.
        </p>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Sectors" value={sifDash?.sector_count ?? '—'} hint="Framework coverage" />
          <Stat
            label="Queries"
            value={sifDash?.usage?.queries ?? '—'}
            hint={`${sifDash?.usage?.blocked_recommendations ?? 0} reco blocked`}
          />
          <Stat
            label="HDFC banking KPIs"
            value={(sifGates?.hdfc_banking_hits || []).length || '—'}
            hint={(sifGates?.hdfc_banking_hits || []).slice(0, 6).join(', ') || '—'}
          />
          <Stat
            label="Sector outranks generic"
            value={sifGates?.checks?.sector_outranks_generic ? 'Yes' : 'No'}
            hint="Banks: NIM/CASA before liquidity"
          />
        </div>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(sifGates?.checks || {}).map(([key, ok]) => (
            <div key={key} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-emerald-600" />
            <div>
              <h2 className="font-semibold text-slate-900">Academy Books V2 — Personal Library</h2>
              <p className="text-xs text-slate-500">
                PDF/EPUB/DOCX/MD + spreadsheets → structured knowledge. Never searchable PDFs. Never verbatim copyrighted text.
              </p>
              <p className="text-[11px] text-slate-400 mt-1">
                Library root: {booksDash?.library_root || '—'} · scanned files:{' '}
                {booksDash?.library_scan?.total_supported ?? '—'}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            disabled={busy === 'ingest-library' || loading}
            onClick={async () => {
              setBusy('ingest-library');
              setError('');
              try {
                const report = await ingestAcademyBooksLibrary({});
                setBooksReport(report);
                await load();
              } catch (err) {
                setError(err?.message || 'Library ingest failed');
              } finally {
                setBusy('');
              }
            }}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${busy === 'ingest-library' ? 'animate-spin' : ''}`} />
            Ingest library
          </Button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-6">
          <Stat label="Ingested books" value={booksDash?.books_successfully_ingested ?? '—'} hint="Non-seed library" />
          <Stat label="Concepts" value={booksDash?.concept_count ?? '—'} hint="AGI-owned objects" />
          <Stat label="Frameworks" value={booksDash?.framework_count ?? '—'} hint="Decision logic" />
          <Stat label="Formulas" value={booksDash?.formula_count ?? '—'} hint="WACC / ROIC / DCF…" />
          <Stat label="Spreadsheets" value={booksDash?.spreadsheet_count ?? '—'} hint="Models / templates" />
          <Stat label="Graph edges" value={booksDash?.graph_edges ?? '—'} hint="Knowledge graph" />
        </div>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(booksGates?.checks || {}).map(([key, ok]) => (
            <div key={key} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 text-xs text-slate-600">
          {Object.entries(booksDash?.flags || {}).map(([k, v]) => (
            <span key={k} className="rounded-full border border-slate-200 px-2 py-1">
              {k}={String(v)}
            </span>
          ))}
        </div>
        <p className="text-xs text-slate-500">
          Companies: {(booksDash?.linked_companies || []).join(', ') || '—'} · Sectors:{' '}
          {(booksDash?.sectors_linked || []).slice(0, 10).join(', ') || '—'}
        </p>
        {booksReport?.reports?.length ? (
          <div className="overflow-x-auto border border-slate-100 rounded-lg">
            <table className="min-w-full text-xs">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="text-left px-3 py-2">Title</th>
                  <th className="text-left px-3 py-2">Quality</th>
                  <th className="text-right px-3 py-2">Pages</th>
                  <th className="text-right px-3 py-2">Concepts</th>
                  <th className="text-right px-3 py-2">Frameworks</th>
                  <th className="text-right px-3 py-2">Formulas</th>
                </tr>
              </thead>
              <tbody>
                {booksReport.reports.slice(0, 20).map((r) => (
                  <tr key={`${r.filename}-${r.book_id || r.title}`} className="border-t border-slate-100">
                    <td className="px-3 py-2 text-slate-800">{r.title || r.filename}</td>
                    <td className="px-3 py-2">{r.extraction_quality || (r.ok ? 'ok' : 'fail')}</td>
                    <td className="px-3 py-2 text-right">{r.pages_processed ?? '—'}</td>
                    <td className="px-3 py-2 text-right">{r.concepts_extracted ?? 0}</td>
                    <td className="px-3 py-2 text-right">{r.frameworks_extracted ?? 0}</td>
                    <td className="px-3 py-2 text-right">{r.formulas_extracted ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="text-[11px] text-slate-400 px-3 py-2">
              Ingest summary: {booksReport.succeeded ?? 0} succeeded / {booksReport.failed ?? 0} failed of{' '}
              {booksReport.attempted ?? 0}
            </p>
          </div>
        ) : null}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-900 mb-3">Completion criteria</h2>
        <div className="grid gap-2 sm:grid-cols-2 text-sm">
          {Object.entries(completion?.criteria || {}).map(([key, ok]) => (
            <div key={key} className="flex items-center justify-between border border-slate-100 rounded-lg px-3 py-2">
              <span className="text-slate-600">{key.replaceAll('_', ' ')}</span>
              <span className={ok ? 'text-emerald-600 font-medium' : 'text-amber-600 font-medium'}>
                {ok ? 'Yes' : 'No'}
              </span>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400 mt-3">
          Architecture v1.0.1 locked · Academy framework pattern preserved · soft consumers only · PDFs
          gitignored
        </p>
      </div>
    </div>
  );
}
