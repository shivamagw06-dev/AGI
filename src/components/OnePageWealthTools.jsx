// src/components/WealthManagementFull.jsx
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { supabase } from "@/lib/supabaseClient";
import { jsPDF } from "jspdf";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as ReTooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";

/*
WealthManagementFull.jsx — CA-oriented enhancements (final)

Features:
- Tax Assistant (old/new comparison)
- Tax Saving Recommendations engine (collapsible, auto-open on run)
- Visual: Pie + Bar charts for deductions & recommendations
- CSV imports: transactions, TDS, bank (demo)
- Export ITR JSON + tax PDF
- Client-side demo only — move tax engine + PII to server for production
*/

const FY_SLABS = {
  "2024-25": {
    old: [
      { upTo: 250000, rate: 0 },
      { upTo: 500000, rate: 0.05 },
      { upTo: 1000000, rate: 0.2 },
      { upTo: Infinity, rate: 0.3 },
    ],
    new: [
      { upTo: 300000, rate: 0 },
      { upTo: 600000, rate: 0.05 },
      { upTo: 900000, rate: 0.1 },
      { upTo: 1200000, rate: 0.15 },
      { upTo: 1500000, rate: 0.2 },
      { upTo: Infinity, rate: 0.3 },
    ],
    rebate87A: { old: { threshold: 500000, amount: 12500 }, new: { threshold: 700000, amount: 25000 } },
  },
  "2025-26": {
    old: [
      { upTo: 250000, rate: 0 },
      { upTo: 500000, rate: 0.05 },
      { upTo: 1000000, rate: 0.2 },
      { upTo: Infinity, rate: 0.3 },
    ],
    new: [
      { upTo: 400000, rate: 0 },
      { upTo: 800000, rate: 0.05 },
      { upTo: 1200000, rate: 0.1 },
      { upTo: 1600000, rate: 0.15 },
      { upTo: 2000000, rate: 0.2 },
      { upTo: Infinity, rate: 0.3 },
    ],
    rebate87A: { old: { threshold: 500000, amount: 12500 }, new: { threshold: 1200000, amount: 60000 } },
  },
};

function saveLS(key, val) {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    // ignore
  }
}
function loadLS(key, fallback) {
  try {
    const v = localStorage.getItem(key);
    return v ? JSON.parse(v) : fallback;
  } catch (e) {
    return fallback;
  }
}

/* ---------- helpers ---------- */
function calcTaxFromSlabs(taxableIncome, slabs) {
  let remaining = taxableIncome;
  let tax = 0;
  let lower = 0;
  for (const slab of slabs) {
    const limit = slab.upTo - lower;
    const amount = Math.min(remaining, limit);
    if (amount <= 0) break;
    tax += amount * slab.rate;
    remaining -= amount;
    lower = slab.upTo;
  }
  return Math.max(0, tax);
}
function calcTaxWithSurchargeAndCess(taxableIncome, slabs, opts = {}) {
  const rebateCfg = opts.rebate87A || { threshold: 0, amount: 0 };
  const taxBefore = calcTaxFromSlabs(taxableIncome, slabs);

  const surchargeBands = opts.surchargeBands || [
    { threshold: 5000000, rate: 0.1 },
    { threshold: 10000000, rate: 0.15 },
    { threshold: 20000000, rate: 0.25 },
    { threshold: 50000000, rate: 0.37 },
  ];
  let surcharge = 0;
  for (let i = surchargeBands.length - 1; i >= 0; i--) {
    const b = surchargeBands[i];
    if (taxableIncome > b.threshold) {
      surcharge = taxBefore * b.rate;
      break;
    }
  }

  let rebate = 0;
  if (rebateCfg && taxableIncome <= (rebateCfg.threshold || 0)) {
    rebate = Math.min(rebateCfg.amount || 0, Math.round(taxBefore + surcharge));
  }

  const taxAfter = Math.max(0, taxBefore + surcharge - rebate);
  const cess = taxAfter * 0.04;
  const totalTax = Math.round(taxAfter + cess);

  return {
    taxBefore: Math.round(taxBefore),
    surcharge: Math.round(surcharge),
    rebate: Math.round(rebate),
    cess: Math.round(cess),
    totalTax,
  };
}

// CSV parsers (very simple / demo)
function parseTransactionsCSV(text) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const rows = [];
  for (const ln of lines) {
    const parts = ln.split(",").map((p) => p.trim());
    if (parts.length < 5) continue;
    const [date, symbol, type, qtyStr, priceStr] = parts;
    const qty = Number(qtyStr || 0);
    const price = Number(priceStr || 0);
    rows.push({ date, symbol: (symbol || "").toUpperCase(), type: (type || "").toUpperCase(), qty, price });
  }
  return rows;
}
function computeRealizedGainsFromTransactions(rows) {
  const buyQueues = {};
  let realized = 0;
  for (const r of rows) {
    if (r.type === "BUY") {
      buyQueues[r.symbol] = buyQueues[r.symbol] || [];
      buyQueues[r.symbol].push({ qty: r.qty, price: r.price });
    } else if (r.type === "SELL") {
      let remaining = r.qty;
      const q = buyQueues[r.symbol] || [];
      while (remaining > 0 && q.length) {
        const lot = q[0];
        const take = Math.min(lot.qty, remaining);
        realized += take * (r.price - lot.price);
        lot.qty -= take;
        remaining -= take;
        if (lot.qty === 0) q.shift();
      }
    }
  }
  return Math.max(0, Math.round(realized));
}

function parseTDSCSV(text) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const rows = [];
  for (const ln of lines) {
    const parts = ln.split(",").map((p) => p.trim());
    if (parts.length < 3) continue;
    const deductor = parts[0] || "";
    const section = parts[1] || "";
    const amount = Number(parts[2] || 0);
    const date = parts[3] || "";
    const pan = parts[4] || "";
    rows.push({ deductor, section, amount, date, pan });
  }
  return rows;
}

function parseBankCSV(text) {
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const rows = [];
  for (const ln of lines) {
    const parts = ln.split(",").map((p) => p.trim());
    if (parts.length < 4) continue;
    const [date, desc, amtStr, type] = parts;
    const amount = Number(amtStr || 0);
    rows.push({ date, desc, amount, type: (type || "CREDIT").toUpperCase() });
  }
  return rows;
}

/* ---------- Component ---------- */
export default function WealthManagementFull({ section = "Wealth Management" }) {
  // Portfolio
  const [holdings, setHoldings] = useState(() =>
    loadLS("wm_holdings", [
      { id: 1, type: "equity", symbol: "RELIANCE", qty: 10, avgPrice: 2300, currentPrice: 2254.06, goalId: null },
      { id: 2, type: "mf", symbol: "HDFC_ELSS", qty: 50, avgPrice: 120, currentPrice: 122.16, goalId: 1 },
    ])
  );
  const [goals, setGoals] = useState(() => loadLS("wm_goals", [{ id: 1, name: "Emergency Fund", target: 200000, current: 40000, monthlySIP: 5000, expectedReturnPct: 0.06 }]));
  const [alerts, setAlerts] = useState(() => loadLS("wm_alerts", []));
  const [activePanel, setActivePanel] = useState(() => loadLS("wm_activePanel", "overview"));
  const [articles, setArticles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [csvError, setCsvError] = useState("");

  // CA-focused
  const [transactionsRows, setTransactionsRows] = useState(() => loadLS("wm_transactionsRows", []));
  const [transactionsPreview, setTransactionsPreview] = useState(null);

  const [tdsEntries, setTdsEntries] = useState(() => loadLS("wm_tdsEntries", []));
  const [tdsReconciliation, setTdsReconciliation] = useState(null);

  const [bankRows, setBankRows] = useState(() => loadLS("wm_bankRows", []));
  const [bankReconciliation, setBankReconciliation] = useState(null);

  const [auditLog, setAuditLog] = useState(() => loadLS("wm_auditLog", []));

  // tax form
  const [incomeForm, setIncomeForm] = useState(() =>
    loadLS("wm_incomeForm", {
      preset: "custom",
      fy: "2025-26",
      ageGroup: "0-60",
      salary: 0,
      exemptAllowances: 0,
      interestIncome: 0,
      dividendIncome: 0,
      rentalIncome: 0,
      digitalIncome: 0,
      otherIncome: 0,
      homeLoanInterestSelf: 0,
      homeLoanInterestLetOut: 0,
      tdsPaid: 0,
      includeCapitalGains: false,
      useTransactionsCSV: false,
      deductions: {},
    })
  );
  const [taxComparison, setTaxComparison] = useState(null);

  // recommendations
  const [recommendations, setRecommendations] = useState([]);
  const [showRecommendations, setShowRecommendations] = useState(false);

  // validation & UI hints
  const [validation, setValidation] = useState({}); // { field: { severity: 'warn'|'error', message: '' } }

  // persisting
  useEffect(() => saveLS("wm_holdings", holdings), [holdings]);
  useEffect(() => saveLS("wm_goals", goals), [goals]);
  useEffect(() => saveLS("wm_alerts", alerts), [alerts]);
  useEffect(() => saveLS("wm_activePanel", activePanel), [activePanel]);
  useEffect(() => saveLS("wm_incomeForm", incomeForm), [incomeForm]);
  useEffect(() => saveLS("wm_transactionsRows", transactionsRows), [transactionsRows]);
  useEffect(() => saveLS("wm_tdsEntries", tdsEntries), [tdsEntries]);
  useEffect(() => saveLS("wm_bankRows", bankRows), [bankRows]);
  useEffect(() => saveLS("wm_auditLog", auditLog), [auditLog]);

  useEffect(() => {
    // load articles non-blocking
    supabase
      .from("articles")
      .select("title, slug, excerpt, cover_url, tags, published_at")
      .eq("section", section)
      .eq("status", "published")
      .order("published_at", { ascending: false })
      .then(({ data, error }) => {
        if (!error) setArticles(data || []);
        else setArticles([]);
      });
  }, [section]);

  // derived
  const invested = useMemo(() => holdings.reduce((s, h) => s + (h.avgPrice || 0) * (h.qty || 0), 0), [holdings]);
  const portfolioValue = useMemo(() => holdings.reduce((s, h) => s + (h.currentPrice || h.avgPrice || 0) * (h.qty || 0), 0), [holdings]);
  const unrealizedPL = useMemo(() => portfolioValue - invested, [portfolioValue, invested]);

  /* ---------- helpers ---------- */
  function pushAudit(entry) {
    const e = { id: Date.now(), ts: new Date().toISOString(), ...entry };
    setAuditLog((p) => [e, ...p].slice(0, 500));
  }
  function pushAlert(payload) {
    const a = { id: Date.now(), seen: false, created_at: Date.now(), ...payload };
    setAlerts((prev) => [a, ...prev].slice(0, 200));
  }
  function dismissAlert(id) {
    setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, seen: true } : a)));
  }

  function fieldClassFor(name) {
    const v = validation[name];
    if (!v) return "";
    if (v.severity === "error") return "border-red-500";
    if (v.severity === "warn") return "border-yellow-400";
    return "";
  }

  function validateAll() {
    const v = {};
    // 80C warning
    const eightyC = Number((incomeForm.deductions && incomeForm.deductions["80C"]) || 0);
    if (eightyC > 150000) {
      v["80C"] = { severity: "warn", message: "80C exceeds ₹1,50,000 — only ₹1,50,000 is allowed for most deductions." };
    }
    // TDS mismatch if reconcile present
    if (tdsReconciliation && tdsReconciliation.status !== "matched") {
      v["tds_reconcile"] = { severity: "warn", message: `TDS mismatch: declared ₹${tdsReconciliation.declared}, imported ₹${tdsReconciliation.importedSum}` };
    }
    // Bank mismatch
    if (bankReconciliation && bankReconciliation.status !== "ok") {
      v["bank_reconcile"] = { severity: "warn", message: `Bank reconciliation flagged: diff ₹${bankReconciliation.diff}` };
    }
    // basic sanity: negative incomes
    if (Number(incomeForm.salary || 0) < 0) v["salary"] = { severity: "error", message: "Salary cannot be negative" };
    // 80E / 80TTB quick sanity (non-negative)
    const eightyE = Number((incomeForm.deductions && incomeForm.deductions["80E"]) || 0);
    const e80ttb = Number((incomeForm.deductions && incomeForm.deductions["80TTB"]) || 0);
    if (eightyE < 0) v["80E"] = { severity: "error", message: "80E value cannot be negative" };
    if (e80ttb < 0) v["80TTB"] = { severity: "error", message: "80TTB value cannot be negative" };

    setValidation(v);
    return v;
  }

  /* ---------- CSV handlers ---------- */
  async function handleTransactionsUpload(e) {
    const file = e.target?.files?.[0];
    if (!file) return;
    setUploading(true);
    setCsvError("");
    try {
      const text = await file.text();
      const rows = parseTransactionsCSV(text);
      if (!rows.length) throw new Error("No valid rows found. Expect CSV: date,symbol,type(BUY/SELL),qty,price");
      setTransactionsRows(rows);
      setTransactionsPreview(rows.slice(0, 20));
      pushAlert({ type: "success", message: `Loaded ${rows.length} transactions.` });
      pushAudit({ action: "transactions_upload", detail: { rows: rows.length } });
    } catch (err) {
      setCsvError(String(err.message || err));
      pushAudit({ action: "transactions_upload_failed", detail: { error: String(err.message || err) } });
    } finally {
      setUploading(false);
      if (e.target) e.target.value = "";
    }
  }

  async function handleTDSUpload(e) {
    const file = e.target?.files?.[0];
    if (!file) return;
    setUploading(true);
    setCsvError("");
    try {
      const text = await file.text();
      const rows = parseTDSCSV(text);
      if (!rows.length) throw new Error("No valid TDS rows found. Expect CSV: deductor,section,amount[,date,pan]");
      setTdsEntries(rows);
      pushAlert({ type: "success", message: `Imported ${rows.length} TDS entries.` });
      pushAudit({ action: "tds_upload", detail: { rows: rows.length } });
    } catch (err) {
      setCsvError(String(err.message || err));
      pushAudit({ action: "tds_upload_failed", detail: { error: String(err.message || err) } });
    } finally {
      setUploading(false);
      if (e.target) e.target.value = "";
    }
  }

  async function handleBankUpload(e) {
    const file = e.target?.files?.[0];
    if (!file) return;
    setUploading(true);
    setCsvError("");
    try {
      const text = await file.text();
      const rows = parseBankCSV(text);
      if (!rows.length) throw new Error("No valid bank rows found. Expect CSV: date,desc,amount,type");
      setBankRows(rows);
      pushAlert({ type: "success", message: `Imported ${rows.length} bank rows.` });
      pushAudit({ action: "bank_upload", detail: { rows: rows.length } });
    } catch (err) {
      setCsvError(String(err.message || err));
      pushAudit({ action: "bank_upload_failed", detail: { error: String(err.message || err) } });
    } finally {
      setUploading(false);
      if (e.target) e.target.value = "";
    }
  }

  /* ---------- Reconciliations ---------- */
  function reconcileTDS() {
    const importedSum = tdsEntries.reduce((s, r) => s + (Number(r.amount) || 0), 0);
    const declared = Math.round(Number(incomeForm.tdsPaid || 0));
    const diff = Math.round(declared - importedSum);
    const res = { importedSum: Math.round(importedSum), declared, diff, status: diff === 0 ? "matched" : diff > 0 ? "declared_more" : "import_more" };
    setTdsReconciliation(res);
    pushAudit({ action: "tds_reconcile", detail: res });
    pushAlert({ type: "info", message: `TDS reconcile: imported ₹${res.importedSum}, declared ₹${res.declared}, diff ₹${res.diff}` });
    validateAll();
    return res;
  }

  function reconcileBank() {
    const credits = bankRows.filter((r) => r.type === "CREDIT").reduce((s, r) => s + (Number(r.amount) || 0), 0);
    const declaredIncome = Number(incomeForm.salary || 0) + Number(incomeForm.otherIncome || 0) + Number(incomeForm.rentalIncome || 0) + Number(incomeForm.interestIncome || 0) + Number(incomeForm.dividendIncome || 0);
    const diff = Math.round(declaredIncome - credits);
    const res = { credits: Math.round(credits), declaredIncome: Math.round(declaredIncome), diff, status: Math.abs(diff) <= Math.max(1000, 0.01 * (declaredIncome || 1)) ? "ok" : "mismatch" };
    setBankReconciliation(res);
    pushAudit({ action: "bank_reconcile", detail: res });
    pushAlert({ type: "info", message: `Bank reconcile: credits ₹${res.credits}, declared income ₹${res.declaredIncome}, diff ₹${res.diff}` });
    validateAll();
    return res;
  }

  /* ---------- Presets ---------- */
  function applyPreset(preset) {
    if (preset === "salaried") {
      setIncomeForm((f) => ({
        ...f,
        preset: "salaried",
        salary: 1200000,
        exemptAllowances: 100000,
        interestIncome: 20000,
        dividendIncome: 5000,
        rentalIncome: 0,
        digitalIncome: 0,
        otherIncome: 0,
        tdsPaid: 150000,
        includeCapitalGains: false,
        useTransactionsCSV: false,
        deductions: { "80C": 100000, "80D": 0, "80CCD": 0, "80E": 0, "80TTB": 0, "80G": 0 },
      }));
    } else if (preset === "self") {
      setIncomeForm((f) => ({
        ...f,
        preset: "self",
        salary: 0,
        exemptAllowances: 0,
        interestIncome: 50000,
        dividendIncome: 0,
        rentalIncome: 200000,
        digitalIncome: 0,
        otherIncome: 50000,
        tdsPaid: 20000,
        includeCapitalGains: false,
        useTransactionsCSV: false,
        deductions: { "80C": 50000, "80D": 15000, "80CCD": 0, "80E": 0, "80TTB": 0, "80G": 0 },
      }));
    } else {
      setIncomeForm((f) => ({ ...f, preset: "custom" }));
    }
    setTimeout(() => validateAll(), 50);
  }

  /* ---------- Recommendation helpers ---------- */
  // get marginal rate for a given taxable income & regime slab list
  function getMarginalRate(taxableIncome, slabs) {
    for (const slab of slabs) {
      if (taxableIncome <= slab.upTo) return slab.rate;
    }
    // fallback highest rate
    return slabs[slabs.length - 1].rate || 0.3;
  }

  // generate recommendations array based on computed tax result
  function generateRecommendations(result) {
    if (!result) return [];
    const fyCfg = FY_SLABS[result.fy] || FY_SLABS["2025-26"];
    // choose the recommended regime to pick marginal rate (could be refined to show both)
    const regime = result.recommendation || "old";
    const taxableForRate = regime === "old" ? result.old.taxableIncome : result.new.taxableIncome;
    const slabs = regime === "old" ? fyCfg.old : fyCfg.new;
    const marginalRate = getMarginalRate(taxableForRate, slabs);

    // current deduction usage
    const d = result.deductions || {};
    const used80C = Number(d.ded80C || d.ded80C === 0 ? d.ded80C : d.ded80C) || Number(incomeForm.deductions?.["80C"] || 0);
    // but our computeTax stores ded80C as result.deductions.ded80C earlier, account for both:
    const current80C = Number(result.deductions?.ded80C ?? incomeForm.deductions?.["80C"] ?? 0);
    const current80CCD = Number(result.deductions?.ded80CCD ?? incomeForm.deductions?.["80CCD"] ?? 0);
    const current80D = Number(result.deductions?.ded80D ?? incomeForm.deductions?.["80D"] ?? 0);
    const current80G = Number(result.deductions?.ded80G ?? incomeForm.deductions?.["80G"] ?? 0);
    const current80E = Number(result.deductions?.ded80E ?? incomeForm.deductions?.["80E"] ?? 0);
    const current80TTB = Number(result.deductions?.ded80TTB ?? incomeForm.deductions?.["80TTB"] ?? 0);

    // remaining capacity (simple rules):
    const rem80C = Math.max(0, 150000 - current80C);
    const rem80CCD = Math.max(0, 50000 - current80CCD);
    const rem80D = Math.max(0, 100000 - current80D); // generic cap for parent+self combo (simplified)
    const rem80G = Math.max(0, 1000000 - current80G); // very permissive for demo
    const rem80E = Math.max(0, 500000 - current80E); // no fixed limit (demo cap)
    const rem80TTB = Math.max(0, 50000 - current80TTB); // demo cap for seniors

    const suggestions = [];

    if (rem80C > 0) {
      suggestions.push({
        key: "80C",
        name: "80C — ELSS / PPF / EPF / Life",
        description: "Invest in ELSS, PPF, EPF, or life insurance to claim up to ₹1,50,000 under Section 80C.",
        maxInvestable: rem80C,
        estTaxSaved: Math.round(rem80C * marginalRate),
        learnMore: "#",
      });
    }

    if (rem80CCD > 0) {
      suggestions.push({
        key: "80CCD",
        name: "80CCD(1B) — NPS top-up",
        description: "Contribute to NPS under 80CCD(1B) for an additional deduction (max ₹50,000).",
        maxInvestable: rem80CCD,
        estTaxSaved: Math.round(rem80CCD * marginalRate),
        learnMore: "#",
      });
    }

    if (rem80D > 0) {
      suggestions.push({
        key: "80D",
        name: "80D — Health insurance premium",
        description: "Pay or increase family/parent health insurance premiums to claim deduction under 80D.",
        maxInvestable: Math.min(rem80D, 30000), // suggest reasonable chunk
        estTaxSaved: Math.round(Math.min(rem80D, 30000) * marginalRate),
        learnMore: "#",
      });
    }

    if (rem80G > 0) {
      suggestions.push({
        key: "80G",
        name: "80G — Donations",
        description: "Donate to approved institutions; eligible donations can be 50% or 100% deductible depending on the institution.",
        maxInvestable: Math.min(rem80G, 50000),
        estTaxSaved: Math.round(Math.min(rem80G, 50000) * marginalRate * 0.5), // conservative 50% eligible assumption
        learnMore: "#",
      });
    }

    if (rem80E > 0 && current80E === 0 && Number(incomeForm.otherIncome || 0) > 0) {
      suggestions.push({
        key: "80E",
        name: "80E — Education loan interest",
        description: "If you're paying education loan interest, claim deduction under 80E for the interest component.",
        maxInvestable: Math.min(rem80E, 200000),
        estTaxSaved: Math.round(Math.min(rem80E, 200000) * marginalRate),
        learnMore: "#",
      });
    }

    // 80TTB for senior citizens (only show if age group indicates)
    if ((incomeForm.ageGroup === "60-80" || incomeForm.ageGroup === "80+") && rem80TTB > 0) {
      suggestions.push({
        key: "80TTB",
        name: "80TTB — Senior citizen deposit interest",
        description: "Senior citizens can claim deduction on interest from deposits under 80TTB (up to limit).",
        maxInvestable: rem80TTB,
        estTaxSaved: Math.round(rem80TTB * marginalRate),
        learnMore: "#",
      });
    }

    // If no suggestions (all utilised) provide a friendly message
    if (suggestions.length === 0) {
      suggestions.push({
        key: "none",
        name: "No immediate suggestions",
        description: "Your entered deductions appear fully utilised or no clear opportunities detected. Consider reviewing portfolio for ELSS or NPS top-ups.",
        maxInvestable: 0,
        estTaxSaved: 0,
        learnMore: "#",
      });
    }

    // sort descending by estTaxSaved
    suggestions.sort((a, b) => b.estTaxSaved - a.estTaxSaved);

    setRecommendations(suggestions);
    return suggestions;
  }

  /* ---------- Tax computation ---------- */
  function computeTax() {
    const v = validateAll();
    // If there are errors, don't proceed (warnings allowed)
    const hasError = Object.values(v).some((vv) => vv.severity === "error");
    if (hasError) {
      pushAlert({ type: "error", message: "Fix errors before running calculation." });
      return;
    }

    const form = incomeForm;
    const fyCfg = FY_SLABS[form.fy] || FY_SLABS["2025-26"];

    const salary = Number(form.salary || 0);
    const exemptAllowances = Number(form.exemptAllowances || 0);
    const interestIncome = Number(form.interestIncome || 0);
    const dividendIncome = Number(form.dividendIncome || 0);
    const rentalIncome = Number(form.rentalIncome || 0);
    const digitalIncome = Number(form.digitalIncome || 0);
    const otherIncome = Number(form.otherIncome || 0);

    let grossTotal = salary + interestIncome + dividendIncome + rentalIncome + digitalIncome + otherIncome;
    grossTotal = Math.max(0, grossTotal - exemptAllowances);

    let capGains = 0;
    if (form.includeCapitalGains && form.useTransactionsCSV && transactionsRows.length) {
      capGains = computeRealizedGainsFromTransactions(transactionsRows);
    } else if (form.includeCapitalGains && !form.useTransactionsCSV) {
      pushAlert({ type: "warning", message: "Capital gains inclusion selected but no transactions CSV uploaded — not included." });
    }
    grossTotal += capGains;

    const d = form.deductions || {};
    const ded80C = Math.min(Number(d["80C"] || 0), 150000);
    const ded80CCD = Math.min(Number(d["80CCD"] || 0), 50000);
    const ded80D = Number(d["80D"] || 0);
    const ded80EEA = Number(d["80EEA"] || 0);
    const ded80G = Number(d["80G"] || 0);
    const ded80TTA = Number(d["80TTA"] || 0);
    const ded80E = Number(d["80E"] || 0); // education loan interest
    const ded80TTB = Number(d["80TTB"] || 0); // senior citizen deposit interest
    const dedOther = Number(d["other"] || 0);
    const homeLoanSelf = Number(form.homeLoanInterestSelf || 0);

    const totalDeductionsOld = ded80C + ded80CCD + ded80D + ded80EEA + ded80G + ded80TTA + ded80E + ded80TTB + dedOther + homeLoanSelf;
    const totalDeductionsNew = homeLoanSelf; // simplified for demo

    const taxableOld = Math.max(0, grossTotal - totalDeductionsOld);
    const taxableNew = Math.max(0, grossTotal - totalDeductionsNew);

    const oldRes = calcTaxWithSurchargeAndCess(taxableOld, fyCfg.old, { rebate87A: fyCfg.rebate87A?.old });
    const newRes = calcTaxWithSurchargeAndCess(taxableNew, fyCfg.new, { rebate87A: fyCfg.rebate87A?.new });

    const declaredTDS = Math.round(Number(form.tdsPaid || 0));
    const netOld = Math.max(0, oldRes.totalTax - declaredTDS);
    const netNew = Math.max(0, newRes.totalTax - declaredTDS);
    const recommendation = oldRes.totalTax <= newRes.totalTax ? "old" : "new";

    const result = {
      fy: form.fy,
      grossTotalIncome: Math.round(grossTotal),
      capGains: Math.round(capGains),
      old: { taxableIncome: Math.round(taxableOld), ...oldRes, netPayable: Math.round(netOld) },
      new: { taxableIncome: Math.round(taxableNew), ...newRes, netPayable: Math.round(netNew) },
      recommendation,
      deductions: {
        ded80C,
        ded80CCD,
        ded80D,
        ded80EEA,
        ded80G,
        ded80TTA,
        ded80E,
        ded80TTB,
        dedOther,
        homeLoanSelf,
        totalDeductionsOld: Math.round(totalDeductionsOld),
      },
    };

    setTaxComparison(result);
    pushAudit({ action: "tax_run", detail: { fy: form.fy, gross: result.grossTotalIncome, recommendation } });
    pushAlert({ type: "success", message: "Tax calculation complete. Review summary on the right." });

    // Generate recommendations and auto-expand the collapsible panel
    generateRecommendations(result);
    setShowRecommendations(true);

    return result;
  }

  /* ---------- Exports ---------- */
  function exportITRJSON() {
    if (!taxComparison) {
      pushAlert({ type: "error", message: "Run calculation first before exporting ITR draft." });
      return;
    }
    const itr = {
      meta: {
        fy: taxComparison.fy,
        generatedAt: new Date().toISOString(),
        disclaimer: "This is a draft ITR JSON for review. Validate and sign before filing.",
      },
      personal: {
        ageGroup: incomeForm.ageGroup,
      },
      income: {
        salary: Number(incomeForm.salary || 0),
        interest: Number(incomeForm.interestIncome || 0),
        dividend: Number(incomeForm.dividendIncome || 0),
        rental: Number(incomeForm.rentalIncome || 0),
        digital: Number(incomeForm.digitalIncome || 0),
        other: Number(incomeForm.otherIncome || 0),
        capitalGains: Number(taxComparison.capGains || 0),
        grossTotal: Number(taxComparison.grossTotalIncome || 0),
      },
      deductions: incomeForm.deductions || {},
      tax: {
        old: taxComparison.old,
        new: taxComparison.new,
        recommendation: taxComparison.recommendation,
      },
      tdsImported: tdsEntries || [],
      bankImported: bankRows ? bankRows.slice(0, 100) : [],
      audit: auditLog.slice(0, 50),
    };

    const blob = new Blob([JSON.stringify(itr, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `itr-draft-${taxComparison.fy}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    pushAudit({ action: "export_itr", detail: { fy: taxComparison.fy } });
    pushAlert({ type: "success", message: "Downloaded ITR draft JSON (for CA review)." });
  }

  function downloadTaxPDF() {
    if (!taxComparison) {
      pushAlert({ type: "error", message: "No tax calculation available — click View Calculation first." });
      return;
    }
    const doc = new jsPDF();
    doc.setFontSize(14);
    doc.text("Tax Summary", 14, 20);
    doc.setFontSize(11);
    doc.text(`FY: ${taxComparison.fy}`, 14, 30);
    doc.text(`Gross Total Income: ₹${taxComparison.grossTotalIncome.toLocaleString("en-IN")}`, 14, 36);
    doc.text(`Capital Gains (estimated): ₹${taxComparison.capGains.toLocaleString("en-IN")}`, 14, 42);
    doc.text(`Old Regime: Taxable ₹${taxComparison.old.taxableIncome.toLocaleString("en-IN")} | Total Tax ₹${taxComparison.old.totalTax.toLocaleString("en-IN")}`, 14, 50);
    doc.text(`New Regime: Taxable ₹${taxComparison.new.taxableIncome.toLocaleString("en-IN")} | Total Tax ₹${taxComparison.new.totalTax.toLocaleString("en-IN")}`, 14, 58);
    doc.text(`Recommended regime: ${taxComparison.recommendation.toUpperCase()}`, 14, 66);
    doc.save(`tax-summary-${taxComparison.fy}.pdf`);
    pushAudit({ action: "export_tax_pdf", detail: { fy: taxComparison.fy } });
  }

  /* ---------- portfolio CSV ---------- */
  async function handlePortfolioCSV(e) {
    const file = e.target?.files?.[0];
    if (!file) return;
    setUploading(true);
    setCsvError("");
    try {
      const text = await file.text();
      const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
      const parsed = [];
      lines.forEach((ln, i) => {
        const parts = ln.split(",").map((p) => p.trim());
        if (parts.length < 4) return;
        const [type, symbol, qtyStr, avgStr] = parts;
        const qty = Number(qtyStr || 0);
        const avgPrice = Number(avgStr || 0);
        parsed.push({ id: Date.now() + i, type: type || "equity", symbol: symbol.toUpperCase(), qty, avgPrice, currentPrice: avgPrice, goalId: null });
      });
      if (!parsed.length) throw new Error("No valid portfolio rows found. Expect: type,symbol,qty,avgPrice");
      setHoldings((h) => [...parsed, ...h]);
      pushAlert({ type: "success", message: `Imported ${parsed.length} holdings.` });
      pushAudit({ action: "portfolio_import", detail: { rows: parsed.length } });
    } catch (err) {
      setCsvError(String(err.message || err));
      pushAudit({ action: "portfolio_import_failed", detail: { error: String(err.message || err) } });
    } finally {
      setUploading(false);
      if (e.target) e.target.value = "";
    }
  }

  /* ---------- reset ---------- */
  function resetTaxForm() {
    setIncomeForm({
      preset: "custom",
      fy: "2025-26",
      ageGroup: "0-60",
      salary: 0,
      exemptAllowances: 0,
      interestIncome: 0,
      dividendIncome: 0,
      rentalIncome: 0,
      digitalIncome: 0,
      otherIncome: 0,
      homeLoanInterestSelf: 0,
      homeLoanInterestLetOut: 0,
      tdsPaid: 0,
      includeCapitalGains: false,
      useTransactionsCSV: false,
      deductions: {},
    });
    setTaxComparison(null);
    setTransactionsRows([]);
    setTransactionsPreview(null);
    setTdsEntries([]);
    setTdsReconciliation(null);
    setBankRows([]);
    setBankReconciliation(null);
    setValidation({});
    setRecommendations([]);
    setShowRecommendations(false);
    pushAudit({ action: "tax_form_reset" });
  }

  /* ---------- Deduction summary for charts ---------- */
  function deductionSummaryForCharts() {
    const d = incomeForm.deductions || {};
    const data = [
      { key: "80C", value: Number(d["80C"] || 0), limit: 150000 },
      { key: "80CCD", value: Number(d["80CCD"] || 0), limit: 50000 },
      { key: "80D", value: Number(d["80D"] || 0), limit: 100000 },
      { key: "80E", value: Number(d["80E"] || 0), limit: Infinity },
      { key: "80G", value: Number(d["80G"] || 0), limit: Infinity },
      { key: "80TTB", value: Number(d["80TTB"] || 0), limit: Infinity },
      { key: "80TTA", value: Number(d["80TTA"] || 0), limit: Infinity },
      { key: "other", value: Number(d["other"] || 0), limit: Infinity },
    ];
    const filtered = data.filter((x) => x.value > 0);
    return filtered;
  }

  // colors for chart slices
  const CHART_COLORS = ["#4f46e5", "#06b6d4", "#16a34a", "#f59e0b", "#ef4444", "#8b5cf6", "#10b981", "#f97316"];

  /* ---------- UI ---------- */
  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Wealth Management — Cockpit</h1>
        <div className="flex items-center gap-3">
          <input aria-label="search" placeholder="Search..." className="border rounded px-3 py-2 text-sm" />
          <Link to="/advisor/book" className="px-3 py-2 border rounded text-sm">Book Advisor</Link>
        </div>
      </div>

      {/* top nav */}
      <div className="flex gap-3 flex-wrap">
        <button onClick={() => setActivePanel("overview")} className={`px-4 py-2 rounded ${activePanel === "overview" ? "bg-slate-900 text-white" : "border"}`}>Overview</button>
        <button onClick={() => setActivePanel("tax")} className={`px-4 py-2 rounded ${activePanel === "tax" ? "bg-amber-500 text-black" : "border"}`}>Tax Assistant</button>
        <button onClick={() => setActivePanel("investments")} className={`px-4 py-2 rounded ${activePanel === "investments" ? "bg-green-600 text-white" : "border"}`}>Investments</button>
        <button onClick={() => setActivePanel("screener")} className={`px-4 py-2 rounded ${activePanel === "screener" ? "bg-indigo-600 text-white" : "border"}`}>Screener</button>
        <button onClick={() => setActivePanel("alerts")} className={`px-4 py-2 rounded ${activePanel === "alerts" ? "bg-pink-600 text-white" : "border"}`}>Alerts ({alerts.filter((a) => !a.seen).length})</button>
        <button onClick={() => setActivePanel("macro")} className={`px-4 py-2 rounded ${activePanel === "macro" ? "bg-emerald-600 text-white" : "border"}`}>Macro</button>
      </div>

      {/* Overview */}
      {activePanel === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-white border rounded-lg p-4">
              <h2 className="text-xl font-semibold">Quick Actions</h2>
              <div className="mt-3 flex gap-2">
                <button onClick={() => setActivePanel("tax")} className="px-3 py-2 border rounded">Open Tax Assistant</button>
                <button onClick={() => setActivePanel("investments")} className="px-3 py-2 border rounded">Investment Ideas</button>
                <button onClick={() => setActivePanel("screener")} className="px-3 py-2 border rounded">Run Screener</button>
              </div>
            </div>

            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium">Portfolio Snapshot</h3>
              <div className="mt-3 grid grid-cols-3 gap-4">
                <div className="p-3 bg-slate-50 rounded">
                  <div className="text-sm">Net Worth</div>
                  <div className="font-semibold mt-2">₹{Math.round(portfolioValue).toLocaleString("en-IN")}</div>
                </div>
                <div className="p-3 bg-slate-50 rounded">
                  <div className="text-sm">Invested</div>
                  <div className="font-semibold mt-2">₹{Math.round(invested).toLocaleString("en-IN")}</div>
                </div>
                <div className="p-3 bg-slate-50 rounded">
                  <div className="text-sm">Unrealized P&L</div>
                  <div className={`font-semibold mt-2 ${unrealizedPL >= 0 ? "text-green-600" : "text-red-500"}`}>₹{Math.round(unrealizedPL).toLocaleString("en-IN")}</div>
                </div>
              </div>
            </div>

            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium">Goals</h3>
              <div className="mt-3 space-y-2">
                {goals.map((g) => (
                  <div key={g.id} className="border rounded p-3 flex justify-between items-center">
                    <div>
                      <div className="font-medium">{g.name}</div>
                      <div className="text-xs">Target ₹{g.target.toLocaleString("en-IN")}</div>
                    </div>
                    <div className="text-sm">Suggested SIP ₹{g.monthlySIP}</div>
                  </div>
                ))}
                {goals.length === 0 && <div className="text-sm text-muted-foreground">No goals yet — add one.</div>}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium">Latest Articles</h3>
              <div className="mt-3 space-y-2">
                {articles.slice(0, 4).map((a) => (
                  <Link key={a.slug} to={`/article/${a.slug}`} className="block text-sm border rounded px-2 py-1">{a.title}</Link>
                ))}
              </div>
            </div>

            <div className="bg-white border rounded-lg p-4">
              <h3 className="font-medium">Reminders</h3>
              <div className="mt-2 text-sm">ITR filing window, advance tax reminders (configure in Alerts)</div>
            </div>
          </div>
        </div>
      )}

      {/* TAX PANEL */}
      {activePanel === "tax" && (
        <div className="bg-white border rounded-lg p-6">
          <div className="flex items-start gap-6">
            {/* Left: Form */}
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-semibold">Income Tax Assistant — FY {incomeForm.fy}</h2>
                <div className="text-xs text-muted-foreground">Estimate only · CA review required</div>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm">Financial Year</label>
                  <select value={incomeForm.fy} onChange={(e) => setIncomeForm((f) => ({ ...f, fy: e.target.value }))} className="w-full border rounded px-3 py-2">
                    {Object.keys(FY_SLABS).map((fy) => <option key={fy} value={fy}>{fy}</option>)}
                  </select>
                </div>

                <div>
                  <label className="text-sm">Age group</label>
                  <select value={incomeForm.ageGroup} onChange={(e) => setIncomeForm((f) => ({ ...f, ageGroup: e.target.value }))} className="w-full border rounded px-3 py-2">
                    <option value="0-60">0-60</option>
                    <option value="60-80">60-80 (Senior)</option>
                    <option value="80+">80+ (Super Senior)</option>
                  </select>
                </div>

                <div className="md:col-span-2 flex gap-2">
                  <button onClick={() => applyPreset("salaried")} className="px-3 py-2 border rounded text-sm">Preset: Salaried</button>
                  <button onClick={() => applyPreset("self")} className="px-3 py-2 border rounded text-sm">Preset: Self-employed</button>
                  <button onClick={() => applyPreset("custom")} className="px-3 py-2 border rounded text-sm">Custom</button>
                  <button onClick={resetTaxForm} className="px-3 py-2 border rounded text-sm">Reset</button>
                </div>

                {/* Income fields */}
                <div>
                  <label className="text-sm">Income from Salary</label>
                  <input type="number" value={incomeForm.salary} onChange={(e) => { setIncomeForm((f) => ({ ...f, salary: Number(e.target.value || 0) })); setTimeout(() => validateAll(), 50); }} className={`w-full border rounded px-3 py-2 ${fieldClassFor("salary")}`} />
                  {validation.salary && <div className="text-xs text-red-600 mt-1">{validation.salary.message}</div>}
                </div>

                <div>
                  <label className="text-sm">Exempt allowances</label>
                  <input type="number" value={incomeForm.exemptAllowances} onChange={(e) => setIncomeForm((f) => ({ ...f, exemptAllowances: Number(e.target.value || 0) }))} className="w-full border rounded px-3 py-2" />
                </div>

                <div>
                  <label className="text-sm">Income from interest</label>
                  <input type="number" value={incomeForm.interestIncome} onChange={(e) => setIncomeForm((f) => ({ ...f, interestIncome: Number(e.target.value || 0) }))} className="w-full border rounded px-3 py-2" />
                </div>

                <div>
                  <label className="text-sm">Income from dividends</label>
                  <input type="number" value={incomeForm.dividendIncome || 0} onChange={(e) => setIncomeForm((f) => ({ ...f, dividendIncome: Number(e.target.value || 0) }))} className="w-full border rounded px-3 py-2" />
                </div>

                <div>
                  <label className="text-sm">Interest on home loan — Self occupied</label>
                  <input type="number" value={incomeForm.homeLoanInterestSelf} onChange={(e) => setIncomeForm((f) => ({ ...f, homeLoanInterestSelf: Number(e.target.value || 0) }))} className="w-full border rounded px-3 py-2" />
                </div>

                <div>
                  <label className="text-sm">Rental income received</label>
                  <input type="number" value={incomeForm.rentalIncome} onChange={(e) => setIncomeForm((f) => ({ ...f, rentalIncome: Number(e.target.value || 0) }))} className="w-full border rounded px-3 py-2" />
                </div>

                <div>
                  <label className="text-sm">Interest on home loan — Let out</label>
                  <input type="number" value={incomeForm.homeLoanInterestLetOut} onChange={(e) => setIncomeForm((f) => ({ ...f, homeLoanInterestLetOut: Number(e.target.value || 0) }))} className="w-full border rounded px-3 py-2" />
                </div>

                <div>
                  <label className="text-sm">Income from digital assets</label>
                  <input type="number" value={incomeForm.digitalIncome} onChange={(e) => setIncomeForm((f) => ({ ...f, digitalIncome: Number(e.target.value || 0) }))} className="w-full border rounded px-3 py-2" />
                </div>

                <div>
                  <label className="text-sm">Other income</label>
                  <input type="number" value={incomeForm.otherIncome} onChange={(e) => setIncomeForm((f) => ({ ...f, otherIncome: Number(e.target.value || 0) }))} className="w-full border rounded px-3 py-2" />
                </div>

                <div>
                  <label className="text-sm">TDS / Tax already paid</label>
                  <input type="number" value={incomeForm.tdsPaid} onChange={(e) => setIncomeForm((f) => ({ ...f, tdsPaid: Number(e.target.value || 0) }))} className={`w-full border rounded px-3 py-2 ${fieldClassFor("tds_reconcile")}`} />
                  {validation.tds_reconcile && <div className="text-xs text-yellow-700 mt-1">{validation.tds_reconcile.message}</div>}
                </div>

                {/* Capital gains */}
                <div className="md:col-span-2">
                  <label className="inline-flex items-center gap-2">
                    <input type="checkbox" checked={incomeForm.includeCapitalGains} onChange={(e) => setIncomeForm((f) => ({ ...f, includeCapitalGains: e.target.checked }))} />
                    Include capital gains in computation
                  </label>
                </div>

                {incomeForm.includeCapitalGains && (
                  <>
                    <div className="md:col-span-2">
                      <label className="inline-flex items-center gap-2">
                        <input type="checkbox" checked={incomeForm.useTransactionsCSV} onChange={(e) => setIncomeForm((f) => ({ ...f, useTransactionsCSV: e.target.checked }))} />
                        Use transactions CSV (recommended)
                      </label>
                    </div>

                    {incomeForm.useTransactionsCSV && (
                      <div className="md:col-span-2">
                        <label className="text-sm">Upload transactions CSV</label>
                        <input type="file" accept=".csv" onChange={handleTransactionsUpload} className="w-full" />
                        {uploading && <div className="text-xs text-muted-foreground mt-1">Parsing CSV…</div>}
                        {csvError && <div className="text-xs text-red-500 mt-1">{csvError}</div>}
                        {transactionsPreview && <div className="mt-1 text-xs">Preview {transactionsPreview.length} rows (up to 20)</div>}
                      </div>
                    )}
                  </>
                )}

                {/* TDS import */}
                <div className="md:col-span-2">
                  <h4 className="font-medium">TDS / Form 26AS import</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
                    <div className="md:col-span-2">
                      <input type="file" accept=".csv" onChange={handleTDSUpload} />
                      <div className="text-xs text-muted-foreground mt-1">CSV columns (demo): deductor,section,amount[,date,pan]</div>
                      {tdsEntries.length > 0 && <div className="text-xs mt-1">{tdsEntries.length} TDS entries imported</div>}
                    </div>
                    <div>
                      <button onClick={() => reconcileTDS()} className="px-3 py-2 border rounded w-full">Reconcile TDS</button>
                    </div>
                  </div>
                  {tdsReconciliation && (
                    <div className="mt-2 text-xs">
                      Imported: ₹{tdsReconciliation.importedSum.toLocaleString("en-IN")}, Declared: ₹{tdsReconciliation.declared.toLocaleString("en-IN")}, Diff: ₹{tdsReconciliation.diff.toLocaleString("en-IN")} — Status: {tdsReconciliation.status}
                    </div>
                  )}
                </div>

                {/* Bank import */}
                <div className="md:col-span-2">
                  <h4 className="font-medium">Bank statement import (optional)</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-2">
                    <div className="md:col-span-2">
                      <input type="file" accept=".csv" onChange={handleBankUpload} />
                      <div className="text-xs text-muted-foreground mt-1">CSV demo: date,description,amount,type(CREDIT/DEBIT)</div>
                    </div>
                    <div>
                      <button onClick={() => reconcileBank()} className="px-3 py-2 border rounded w-full">Reconcile Bank</button>
                    </div>
                  </div>
                  {bankReconciliation && (
                    <div className="mt-2 text-xs">
                      Credits: ₹{bankReconciliation.credits.toLocaleString("en-IN")}, Declared Income: ₹{bankReconciliation.declaredIncome.toLocaleString("en-IN")}, Diff: ₹{bankReconciliation.diff.toLocaleString("en-IN")} — {bankReconciliation.status}
                    </div>
                  )}
                  {validation.bank_reconcile && <div className="text-xs text-yellow-700 mt-1">{validation.bank_reconcile.message}</div>}
                </div>

                {/* Deductions */}
                <div className="md:col-span-2">
                  <h4 className="font-medium">Deductions</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-2">
                    <div>
                      <label className="text-sm">80C (max ₹1,50,000)</label>
                      <input
                        type="number"
                        value={(incomeForm.deductions && incomeForm.deductions["80C"]) || 0}
                        onChange={(e) => {
                          const v = Number(e.target.value || 0);
                          setIncomeForm((f) => ({ ...f, deductions: { ...(f.deductions || {}), "80C": v } }));
                          setTimeout(() => validateAll(), 50);
                        }}
                        className={`w-full border rounded px-3 py-2 ${fieldClassFor("80C")}`}
                      />
                      {validation["80C"] && <div className="text-xs text-yellow-700 mt-1">{validation["80C"].message}</div>}
                    </div>

                    <div>
                      <label className="text-sm">80CCD(1B) NPS</label>
                      <input type="number" value={(incomeForm.deductions && incomeForm.deductions["80CCD"]) || 0} onChange={(e) => { setIncomeForm((f) => ({ ...f, deductions: { ...(f.deductions || {}), "80CCD": Number(e.target.value || 0) } })); }} className="w-full border rounded px-3 py-2" />
                    </div>

                    <div>
                      <label className="text-sm">80D (Medical)</label>
                      <input type="number" value={(incomeForm.deductions && incomeForm.deductions["80D"]) || 0} onChange={(e) => { setIncomeForm((f) => ({ ...f, deductions: { ...(f.deductions || {}), "80D": Number(e.target.value || 0) } })); }} className="w-full border rounded px-3 py-2" />
                    </div>

                    <div>
                      <label className="text-sm">80G (Donations)</label>
                      <input type="number" value={(incomeForm.deductions && incomeForm.deductions["80G"]) || 0} onChange={(e) => { setIncomeForm((f) => ({ ...f, deductions: { ...(f.deductions || {}), "80G": Number(e.target.value || 0) } })); }} className="w-full border rounded px-3 py-2" />
                    </div>

                    <div>
                      <label className="text-sm">80TTA (Interest on deposits)</label>
                      <input type="number" value={(incomeForm.deductions && incomeForm.deductions["80TTA"]) || 0} onChange={(e) => { setIncomeForm((f) => ({ ...f, deductions: { ...(f.deductions || {}), "80TTA": Number(e.target.value || 0) } })); }} className="w-full border rounded px-3 py-2" />
                    </div>

                    <div>
                      <label className="text-sm">80E (Education loan interest)</label>
                      <input type="number" value={(incomeForm.deductions && incomeForm.deductions["80E"]) || 0} onChange={(e) => { setIncomeForm((f) => ({ ...f, deductions: { ...(f.deductions || {}), "80E": Number(e.target.value || 0) } })); setTimeout(() => validateAll(), 50); }} className="w-full border rounded px-3 py-2" />
                    </div>

                    <div>
                      <label className="text-sm">80TTB (Senior citizen deposits)</label>
                      <input type="number" value={(incomeForm.deductions && incomeForm.deductions["80TTB"]) || 0} onChange={(e) => { setIncomeForm((f) => ({ ...f, deductions: { ...(f.deductions || {}), "80TTB": Number(e.target.value || 0) } })); setTimeout(() => validateAll(), 50); }} className="w-full border rounded px-3 py-2" />
                    </div>

                    <div className="md:col-span-2">
                      <label className="text-sm">Any other deduction</label>
                      <input type="number" value={(incomeForm.deductions && incomeForm.deductions["other"]) || 0} onChange={(e) => { setIncomeForm((f) => ({ ...f, deductions: { ...(f.deductions || {}), "other": Number(e.target.value || 0) } })); }} className="w-full border rounded px-3 py-2" />
                    </div>
                  </div>
                </div>

                {/* Buttons */}
                <div className="md:col-span-2 mt-4 flex gap-3">
                  <button onClick={() => computeTax()} className="px-4 py-2 bg-blue-600 text-white rounded">View Calculation</button>
                  <button onClick={() => resetTaxForm()} className="px-4 py-2 border rounded">Reset</button>
                  <button onClick={() => { if (taxComparison) downloadTaxPDF(); else pushAlert({ type: "error", message: "Run calculation before exporting." }); }} className="px-4 py-2 border rounded">Export PDF</button>
                  <button onClick={() => exportITRJSON()} className="px-4 py-2 border rounded">Export ITR JSON</button>
                </div>

                <div className="md:col-span-2 text-xs text-muted-foreground mt-3">
                  <strong>Disclaimer:</strong> This is a simplified estimator. It omits many corner-case rules. For filing or legally binding advice consult a qualified Chartered Accountant. Move logic server-side and run CA-reviewed tests before production.
                </div>
              </div>
            </div>

            {/* Right: summary & charts */}
            <div className="w-80">
              <div className="bg-slate-50 border rounded p-4">
                <h3 className="font-semibold">Tax Liability Summary</h3>
                <div className="mt-3 text-sm">
                  <div>FY: <strong>{incomeForm.fy}</strong></div>
                  <div className="mt-2">Gross Income: <strong>₹{(taxComparison?.grossTotalIncome || 0).toLocaleString("en-IN")}</strong></div>
                  <div className="mt-3 flex justify-between">
                    <div>Old Regime</div>
                    <div>₹{taxComparison ? (taxComparison.old.totalTax || 0).toLocaleString("en-IN") : "0"}</div>
                  </div>
                  <div className="flex justify-between">
                    <div>New Regime</div>
                    <div>₹{taxComparison ? (taxComparison.new.totalTax || 0).toLocaleString("en-IN") : "0"}</div>
                  </div>

                  <div className="mt-3 p-3 rounded bg-green-50 text-green-800 text-center">
                    {taxComparison ? (
                      <>
                        <div className="text-sm">Recommendation: <strong>{taxComparison.recommendation.toUpperCase()}</strong></div>
                        <div className="text-xl font-bold mt-2">₹{Math.abs((taxComparison.old.totalTax || 0) - (taxComparison.new.totalTax || 0)).toLocaleString("en-IN")}</div>
                        <div className="text-xs">Difference (Old vs New)</div>
                      </>
                    ) : (
                      <div className="text-sm">Fill details and click <strong>View Calculation</strong></div>
                    )}
                  </div>

                  {taxComparison && (
                    <div className="mt-3 text-xs">
                      <div>Old: Taxable ₹{taxComparison.old.taxableIncome.toLocaleString("en-IN")} · Tax ₹{taxComparison.old.totalTax.toLocaleString("en-IN")}</div>
                      <div>New: Taxable ₹{taxComparison.new.taxableIncome.toLocaleString("en-IN")} · Tax ₹{taxComparison.new.totalTax.toLocaleString("en-IN")}</div>
                      <div className="mt-2">Net payable Old: ₹{taxComparison.old.netPayable.toLocaleString("en-IN")} · New: ₹{taxComparison.new.netPayable.toLocaleString("en-IN")}</div>
                    </div>
                  )}
                </div>
              </div>

              {/* Deduction charts & suggestions */}
              <div className="mt-3 bg-white border rounded p-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium">Tax Saving Snapshot</div>
                  <div className="text-xs text-muted-foreground">Visual</div>
                </div>

                <div className="mt-2 h-48">
                  {deductionSummaryForCharts().length === 0 ? (
                    <div className="text-xs text-muted-foreground mt-4">No deductions entered yet — add values to see suggestions.</div>
                  ) : (
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          dataKey="value"
                          data={deductionSummaryForCharts()}
                          nameKey="key"
                          innerRadius={30}
                          outerRadius={60}
                          paddingAngle={3}
                          label={(entry) => `${entry.key} (${entry.value})`}
                        >
                          {deductionSummaryForCharts().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                          ))}
                        </Pie>
                        <ReTooltip formatter={(value) => `₹${value.toLocaleString("en-IN")}`} />
                        <Legend wrapperStyle={{ fontSize: 10 }} />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>

                {/* small bar chart: claimed vs limit for top items */}
                <div className="mt-3 h-40">
                  {deductionSummaryForCharts().length > 0 && (
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={deductionSummaryForCharts()}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="key" />
                        <YAxis />
                        <ReTooltip formatter={(value) => `₹${value.toLocaleString("en-IN")}`} />
                        <Bar dataKey="value">
                          {deductionSummaryForCharts().map((entry, idx) => (
                            <Cell key={`bar-${idx}`} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>

                {/* suggestions */}
                <div className="mt-3">
                  <button
                    onClick={() => setShowRecommendations((s) => !s)}
                    className="w-full text-left px-3 py-2 border rounded"
                  >
                    {showRecommendations ? "Hide" : "See how to save more tax"}
                  </button>

                  {showRecommendations && (
                    <div className="mt-2 space-y-2">
                      {/* recommendations bar chart */}
                      <div className="h-36">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={recommendations.map((r) => ({ name: r.key, value: r.estTaxSaved }))}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="name" />
                            <YAxis />
                            <ReTooltip formatter={(value) => `₹${value.toLocaleString("en-IN")}`} />
                            <Bar dataKey="value">
                              {recommendations.map((entry, idx) => (
                                <Cell key={`rec-bar-${idx}`} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>

                      <div className="space-y-2 max-h-56 overflow-auto">
                        {recommendations.map((r) => (
                          <div key={r.key} className="border rounded p-2 flex justify-between items-start">
                            <div className="flex-1">
                              <div className="font-medium text-sm">{r.name}</div>
                              <div className="text-xs text-muted-foreground">{r.description}</div>
                              <div className="text-xs mt-1">Suggested investable: <strong>₹{r.maxInvestable.toLocaleString("en-IN")}</strong></div>
                            </div>
                            <div className="text-right ml-3">
                              <div className="font-semibold">Save ≈ ₹{r.estTaxSaved.toLocaleString("en-IN")}</div>
                              <a href={r.learnMore} className="text-xs underline block mt-1">Learn more</a>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-2 text-xs">
                    {validation["80C"] ? (
                      <div className="text-yellow-700">{validation["80C"].message}</div>
                    ) : (
                      <>
                        {((incomeForm.deductions && Number(incomeForm.deductions["80C"] || 0)) < 150000) && (
                          <div>Suggestion: consider investing more in 80C instruments (ELSS, PPF, EPF, etc.) to maximize tax benefit.</div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* TDS preview */}
              <div className={`mt-3 bg-white border rounded p-3 text-xs ${tdsReconciliation && tdsReconciliation.status !== "matched" ? "ring-2 ring-yellow-300" : ""}`}>
                <div className="font-medium">TDS / Form26AS</div>
                <div className="mt-2">
                  Imported: {tdsEntries.length} rows
                  {tdsEntries.length > 0 && (
                    <div className="mt-2 max-h-36 overflow-auto">
                      {tdsEntries.slice(0, 10).map((r, i) => (
                        <div key={i} className="flex justify-between">
                          <div>{r.deductor} · {r.section}</div>
                          <div>₹{Number(r.amount || 0).toLocaleString("en-IN")}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Bank preview */}
              <div className={`mt-3 bg-white border rounded p-3 text-xs ${bankReconciliation && bankReconciliation.status !== "ok" ? "ring-2 ring-yellow-300" : ""}`}>
                <div className="font-medium">Bank Import</div>
                <div className="mt-2">Rows: {bankRows.length}</div>
                {bankRows.length > 0 && (
                  <div className="mt-2 max-h-36 overflow-auto">
                    {bankRows.slice(0, 10).map((r, i) => (
                      <div key={i} className="flex justify-between">
                        <div>{r.date} · {r.desc}</div>
                        <div className={r.type === "CREDIT" ? "text-green-600" : "text-red-600"}>₹{Number(r.amount || 0).toLocaleString("en-IN")}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* transactions preview */}
              {transactionsPreview && (
                <div className="mt-3 bg-white border rounded p-3 text-xs">
                  <div className="font-medium">Transactions (preview)</div>
                  <div className="mt-2 max-h-40 overflow-auto">
                    {transactionsPreview.map((r, i) => (
                      <div key={i} className="flex justify-between">
                        <div>{r.date} · {r.symbol} · {r.type}</div>
                        <div>Qty {r.qty} @ ₹{r.price}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* INVESTMENTS */}
      {activePanel === "investments" && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-lg font-medium">Investment Ideas & Signals</h3>
          <div className="mt-3 space-y-3">
            <div className="border rounded p-3">Model Portfolio examples (Conservative / Balanced / Aggressive). Use Screener to populate ideas.</div>
            <div className="border rounded p-3">Tax-efficient funds: ELSS for 80C, NPS for 80CCD(1B). We auto-detect ELSS in portfolio and suggest deductions (opt-in).</div>
            <div className="border rounded p-3">Corporate actions, dividends & alerts (requires backend API).</div>
          </div>
        </div>
      )}

      {/* SCREENER */}
      {activePanel === "screener" && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-lg font-medium">Screener</h3>
          <div className="mt-3 flex gap-2">
            <input type="number" value={0} onChange={() => {}} className="border rounded px-3 py-2" placeholder="Max P/E" />
            <input type="number" value={0} onChange={() => {}} className="border rounded px-3 py-2" placeholder="Min ROE" />
            <button onClick={() => pushAlert({ type: "info", message: "Screener run (demo)." })} className="bg-indigo-600 text-white px-3 py-2 rounded">Run</button>
          </div>
          <div className="mt-3 text-xs text-muted-foreground">Client-side demo — integrate backend for real results.</div>
        </div>
      )}

      {/* ALERTS */}
      {activePanel === "alerts" && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-lg font-medium">Alerts</h3>
          <div className="mt-3 space-y-2">
            {alerts.length === 0 && <div className="text-sm text-muted-foreground">No alerts</div>}
            {alerts.map((a) => (
              <div key={a.id} className={`border rounded p-2 ${a.seen ? "opacity-60" : ""}`}>
                <div className="flex justify-between">
                  <div className="text-sm">{a.message}</div>
                  <div className="text-xs">{new Date(a.created_at).toLocaleString()}</div>
                </div>
                <div className="mt-2">
                  {!a.seen && <button onClick={() => dismissAlert(a.id)} className="text-xs underline">Dismiss</button>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MACRO */}
      {activePanel === "macro" && (
        <div className="bg-white border rounded-lg p-4">
          <h3 className="text-lg font-medium">Macro Dashboard</h3>
          <div className="mt-3 text-sm">
            <div>Inflation: 6.2%</div>
            <div>GDP growth: 7.1%</div>
            <div>Repo rate: 6.5%</div>
            <div className="text-xs text-muted-foreground mt-2">Integrate World Bank / RBI via backend for up-to-date values.</div>
          </div>
        </div>
      )}

      {/* PORTFOLIO (hidden while in Tax panel) */}
      {activePanel !== "tax" && (
        <div className="bg-white border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Portfolio</h2>
            <div className="flex items-center gap-2">
              <label className="cursor-pointer inline-flex items-center gap-2">
                <span className="text-sm">Upload CSV</span>
                <input type="file" accept=".csv" onChange={handlePortfolioCSV} className="hidden" />
              </label>
              <button
                onClick={() => {
                  setHoldings((prev) => [{ id: Date.now(), type: "equity", symbol: "NEWCO", qty: 1, avgPrice: 100, currentPrice: 100, goalId: null }, ...prev]);
                  pushAudit({ action: "add_holding", detail: { symbol: "NEWCO" } });
                }}
                className="bg-slate-900 text-white px-3 py-2 rounded text-sm"
              >
                + Add
              </button>
            </div>
          </div>

          <div className="mt-4 overflow-auto">
            <table className="min-w-full text-left">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-xs">Symbol</th>
                  <th className="px-3 py-2 text-xs">Qty</th>
                  <th className="px-3 py-2 text-xs">Avg</th>
                  <th className="px-3 py-2 text-xs">Current</th>
                  <th className="px-3 py-2 text-xs">P&L</th>
                  <th className="px-3 py-2 text-xs">Goal</th>
                  <th className="px-3 py-2 text-xs">Actions</th>
                </tr>
              </thead>
              <tbody>
                {holdings.map((h) => (
                  <tr key={h.id} className="border-t">
                    <td className="px-3 py-2">{h.symbol}</td>
                    <td className="px-3 py-2">{h.qty}</td>
                    <td className="px-3 py-2">₹{Math.round(h.avgPrice).toLocaleString("en-IN")}</td>
                    <td className="px-3 py-2">₹{Math.round(h.currentPrice || h.avgPrice).toLocaleString("en-IN")}</td>
                    <td className={`px-3 py-2 ${(((h.currentPrice || h.avgPrice) - h.avgPrice) * h.qty) >= 0 ? "text-green-600" : "text-red-500"}`}>₹{Math.round(((h.currentPrice || h.avgPrice) - h.avgPrice) * h.qty).toLocaleString("en-IN")}</td>
                    <td className="px-3 py-2">
                      <select
                        value={h.goalId || ""}
                        onChange={(e) => {
                          const goalId = e.target.value ? Number(e.target.value) : null;
                          setHoldings((prev) => prev.map((x) => (x.id === h.id ? { ...x, goalId } : x)));
                          pushAudit({ action: "link_holding_goal", detail: { holdingId: h.id, goalId } });
                        }}
                        className="border rounded px-2 py-1 text-sm"
                      >
                        <option value="">— none —</option>
                        {goals.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => {
                          setHoldings((prev) => prev.filter((x) => x.id !== h.id));
                          pushAudit({ action: "remove_holding", detail: { holdingId: h.id } });
                          pushAlert({ type: "info", message: `Removed holding ${h.symbol}` });
                        }}
                        className="text-xs underline"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                ))}
                {holdings.length === 0 && <tr><td colSpan={7} className="px-3 py-6 text-sm text-muted-foreground">No holdings — add or upload CSV.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="border-t pt-6 flex items-center justify-between">
        <div>
          <div className="text-sm text-muted-foreground">Need professional help?</div>
          <div className="text-lg font-semibold">Book a CFP call or upgrade to automated tax reports (server-side integration required).</div>
        </div>
        <div>
          <Link to="/advisor/book" className="bg-amber-500 px-4 py-2 rounded">Book Advisor</Link>
        </div>
      </div>
    </div>
  );
}
