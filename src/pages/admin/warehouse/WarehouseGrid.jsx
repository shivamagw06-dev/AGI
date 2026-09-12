import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { History, Lock, PenLine, RotateCcw } from 'lucide-react';

const EMPTY = '';

function formatValue(column, value) {
  if (value === null || value === undefined || value === '') return EMPTY;
  if (column.type === 'bool') return value ? 'Yes' : 'No';
  if (column.numeric && typeof value === 'number') {
    if (column.type === 'integer') return value.toLocaleString();
    if (Math.abs(value) >= 1e7) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  return String(value);
}

function rawValue(column, value) {
  if (value === null || value === undefined) return '';
  if (column.type === 'bool') return value ? 'true' : 'false';
  return String(value);
}

function parseClipboard(text) {
  const body = String(text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  const lines = body.split('\n');
  while (lines.length && lines[lines.length - 1] === '') lines.pop();
  return lines.map((line) => line.split('\t'));
}

/**
 * Excel-like sheet: frozen header, sticky key column, inline edit, range
 * selection, keyboard navigation, copy and multi-cell paste.
 */
export default function WarehouseGrid({
  tab,
  columns,
  rows,
  loading,
  sort,
  order,
  filters,
  onSortChange,
  onFilterChange,
  onCommitEdits,
  onOpenHistory,
  onClearOverride,
  canEdit,
}) {
  const [anchor, setAnchor] = useState(null); // { r, c }
  const [focusCell, setFocusCell] = useState(null); // { r, c } range end
  const [editing, setEditing] = useState(null); // { r, c, value }
  const [widths, setWidths] = useState({});
  const [notice, setNotice] = useState(null);
  const containerRef = useRef(null);
  const editorRef = useRef(null);
  const resizeRef = useRef(null);

  useEffect(() => {
    setAnchor(null);
    setFocusCell(null);
    setEditing(null);
  }, [tab?.id]);

  useEffect(() => {
    if (editing && editorRef.current) editorRef.current.focus();
  }, [editing]);

  useEffect(() => {
    if (!notice) return undefined;
    const timer = setTimeout(() => setNotice(null), 4000);
    return () => clearTimeout(timer);
  }, [notice]);

  const widthOf = useCallback(
    (column) => widths[column.key] || column.width || 140,
    [widths],
  );

  const selection = useMemo(() => {
    if (!anchor) return null;
    const end = focusCell || anchor;
    return {
      r1: Math.min(anchor.r, end.r),
      r2: Math.max(anchor.r, end.r),
      c1: Math.min(anchor.c, end.c),
      c2: Math.max(anchor.c, end.c),
    };
  }, [anchor, focusCell]);

  const inSelection = useCallback(
    (r, c) => selection && r >= selection.r1 && r <= selection.r2 && c >= selection.c1 && c <= selection.c2,
    [selection],
  );

  const editableAt = useCallback(
    (c) => canEdit && !tab?.read_only && columns[c]?.editable,
    [canEdit, columns, tab],
  );

  /* ---------------------------------------------------------------- edit */

  const beginEdit = useCallback(
    (r, c, seed) => {
      if (!editableAt(c)) {
        setNotice(
          columns[c]?.computed
            ? `${columns[c].label} is calculated on the server and cannot be typed into.`
            : 'This sheet is read only.',
        );
        return;
      }
      const column = columns[c];
      setEditing({ r, c, value: seed !== undefined ? seed : rawValue(column, rows[r]?.[column.key]) });
    },
    [columns, editableAt, rows],
  );

  const commitEdit = useCallback(
    async (move = 'down') => {
      if (!editing) return;
      const { r, c, value } = editing;
      const column = columns[c];
      const row = rows[r];
      setEditing(null);
      if (row && column && rawValue(column, row[column.key]) !== value) {
        await onCommitEdits([{ row_id: row.row_id, column: column.key, value }]);
      }
      if (move === 'down') setAnchor({ r: Math.min(r + 1, rows.length - 1), c });
      if (move === 'right') setAnchor({ r, c: Math.min(c + 1, columns.length - 1) });
      setFocusCell(null);
    },
    [columns, editing, onCommitEdits, rows],
  );

  /* ------------------------------------------------------------ clipboard */

  const copySelection = useCallback(
    (event) => {
      if (!selection) return;
      const lines = [];
      for (let r = selection.r1; r <= selection.r2; r += 1) {
        const cells = [];
        for (let c = selection.c1; c <= selection.c2; c += 1) {
          cells.push(rawValue(columns[c], rows[r]?.[columns[c].key]));
        }
        lines.push(cells.join('\t'));
      }
      const payload = lines.join('\n');
      if (event?.clipboardData) {
        event.clipboardData.setData('text/plain', payload);
        event.preventDefault();
      } else if (navigator.clipboard) {
        navigator.clipboard.writeText(payload);
      }
      setNotice(`Copied ${selection.r2 - selection.r1 + 1} x ${selection.c2 - selection.c1 + 1} cells.`);
    },
    [columns, rows, selection],
  );

  const pasteInto = useCallback(
    async (text) => {
      if (!anchor) return;
      const matrix = parseClipboard(text);
      if (!matrix.length) return;
      const edits = [];
      const blocked = new Set();
      matrix.forEach((line, dr) => {
        const r = anchor.r + dr;
        if (r >= rows.length) return;
        line.forEach((cell, dc) => {
          const c = anchor.c + dc;
          if (c >= columns.length) return;
          if (!editableAt(c)) {
            blocked.add(columns[c].label);
            return;
          }
          edits.push({ row_id: rows[r].row_id, column: columns[c].key, value: cell });
        });
      });
      if (!edits.length) {
        setNotice('Nothing pasted: the target columns are calculated or read only.');
        return;
      }
      await onCommitEdits(edits);
      setNotice(
        blocked.size
          ? `Pasted ${edits.length} cells. Skipped calculated columns: ${[...blocked].join(', ')}.`
          : `Pasted ${edits.length} cells.`,
      );
    },
    [anchor, columns, editableAt, onCommitEdits, rows],
  );

  const fillDown = useCallback(async () => {
    if (!selection || selection.r1 === selection.r2) return;
    const edits = [];
    for (let c = selection.c1; c <= selection.c2; c += 1) {
      if (!editableAt(c)) continue;
      const seed = rawValue(columns[c], rows[selection.r1]?.[columns[c].key]);
      for (let r = selection.r1 + 1; r <= selection.r2; r += 1) {
        edits.push({ row_id: rows[r].row_id, column: columns[c].key, value: seed });
      }
    }
    if (!edits.length) {
      setNotice('Nothing to fill: the selected columns are calculated or read only.');
      return;
    }
    await onCommitEdits(edits);
    setNotice(`Filled ${edits.length} cells from the top row.`);
  }, [columns, editableAt, onCommitEdits, rows, selection]);

  /* -------------------------------------------------------------- keyboard */

  const handleKeyDown = useCallback(
    (event) => {
      if (editing) {
        if (event.key === 'Escape') {
          event.preventDefault();
          setEditing(null);
        } else if (event.key === 'Enter') {
          event.preventDefault();
          commitEdit('down');
        } else if (event.key === 'Tab') {
          event.preventDefault();
          commitEdit('right');
        }
        return;
      }
      if (!anchor) return;
      const { r, c } = anchor;
      const maxR = rows.length - 1;
      const maxC = columns.length - 1;
      const move = (nr, nc) => {
        event.preventDefault();
        const next = { r: Math.max(0, Math.min(nr, maxR)), c: Math.max(0, Math.min(nc, maxC)) };
        if (event.shiftKey) setFocusCell(next);
        else {
          setAnchor(next);
          setFocusCell(null);
        }
      };

      switch (event.key) {
        case 'ArrowDown':
          return move((event.shiftKey ? focusCell?.r ?? r : r) + 1, event.shiftKey ? focusCell?.c ?? c : c);
        case 'ArrowUp':
          return move((event.shiftKey ? focusCell?.r ?? r : r) - 1, event.shiftKey ? focusCell?.c ?? c : c);
        case 'ArrowLeft':
          return move(event.shiftKey ? focusCell?.r ?? r : r, (event.shiftKey ? focusCell?.c ?? c : c) - 1);
        case 'ArrowRight':
          return move(event.shiftKey ? focusCell?.r ?? r : r, (event.shiftKey ? focusCell?.c ?? c : c) + 1);
        case 'Tab':
          return move(r, c + (event.shiftKey ? -1 : 1));
        case 'Enter':
          event.preventDefault();
          return beginEdit(r, c);
        case 'Backspace':
        case 'Delete':
          event.preventDefault();
          if (editableAt(c)) onCommitEdits([{ row_id: rows[r].row_id, column: columns[c].key, value: '' }]);
          return undefined;
        default:
          break;
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'd') {
        event.preventDefault();
        fillDown();
        return undefined;
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'c') {
        copySelection(null);
        return undefined;
      }
      if (!event.metaKey && !event.ctrlKey && event.key.length === 1) {
        beginEdit(r, c, event.key);
      }
      return undefined;
    },
    [anchor, beginEdit, columns, commitEdit, copySelection, editableAt, editing, fillDown, focusCell, onCommitEdits, rows],
  );

  /* --------------------------------------------------------------- resize */

  useEffect(() => {
    const onMove = (event) => {
      if (!resizeRef.current) return;
      const { key, startX, startWidth } = resizeRef.current;
      const next = Math.max(70, startWidth + (event.clientX - startX));
      setWidths((prev) => ({ ...prev, [key]: next }));
    };
    const onUp = () => {
      resizeRef.current = null;
    };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  const startResize = (event, column) => {
    event.preventDefault();
    event.stopPropagation();
    resizeRef.current = { key: column.key, startX: event.clientX, startWidth: widthOf(column) };
  };

  /* ----------------------------------------------------------------- view */

  const keyColumns = new Set(tab?.key || []);

  return (
    <div className="wh-grid-wrap">
      {notice ? <div className="wh-notice">{notice}</div> : null}
      <div
        ref={containerRef}
        className="wh-grid"
        tabIndex={0}
        role="grid"
        onKeyDown={handleKeyDown}
        onCopy={copySelection}
        onPaste={(event) => {
          if (editing) return;
          const text = event.clipboardData?.getData('text/plain');
          if (text) {
            event.preventDefault();
            pasteInto(text);
          }
        }}
      >
        <table>
          <thead>
            <tr>
              <th className="wh-gutter" style={{ width: 54 }}>
                #
              </th>
              {columns.map((column, index) => (
                <th
                  key={column.key}
                  className={[
                    index === 0 ? 'wh-sticky-col' : '',
                    keyColumns.has(column.key) ? 'is-key' : '',
                    column.computed ? 'is-computed' : '',
                    sort === column.key ? 'is-sorted' : '',
                  ].join(' ')}
                  style={{ width: widthOf(column), minWidth: widthOf(column), left: index === 0 ? 54 : undefined }}
                  onClick={() => onSortChange(column.key)}
                  title={column.help || column.label}
                >
                  <span className="wh-th-label">
                    {column.label}
                    {column.computed ? <Lock size={11} className="wh-th-icon" /> : null}
                    {sort === column.key ? <em>{order === 'desc' ? '▼' : '▲'}</em> : null}
                  </span>
                  <span className="wh-resize" onMouseDown={(event) => startResize(event, column)} />
                </th>
              ))}
            </tr>
            <tr className="wh-filter-row">
              <th className="wh-gutter" style={{ width: 54 }} />
              {columns.map((column, index) => (
                <th
                  key={`f-${column.key}`}
                  className={index === 0 ? 'wh-sticky-col' : ''}
                  style={{ left: index === 0 ? 54 : undefined }}
                >
                  <input
                    value={filters?.[column.key]?.value ?? ''}
                    placeholder="filter"
                    onChange={(event) => onFilterChange(column.key, event.target.value)}
                  />
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, r) => {
              const overridden = new Set(row?._meta?.overridden || []);
              return (
                <tr key={row.row_id || r} className={anchor?.r === r ? 'is-active-row' : ''}>
                  <td className="wh-gutter">
                    <span>{r + 1}</span>
                    <button
                      type="button"
                      className="wh-row-history"
                      title="Version history"
                      onClick={() => onOpenHistory(row)}
                    >
                      <History size={12} />
                    </button>
                  </td>
                  {columns.map((column, c) => {
                    const isEditing = editing?.r === r && editing?.c === c;
                    const isOverridden = overridden.has(column.key);
                    return (
                      <td
                        key={column.key}
                        className={[
                          c === 0 ? 'wh-sticky-col' : '',
                          column.numeric ? 'is-num' : '',
                          column.computed ? 'is-computed' : '',
                          inSelection(r, c) ? 'is-selected' : '',
                          anchor?.r === r && anchor?.c === c ? 'is-anchor' : '',
                          isOverridden ? 'is-overridden' : '',
                        ].join(' ')}
                        style={{ width: widthOf(column), minWidth: widthOf(column), left: c === 0 ? 54 : undefined }}
                        onMouseDown={(event) => {
                          if (event.shiftKey && anchor) setFocusCell({ r, c });
                          else {
                            setAnchor({ r, c });
                            setFocusCell(null);
                          }
                          containerRef.current?.focus();
                        }}
                        onDoubleClick={() => beginEdit(r, c)}
                        title={
                          isOverridden
                            ? `Admin override by ${row._meta.override_detail?.[column.key]?.actor || 'admin'}`
                            : undefined
                        }
                      >
                        {isEditing ? (
                          <input
                            ref={editorRef}
                            className="wh-editor"
                            value={editing.value}
                            onChange={(event) => setEditing({ ...editing, value: event.target.value })}
                            onBlur={() => commitEdit(null)}
                          />
                        ) : (
                          <>
                            <span className="wh-cell-text">{formatValue(column, row[column.key])}</span>
                            {isOverridden ? (
                              <button
                                type="button"
                                className="wh-revert"
                                title="Revert to the imported value"
                                onClick={(event) => {
                                  event.stopPropagation();
                                  onClearOverride(row.row_id, column.key);
                                }}
                              >
                                <RotateCcw size={10} />
                              </button>
                            ) : null}
                          </>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
            {!rows.length && !loading ? (
              <tr>
                <td className="wh-empty" colSpan={columns.length + 1}>
                  No rows yet. Run a refresh or import a sheet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
        {loading ? <div className="wh-grid-loading">Loading…</div> : null}
      </div>
      <div className="wh-grid-hint">
        <PenLine size={11} />
        <span>
          Double-click or press Enter to edit · Shift+arrows to select a range · Ctrl/Cmd+C copy ·
          Ctrl/Cmd+V paste from Excel · Ctrl/Cmd+D fill down · calculated columns are locked
        </span>
      </div>
    </div>
  );
}
