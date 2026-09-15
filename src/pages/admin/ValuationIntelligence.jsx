import { Fragment, useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  RefreshCw,
  Upload,
  CheckCircle2,
  RotateCcw,
  Eye,
  FileSpreadsheet,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { isAdmin } from '@/lib/adminAuth';
import {
  exportValuationConsensusSnapshot,
  getValuationConsensusAnalytics,
  getValuationConsensusCompany,
  getValuationConsensusHealth,
  getValuationConsensusRows,
  listValuationConsensusVersions,
  previewValuationConsensusImport,
  publishValuationConsensusImport,
  rollbackValuationConsensus,
  seedValuationConsensus,
  validateValuationConsensusImport,
} from '@/lib/intelligenceApi';
import './valuationIntelligence.css';

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || '');
      const comma = result.indexOf(',');
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.onerror = () => reject(reader.error || new Error('Could not read the Excel file'));
    reader.readAsDataURL(file);
  });
}

function fmt(v, digits = 1) {
  if (v == null || v === '') return '—';
  if (typeof v === 'number') {
    if (Math.abs(v) >= 1000) return v.toLocaleString(undefined, { maximumFractionDigits: 1 });
    return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  }
  return String(v);
}

function upsideTone(v) {
  if (v == null || Number.isNaN(Number(v))) return '';
  const n = Number(v);
  if (n > 20) return 'green';
  if (n >= 10) return 'amber';
  if (n < 0) return 'red';
  return '';
}

function RecoBars({ buy = 0, hold = 0, sell = 0 }) {
  const total = Math.max(1, Number(buy || 0) + Number(hold || 0) + Number(sell || 0));
  const rows = [
    ['Buy', buy, 'buy'],
    ['Hold', hold, 'hold'],
    ['Sell', sell, 'sell'],
  ];
  return (
    <div className="vi-reco" onClick={(e) => e.stopPropagation()}>
      {rows.map(([label, val, cls]) => (
        <div className={`vi-reco-bar ${cls}`} key={label}>
          <span>{label}</span>
          <div className="track">
            <div className="fill" style={{ width: `${(Number(val || 0) / total) * 100}%` }} />
          </div>
          <span>{fmt(val, 0)}</span>
        </div>
      ))}
    </div>
  );
}

function Kv({ data }) {
  if (!data) return null;
  return (
    <div className="vi-kv">
      {Object.entries(data).map(([k, v]) => (
        <div key={k} style={{ display: 'contents' }}>
          <div className="k">{k.replace(/_/g, ' ')}</div>
          <div className="v">
            {typeof v === 'object' && v ? JSON.stringify(v).slice(0, 180) : fmt(v)}
          </div>
        </div>
      ))}
    </div>
  );
}

function ImportModal({ open, actor, onClose, onPublished }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState('');
  const [preview, setPreview] = useState(null);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!open) {
      setFile(null);
      setPreview(null);
      setError('');
      setBusy('');
      setStatus('');
    }
  }, [open]);

  if (!open) return null;

  const runPreview = async (chosen) => {
    const f = chosen || file;
    if (!f) {
      setError('Choose an AGI consensus Excel (.xlsx) file first.');
      return;
    }
    setBusy('preview');
    setError('');
    setStatus(`Reading ${f.name}…`);
    setPreview(null);
    try {
      const content_base64 = await fileToBase64(f);
      setStatus('Parsing and matching tickers…');
      const out = await previewValuationConsensusImport({
        filename: f.name,
        content_base64,
        actor,
      });
      if (!out?.ok) throw new Error(out?.error || 'Preview failed');
      setPreview(out);
      setStatus(`Preview ready — ${out.row_count || 0} companies`);
    } catch (err) {
      setError(err?.message || 'Preview failed');
      setStatus('');
    } finally {
      setBusy('');
    }
  };

  const onPick = (f) => {
    setFile(f || null);
    setPreview(null);
    setError('');
    if (f) runPreview(f);
  };

  const onValidate = async () => {
    if (!preview?.import_id) return;
    setBusy('validate');
    setError('');
    try {
      const out = await validateValuationConsensusImport(preview.import_id, actor);
      if (!out?.ok) throw new Error((out?.errors || []).join(', ') || 'Validation failed');
      setPreview((p) => ({ ...p, validated: true }));
      setStatus('Validated — ready to publish');
    } catch (err) {
      setError(err?.message || 'Validation failed');
    } finally {
      setBusy('');
    }
  };

  const onPublish = async () => {
    if (!preview?.import_id) return;
    setBusy('publish');
    setError('');
    setStatus('Publishing to database…');
    try {
      if (!preview.validated) {
        const v = await validateValuationConsensusImport(preview.import_id, actor);
        if (!v?.ok) throw new Error((v?.errors || []).join(', ') || 'Validation failed');
      }
      const out = await publishValuationConsensusImport(preview.import_id, actor);
      if (!out?.ok) throw new Error(out?.error || 'Publish failed');
      onPublished?.(out);
      onClose?.();
    } catch (err) {
      setError(err?.message || 'Publish failed');
      setStatus('');
    } finally {
      setBusy('');
    }
  };

  const diff = preview?.diff || {};

  return (
    <div className="vi-modal-backdrop" onClick={onClose}>
      <div className="vi-modal" onClick={(e) => e.stopPropagation()}>
        <h2>Import AGI Consensus Estimates</h2>
        <p className="hint">
          Choose an Excel file — preview runs automatically. Then Validate and Publish.
          Spreadsheet is an import source only; numbers are stored as-is.
        </p>
        <label className="vi-btn teal" style={{ cursor: 'pointer', display: 'inline-flex' }}>
          <FileSpreadsheet size={14} />
          {file ? file.name : 'Choose Excel file'}
          <input
            type="file"
            accept=".xlsx,.xls,.xlsm,.csv"
            style={{ display: 'none' }}
            disabled={!!busy}
            onChange={(e) => onPick(e.target.files?.[0] || null)}
          />
        </label>
        {status ? <p className="hint" style={{ marginTop: '0.65rem' }}>{busy ? `${status} (${busy})` : status}</p> : null}
        {error ? <div className="vi-error" style={{ marginTop: '0.75rem' }}>{error}</div> : null}
        {preview ? (
          <div className="vi-preview-grid">
            <div className="vi-stat">
              <div className="label">Rows</div>
              <div className="value">{fmt(preview.row_count, 0)}</div>
            </div>
            <div className="vi-stat">
              <div className="label">Unresolved</div>
              <div className="value">{fmt(preview.unresolved_count, 0)}</div>
            </div>
            <div className="vi-stat">
              <div className="label">Added</div>
              <div className="value">{fmt(diff.rows_added, 0)}</div>
            </div>
            <div className="vi-stat">
              <div className="label">Changed</div>
              <div className="value">{fmt(diff.rows_changed, 0)}</div>
            </div>
            <div className="vi-stat">
              <div className="label">Removed</div>
              <div className="value">{fmt(diff.rows_removed, 0)}</div>
            </div>
            <div className="vi-stat">
              <div className="label">Mapped cols</div>
              <div className="value">{fmt((preview.columns_mapped || []).length, 0)}</div>
            </div>
          </div>
        ) : null}
        <div className="vi-actions" style={{ marginTop: '1rem', justifyContent: 'flex-start' }}>
          <button type="button" className="vi-btn" onClick={onClose} disabled={!!busy}>
            Cancel
          </button>
          <button type="button" className="vi-btn" disabled={!file || !!busy} onClick={() => runPreview()}>
            <Eye size={14} /> {busy === 'preview' ? 'Previewing…' : 'Preview Changes'}
          </button>
          <button type="button" className="vi-btn" disabled={!preview || !!busy} onClick={onValidate}>
            <CheckCircle2 size={14} /> Validate
          </button>
          <button type="button" className="vi-btn primary" disabled={!preview || !!busy} onClick={onPublish}>
            <Upload size={14} /> {busy === 'publish' ? 'Publishing…' : 'Publish'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ValuationIntelligence() {
  const { user } = useAuth();
  const location = useLocation();
  const admin = isAdmin(user);
  const actor = user?.email || user?.id || 'admin';
  const homeLink = location.pathname.startsWith('/admin') ? '/admin' : '/';

  const [health, setHealth] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [rows, setRows] = useState({ items: [], total: 0, page: 1, pages: 0 });
  const [q, setQ] = useState('');
  const [sector, setSector] = useState('');
  const [industry, setIndustry] = useState('');
  const [recommendation, setRecommendation] = useState('');
  const [coverageMin, setCoverageMin] = useState('');
  const [mcapMin, setMcapMin] = useState('');
  const [sort, setSort] = useState('coverage');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [expanded, setExpanded] = useState(null);
  const [detail, setDetail] = useState(null);
  const [tab, setTab] = useState('overview');
  const [importOpen, setImportOpen] = useState(false);
  const [versions, setVersions] = useState([]);
  const [busy, setBusy] = useState('');

  const loadMeta = useCallback(async () => {
    const [h, a, v] = await Promise.all([
      getValuationConsensusHealth(),
      getValuationConsensusAnalytics(),
      admin ? listValuationConsensusVersions().catch(() => ({ versions: [] })) : Promise.resolve({ versions: [] }),
    ]);
    setHealth(h);
    setAnalytics(a);
    setVersions(v?.versions || []);
  }, [admin]);

  const loadRows = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const out = await getValuationConsensusRows({
        q,
        page,
        page_size: 50,
        sort,
        sector,
        industry,
        recommendation,
        coverage_min: coverageMin,
        market_cap_min: mcapMin,
      });
      setRows(out || { items: [], total: 0 });
    } catch (err) {
      setError(err?.message || 'Failed to load valuation consensus');
    } finally {
      setLoading(false);
    }
  }, [q, page, sort, sector, industry, recommendation, coverageMin, mcapMin]);

  useEffect(() => {
    loadMeta().catch((err) => setError(err?.message || 'Failed to load analytics'));
  }, [loadMeta]);

  useEffect(() => {
    loadRows();
  }, [loadRows]);

  const onExpand = async (ticker) => {
    if (expanded === ticker) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    setExpanded(ticker);
    setTab('overview');
    try {
      const out = await getValuationConsensusCompany(ticker);
      setDetail(out);
    } catch (err) {
      setError(err?.message || 'Company detail failed');
    }
  };

  const onExport = async () => {
    setBusy('export');
    try {
      const snap = await exportValuationConsensusSnapshot();
      const blob = new Blob([JSON.stringify(snap, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `valuation_consensus_${snap.version_id || 'snapshot'}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err?.message || 'Export failed');
    } finally {
      setBusy('');
    }
  };

  const onRollback = async () => {
    const prior = (versions || []).find((v) => !v.live);
    if (!prior?.version_id) {
      setError('No prior version available to rollback');
      return;
    }
    if (!window.confirm(`Rollback to version ${prior.version_id}?`)) return;
    setBusy('rollback');
    try {
      await rollbackValuationConsensus(prior.version_id, actor);
      await loadMeta();
      await loadRows();
    } catch (err) {
      setError(err?.message || 'Rollback failed');
    } finally {
      setBusy('');
    }
  };

  const onSeedBrokerEstimates = async () => {
    setBusy('seed');
    setError('');
    try {
      const out = await seedValuationConsensus({ force: true, actor });
      if (!out?.ok) throw new Error(out?.error || 'Seed failed');
      await loadMeta();
      await loadRows();
    } catch (err) {
      setError(err?.message || 'Broker Estimates seed failed');
    } finally {
      setBusy('');
    }
  };

  const sectorCards = useMemo(
    () => (analytics?.sector_cards || []).filter((c) => (c.count || 0) > 0),
    [analytics]
  );

  const industries = analytics?.industries || [];

  return (
    <div className="vi-root">
      <header className="vi-header">
        <div className="vi-brand-row">
          <div className="vi-brand">
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.15rem' }}>
              <Link to={homeLink} style={{ color: 'var(--vi-muted)', fontSize: '0.8rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                <ArrowLeft size={14} /> {location.pathname.startsWith('/admin') ? 'Admin' : 'Home'}
              </Link>
              {!location.pathname.startsWith('/admin') ? (
                <Link to="/market-intelligence" style={{ color: 'var(--vi-muted)', fontSize: '0.8rem', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                  <ArrowLeft size={14} /> Market Intelligence
                </Link>
              ) : null}
            </div>
            <h1>Valuation Intelligence</h1>
            <p>Institutional Consensus Dashboard</p>
          </div>
          {admin ? (
            <div className="vi-actions">
              <button type="button" className="vi-btn" onClick={() => { loadMeta(); loadRows(); }}>
                <RefreshCw size={14} /> Refresh
              </button>
              <button
                type="button"
                className="vi-btn teal"
                disabled={!!busy}
                onClick={() => setImportOpen(true)}
              >
                <FileSpreadsheet size={14} /> Import AGI Consensus Excel
              </button>
              <button
                type="button"
                className="vi-btn primary"
                disabled={!!busy}
                onClick={onSeedBrokerEstimates}
              >
                <Upload size={14} /> {busy === 'seed' ? 'Loading…' : 'Load Broker Estimates'}
              </button>
              <button type="button" className="vi-btn" disabled={!!busy} onClick={onExport}>
                <Download size={14} /> Export Snapshot
              </button>
              <button type="button" className="vi-btn" disabled={!!busy} onClick={onRollback}>
                <RotateCcw size={14} /> Rollback
              </button>
            </div>
          ) : (
            <p style={{ color: 'var(--vi-muted)', fontSize: '0.8rem', maxWidth: 280, textAlign: 'right' }}>
              Browse-only. Sign in as admin to import AGI consensus estimates.
            </p>
          )}
        </div>

        <div className="vi-filters">
          <div className="vi-field" style={{ gridColumn: 'span 1' }}>
            <label>Search</label>
            <input
              value={q}
              placeholder="Ticker, company, sector, products…"
              onChange={(e) => {
                setPage(1);
                setQ(e.target.value);
              }}
            />
          </div>
          <div className="vi-field">
            <label>Sector</label>
            <select
              value={sector}
              onChange={(e) => {
                setPage(1);
                setSector(e.target.value);
              }}
            >
              <option value="">All</option>
              {(analytics?.sectors || []).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="vi-field">
            <label>Industry</label>
            <select
              value={industry}
              onChange={(e) => {
                setPage(1);
                setIndustry(e.target.value);
              }}
            >
              <option value="">All</option>
              {industries.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="vi-field">
            <label>Market Cap Min</label>
            <input
              value={mcapMin}
              placeholder="USD mm"
              onChange={(e) => {
                setPage(1);
                setMcapMin(e.target.value);
              }}
            />
          </div>
          <div className="vi-field">
            <label>Recommendation</label>
            <select
              value={recommendation}
              onChange={(e) => {
                setPage(1);
                setRecommendation(e.target.value);
              }}
            >
              <option value="">All</option>
              <option value="buy">Buy</option>
              <option value="outperform">Outperform</option>
              <option value="hold">Hold</option>
              <option value="sell">Sell</option>
            </select>
          </div>
          <div className="vi-field">
            <label>Coverage Min</label>
            <input
              value={coverageMin}
              placeholder="Analysts"
              onChange={(e) => {
                setPage(1);
                setCoverageMin(e.target.value);
              }}
            />
          </div>
          <div className="vi-updated">
            Updated
            <div style={{ color: 'var(--vi-ink)', fontWeight: 600 }}>
              {health?.updated_at ? new Date(health.updated_at).toLocaleString() : '—'}
            </div>
          </div>
        </div>
      </header>

      <main className="vi-body">
        {error ? <div className="vi-error">{error}</div> : null}

        <p className="vi-note">
          Note: consensus prices, targets and broker recommendation counts are AGI market intelligence.
          AGI Institutional Intelligence is shown inside each company panel.
        </p>

        <section className="vi-analytics">
          <div className="vi-stat">
            <div className="label">Total Companies</div>
            <div className="value">{fmt(analytics?.total_companies, 0)}</div>
          </div>
          <div className="vi-stat">
            <div className="label">Avg Target Upside</div>
            <div className="value">{fmt(analytics?.average_target_upside)}%</div>
          </div>
          <div className="vi-stat">
            <div className="label">Avg Coverage</div>
            <div className="value">{fmt(analytics?.average_coverage)}</div>
          </div>
          <div className="vi-stat">
            <div className="label">Buy / Hold / Sell</div>
            <div className="value">
              {fmt(analytics?.buy_rated, 0)} / {fmt(analytics?.hold_rated, 0)} / {fmt(analytics?.sell_rated, 0)}
            </div>
          </div>
          <div className="vi-stat">
            <div className="label">Highest Upside</div>
            <div className="value">{fmt(analytics?.highest_upside?.value)}%</div>
            <div className="hint">{analytics?.highest_upside?.ticker || '—'}</div>
          </div>
        </section>

        <section className="vi-sectors" aria-label="Primary sectors">
          <button
            type="button"
            className={`vi-sector ${sector === '' ? 'active' : ''}`}
            onClick={() => {
              setPage(1);
              setSector('');
            }}
          >
            <div className="name">All Sectors</div>
            <div className="count">{fmt(analytics?.total_companies, 0)} companies</div>
          </button>
          {sectorCards.map((c) => (
            <button
              type="button"
              key={c.sector}
              className={`vi-sector ${sector === c.sector ? 'active' : ''}`}
              onClick={() => {
                setPage(1);
                setSector((s) => (s === c.sector ? '' : c.sector));
              }}
            >
              <div className="name">{c.sector}</div>
              <div className="count">{fmt(c.count, 0)} companies</div>
            </button>
          ))}
        </section>

        <div className="vi-table-wrap">
          <table className="vi-table">
            <thead>
              <tr>
                {[
                  ['ticker', 'Ticker', 'pin'],
                  ['alphabetical', 'Company', 'pin company'],
                  ['sector', 'Sector', ''],
                  ['industry', 'Industry', ''],
                  ['cmp', 'CMP', ''],
                  ['target', 'Consensus Target', ''],
                  ['upside', 'Upside %', ''],
                  ['buy', 'Reco', ''],
                  ['coverage', 'Coverage', ''],
                  ['updated', 'Updated', ''],
                ].map(([key, label, cls]) => (
                  <th
                    key={key}
                    className={cls}
                    onClick={() => {
                      setSort(key);
                      setPage(1);
                    }}
                  >
                    {label}
                    {sort === key ? ' ▾' : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={10} style={{ padding: '1.5rem', color: 'var(--vi-muted)' }}>
                    Loading consensus…
                  </td>
                </tr>
              ) : (rows.items || []).length === 0 ? (
                <tr>
                  <td colSpan={10} style={{ padding: '1.5rem', color: 'var(--vi-muted)' }}>
                    No companies yet. {admin ? 'Import an AGI consensus Excel export to publish the first snapshot.' : 'Awaiting published consensus.'}
                  </td>
                </tr>
              ) : (
                (rows.items || []).map((r) => (
                  <Fragment key={r.ticker}>
                    <tr
                      className={expanded === r.ticker ? 'open' : ''}
                      onClick={() => onExpand(r.ticker)}
                    >
                      <td className="pin">
                        <strong>{r.ticker}</strong>
                      </td>
                      <td className="pin company">{r.company_name || '—'}</td>
                      <td>{r.sector || '—'}</td>
                      <td>{r.industry || '—'}</td>
                      <td>{fmt(r.cmp)}</td>
                      <td>{fmt(r.target_price)}</td>
                      <td>
                        <span className={`vi-up ${upsideTone(r.upside)}`}>{fmt(r.upside)}%</span>
                      </td>
                      <td>
                        <RecoBars buy={r.buy_count} hold={r.hold_count} sell={r.sell_count} />
                      </td>
                      <td>{fmt(r.coverage, 0)}</td>
                      <td>{r.updated_at ? new Date(r.updated_at).toLocaleDateString() : '—'}</td>
                    </tr>
                    {expanded === r.ticker && detail?.ok ? (
                      <tr>
                        <td colSpan={10} style={{ padding: 0 }}>
                          <Expansion detail={detail} tab={tab} setTab={setTab} />
                        </td>
                      </tr>
                    ) : null}
                  </Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="vi-pager">
          <span>
            {fmt(rows.total, 0)} companies · page {rows.page || page} / {rows.pages || 1}
          </span>
          <div className="vi-actions">
            <button
              type="button"
              className="vi-btn"
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Prev
            </button>
            <button
              type="button"
              className="vi-btn"
              disabled={page >= (rows.pages || 1)}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </main>

      <ImportModal
        open={importOpen}
        actor={actor}
        onClose={() => setImportOpen(false)}
        onPublished={() => {
          loadMeta();
          loadRows();
        }}
      />
    </div>
  );
}

function Expansion({ detail, tab, setTab }) {
  const tabs = ['overview', 'performance', 'valuation', 'business', 'research'];
  const agi = detail.agi_intelligence || {};
  const body =
    tab === 'overview' ? (
      <>
        <p className="vi-desc">{detail.overview?.business_description || 'No business description in this AGI snapshot.'}</p>
        <div style={{ marginTop: '0.75rem' }}>
          <Kv
            data={{
              sector: detail.overview?.sector,
              industry: detail.overview?.industry,
              country: detail.overview?.country,
              exchange: detail.overview?.exchange,
              parent: detail.overview?.parent,
              company_type: detail.overview?.company_type,
              trading_status: detail.overview?.trading_status,
              website: detail.overview?.website,
            }}
          />
        </div>
      </>
    ) : tab === 'performance' ? (
      <Kv data={detail.performance} />
    ) : tab === 'valuation' ? (
      <Kv data={detail.valuation} />
    ) : tab === 'business' ? (
      <>
        <p className="vi-desc">{detail.business?.business_description || '—'}</p>
        <div style={{ marginTop: '0.75rem' }}>
          <Kv
            data={{
              products: detail.business?.products,
              competitors: detail.business?.competitors,
              investors: detail.business?.investors,
              subsidiaries: detail.business?.subsidiaries,
              industry_classification: detail.business?.industry_classification,
            }}
          />
        </div>
      </>
    ) : (
      <Kv
        data={{
          recent_research: detail.research?.recent_research?.title || detail.research?.recent_research,
          open_agi_research: detail.research?.open_agi_research,
          investment_intelligence: detail.research?.investment_intelligence,
          business_intelligence: detail.research?.business_intelligence,
          industry_intelligence: detail.research?.industry_intelligence,
          research_intelligence: detail.research?.research_intelligence,
        }}
      />
    );

  return (
    <div className="vi-expand">
      <div className="vi-tabs">
        {tabs.map((t) => (
          <button
            type="button"
            key={t}
            className={`vi-tab ${tab === t ? 'active' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              setTab(t);
            }}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="vi-panels">
        <div className="vi-panel">
          <h3>AGI Market Consensus</h3>
          {body}
        </div>
        <div className="vi-panel vi-agi">
          <h3>AGI Intelligence</h3>
          <div className="vi-agi-grid">
            {[
              ['Business Quality', agi.business_quality],
              ['Financial Quality', agi.financial_quality],
              ['Industry Quality', agi.industry_quality],
              ['Investment Quality', agi.investment_quality],
              ['Research Coverage', agi.research_coverage],
              ['Evidence Confidence', agi.evidence_confidence],
              ['Monitoring', agi.monitoring_status],
              ['AGI Score', agi.agi_score],
            ].map(([k, v]) => (
              <div key={k}>
                <div className="k">{k}</div>
                <div className="v">{fmt(v)}</div>
              </div>
            ))}
          </div>
          {agi.latest_research?.summary ? (
            <p className="vi-desc" style={{ marginBottom: '0.75rem' }}>
              {agi.latest_research.summary}
            </p>
          ) : null}
          <div className="vi-links">
            {Object.entries(agi.links || {}).map(([k, href]) => (
              <Link key={k} to={href} onClick={(e) => e.stopPropagation()}>
                {k.replace(/_/g, ' ')}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
