import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  RefreshCw,
  Upload,
  Search,
  Download,
  Play,
  Eye,
  X,
  AlertTriangle,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';
import Forbidden403 from '@/components/admin/Forbidden403';
import {
  getKocOverview,
  getKocCompany,
  uploadKocKnowledge,
  uploadCompanySheet,
  runKocAction,
  getKocAudit,
  searchKoc,
  getKocEvidence,
  runKocCgl,
  runKocKil,
  runKocCoverage,
  runKocRepair,
} from '@/lib/intelligenceApi';
import './knowledgeOps.css';

const DOC_TYPES = [
  { value: 'annual_report', label: 'Annual Report' },
  { value: 'quarterly_results', label: 'Quarterly Results' },
  { value: 'investor_presentation', label: 'Investor Presentation' },
  { value: 'transcript', label: 'Transcript' },
  { value: 'shareholding', label: 'Shareholding Pattern' },
  { value: 'corporate_action', label: 'Corporate Actions' },
  { value: 'management_guidance', label: 'Management Guidance' },
  { value: 'credit_rating', label: 'Credit Rating' },
  { value: 'investor_day', label: 'Investor Day' },
  { value: 'segment_data', label: 'Segment Information' },
  { value: 'other', label: 'Other' },
];

function fmt(v) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') return Number.isInteger(v) ? String(v) : v.toFixed(1);
  return String(v);
}

function PriorityBadge({ priority }) {
  return <span className={`koc-badge ${String(priority || 'medium').toLowerCase()}`}>{priority || 'Medium'}</span>;
}

function StatusDot({ ok, warn, info }) {
  const cls = ok ? 'ok' : warn ? 'warn' : info ? 'info' : 'bad';
  return <span className={`koc-dot ${cls}`} />;
}

function Kpi({ label, value }) {
  return (
    <div className="koc-kpi">
      <div className="label">{label}</div>
      <div className="value">{fmt(value)}</div>
    </div>
  );
}

function HealthCell({ label, value, tone }) {
  const color =
    tone === 'ok' ? 'var(--koc-green)' : tone === 'warn' ? 'var(--koc-orange)' : tone === 'bad' ? 'var(--koc-red)' : tone === 'info' ? 'var(--koc-blue)' : undefined;
  return (
    <div className="koc-health-cell">
      <div className="label">{label}</div>
      <div className="value" style={color ? { color } : undefined}>
        {fmt(value)}
      </div>
    </div>
  );
}

function toneForStatus(s) {
  const v = String(s || '').toLowerCase();
  if (['running', 'ready', 'healthy', 'enabled', 'ok'].some((x) => v.includes(x))) return 'ok';
  if (['warn', 'degraded', 'warning'].some((x) => v.includes(x))) return 'warn';
  if (['stop', 'off', 'fail', 'error', 'missing'].some((x) => v.includes(x))) return 'bad';
  return 'info';
}

function UploadModal({ open, ticker, documentType, company, actor, onClose, onDone }) {
  const [dtype, setDtype] = useState(documentType || 'investor_presentation');
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (open) {
      setDtype(documentType || 'investor_presentation');
      setFile(null);
      setError('');
      setResult(null);
    }
  }, [open, documentType]);

  if (!open) return null;

  const submit = async () => {
    if (!file || !ticker) {
      setError('Choose a company and a file.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const buf = await file.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let binary = '';
      bytes.forEach((b) => {
        binary += String.fromCharCode(b);
      });
      const res = await uploadKocKnowledge({
        ticker,
        document_type: dtype,
        filename: file.name,
        content_base64: btoa(binary),
        mime_type: file.type || undefined,
        actor: actor || 'admin',
      });
      setResult(res);
      onDone?.(res);
    } catch (err) {
      setError(err?.message || 'Upload failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="koc-modal-backdrop" role="dialog" aria-modal="true">
      <div className="koc-modal">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="koc-kicker">Manual Knowledge Upload</p>
            <h2 className="mt-1 text-lg font-semibold">{company || ticker}</h2>
            <p className="mt-1 text-xs text-[var(--koc-muted)]">
              Upload → scan → checksum → OCR → extract → evidence → memory → graph → readiness → snapshot.
              Append-only. Never overwrites.
            </p>
          </div>
          <button type="button" className="koc-btn" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-4 space-y-3">
          <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--koc-caption)]">
            Document type
            <select className="koc-select mt-1 w-full" value={dtype} onChange={(e) => setDtype(e.target.value)}>
              {DOC_TYPES.map((d) => (
                <option key={d.value} value={d.value}>{d.label}</option>
              ))}
            </select>
          </label>
          <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--koc-caption)]">
            File (PDF / PPT / DOCX / XLSX / ZIP)
            <input
              type="file"
              className="mt-1 block w-full text-sm"
              accept=".pdf,.ppt,.pptx,.doc,.docx,.xls,.xlsx,.zip"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
          </label>
          {error ? (
            <p className="flex items-center gap-2 text-sm text-[var(--koc-red)]">
              <AlertTriangle className="h-4 w-4" /> {error}
            </p>
          ) : null}
          {result?.ok ? (
            <div className="border border-[var(--koc-line)] bg-[var(--koc-green-bg)] p-3 text-xs">
              Uploaded · hash {(result.upload?.sha256 || '').slice(0, 16)}… · evidence{' '}
              {(result.upload?.evidence_ids || []).join(', ') || '—'}
            </div>
          ) : null}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="koc-btn" onClick={onClose}>Cancel</button>
            <button type="button" className="koc-btn primary" disabled={busy} onClick={submit}>
              <Upload className="h-3.5 w-3.5" />
              {busy ? 'Processing…' : 'Upload & process'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function SheetUploadModal({ open, actor, onClose, onDone }) {
  const [file, setFile] = useState(null);
  const [dryRun, setDryRun] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState(null);

  useEffect(() => {
    if (open) {
      setFile(null);
      setDryRun(true);
      setError('');
      setResult(null);
    }
  }, [open]);

  if (!open) return null;

  const submit = async () => {
    if (!file) {
      setError('Choose an Excel (.xlsx) or CSV file.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const buf = await file.arrayBuffer();
      const bytes = new Uint8Array(buf);
      let binary = '';
      bytes.forEach((b) => {
        binary += String.fromCharCode(b);
      });
      const res = await uploadCompanySheet({
        filename: file.name,
        content_base64: btoa(binary),
        dry_run: dryRun,
        actor: actor || 'admin',
      });
      setResult(res);
      if (!dryRun) onDone?.(res);
    } catch (err) {
      setError(err?.message || 'Upload failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="koc-modal-backdrop" role="dialog" aria-modal="true">
      <div className="koc-modal">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="koc-kicker">Bulk Company Info Sheet</p>
            <h2 className="mt-1 text-lg font-semibold">Upload Excel / CSV</h2>
            <p className="mt-1 text-xs text-[var(--koc-muted)]">
              One row per company. Recognized columns (Ticker/Company Name, Sector, Industry, CEO,
              CFO, PE, PB, Market Cap, ISIN, Website, …) are written as versioned facts. Rows that
              can&apos;t be matched to a real ticker are reported, never guessed.
            </p>
          </div>
          <button type="button" className="koc-btn" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-4 space-y-3">
          <label className="block text-xs font-semibold uppercase tracking-wide text-[var(--koc-caption)]">
            File (.xlsx / .xls / .csv)
            <input
              type="file"
              className="mt-1 block w-full text-sm"
              accept=".xlsx,.xls,.csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setResult(null);
              }}
            />
          </label>
          <label className="flex items-center gap-2 text-xs text-[var(--koc-muted)]">
            <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
            Preview only (dry run) — don&apos;t write facts yet
          </label>
          {error ? (
            <p className="flex items-center gap-2 text-sm text-[var(--koc-red)]">
              <AlertTriangle className="h-4 w-4" /> {error}
            </p>
          ) : null}
          {result ? (
            result.ok ? (
              <div className="border border-[var(--koc-line)] bg-[var(--koc-green-bg)] p-3 text-xs space-y-1">
                <div>
                  {result.dry_run ? 'Preview: ' : 'Written: '}
                  {result.resolved_count}/{result.total_rows} rows resolved ·{' '}
                  {result.fields_written_total} field values → tables{' '}
                  {(result.tables_touched || []).join(', ') || '—'}
                </div>
                {result.unresolved_count > 0 ? (
                  <div className="text-[var(--koc-orange)]">
                    {result.unresolved_count} row(s) unresolved (no matching ticker/company name) —
                    not written.
                  </div>
                ) : null}
                {(result.unmapped_columns || []).length > 0 ? (
                  <div className="text-[var(--koc-muted)]">
                    Ignored columns: {result.unmapped_columns.join(', ')}
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="flex items-center gap-2 text-sm text-[var(--koc-red)]">
                <AlertTriangle className="h-4 w-4" /> {result.error || 'Upload failed'}
                {result.hint ? ` — ${result.hint}` : ''}
              </p>
            )
          ) : null}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" className="koc-btn" onClick={onClose}>Cancel</button>
            <button type="button" className="koc-btn primary" disabled={busy} onClick={submit}>
              <Upload className="h-3.5 w-3.5" />
              {busy ? 'Processing…' : dryRun ? 'Preview' : 'Upload & write facts'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function KnowledgeOperations() {
  const { user } = useAuth();
  const [desk, setDesk] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [globalQ, setGlobalQ] = useState('');
  const [searchHits, setSearchHits] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [actionBusy, setActionBusy] = useState('');
  const [audit, setAudit] = useState(null);
  const [uploadState, setUploadState] = useState({
    open: false,
    ticker: '',
    company: '',
    documentType: 'investor_presentation',
  });
  const [sheetUploadOpen, setSheetUploadOpen] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [d, a] = await Promise.all([
        getKocOverview({ scope: 'TOP20' }),
        getKocAudit({ limit: 25 }).catch(() => null),
      ]);
      setDesk(d);
      setAudit(a);
      if (d?.degraded || d?.engine_error) {
        setError(
          d.engine_error ||
            d.error ||
            'Intelligence engine is offline. Knowledge Operations Center opened in degraded mode — Retry after Render restarts agib-intelligence-engine.'
        );
      }
    } catch (err) {
      setError(err?.message || 'Failed to load Knowledge Operations Center');
      // Keep a minimal desk so the page shell stays usable (upload / retry).
      setDesk((prev) =>
        prev || {
          ok: true,
          degraded: true,
          kpis: {},
          system_health: { bar: { koc: { status: 'Degraded' } } },
          missing_inbox: { title: 'Missing Knowledge Inbox', count: 0, items: [], by_priority: {} },
          coverage_table: [],
          gap_ai: { items: [] },
          ingestion_timeline: [],
          knowledge_queue: { boards: [] },
          collector_health: [],
          coverage_heatmap: {},
          knowledge_versions: [],
        }
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAdmin(user)) load();
  }, [user, load]);

  const openCompany = async (ticker) => {
    setSelected(ticker);
    try {
      setDetail(await getKocCompany(ticker));
    } catch (err) {
      setDetail({ error: err?.message });
    }
  };

  const openUpload = (row, missingClass) => {
    const map = {
      annual_reports: 'annual_report',
      quarterly_results: 'quarterly_results',
      financial_statements: 'quarterly_results',
      earnings_presentations: 'investor_presentation',
      earnings_call_transcripts: 'transcript',
      shareholding: 'shareholding',
      corporate_actions: 'corporate_action',
      management_guidance: 'management_guidance',
      segment_kpis: 'segment_data',
      credit_rating: 'credit_rating',
      investor_day: 'investor_day',
    };
    setUploadState({
      open: true,
      ticker: row.ticker || row,
      company: row.company || row.ticker || row,
      documentType: map[missingClass] || 'other',
    });
  };

  const runAction = async (action, ticker) => {
    setActionBusy(action);
    try {
      if (action === 'run_cgl') await runKocCgl({ actor: user?.email });
      else if (action === 'run_kil') await runKocKil({ ticker, actor: user?.email });
      else if (action === 'run_full_coverage') await runKocCoverage({ actor: user?.email });
      else if (action === 'run_auto_repair') await runKocRepair({ ticker, actor: user?.email });
      else await runKocAction({ action, ticker, actor: user?.email || 'admin' });
      await load();
      if (ticker) await openCompany(ticker);
    } catch (err) {
      setError(err?.message || 'Action failed');
    } finally {
      setActionBusy('');
    }
  };

  const onGlobalSearch = async (e) => {
    e?.preventDefault?.();
    if (!globalQ.trim()) {
      setSearchHits(null);
      return;
    }
    try {
      setSearchHits(await searchKoc({ q: globalQ.trim(), limit: 20 }));
    } catch (err) {
      setError(err?.message || 'Search failed');
    }
  };

  const loadEvidence = async () => {
    try {
      setEvidence(await getKocEvidence({ limit: 40, ticker: selected || undefined }));
    } catch (err) {
      setError(err?.message || 'Evidence load failed');
    }
  };

  const kpis = desk?.kpis || {};
  const bar = desk?.system_health?.bar || {};
  const inbox = desk?.missing_inbox || {};
  const gapAi = desk?.gap_ai || {};
  const table = desk?.coverage_table || [];
  const timeline = desk?.ingestion_timeline || [];
  const queue = desk?.knowledge_queue || {};
  const collectors = desk?.collector_health || [];
  const heatmap = desk?.coverage_heatmap || {};
  const versions = desk?.knowledge_versions || [];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return table;
    return table.filter(
      (r) =>
        String(r.ticker || '').toLowerCase().includes(q) ||
        String(r.company || '').toLowerCase().includes(q) ||
        (r.missing_items || []).join(' ').toLowerCase().includes(q)
    );
  }, [table, query]);

  const exportCsv = () => {
    const header = ['ticker', 'company', 'coverage_pct', 'knowledge_confidence', 'research_readiness', 'claim_safe', 'coverage_state', 'missing'];
    const lines = [header.join(',')];
    filtered.forEach((r) => {
      lines.push(
        [
          r.ticker,
          JSON.stringify(r.company || ''),
          r.coverage_pct,
          r.knowledge_confidence,
          r.research_readiness,
          r.claim_safe,
          JSON.stringify(r.coverage_state || ''),
          JSON.stringify((r.missing_items || []).join('; ')),
        ].join(',')
      );
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'koc-coverage.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isAdmin(user)) {
    return <Forbidden403 resource="Knowledge Operations" />;
  }

  return (
    <div className="koc-root">
      <div className="koc-shell space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="koc-kicker">Admin only · AGI V1.2 · Institutional Knowledge OS</p>
            <h1 className="koc-title mt-2">Knowledge Operations Center</h1>
            <p className="mt-2 max-w-3xl text-sm text-[var(--koc-muted)]">
              Monitor, Validate, Learn and Improve Institutional Knowledge across the AGI Universe.
            </p>
            <form onSubmit={onGlobalSearch} className="mt-4 flex max-w-xl flex-wrap gap-2">
              <div className="relative min-w-[220px] flex-1">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--koc-caption)]" />
                <input
                  className="koc-input w-full pl-8"
                  placeholder="Search companies, evidence, documents, versions, packs"
                  value={globalQ}
                  onChange={(e) => setGlobalQ(e.target.value)}
                />
              </div>
              <button type="submit" className="koc-btn primary">Search</button>
            </form>
            {searchHits?.results ? (
              <div className="koc-search-results mt-2 p-3 text-xs">
                <div className="font-semibold">Companies · {(searchHits.results.companies || []).length}</div>
                {(searchHits.results.companies || []).slice(0, 6).map((c) => (
                  <button
                    key={c.ticker}
                    type="button"
                    className="mt-1 block text-left hover:underline"
                    onClick={() => openCompany(c.ticker)}
                  >
                    {c.ticker} — {c.company}
                  </button>
                ))}
                <div className="mt-2 font-semibold">Evidence · {(searchHits.results.evidence || []).length}</div>
                {(searchHits.results.evidence || []).slice(0, 4).map((e) => (
                  <div key={e.document_id} className="mt-1 text-[var(--koc-muted)]">
                    {e.ticker} · {e.document_type} · {e.source}
                  </div>
                ))}
              </div>
            ) : null}
            <p className="mt-2 text-[11px] text-[var(--koc-caption)]">
              {desk?.generated_at || '—'} · {desk?.version || 'koc-01-v1.2.0'} · Evidence immutable
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to="/" className="koc-btn"><ArrowLeft className="h-3.5 w-3.5" /> Home</Link>
            <button type="button" className="koc-btn" onClick={() => setSheetUploadOpen(true)}>
              <Upload className="h-3.5 w-3.5" /> Upload Company Sheet
            </button>
            <button type="button" className="koc-btn" onClick={exportCsv}>
              <Download className="h-3.5 w-3.5" /> Export
            </button>
            <button type="button" className="koc-btn primary" onClick={load} disabled={loading}>
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </header>

        {error || desk?.degraded ? (
          <div className="koc-panel flex flex-wrap items-start justify-between gap-3 border-[var(--koc-orange)] bg-[var(--koc-orange-bg)] p-3 text-sm text-[var(--koc-orange)]">
            <div className="flex min-w-0 items-start gap-2">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <div className="font-semibold">
                  {desk?.degraded ? 'Engine offline — degraded mode' : 'Load issue'}
                </div>
                <p className="mt-1 text-[var(--koc-muted)]">
                  {error ||
                    'agib-intelligence-engine is not responding. The page is open; coverage data will fill when the engine recovers.'}
                </p>
              </div>
            </div>
            <button type="button" className="koc-btn primary shrink-0" onClick={load} disabled={loading}>
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
              Retry
            </button>
          </div>
        ) : null}

        {/* System Health Bar */}
        <section>
          <p className="koc-kicker mb-2">System Health</p>
          <div className="koc-health-bar">
            <HealthCell label="CGL" value={bar.cgl?.status || kpis.cgl_status} tone={toneForStatus(bar.cgl?.status || kpis.cgl_status)} />
            <HealthCell label="KIL" value={bar.kil?.status || kpis.kil_status} tone={toneForStatus(bar.kil?.status || kpis.kil_status)} />
            <HealthCell label="ICF" value={bar.icf?.status || kpis.icf_status} tone={toneForStatus(bar.icf?.status || kpis.icf_status)} />
            <HealthCell label="Scheduler" value={bar.scheduler?.status || kpis.scheduler_status} tone={toneForStatus(bar.scheduler?.status)} />
            <HealthCell label="Collector Health" value={bar.collector_health_pct != null ? `${bar.collector_health_pct}%` : kpis.collector_success_pct} tone={bar.collector_health_pct >= 90 ? 'ok' : 'warn'} />
            <HealthCell label="Knowledge Latency" value={bar.knowledge_latency_minutes != null ? `${bar.knowledge_latency_minutes} min` : kpis.knowledge_latency} tone="info" />
            <HealthCell label="Repair Queue" value={bar.repair_queue ?? kpis.repair_queue} tone={(bar.repair_queue || 0) > 50 ? 'warn' : 'info'} />
            <HealthCell label="Auto Repair" value={bar.auto_repair || 'Enabled'} tone="ok" />
            <HealthCell label="KOC" value={bar.koc?.status || kpis.koc_status} tone={toneForStatus(bar.koc?.status || kpis.koc_status)} />
          </div>
        </section>

        {/* KPI Dashboard */}
        <section className="grid gap-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
          <Kpi label="Companies Covered" value={kpis.companies_covered} />
          <Kpi label="ICC Complete" value={kpis.institutional_coverage_complete} />
          <Kpi label="Knowledge Ready" value={kpis.knowledge_ready} />
          <Kpi label="Research Ready" value={kpis.research_ready} />
          <Kpi label="Claim Safe" value={kpis.claim_safe} />
          <Kpi label="Knowledge Confidence" value={kpis.knowledge_confidence} />
          <Kpi label="Evidence Objects" value={kpis.evidence_objects} />
          <Kpi label="Docs Collected Today" value={kpis.documents_collected_today} />
          <Kpi label="Docs Processed Today" value={kpis.documents_processed_today} />
          <Kpi label="Claims Extracted Today" value={kpis.claims_extracted_today ?? kpis.claims_created_today} />
          <Kpi label="Knowledge Snapshots" value={kpis.knowledge_snapshots} />
          <Kpi label="Memory Updates" value={kpis.company_memory_updates} />
          <Kpi label="KG Updates" value={kpis.knowledge_graph_updates} />
          <Kpi label="Research Refreshes" value={kpis.research_refreshes} />
          <Kpi label="Research Invalidations" value={kpis.research_invalidations ?? kpis.research_invalidated_today} />
          <Kpi label="Collector Success %" value={kpis.collector_success_pct} />
          <Kpi label="CGL Status" value={kpis.cgl_status} />
          <Kpi label="KIL Status" value={kpis.kil_status} />
          <Kpi label="ICF Status" value={kpis.icf_status} />
          <Kpi label="KOC Status" value={kpis.koc_status} />
        </section>

        {/* Section 4 — Missing Knowledge Inbox (highest priority) */}
        <section className="koc-panel p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="koc-kicker">Section 4 · Highest priority</p>
              <h2 className="mt-1 text-lg font-semibold">{inbox.title || 'Missing Knowledge Inbox'}</h2>
              <p className="mt-1 text-xs text-[var(--koc-muted)]">
                {inbox.workflow} · {fmt(inbox.count)} items · Critical {fmt(inbox.by_priority?.Critical)} · High{' '}
                {fmt(inbox.by_priority?.High)}
              </p>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="koc-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Missing</th>
                  <th>Priority</th>
                  <th>ICC Gain</th>
                  <th>Research Δ</th>
                  <th>Confidence Δ</th>
                  <th>Claims</th>
                  <th>ETA</th>
                  <th>Upload</th>
                </tr>
              </thead>
              <tbody>
                {(inbox.items || []).slice(0, 30).map((item) => (
                  <tr key={`${item.ticker}-${item.missing_class}`}>
                    <td>
                      <button type="button" className="font-semibold hover:underline" onClick={() => openCompany(item.ticker)}>
                        {item.company || item.ticker}
                      </button>
                      <div className="koc-mono text-[11px] text-[var(--koc-caption)]">{item.ticker}</div>
                    </td>
                    <td>{item.missing}</td>
                    <td><PriorityBadge priority={item.priority} /></td>
                    <td className="koc-mono">+{fmt(item.estimated_icc_gain_pct)}%</td>
                    <td className="koc-mono">+{fmt(item.estimated_research_improvement)}</td>
                    <td className="koc-mono">+{fmt(item.estimated_knowledge_confidence_improvement)}</td>
                    <td className="koc-mono">{fmt(item.expected_claims)}</td>
                    <td className="koc-mono">{fmt(item.estimated_processing_minutes)}m</td>
                    <td>
                      {item.uploadable ? (
                        <button type="button" className="koc-btn" onClick={() => openUpload(item, item.missing_class)}>
                          <Upload className="h-3.5 w-3.5" /> Upload
                        </button>
                      ) : (
                        <button type="button" className="koc-btn" disabled={!!actionBusy} onClick={() => runAction('run_auto_repair', item.ticker)}>
                          Repair
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {!inbox.items?.length && !loading ? (
                  <tr><td colSpan={9} className="text-[var(--koc-muted)]">Inbox clear — no missing knowledge in scope.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 1 — Timeline */}
        <section className="koc-panel p-4">
          <p className="koc-kicker">Section 1</p>
          <h2 className="mt-1 text-lg font-semibold">Today&apos;s Knowledge Timeline</h2>
          <div className="mt-3">
            {timeline.length ? timeline.slice(0, 12).map((ev, idx) => (
              <div className="koc-timeline-item" key={`${ev.timestamp}-${idx}`}>
                <div className="koc-mono text-sm font-medium">{ev.time || '—'}</div>
                <div>
                  <div className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-semibold">{ev.ticker || '—'}</span>
                    <span className="text-[var(--koc-muted)]">{ev.document_type}</span>
                    <span className="koc-pill"><StatusDot ok={ev.status === 'Collected'} />{ev.status || '—'}</span>
                    {ev.raw?.slot || ev.timestamp ? (
                      <span className="koc-badge info">{ev.raw?.slot || 'snapshot'}</span>
                    ) : null}
                  </div>
                  <div className="mt-1 grid gap-1 text-xs text-[var(--koc-muted)] sm:grid-cols-2 lg:grid-cols-4">
                    <span>Source · {ev.source || '—'}</span>
                    <span>Evidence · {fmt(ev.evidence_objects)}</span>
                    <span>Claims · {fmt(ev.claims_extracted)}</span>
                    <span>
                      Memory {ev.knowledge_updated ? 'Updated' : '—'} · Graph {ev.knowledge_updated ? 'Updated' : '—'} · Research{' '}
                      {ev.research_invalidated ? 'Invalidated' : '—'}
                    </span>
                  </div>
                </div>
              </div>
            )) : (
              <p className="text-sm text-[var(--koc-muted)]">No ingestion events yet. Run CGL or upload knowledge.</p>
            )}
          </div>
        </section>

        {/* Section 2 — Coverage table */}
        <section className="koc-panel p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="koc-kicker">Section 2</p>
              <h2 className="mt-1 text-lg font-semibold">Institutional Coverage Dashboard</h2>
            </div>
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-[var(--koc-caption)]" />
              <input
                className="koc-input w-64 pl-8"
                placeholder="Filter ticker / company / missing"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="koc-table">
              <thead>
                <tr>
                  <th>Ticker</th>
                  <th>Company</th>
                  <th>Coverage %</th>
                  <th>Research Ready</th>
                  <th>Confidence</th>
                  <th>Claim Safe</th>
                  <th>State</th>
                  <th>Evidence</th>
                  <th>Missing</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.ticker}>
                    <td className="koc-mono font-semibold">{r.ticker}</td>
                    <td>{r.company}</td>
                    <td className="koc-mono">{fmt(r.coverage_pct)}%</td>
                    <td className="koc-mono">{fmt(r.research_readiness)}</td>
                    <td className="koc-mono">{fmt(r.knowledge_confidence)}</td>
                    <td>
                      <span className="koc-pill">
                        <StatusDot ok={!!r.claim_safe} />
                        {r.claim_safe ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="text-xs">{r.coverage_state || r.status || '—'}</td>
                    <td className="koc-mono">{fmt(r.evidence_count)}</td>
                    <td className="max-w-[220px] text-xs text-[var(--koc-muted)]">
                      {(r.missing_items || []).slice(0, 4).join(', ') || '—'}
                    </td>
                    <td>
                      <div className="flex flex-wrap gap-1">
                        <button type="button" className="koc-btn" onClick={() => openCompany(r.ticker)}>
                          <Eye className="h-3.5 w-3.5" /> View
                        </button>
                        <button type="button" className="koc-btn" disabled={!!actionBusy} onClick={() => runAction('run_icf_dispatch', r.ticker)}>
                          Refresh
                        </button>
                        <button type="button" className="koc-btn" onClick={() => openUpload(r)}>
                          <Upload className="h-3.5 w-3.5" /> Upload
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 3 — Company detail */}
        {selected ? (
          <section className="koc-panel p-4" id="company-detail">
            <p className="koc-kicker">Section 3 · Company Detail</p>
            <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{detail?.company || selected}</h2>
                <p className="koc-mono text-sm text-[var(--koc-muted)]">{selected}</p>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-4">
                <div>Coverage <div className="koc-mono text-base">{fmt(detail?.coverage_pct)}%</div></div>
                <div>Confidence <div className="koc-mono text-base">{fmt(detail?.knowledge_confidence)}</div></div>
                <div>Research Ready <div className="koc-mono text-base">{fmt(detail?.research_readiness)}</div></div>
                <div>Claim Safe <div className="koc-mono text-base">{detail?.claim_safe ? 'Yes' : 'No'}</div></div>
              </div>
            </div>
            <div className="koc-bar mt-3">
              <span style={{ width: `${Math.min(100, Number(detail?.coverage_pct) || 0)}%` }} />
            </div>
            {detail?.error ? (
              <p className="mt-2 text-sm text-[var(--koc-red)]">{detail.error}</p>
            ) : (
              <div className="koc-progress-grid mt-4">
                {(detail?.checklist || []).map((item) => (
                  <div key={item.id} className={`koc-progress-item ${item.state}`}>
                    <div className="font-semibold">{item.label}</div>
                    <div className="mt-1 capitalize text-[11px]">{item.state}</div>
                  </div>
                ))}
              </div>
            )}
          </section>
        ) : null}

        {/* Section 12 — Knowledge Gap AI */}
        <section className="koc-panel p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="koc-kicker">Section 12</p>
              <h2 className="mt-1 flex items-center gap-2 text-lg font-semibold">
                <Sparkles className="h-4 w-4 text-[var(--koc-blue)]" />
                Knowledge Gap AI
              </h2>
              <p className="mt-1 text-xs text-[var(--koc-muted)]">{gapAi.note}</p>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="koc-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Missing</th>
                  <th>Coverage</th>
                  <th>Confidence</th>
                  <th>Research Ready</th>
                  <th>New Claims</th>
                  <th>ETA</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {(gapAi.items || []).slice(0, 15).map((g) => (
                  <tr key={g.ticker}>
                    <td>
                      <button type="button" className="font-semibold hover:underline" onClick={() => openCompany(g.ticker)}>
                        {g.company}
                      </button>
                    </td>
                    <td className="max-w-[240px] text-xs">{(g.missing || []).join(', ')}</td>
                    <td className="koc-mono text-xs">
                      {fmt(g.coverage_now)}% → {fmt(g.coverage_expected)}%
                    </td>
                    <td className="koc-mono text-xs">
                      {fmt(g.knowledge_confidence_now)} → {fmt(g.knowledge_confidence_expected)}
                    </td>
                    <td className="koc-mono text-xs">
                      {fmt(g.research_ready_now)} → {fmt(g.research_ready_expected)}
                    </td>
                    <td className="koc-mono">{fmt(g.estimated_new_claims)}</td>
                    <td className="koc-mono">{fmt(g.estimated_processing_minutes)}m</td>
                    <td>
                      <button type="button" className="koc-btn" onClick={() => openUpload(g, (g.missing_classes || [])[0])}>
                        Find Missing Knowledge
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 6 — Queue */}
        <section className="koc-panel p-4">
          <p className="koc-kicker">Section 6</p>
          <h2 className="mt-1 text-lg font-semibold">Knowledge Queue</h2>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            {(queue.boards || (desk?.queue_stages || []).map((stage) => ({
              stage,
              count: (queue.stages || {})[stage] || 0,
            }))).map((b) => (
              <div key={b.stage} className="border border-[var(--koc-line)] p-3">
                <div className="text-[10px] font-bold uppercase tracking-wide text-[var(--koc-caption)]">{b.stage}</div>
                <div className="koc-mono mt-1 text-xl">{fmt(b.count)}</div>
                <button
                  type="button"
                  className="koc-btn mt-2"
                  disabled={!!actionBusy}
                  onClick={() => runAction('run_auto_repair', selected || 'RELIANCE')}
                >
                  Retry
                </button>
              </div>
            ))}
          </div>
        </section>

        {/* Section 7 — Collectors */}
        <section className="koc-panel p-4">
          <p className="koc-kicker">Section 7</p>
          <h2 className="mt-1 text-lg font-semibold">Collector Health</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="koc-table">
              <thead>
                <tr>
                  <th>Collector</th>
                  <th>Health</th>
                  <th>Success %</th>
                  <th>Latency</th>
                  <th>Failures</th>
                  <th>Last Success</th>
                  <th>Retry</th>
                </tr>
              </thead>
              <tbody>
                {collectors.map((c) => (
                  <tr key={c.collector}>
                    <td>{c.collector}</td>
                    <td>
                      <span className="koc-pill">
                        <StatusDot ok={c.health === 'Healthy'} warn={c.health === 'Warning' || c.health === 'Degraded'} />
                        {c.health}
                      </span>
                    </td>
                    <td className="koc-mono">{fmt(c.success_rate)}</td>
                    <td className="koc-mono">{c.latency_ms != null ? `${Math.round(c.latency_ms / 1000)}s` : '—'}</td>
                    <td className="koc-mono">{fmt(c.failures)}</td>
                    <td className="koc-mono text-xs">{(c.last_success || '').slice(0, 19) || '—'}</td>
                    <td>
                      <button type="button" className="koc-btn" disabled={!!actionBusy} onClick={() => runAction('run_cgl')}>
                        Retry
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 8 — Evidence Explorer */}
        <section className="koc-panel p-4">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="koc-kicker">Section 8</p>
              <h2 className="mt-1 text-lg font-semibold">Evidence Explorer</h2>
            </div>
            <button type="button" className="koc-btn" onClick={loadEvidence}>Load evidence</button>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="koc-table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Document</th>
                  <th>Type</th>
                  <th>Source</th>
                  <th>Hash</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {(evidence?.items || []).map((e) => (
                  <tr key={e.document_id}>
                    <td className="koc-mono">{e.ticker}</td>
                    <td className="text-xs">{e.document_id}</td>
                    <td>{e.document_type}</td>
                    <td>{e.source}</td>
                    <td className="koc-mono text-xs">{e.hash || '—'}</td>
                    <td>{e.status}</td>
                  </tr>
                ))}
                {!evidence?.items?.length ? (
                  <tr><td colSpan={6} className="text-[var(--koc-muted)]">Click Load evidence (scoped to selected company when set).</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 9 — KG viewer (lineage summary) */}
        {detail?.knowledge_graph ? (
          <section className="koc-panel p-4">
            <p className="koc-kicker">Section 9</p>
            <h2 className="mt-1 text-lg font-semibold">Knowledge Graph · {selected}</h2>
            <p className="mt-2 text-xs text-[var(--koc-muted)]">
              Company → Evidence → Claims → Financial Statements → Research Pack → Portfolio
            </p>
            <pre className="mt-3 max-h-56 overflow-auto border border-[var(--koc-line)] bg-[#fafbfc] p-3 text-[11px] text-[var(--koc-muted)]">
              {JSON.stringify(detail.knowledge_graph, null, 2).slice(0, 2500)}
            </pre>
          </section>
        ) : null}

        {/* Section 10 — Versions */}
        <section className="koc-panel p-4">
          <p className="koc-kicker">Section 10</p>
          <h2 className="mt-1 text-lg font-semibold">Knowledge Version History</h2>
          <div className="mt-3 overflow-x-auto">
            <table className="koc-table">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Companies Updated</th>
                  <th>Evidence Added</th>
                  <th>Research Invalidated</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {(versions.length ? versions : [{ knowledge_version: '—' }]).map((v, i) => (
                  <tr key={v.snapshot_id || v.knowledge_version || i}>
                    <td className="koc-mono">{v.knowledge_version || v.version || '—'}</td>
                    <td className="koc-mono">
                      {fmt(Array.isArray(v.companies_updated) ? v.companies_updated.length : v.companies_updated)}
                    </td>
                    <td className="koc-mono">{fmt(v.evidence_added)}</td>
                    <td className="koc-mono">
                      {fmt(Array.isArray(v.research_invalidated) ? v.research_invalidated.length : v.research_invalidated)}
                    </td>
                    <td className="koc-mono text-xs">{(v.timestamp || v.created_at || '').slice(0, 19) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Section 11 — Heatmap */}
        <section className="koc-panel p-4">
          <p className="koc-kicker">Section 11</p>
          <h2 className="mt-1 text-lg font-semibold">Institutional Coverage Heatmap</h2>
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {['TOP20', 'NIFTY50', 'NIFTY100', 'NIFTY500'].map((band) => {
              const cell = heatmap[band] || {};
              return (
                <div key={band} className="koc-heat-cell">
                  <div className="text-[10px] font-bold uppercase tracking-wide text-[var(--koc-caption)]">{band}</div>
                  {cell.coverage_pct != null ? (
                    <div className="mt-2 space-y-1 text-xs">
                      <div>Coverage <span className="koc-mono">{fmt(cell.coverage_pct)}%</span></div>
                      <div>Confidence <span className="koc-mono">{fmt(cell.knowledge_confidence)}</span></div>
                      <div>Research ready <span className="koc-mono">{fmt(cell.research_ready)}</span></div>
                      <div>Claim safe <span className="koc-mono">{fmt(cell.claim_safe_pct)}%</span></div>
                      <div>ICC <span className="koc-mono">{fmt(cell.icc_complete)}</span></div>
                    </div>
                  ) : (
                    <p className="mt-2 text-xs text-[var(--koc-muted)]">{cell.note || '—'}</p>
                  )}
                </div>
              );
            })}
          </div>
        </section>

        {/* Section 13 — Operations */}
        <section className="koc-panel p-4">
          <p className="koc-kicker">Section 13</p>
          <h2 className="mt-1 text-lg font-semibold">Operations</h2>
          <p className="mt-1 text-xs text-[var(--koc-muted)]">Every action is audit-logged. Evidence is never overwritten.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {[
              ['run_cgl', 'Run CGL'],
              ['run_kil', 'Run KIL'],
              ['run_full_coverage', 'Run ICF'],
              ['run_research_refresh', 'Research Refresh'],
              ['run_company_memory_refresh', 'Memory Refresh'],
              ['rebuild_knowledge_graph', 'KG Refresh'],
              ['run_auto_repair', 'Auto Repair'],
              ['run_knowledge_validation', 'Validation'],
              ['run_coverage_scan', 'Coverage Scan'],
              ['run_institutional_coverage_check', 'ICC Check'],
              ['run_top20_audit', 'Top20 Audit'],
            ].map(([action, label]) => (
              <button
                key={action}
                type="button"
                className="koc-btn"
                disabled={!!actionBusy}
                onClick={() =>
                  runAction(
                    action,
                    ['run_cgl', 'run_full_coverage', 'run_coverage_scan', 'run_top20_audit'].includes(action)
                      ? undefined
                      : selected || 'RELIANCE'
                  )
                }
              >
                <Play className="h-3.5 w-3.5" />
                {actionBusy === action ? 'Running…' : label}
              </button>
            ))}
          </div>
        </section>

        {/* Section 14 — Audit */}
        <section className="koc-panel p-4">
          <p className="koc-kicker">Section 14 · Audit Trail</p>
          <h2 className="mt-1 text-lg font-semibold">Immutable Operations Log</h2>
          <p className="mt-1 text-xs text-[var(--koc-muted)]">
            Nothing permanently deleted. Everything versioned. Rollback reserved for future restore APIs.
          </p>
          <div className="mt-3 overflow-x-auto">
            <table className="koc-table">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Who</th>
                  <th>What</th>
                  <th>Company</th>
                  <th>Hash</th>
                  <th>Version</th>
                </tr>
              </thead>
              <tbody>
                {(audit?.entries || []).map((e) => (
                  <tr key={e.audit_id}>
                    <td className="koc-mono text-xs">{(e.when || '').slice(0, 19)}</td>
                    <td className="text-xs">{e.actor}</td>
                    <td>{e.action}</td>
                    <td className="koc-mono">{e.ticker || '—'}</td>
                    <td className="koc-mono text-xs">{(e.document_hash || '').slice(0, 12) || '—'}</td>
                    <td className="koc-mono text-xs">{e.knowledge_version || '—'}</td>
                  </tr>
                ))}
                {!audit?.entries?.length ? (
                  <tr><td colSpan={6} className="text-[var(--koc-muted)]">No audited actions yet.</td></tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <UploadModal
        open={uploadState.open}
        ticker={uploadState.ticker}
        company={uploadState.company}
        documentType={uploadState.documentType}
        actor={user?.email}
        onClose={() => setUploadState((s) => ({ ...s, open: false }))}
        onDone={() => load()}
      />
      <SheetUploadModal
        open={sheetUploadOpen}
        actor={user?.email}
        onClose={() => setSheetUploadOpen(false)}
        onDone={() => load()}
      />
    </div>
  );
}
