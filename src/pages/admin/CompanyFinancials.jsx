import { useEffect, useMemo, useState } from 'react';
import { API_ORIGIN } from '@/config';

const YEARS = Array.from({ length: 11 }, (_, i) => 2016 + i);
const FIELDS = [['Revenue', 'revenue'], ['Gross Profit', 'gross_profit'], ['EBITDA', 'ebitda'], ['EBIT', 'ebit'], ['PBT', 'pbt'], ['PAT', 'pat'], ['EPS', 'eps'], ['Cash & Equivalents', 'cash'], ['Total Current Assets', 'current_assets'], ['Total Assets', 'assets'], ['Total Current Liabilities', 'current_liabilities'], ['Total Debt', 'debt'], ['Total Equity', 'equity'], ['Working Capital', 'working_capital'], ['Cash Flow from Operations', 'cfo'], ['Capital Expenditure', 'capex'], ['Free Cash Flow', 'free_cash_flow'], ['Cash Flow from Investing', 'cfi'], ['Cash Flow from Financing', 'cff']];
const money = (value) => value == null ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });

export default function CompanyFinancials() {
  const [query, setQuery] = useState('TCS');
  const [resolvedSymbol, setResolvedSymbol] = useState('TCS');
  const [year, setYear] = useState(2024);
  const [rows, setRows] = useState([]);
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const text = query.trim();
    if (text.length < 2) { setSuggestions([]); return undefined; }
    const timer = setTimeout(async () => {
      try {
        const response = await fetch(`${API_ORIGIN}/api/intelligence/company/search?q=${encodeURIComponent(text)}`);
        const data = await response.json();
        setSuggestions(response.ok ? data.results || [] : []);
      } catch { setSuggestions([]); }
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  const load = async (identity) => {
    setError(''); setShowSuggestions(false);
    try {
      let company = identity;
      if (!company) {
        const response = await fetch(`${API_ORIGIN}/api/intelligence/company/resolve?q=${encodeURIComponent(query.trim())}`);
        company = await response.json();
        if (!response.ok) throw new Error(company?.error || 'Company not found');
      }
      const response = await fetch(`${API_ORIGIN}/api/intelligence/company/statements/${encodeURIComponent(company.symbol)}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data?.detail || data?.error || 'Request failed');
      setResolvedSymbol(company.symbol);
      setQuery(company.company_name || company.symbol);
      setRows((data.annual || []).filter((entry) => entry.statement_version?.startsWith('capiq_workbook_')));
    } catch (err) { setRows([]); setError(err.message || 'Could not load company financials. Please retry.'); }
  };
  const row = useMemo(() => rows.find((entry) => entry.fiscal_year === `FY${year}`), [rows, year]);

  return <div className="min-h-full bg-slate-50 p-6 text-slate-900"><div className="mx-auto max-w-7xl"><p className="text-xs font-semibold uppercase tracking-[.2em] text-emerald-700">AGI · reported financials</p><h1 className="mt-2 text-3xl font-bold text-slate-950">Company Financials</h1><p className="mt-2 text-slate-600">11-year AGI view · INR million · consolidated annual statements</p><form onSubmit={(event) => { event.preventDefault(); load(); }} className="relative mt-6 flex max-w-xl gap-2"><div className="relative flex-1"><input value={query} onChange={(event) => { setQuery(event.target.value); setShowSuggestions(true); }} onFocus={() => setShowSuggestions(true)} className="w-full rounded border border-slate-300 bg-white px-3 py-2 text-slate-950" placeholder="Company name or ticker — e.g. ICICI Bank" autoComplete="off" />{showSuggestions && suggestions.length > 0 && <div className="absolute z-20 mt-1 w-full overflow-hidden rounded border border-slate-200 bg-white shadow-lg">{suggestions.map((company) => <button type="button" key={company.symbol} onMouseDown={(event) => event.preventDefault()} onClick={() => load(company)} className="flex w-full items-center justify-between px-3 py-2 text-left hover:bg-emerald-50"><span className="font-medium text-slate-900">{company.company_name}</span><span className="ml-4 font-mono text-xs text-emerald-700">{company.symbol}</span></button>)}</div>}</div><button className="rounded bg-emerald-700 px-4 py-2 font-semibold text-white">Load company</button></form>{error && <p className="mt-3 text-red-700">{error}</p>}<div className="mt-6 flex flex-wrap gap-2">{YEARS.map((value) => <button key={value} onClick={() => setYear(value)} className={`rounded px-3 py-2 text-sm font-medium ${year === value ? 'bg-emerald-700 text-white' : 'border border-slate-300 bg-white text-slate-700'}`}>FY{value}</button>)}</div><div className="mt-6 overflow-x-auto rounded border border-slate-200 bg-white"><table className="w-full text-sm"><thead className="bg-slate-900 text-left text-white"><tr><th className="p-3">FY{year} · {resolvedSymbol}</th><th className="p-3">INR million</th></tr></thead><tbody>{FIELDS.map(([label, key]) => <tr key={key} className="border-t border-slate-200"><td className="p-3 font-medium text-slate-800">{label}</td><td className="p-3 font-mono text-slate-950">{money(row?.[key])}</td></tr>)}</tbody></table></div>{row && <p className="mt-3 text-xs text-slate-600">Source: AGI financial warehouse · {row.statement_type}</p>}</div></div>;
}
