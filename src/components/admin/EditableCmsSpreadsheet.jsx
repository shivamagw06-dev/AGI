import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Check, Loader2, Plus, Trash2 } from 'lucide-react';
import {
  createCmsRecord,
  deleteCmsRecord,
  publishCmsRecord,
  updateCmsRecord,
} from '@/lib/intelligenceCmsApi';

function emptyRowData(columns) {
  const data = {};
  columns.forEach((col) => {
    data[col.key] = '';
  });
  return data;
}

export default function EditableCmsSpreadsheet({
  moduleId,
  moduleDef,
  records,
  loading,
  onReload,
  actor,
  autoPublish = true,
}) {
  const columns = useMemo(
    () => (moduleDef?.columns || []).filter((col) => col.grid !== false),
    [moduleDef]
  );

  const [drafts, setDrafts] = useState({});
  const [savingIds, setSavingIds] = useState({});
  const [savedIds, setSavedIds] = useState({});
  const saveTimers = useRef({});

  useEffect(() => {
    const next = {};
    records.forEach((record) => {
      next[record.id] = { ...record.data };
    });
    setDrafts(next);
  }, [records]);

  const markSaved = useCallback((id) => {
    setSavedIds((prev) => ({ ...prev, [id]: true }));
    window.setTimeout(() => {
      setSavedIds((prev) => {
        const copy = { ...prev };
        delete copy[id];
        return copy;
      });
    }, 1800);
  }, []);

  const persistRow = useCallback(
    async (record, dataPatch) => {
      if (!record?.id) return;
      setSavingIds((prev) => ({ ...prev, [record.id]: true }));
      try {
        const nextData = { ...(drafts[record.id] || record.data || {}), ...dataPatch };
        await updateCmsRecord(record.id, {
          data: nextData,
          actor,
          status: autoPublish ? 'published' : record.status,
        });
        if (autoPublish && record.status !== 'published') {
          await publishCmsRecord(record.id, actor);
        }
        markSaved(record.id);
        onReload?.();
      } finally {
        setSavingIds((prev) => {
          const copy = { ...prev };
          delete copy[record.id];
          return copy;
        });
      }
    },
    [actor, autoPublish, drafts, markSaved, onReload]
  );

  const queueSave = useCallback(
    (record, key, value) => {
      if (!record?.id) return;
      setDrafts((prev) => ({
        ...prev,
        [record.id]: { ...(prev[record.id] || {}), [key]: value },
      }));

      if (saveTimers.current[record.id]) {
        window.clearTimeout(saveTimers.current[record.id]);
      }
      saveTimers.current[record.id] = window.setTimeout(() => {
        persistRow(record, { [key]: value });
      }, 450);
    },
    [persistRow]
  );

  const handleAddRow = async () => {
    const data = emptyRowData(columns);
    const record = await createCmsRecord(moduleId, {
      data,
      status: autoPublish ? 'published' : 'draft',
      actor,
    });
    if (autoPublish) await publishCmsRecord(record.id, actor);
    onReload?.();
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this row?')) return;
    await deleteCmsRecord(id);
    onReload?.();
  };

  const handlePaste = async (event, startRecordId, startColIndex) => {
    const text = event.clipboardData?.getData('text/plain');
    if (!text || !text.includes('\t')) return;
    event.preventDefault();

    const lines = text.trim().split(/\r?\n/).filter(Boolean);
    const startIndex = records.findIndex((r) => r.id === startRecordId);
    if (startIndex < 0) return;

    for (let rowOffset = 0; rowOffset < lines.length; rowOffset += 1) {
      const cells = lines[rowOffset].split('\t');
      let record = records[startIndex + rowOffset];
      if (!record) {
        record = await createCmsRecord(moduleId, {
          data: emptyRowData(columns),
          status: autoPublish ? 'published' : 'draft',
          actor,
        });
        if (autoPublish) await publishCmsRecord(record.id, actor);
      }

      const patch = {};
      cells.forEach((value, colOffset) => {
        const col = columns[startColIndex + colOffset];
        if (col) patch[col.key] = value.trim();
      });
      if (Object.keys(patch).length) {
        await persistRow(record, patch);
      }
    }
    onReload?.();
  };

  if (!moduleDef) return null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-slate-500">
        <p>
          Edit cells inline like a spreadsheet. Changes save automatically
          {autoPublish ? ' and publish to the Private Markets page.' : '.'}
        </p>
        <button
          type="button"
          onClick={handleAddRow}
          className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          <Plus size={16} /> Add row
        </button>
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              {columns.map((col) => (
                <th key={col.key} className="whitespace-nowrap px-2 py-2 text-left font-medium text-slate-600">
                  {col.label}
                </th>
              ))}
              <th className="px-2 py-2 text-left font-medium text-slate-600">Status</th>
              <th className="px-2 py-2 w-24" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length + 2} className="p-10 text-center text-slate-400">
                  Loading spreadsheet…
                </td>
              </tr>
            ) : records.length === 0 ? (
              <tr>
                <td colSpan={columns.length + 2} className="p-10 text-center text-slate-400">
                  No rows yet. Click &quot;Add row&quot; or paste from Excel.
                </td>
              </tr>
            ) : (
              records.map((record) => (
                <tr key={record.id} className="border-b border-slate-100 hover:bg-slate-50/70">
                  {columns.map((col, colIndex) => (
                    <td key={col.key} className="p-0 align-top">
                      <input
                        className="w-full min-w-[120px] border-0 bg-transparent px-2 py-2 outline-none focus:bg-blue-50 focus:ring-1 focus:ring-inset focus:ring-blue-200"
                        value={drafts[record.id]?.[col.key] ?? ''}
                        onChange={(e) => queueSave(record, col.key, e.target.value)}
                        onPaste={(e) => handlePaste(e, record.id, colIndex)}
                        onBlur={() => {
                          if (saveTimers.current[record.id]) {
                            window.clearTimeout(saveTimers.current[record.id]);
                            delete saveTimers.current[record.id];
                          }
                          persistRow(record, drafts[record.id] || {});
                        }}
                      />
                    </td>
                  ))}
                  <td className="px-2 py-2 text-xs uppercase tracking-wide text-slate-500 whitespace-nowrap">
                    {record.status}
                  </td>
                  <td className="px-2 py-2 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      {savingIds[record.id] ? (
                        <Loader2 size={14} className="animate-spin text-slate-400" />
                      ) : savedIds[record.id] ? (
                        <Check size={14} className="text-green-600" />
                      ) : null}
                      <button
                        type="button"
                        className="text-red-600 hover:text-red-700"
                        onClick={() => handleDelete(record.id)}
                        aria-label="Delete row"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
