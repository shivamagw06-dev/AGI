import { useEffect, useState } from 'react';
import { Plus, RefreshCw, Save, Trash2 } from 'lucide-react';
import {
  addFounderTransaction,
  addFounderTransactions,
  getFounderPortfolioAdmin,
  removeFounderDisclosure,
  saveFounderDisclosure,
  saveFounderPortfolioSettings,
} from '@/lib/founderPortfolio';

const emptyDisclosure = {
  id: '', symbol: '', asset_name: '', asset_type: 'indian_stock', market: 'NSE', country: 'India', provider_key: '',
  currency: 'INR', public_weight: '', return_pct: '', conviction: 'Core', status: 'Holding', sector: '',
  entry_month: '', thesis: '', change_note: '', source: 'manual_disclosure', is_published: false,
};
const emptyTransaction = {
  trade_date: new Date().toISOString().slice(0, 10), symbol: '', asset_name: '', asset_type: 'indian_stock',
  market: 'NSE', currency: 'INR', provider_key: '', action: 'buy', quantity: '', price: '', fees: 0, notes: '',
};

const inputClass = 'w-full rounded border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900';

function numericOrNull(value) {
  return value === '' || value == null ? null : Number(value);
}

function parseCsvLine(line) {
  const cells = []; let value = ''; let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"' && line[i + 1] === '"' && quoted) { value += '"'; i += 1; }
    else if (char === '"') quoted = !quoted;
    else if (char === ',' && !quoted) { cells.push(value.trim()); value = ''; }
    else value += char;
  }
  cells.push(value.trim());
  return cells;
}

export default function FounderPortfolioAdmin() {
  const [state, setState] = useState({ settings: null, disclosures: [], transactions: [], reports: [] });
  const [disclosure, setDisclosure] = useState(emptyDisclosure);
  const [transaction, setTransaction] = useState(emptyTransaction);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const downloadTemplate = () => {
    const header = 'trade_date,symbol,asset_name,asset_type,market,currency,provider_key,action,quantity,price,fees,notes';
    const sample = '2026-08-26,RELIANCE,Reliance Industries,indian_stock,NSE,INR,NSE_EQ|INE002A01018,buy,10,1450,0,Initial position';
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([`${header}\n${sample}\n`], { type: 'text/csv' }));
    link.download = 'founder-portfolio-transactions.csv'; link.click(); URL.revokeObjectURL(link.href);
  };

  const importCsv = async (event) => {
    const file = event.target.files?.[0]; if (!file) return;
    setBusy(true);
    try {
      const lines = (await file.text()).split(/\r?\n/).filter((line) => line.trim());
      const headers = parseCsvLine(lines.shift()).map((item) => item.trim());
      const required = ['trade_date', 'symbol', 'asset_name', 'asset_type', 'currency', 'action', 'quantity', 'price'];
      if (required.some((key) => !headers.includes(key))) throw new Error(`CSV is missing required columns: ${required.join(', ')}`);
      const rows = lines.map((line) => Object.fromEntries(headers.map((key, index) => [key, parseCsvLine(line)[index] ?? '']))).map((row) => ({
        ...row, symbol: row.symbol.toUpperCase(), quantity: Number(row.quantity), price: Number(row.price), fees: Number(row.fees || 0), provider_key: row.provider_key || null, notes: row.notes || null,
      }));
      if (rows.some((row) => !Number.isFinite(row.quantity) || !Number.isFinite(row.price))) throw new Error('CSV contains an invalid quantity or price.');
      const saved = await addFounderTransactions(rows);
      setState((current) => ({ ...current, transactions: [...saved, ...current.transactions] }));
      setMessage(`${saved.length} private transactions imported.`);
    } catch (err) { setMessage(err?.message || 'CSV import failed.'); }
    finally { setBusy(false); event.target.value = ''; }
  };

  const load = async () => {
    setBusy(true);
    try { setState(await getFounderPortfolioAdmin()); setMessage(''); }
    catch (err) { setMessage(err?.message || 'Unable to load founder portfolio.'); }
    finally { setBusy(false); }
  };
  useEffect(() => { load(); }, []);

  const settings = state.settings || {
    name: "Founder's Portfolio", launch_date: '', base_currency: 'INR', benchmark: 'Blended benchmark',
    portfolio_return_pct: '', benchmark_return_pct: '', cash_weight_pct: '',
    disclosure_delay: 'After market close', benchmark_components: '^NSEI:60,^GSPC:40', status: 'preparing', last_published_at: null,
  };

  const updateSettings = (key, value) => setState((s) => ({ ...s, settings: { ...settings, [key]: value } }));

  const submitSettings = async () => {
    setBusy(true);
    try {
      const saved = await saveFounderPortfolioSettings({
        ...settings,
        portfolio_return_pct: numericOrNull(settings.portfolio_return_pct),
        benchmark_return_pct: numericOrNull(settings.benchmark_return_pct),
        cash_weight_pct: numericOrNull(settings.cash_weight_pct),
        last_published_at: new Date().toISOString(),
      });
      setState((s) => ({ ...s, settings: saved }));
      setMessage('Portfolio settings published.');
    } catch (err) { setMessage(err?.message || 'Settings could not be saved.'); }
    finally { setBusy(false); }
  };

  const submitDisclosure = async (event) => {
    event.preventDefault(); setBusy(true);
    try {
      const saved = await saveFounderDisclosure({
        ...disclosure,
        public_weight: numericOrNull(disclosure.public_weight),
        return_pct: numericOrNull(disclosure.return_pct),
      });
      setState((s) => ({ ...s, disclosures: [saved, ...s.disclosures.filter((r) => r.id !== saved.id)] }));
      setDisclosure(emptyDisclosure); setMessage('Public disclosure saved.');
    } catch (err) { setMessage(err?.message || 'Disclosure could not be saved.'); }
    finally { setBusy(false); }
  };

  const submitTransaction = async (event) => {
    event.preventDefault(); setBusy(true);
    try {
      const saved = await addFounderTransaction({
        ...transaction,
        quantity: Number(transaction.quantity), price: Number(transaction.price), fees: Number(transaction.fees || 0),
      });
      setState((s) => ({ ...s, transactions: [saved, ...s.transactions] }));
      setTransaction(emptyTransaction); setMessage('Private transaction recorded.');
    } catch (err) { setMessage(err?.message || 'Transaction could not be recorded.'); }
    finally { setBusy(false); }
  };

  const deleteDisclosure = async (id) => {
    if (!window.confirm('Delete this public disclosure?')) return;
    setBusy(true);
    try { await removeFounderDisclosure(id); setState((s) => ({ ...s, disclosures: s.disclosures.filter((r) => r.id !== id) })); }
    catch (err) { setMessage(err?.message || 'Disclosure could not be deleted.'); }
    finally { setBusy(false); }
  };

  const fields = (model, setter) => (key) => ({ value: model[key] ?? '', onChange: (e) => setter((s) => ({ ...s, [key]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })) });
  const d = fields(disclosure, setDisclosure); const t = fields(transaction, setTransaction);

  return (
    <div className="min-h-screen bg-slate-100 p-6 text-slate-900">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center justify-between">
          <div><p className="text-xs font-bold tracking-[.2em] text-emerald-700">PRIVATE ADMIN</p><h1 className="text-3xl font-semibold">Founder Portfolio Manager</h1><p className="mt-1 text-sm text-slate-600">Private transactions and public disclosures are stored separately.</p></div>
          <button onClick={load} disabled={busy} className="flex items-center gap-2 rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white"><RefreshCw size={16} /> Refresh</button>
        </div>
        {message ? <div className="mb-5 rounded border border-amber-200 bg-amber-50 p-3 text-sm">{message}</div> : null}

        <section className="mb-6 rounded-lg border border-sky-200 bg-sky-50 p-5 shadow-sm">
          <h2 className="text-lg font-semibold">Bulk transaction import</h2>
          <p className="mt-1 text-sm text-slate-600">Import Indian stocks, US stocks, mutual funds, ETFs, cash flows, dividends and fees into the private ledger.</p>
          <div className="mt-4 flex flex-wrap gap-3">
            <button type="button" onClick={downloadTemplate} className="rounded border border-slate-300 bg-white px-4 py-2 text-sm font-semibold">Download CSV template</button>
            <label className="cursor-pointer rounded bg-sky-700 px-4 py-2 text-sm font-semibold text-white">Import CSV<input type="file" accept=".csv,text/csv" className="hidden" onChange={importCsv} disabled={busy} /></label>
          </div>
        </section>

        <section className="mb-6 rounded-lg bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold">Public portfolio settings</h2>
          <div className="grid gap-3 md:grid-cols-4">
            <label className="text-xs font-semibold">Launch date<input type="date" className={inputClass} value={settings.launch_date || ''} onChange={(e) => updateSettings('launch_date', e.target.value)} /></label>
            <label className="text-xs font-semibold">Benchmark<input className={inputClass} value={settings.benchmark || ''} onChange={(e) => updateSettings('benchmark', e.target.value)} /></label>
            <label className="text-xs font-semibold">Benchmark components<input className={inputClass} value={settings.benchmark_components || ''} onChange={(e) => updateSettings('benchmark_components', e.target.value)} placeholder="^NSEI:60,^GSPC:40" /></label>
            <label className="text-xs font-semibold">Portfolio return %<input type="number" step="0.01" className={inputClass} value={settings.portfolio_return_pct ?? ''} onChange={(e) => updateSettings('portfolio_return_pct', e.target.value)} /></label>
            <label className="text-xs font-semibold">Benchmark return %<input type="number" step="0.01" className={inputClass} value={settings.benchmark_return_pct ?? ''} onChange={(e) => updateSettings('benchmark_return_pct', e.target.value)} /></label>
          </div>
          <button onClick={submitSettings} disabled={busy} className="mt-4 flex items-center gap-2 rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white"><Save size={16} /> Publish settings</button>
        </section>

        <div className="grid gap-6 xl:grid-cols-2">
          <form onSubmit={submitTransaction} className="rounded-lg bg-white p-5 shadow-sm">
            <p className="text-xs font-bold tracking-[.15em] text-rose-700">PRIVATE LEDGER</p><h2 className="mb-4 text-xl font-semibold">Record transaction</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs font-semibold">Date<input required type="date" className={inputClass} {...t('trade_date')} /></label>
              <label className="text-xs font-semibold">Action<select className={inputClass} {...t('action')}><option value="buy">Buy</option><option value="sell">Sell</option><option value="dividend">Dividend</option><option value="fee">Fee</option><option value="deposit">Deposit</option><option value="withdrawal">Withdrawal</option></select></label>
              <label className="text-xs font-semibold">Symbol<input required className={inputClass} {...t('symbol')} /></label>
              <label className="text-xs font-semibold">Name<input required className={inputClass} {...t('asset_name')} /></label>
              <label className="text-xs font-semibold">Asset class<select className={inputClass} {...t('asset_type')}><option value="indian_stock">Indian stock</option><option value="us_stock">US stock</option><option value="mutual_fund">Mutual fund</option><option value="etf">ETF</option><option value="cash">Cash</option></select></label>
              <label className="text-xs font-semibold">Market<input className={inputClass} {...t('market')} /></label>
              <label className="text-xs font-semibold">Provider key<input className={inputClass} {...t('provider_key')} placeholder="Upstox instrument key or AMFI code" /></label>
              <label className="text-xs font-semibold">Quantity<input required type="number" step="0.000001" className={inputClass} {...t('quantity')} /></label>
              <label className="text-xs font-semibold">Price<input required type="number" step="0.0001" className={inputClass} {...t('price')} /></label>
            </div>
            <button disabled={busy} className="mt-4 flex items-center gap-2 rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white"><Plus size={16} /> Add private transaction</button>
          </form>

          <form onSubmit={submitDisclosure} className="rounded-lg bg-white p-5 shadow-sm">
            <p className="text-xs font-bold tracking-[.15em] text-emerald-700">PUBLIC SAFE VIEW</p><h2 className="mb-4 text-xl font-semibold">Publish holding</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className="text-xs font-semibold">Symbol<input required className={inputClass} {...d('symbol')} /></label>
              <label className="text-xs font-semibold">Name<input required className={inputClass} {...d('asset_name')} /></label>
              <label className="text-xs font-semibold">Asset class<select className={inputClass} {...d('asset_type')}><option value="indian_stock">Indian stock</option><option value="us_stock">US stock</option><option value="mutual_fund">Mutual fund</option><option value="etf">ETF</option><option value="cash">Cash</option></select></label>
              <label className="text-xs font-semibold">Market<input className={inputClass} {...d('market')} /></label>
              <label className="text-xs font-semibold">Provider key<input className={inputClass} {...d('provider_key')} placeholder="Upstox instrument key or AMFI code" /></label>
              <label className="text-xs font-semibold">Public weight %<input required type="number" step="0.01" className={inputClass} {...d('public_weight')} /></label>
              <label className="text-xs font-semibold">Return %<input type="number" step="0.01" className={inputClass} {...d('return_pct')} /></label>
              <label className="text-xs font-semibold">Conviction<select className={inputClass} {...d('conviction')}><option>Core</option><option>High</option><option>Medium</option><option>Watch</option></select></label>
              <label className="text-xs font-semibold">Entry month<input type="date" className={inputClass} {...d('entry_month')} /></label>
              <label className="text-xs font-semibold sm:col-span-2">Public thesis<textarea rows="3" className={inputClass} {...d('thesis')} /></label>
              <label className="flex items-center gap-2 text-sm font-semibold sm:col-span-2"><input type="checkbox" checked={Boolean(disclosure.is_published)} onChange={(e) => setDisclosure((s) => ({ ...s, is_published: e.target.checked }))} /> Visible to clients</label>
            </div>
            <button disabled={busy} className="mt-4 flex items-center gap-2 rounded bg-emerald-700 px-4 py-2 text-sm font-semibold text-white"><Save size={16} /> Save public disclosure</button>
          </form>
        </div>

        <section className="mt-6 rounded-lg bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-xl font-semibold">Public disclosures</h2>
          <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead><tr className="border-b text-xs uppercase text-slate-500"><th className="p-2">Holding</th><th>Class</th><th>Weight</th><th>Published</th><th>Updated</th><th /></tr></thead><tbody>{state.disclosures.map((row) => <tr key={row.id} className="border-b"><td className="p-2"><button className="font-semibold text-blue-700" onClick={() => setDisclosure({ ...emptyDisclosure, ...row })}>{row.asset_name} ({row.symbol})</button></td><td>{row.asset_type}</td><td>{row.public_weight}%</td><td>{row.is_published ? 'Yes' : 'No'}</td><td>{new Date(row.updated_at).toLocaleString('en-IN')}</td><td><button onClick={() => deleteDisclosure(row.id)} className="text-rose-700" aria-label="Delete"><Trash2 size={16} /></button></td></tr>)}</tbody></table></div>
        </section>

        <section className="mt-6 rounded-lg bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-xl font-semibold">Private transaction history</h2>
          <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead><tr className="border-b text-xs uppercase text-slate-500"><th className="p-2">Date</th><th>Holding</th><th>Action</th><th>Quantity</th><th>Price</th><th>Currency</th></tr></thead><tbody>{state.transactions.map((row) => <tr key={row.id} className="border-b"><td className="p-2">{row.trade_date}</td><td>{row.asset_name} ({row.symbol})</td><td className="uppercase">{row.action}</td><td>{row.quantity}</td><td>{row.price}</td><td>{row.currency}</td></tr>)}</tbody></table></div>
        </section>
        <section className="mt-6 rounded-lg bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-xl font-semibold">Daily validation reports</h2>
          <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead><tr className="border-b text-xs uppercase text-slate-500"><th className="p-2">Run</th><th>Status</th><th>Assets</th><th>Priced</th><th>Snapshot</th><th>Message</th></tr></thead><tbody>{state.reports.map((row) => <tr key={row.id} className="border-b"><td className="p-2">{new Date(row.run_at).toLocaleString('en-IN')}</td><td className={row.status === 'OK' ? 'font-bold text-emerald-700' : 'font-bold text-rose-700'}>{row.status}</td><td>{row.asset_count}</td><td>{row.priced_count}</td><td>{row.snapshot_written ? 'Yes' : 'No'}</td><td>{row.message}</td></tr>)}</tbody></table></div>
        </section>
      </div>
    </div>
  );
}
