import { useCallback, useMemo, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, FileSpreadsheet, Upload, X } from 'lucide-react';
import { commitImport, stageImport } from '@/lib/warehouseApi';

/**
 * Two-step import: stage (parse, auto-map, validate) then commit. Nothing
 * reaches the warehouse until the validation report is on screen and accepted.
 */
export default function ImportDialog({ tab, columns, onClose, onImported }) {
  const [text, setText] = useState('');
  const [staged, setStaged] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [mapping, setMapping] = useState(null);
  const fileRef = useRef(null);

  const columnOptions = useMemo(
    () => columns.filter((c) => c.editable || (tab?.key || []).includes(c.key)),
    [columns, tab],
  );

  const readFile = useCallback((file) => {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result || ''));
    reader.readAsText(file);
  }, []);

  const doStage = useCallback(
    async (overrideMapping) => {
      setBusy(true);
      setError(null);
      try {
        const result = await stageImport(tab.id, {
          text,
          mapping: overrideMapping || undefined,
          source: 'admin_paste',
        });
        if (!result?.ok) throw new Error(result?.error || 'import_failed');
        setStaged(result);
        setMapping(result.mapping?.mapping || {});
      } catch (err) {
        setError(err.message);
      } finally {
        setBusy(false);
      }
    },
    [tab, text],
  );

  const doCommit = useCallback(async () => {
    if (!staged?.import_id) return;
    setBusy(true);
    setError(null);
    try {
      const result = await commitImport(staged.import_id);
      if (!result?.ok) throw new Error(result?.error || 'commit_failed');
      onImported(result);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }, [onClose, onImported, staged]);

  return (
    <div className="wh-modal-backdrop" role="dialog" aria-modal="true">
      <div className="wh-modal wh-modal-wide">
        <header>
          <h2>
            <FileSpreadsheet size={15} /> Import into {tab.label}
          </h2>
          <button type="button" onClick={onClose} aria-label="Close">
            <X size={15} />
          </button>
        </header>

        <div className="wh-modal-body">
          <p className="wh-modal-help">
            Paste straight from Excel, Google Sheets or an AGI data export. The first row must be
            headers — they are mapped onto warehouse columns automatically and every row is
            validated before anything is written.
          </p>

          <div className="wh-import-actions">
            <button type="button" className="wh-btn" onClick={() => fileRef.current?.click()}>
              <Upload size={13} /> Choose CSV / TSV file
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.tsv,.txt"
              hidden
              onChange={(event) => readFile(event.target.files?.[0])}
            />
            <span className="wh-muted">XLSX: save as CSV, or copy the cells and paste below.</span>
          </div>

          <textarea
            className="wh-paste"
            value={text}
            placeholder={`Symbol\tDate\tClose\nRELIANCE\t2026-07-31\t1450.25`}
            onChange={(event) => setText(event.target.value)}
            rows={8}
          />

          {staged ? (
            <div className="wh-import-report">
              <div className="wh-import-counts">
                <span className="ok">
                  <CheckCircle2 size={13} /> {staged.accepted} accepted
                </span>
                <span className={staged.rejected ? 'bad' : ''}>
                  <AlertTriangle size={13} /> {staged.rejected} rejected
                </span>
                <span>{staged.duplicates} duplicate keys</span>
                <span>{staged.warnings?.length || 0} warnings</span>
              </div>

              {mapping ? (
                <div className="wh-mapping">
                  <h3>Column mapping</h3>
                  <div className="wh-mapping-grid">
                    {Object.entries(mapping).map(([header, target]) => (
                      <label key={header} className={target ? '' : 'is-unmapped'}>
                        <span>{header}</span>
                        <select
                          value={target || ''}
                          onChange={(event) => {
                            const next = { ...mapping, [header]: event.target.value || null };
                            setMapping(next);
                            doStage(next);
                          }}
                        >
                          <option value="">— ignore —</option>
                          {columnOptions.map((column) => (
                            <option key={column.key} value={column.key}>
                              {column.label}
                            </option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </div>
                </div>
              ) : null}

              {staged.rejections?.length ? (
                <div className="wh-rejections">
                  <h3>Rejected rows</h3>
                  <ul>
                    {staged.rejections.slice(0, 12).map((entry) => (
                      <li key={`${entry.index}`}>
                        <strong>Row {entry.index + 1}</strong>{' '}
                        {entry.issues.map((issue) => issue.message).join('; ')}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {staged.preview?.length ? (
                <div className="wh-preview">
                  <h3>Preview</h3>
                  <table>
                    <thead>
                      <tr>
                        {Object.keys(staged.preview[0]).map((key) => (
                          <th key={key}>{key}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {staged.preview.slice(0, 8).map((row, index) => (
                        <tr key={index}>
                          {Object.keys(staged.preview[0]).map((key) => (
                            <td key={key}>{String(row[key] ?? '')}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </div>
          ) : null}

          {error ? <div className="wh-error">{error}</div> : null}
        </div>

        <footer>
          <button type="button" className="wh-btn" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="wh-btn" disabled={!text.trim() || busy} onClick={() => doStage(null)}>
            {busy ? 'Validating…' : 'Validate'}
          </button>
          <button
            type="button"
            className="wh-btn wh-btn-primary"
            disabled={!staged?.accepted || busy}
            onClick={doCommit}
          >
            Commit {staged?.accepted ? `${staged.accepted} rows` : ''}
          </button>
        </footer>
      </div>
    </div>
  );
}
