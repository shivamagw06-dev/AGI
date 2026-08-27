import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useParams, useSearchParams } from 'react-router-dom';
import { Download, Upload } from 'lucide-react';
import {
  exportCmsModuleCsv,
  fetchCmsRecords,
  importCmsModuleCsv,
} from '@/lib/intelligenceCmsApi';
import { useAuth } from '@/contexts/AuthContext';
import EditableCmsSpreadsheet from '@/components/admin/EditableCmsSpreadsheet';

const SLUG_TO_MODULE = {
  'valuation-monitor': 'valuation_monitor',
  transactions: 'transactions',
  'pe-firms': 'pe_firms',
  'portfolio-companies': 'portfolio_companies',
  funds: 'funds',
  industries: 'industries',
  people: 'people',
  'editors-desk': 'editors_desk',
};

function resolveModuleId(moduleSlug, pathname) {
  if (moduleSlug && SLUG_TO_MODULE[moduleSlug]) return SLUG_TO_MODULE[moduleSlug];
  const tail = pathname.split('/').filter(Boolean).pop();
  return SLUG_TO_MODULE[tail] || null;
}

export default function IntelligenceModulePage() {
  const { moduleSlug } = useParams();
  const { pathname } = useLocation();
  const [searchParams, setSearchParams] = useSearchParams();
  const moduleId = resolveModuleId(moduleSlug, pathname);
  const { user } = useAuth();
  const actor = user?.email || 'admin';

  const [moduleDef, setModuleDef] = useState(null);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [status, setStatus] = useState(searchParams.get('status') || '');

  const reload = useCallback(async () => {
    if (!moduleId) return;
    setLoading(true);
    try {
      const res = await fetchCmsRecords(moduleId, { status: status || undefined, q: q || undefined });
      setModuleDef(res.module);
      setRecords(res.records);
    } finally {
      setLoading(false);
    }
  }, [moduleId, status, q]);

  useEffect(() => { reload(); }, [reload]);

  const publicPreviewPath = useMemo(() => {
    if (moduleId === 'valuation_monitor') return '/private-markets#valuation-monitor';
    if (moduleId === 'transactions') return '/private-markets#recent-transactions';
    return moduleDef?.publicPath || '/private-markets';
  }, [moduleDef, moduleId]);

  const handleImport = async (file) => {
    const csv = await file.text();
    await importCmsModuleCsv(moduleId, csv, actor);
    reload();
  };

  if (!moduleId) {
    return <div className="p-8 text-slate-500">Module not found.</div>;
  }

  return (
    <div className="p-6 lg:p-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{moduleDef?.label || moduleSlug}</h1>
          <p className="text-slate-500 mt-1">{moduleDef?.description}</p>
          <a
            href={publicPreviewPath}
            target="_blank"
            rel="noreferrer"
            className="inline-block mt-2 text-sm font-medium text-[#0b3b60] hover:underline"
          >
            Preview on Private Markets page →
          </a>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <input
          type="search"
          placeholder="Search rows…"
          className="border border-slate-200 rounded-md px-3 py-2 text-sm w-48"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          className="border border-slate-200 rounded-md px-3 py-2 text-sm"
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setSearchParams(e.target.value ? { status: e.target.value } : {});
          }}
        >
          <option value="">All statuses</option>
          {['draft', 'review', 'published', 'archived'].map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
        <button type="button" onClick={() => exportCmsModuleCsv(moduleId)} className="inline-flex items-center gap-1 px-3 py-2 border text-sm rounded-md">
          <Download size={16} /> Export CSV
        </button>
        <label className="inline-flex items-center gap-1 px-3 py-2 border text-sm rounded-md cursor-pointer">
          <Upload size={16} /> Import CSV
          <input type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => e.target.files?.[0] && handleImport(e.target.files[0])} />
        </label>
      </div>

      <EditableCmsSpreadsheet
        moduleId={moduleId}
        moduleDef={moduleDef}
        records={records}
        loading={loading}
        onReload={reload}
        actor={actor}
        autoPublish
      />
    </div>
  );
}
