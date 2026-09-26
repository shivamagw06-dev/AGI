import { useState } from 'react';
import { importNewsletterCsv } from '@/lib/publishingApi';
import { Button } from '@/components/ui/button';

const SAMPLE = `email,first_name,last_name,tags
alpha@example.com,Ada,Lovelace,macro|research
beta@example.com,Alan,Turing,forecast
not-an-email,Bad,Row,
alpha@example.com,Dup,User,linkedin`;

export default function NewsletterImport() {
  const [csvText, setCsvText] = useState(SAMPLE);
  const [source, setSource] = useState('LinkedIn Campaign July 2026');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function run(previewOnly) {
    setBusy(true);
    setError('');
    try {
      const data = await importNewsletterCsv({
        csv_text: csvText,
        source: source || 'csv_upload',
        filename: 'manual-import.csv',
        preview_only: previewOnly,
        dry_run: previewOnly,
      });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold">Import CSV</h1>
        <p className="text-sm text-slate-500 mt-1">Validate emails, skip invalid, detect duplicates, preview before import.</p>
      </div>

      <label className="block text-sm">
        Import source label
        <input className="mt-1 w-full border rounded-lg px-3 py-2" value={source} onChange={(e) => setSource(e.target.value)} />
      </label>

      <textarea
        className="w-full min-h-[200px] border rounded-xl px-3 py-2 font-mono text-xs"
        value={csvText}
        onChange={(e) => setCsvText(e.target.value)}
      />

      <div className="flex gap-2">
        <Button variant="outline" disabled={busy} onClick={() => run(true)}>Preview</Button>
        <Button className="bg-blue-700 hover:bg-blue-800" disabled={busy} onClick={() => run(false)}>
          {busy ? 'Working…' : 'Import'}
        </Button>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {result && (
        <div className="bg-white border rounded-xl p-4 space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div><p className="text-xs text-slate-400">Imported</p><p className="text-xl font-semibold">{result.imported}</p></div>
            <div><p className="text-xs text-slate-400">Skipped</p><p className="text-xl font-semibold">{result.skipped}</p></div>
            <div><p className="text-xs text-slate-400">Duplicates</p><p className="text-xl font-semibold">{result.duplicates}</p></div>
            <div><p className="text-xs text-slate-400">Errors</p><p className="text-xl font-semibold">{result.errors}</p></div>
          </div>
          <div className="max-h-64 overflow-auto text-xs border rounded-lg">
            <table className="w-full">
              <thead className="bg-slate-50 sticky top-0"><tr><th className="text-left p-2">Line</th><th className="text-left p-2">Email</th><th className="text-left p-2">Status</th><th className="text-left p-2">Reason</th></tr></thead>
              <tbody>
                {(result.preview || []).map((p, idx) => (
                  <tr key={`${p.line}-${idx}`} className="border-t">
                    <td className="p-2">{p.line}</td>
                    <td className="p-2">{p.email}</td>
                    <td className="p-2">{p.status}</td>
                    <td className="p-2 text-slate-500">{p.reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
