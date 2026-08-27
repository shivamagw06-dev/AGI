import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowLeft,
  Database,
  Download,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  Upload,
} from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import {
  clearOverride as clearOverrideApi,
  editCells,
  exportTab,
  getSheet,
  getWarehouseHealth,
  getWarehouseWhoami,
  getWorkbook,
  publishTab,
  searchWarehouse,
  setWarehouseActor,
} from '@/lib/warehouseApi';
import HistoryDrawer from './warehouse/HistoryDrawer';
import ImportDialog from './warehouse/ImportDialog';
import OpsPanel from './warehouse/OpsPanel';
import WarehouseGrid from './warehouse/WarehouseGrid';
import './dataWarehouse.css';

const PAGE_SIZE = 100;

function downloadCsv(filename, csv) {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function DataWarehouse({ initialTabId = 'company_master', focused = false }) {
  const { user } = useAuth() || {};
  const [searchParams] = useSearchParams();
  const [workbook, setWorkbook] = useState(null);
  const [health, setHealth] = useState(null);
  const [role, setRole] = useState(null);
  const requestedTab = searchParams.get('tab') || initialTabId;
  const [activeTabId, setActiveTabId] = useState(requestedTab);
  const [sheet, setSheet] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [offset, setOffset] = useState(0);
  const [sort, setSort] = useState(null);
  const [order, setOrder] = useState('asc');
  const [filters, setFilters] = useState({});
  const [query, setQuery] = useState('');
  const [globalHits, setGlobalHits] = useState(null);
  const [historyRow, setHistoryRow] = useState(null);
  const [showImport, setShowImport] = useState(false);
  const [showOps, setShowOps] = useState(false);
  const [status, setStatus] = useState(null);
  const filterTimer = useRef(null);

  useEffect(() => {
    setWarehouseActor(user?.email || user?.id || 'admin');
  }, [user]);

  const activeTab = useMemo(
    () => (workbook?.tabs || []).find((tab) => tab.id === activeTabId) || null,
    [workbook, activeTabId],
  );

  const columns = sheet?.columns || activeTab?.columns || [];
  const visibleTabs = focused ? (workbook?.tabs || []).filter((tab) => tab.id === activeTabId) : (workbook?.tabs || []);

  /* --------------------------------------------------------------- loading */

  useEffect(() => {
    (async () => {
      try {
        const [book, hp, who] = await Promise.all([
          getWorkbook(),
          getWarehouseHealth(),
          getWarehouseWhoami(),
        ]);
        setWorkbook(book);
        setHealth(hp);
        setRole(who);
      } catch (err) {
        setError(err.message);
      }
    })();
  }, []);

  const loadSheet = useCallback(async () => {
    if (!activeTabId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getSheet(activeTabId, {
        limit: PAGE_SIZE,
        offset,
        sort,
        order,
        filters,
      });
      if (!result?.ok) throw new Error(result?.error || 'sheet_failed');
      setSheet(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [activeTabId, filters, offset, order, sort]);

  useEffect(() => {
    loadSheet();
  }, [loadSheet]);

  /* --------------------------------------------------------------- actions */

  const selectTab = (tabId) => {
    setActiveTabId(tabId);
    setOffset(0);
    setSort(null);
    setOrder('asc');
    setFilters({});
    setGlobalHits(null);
  };

  const onSortChange = (columnKey) => {
    if (sort === columnKey) setOrder(order === 'asc' ? 'desc' : 'asc');
    else {
      setSort(columnKey);
      setOrder('asc');
    }
    setOffset(0);
  };

  const onFilterChange = (columnKey, value) => {
    const next = { ...filters };
    if (value) next[columnKey] = { op: 'contains', value };
    else delete next[columnKey];
    if (filterTimer.current) clearTimeout(filterTimer.current);
    filterTimer.current = setTimeout(() => {
      setFilters(next);
      setOffset(0);
    }, 300);
  };

  const commitEdits = useCallback(
    async (edits) => {
      try {
        const result = await editCells(activeTabId, edits, { reason: 'admin workspace edit' });
        if (!result?.ok) throw new Error(result?.error || 'edit_failed');
        if (result.rejected?.length) {
          setStatus(`${result.applied} applied, ${result.rejected.length} rejected.`);
        } else {
          setStatus(`${result.applied} cell${result.applied === 1 ? '' : 's'} updated and versioned.`);
        }
        await loadSheet();
      } catch (err) {
        setError(err.message);
      }
    },
    [activeTabId, loadSheet],
  );

  const clearOverride = useCallback(
    async (rowId, column) => {
      try {
        await clearOverrideApi(activeTabId, rowId, column);
        setStatus(`Reverted ${column} to the imported value.`);
        await loadSheet();
      } catch (err) {
        setError(err.message);
      }
    },
    [activeTabId, loadSheet],
  );

  const runSearch = async (event) => {
    event.preventDefault();
    if (!query.trim()) {
      setGlobalHits(null);
      return;
    }
    try {
      const result = await searchWarehouse(query.trim(), { per_tab: 3 });
      setGlobalHits(result);
    } catch (err) {
      setError(err.message);
    }
  };

  const doExport = async () => {
    try {
      const result = await exportTab(activeTabId, { limit: 5000 });
      if (result?.csv) downloadCsv(result.filename || `${activeTabId}.csv`, result.csv);
    } catch (err) {
      setError(err.message);
    }
  };

  const doPublish = async () => {
    try {
      const result = await publishTab(activeTabId);
      if (!result?.ok) throw new Error(result?.error || 'publish_failed');
      setStatus(`Published ${result.published} rows.`);
    } catch (err) {
      setError(err.message);
    }
  };

  const canEdit = Boolean(role?.actions?.includes('edit'));
  const total = sheet?.total || 0;
  const showingTo = Math.min(offset + PAGE_SIZE, total);

  return (
    <div className="wh-root">
      <header className="wh-top">
        <div className="wh-top-left">
          <Link to="/admin" className="wh-back">
            <ArrowLeft size={13} /> Admin
          </Link>
          <h1>
            <Database size={16} /> {activeTabId === 'sector_evidence_matrix' ? 'Sector Missing Data Workbook' : 'Institutional Data Warehouse'}
          </h1>
          <span className="wh-sub">
            {health ? `${health.total_rows?.toLocaleString()} rows · ${health.dialect}` : 'connecting…'}
          </span>
        </div>

        <form className="wh-search" onSubmit={runSearch}>
          <Search size={13} />
          <input
            value={query}
            placeholder="Search every sheet — try a company name"
            onChange={(event) => setQuery(event.target.value)}
          />
        </form>

        <div className="wh-top-actions">
          <span className="wh-role" title={`Role: ${role?.role || 'unknown'}`}>
            {role?.role || '—'}
          </span>
          <button type="button" className="wh-btn" onClick={() => loadSheet()} title="Reload sheet">
            <RefreshCw size={13} />
          </button>
          <button type="button" className="wh-btn" onClick={doExport} title="Export CSV">
            <Download size={13} />
          </button>
          <button
            type="button"
            className="wh-btn"
            disabled={!canEdit || activeTab?.read_only}
            onClick={() => setShowImport(true)}
          >
            <Upload size={13} /> Import
          </button>
          <button type="button" className="wh-btn" onClick={() => setShowOps(true)}>
            <Settings2 size={13} /> Operations
          </button>
        </div>
      </header>

      {globalHits ? (
        <div className="wh-global-hits">
          <div className="wh-global-head">
            <strong>{globalHits.total_matches}</strong> matches for “{globalHits.query}”
            {globalHits.symbol ? ` · resolved to ${globalHits.symbol}` : ''}
            <button type="button" onClick={() => setGlobalHits(null)}>
              clear
            </button>
          </div>
          <div className="wh-global-list">
            {(globalHits.tabs || []).map((hit) => (
              <button key={hit.tab} type="button" onClick={() => selectTab(hit.tab)}>
                <span>{hit.label}</span>
                <em>{hit.matches}</em>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <nav className="wh-tabstrip">
        {visibleTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={tab.id === activeTabId ? 'is-active' : ''}
            onClick={() => selectTab(tab.id)}
            title={tab.description}
          >
            {tab.label}
            <em>{tab.rows?.toLocaleString?.() ?? tab.rows ?? 0}</em>
          </button>
        ))}
      </nav>

      {activeTab ? (
        <div className="wh-tabmeta">
          <p>
            {activeTab.description}
            {activeTabId === 'sector_evidence_matrix'
              ? ' Start with DATA_REQUIRED rows; enter the value, stated unit, period, publication date and primary-source URL.'
              : ''}
          </p>
          <div className="wh-tabmeta-flags">
            {activeTab.read_only ? <span className="wh-pill is-locked">calculated · read only</span> : null}
            {activeTab.append_only ? <span className="wh-pill is-append">append only</span> : null}
            <span className="wh-pill">key: {activeTab.key.join(' + ')}</span>
          </div>
        </div>
      ) : null}

      {error ? <div className="wh-error wh-error-bar">{error}</div> : null}
      {status ? (
        <div className="wh-status-bar" onAnimationEnd={() => setStatus(null)}>
          {status}
        </div>
      ) : null}

      {activeTab ? (
        <WarehouseGrid
          tab={activeTab}
          columns={columns}
          rows={sheet?.rows || []}
          loading={loading}
          sort={sort}
          order={order}
          filters={filters}
          onSortChange={onSortChange}
          onFilterChange={onFilterChange}
          onCommitEdits={commitEdits}
          onOpenHistory={setHistoryRow}
          onClearOverride={clearOverride}
          canEdit={canEdit}
        />
      ) : null}

      <footer className="wh-bottom">
        <span>
          {total ? `${offset + 1}–${showingTo} of ${total.toLocaleString()}` : 'no rows'}
        </span>
        <div className="wh-pager">
          <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
            Previous
          </button>
          <button
            type="button"
            disabled={showingTo >= total}
            onClick={() => setOffset(offset + PAGE_SIZE)}
          >
            Next
          </button>
        </div>
        <div className="wh-bottom-actions">
          <button
            type="button"
            className="wh-btn"
            disabled={!canEdit || activeTab?.read_only}
            onClick={() => setShowImport(true)}
          >
            <Plus size={12} /> Add rows
          </button>
          <button
            type="button"
            className="wh-btn"
            disabled={!role?.actions?.includes('publish')}
            onClick={doPublish}
          >
            Publish sheet
          </button>
        </div>
      </footer>

      {showImport && activeTab ? (
        <ImportDialog
          tab={activeTab}
          columns={columns}
          onClose={() => setShowImport(false)}
          onImported={(result) => {
            setStatus(`Imported ${result.inserted || 0} new and ${result.updated || 0} updated rows.`);
            loadSheet();
          }}
        />
      ) : null}

      {historyRow && activeTab ? (
        <HistoryDrawer
          tab={activeTab}
          row={historyRow}
          onClose={() => setHistoryRow(null)}
          onRestored={() => {
            setStatus('Row restored to an earlier version.');
            loadSheet();
          }}
        />
      ) : null}

      {showOps ? (
        <OpsPanel
          onClose={() => setShowOps(false)}
          onRefreshed={() => {
            setStatus('Refresh finished.');
            loadSheet();
          }}
        />
      ) : null}
    </div>
  );
}
