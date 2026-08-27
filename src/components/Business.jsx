// Business.jsx (or TaxCAWorkspace.jsx)
import React, { useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import jsPDF from "jspdf";

// ----------------- Helper util functions (exportable for tests) -----------------
export function computeDepreciation(assts) {
  return assts.reduce(
    (s, a) => s + (Number(a.cost || 0) * Number(a.depreciationRate || 0)) / 100,
    0
  );
}

export function computeSlabTax(taxableIncome, slabs) {
  let tax = 0;
  let remaining = taxableIncome;
  let lower = 0;
  for (const slab of slabs) {
    const upper = slab.upTo;
    const slabAmount = Math.max(0, Math.min(remaining, upper - lower));
    tax += slabAmount * slab.rate;
    remaining -= slabAmount;
    lower = upper;
    if (remaining <= 0) break;
  }
  return Math.round(tax);
}

export function computeSurchargeForIndividual(taxBeforeSurcharge, taxableIncome, brackets) {
  let surchargePct = 0;
  for (const b of brackets) {
    if (taxableIncome > b.above) {
      surchargePct = Math.max(surchargePct, b.surcharge);
    }
  }
  return Math.round(taxBeforeSurcharge * surchargePct);
}

export function computeCorporateTax(bookProfit, pol) {
  const baseTax = bookProfit * pol.companyRate;
  const surcharge = baseTax * pol.corporateSurchargePct;
  const cess = (baseTax + surcharge) * pol.cessPct;
  return {
    baseTax: Math.round(baseTax),
    surcharge: Math.round(surcharge),
    cess: Math.round(cess),
    total: Math.round(baseTax + surcharge + cess),
  };
}

export function computeMAT(bookProfit, pol) {
  // Simplified MAT (Section 115JB-like)
  const matBase = Math.round(bookProfit * pol.matRatePct);
  const surcharge = Math.round(matBase * pol.corporateSurchargePct);
  const cess = Math.round((matBase + surcharge) * pol.cessPct);
  return Math.round(matBase + surcharge + cess);
}

export function computeAMT(adjustedTotalIncome, pol) {
  const amtBase = Math.round(adjustedTotalIncome * pol.amtRatePct);
  const surcharge = Math.round(amtBase * pol.corporateSurchargePct);
  const cess = Math.round((amtBase + surcharge) * pol.cessPct);
  return Math.round(amtBase + surcharge + cess);
}

// CSV helper
function toCSV(obj) {
  const rows = [];
  for (const [k, v] of Object.entries(obj)) {
    rows.push(`"${k}","${String(v).replace(/"/g, '""')}"`);
  }
  return rows.join("\n");
}

// ----------------- Component -----------------
export default function TaxCAWorkspace() {
  // ======= App State =======
  const [profile, setProfile] = useState({
    businessName: "My Business",
    businessType: "Proprietorship",
    pan: "",
    gstin: "",
    fy: "2025-2026",
    accountingMethod: "Accrual",
  });

  const [incomeRows, setIncomeRows] = useState([
    { id: 1, source: "Sales Revenue", amount: 0, category: "Business" },
    { id: 2, source: "Interest Income", amount: 0, category: "Other" },
  ]);

  const [expenseRows, setExpenseRows] = useState([
    { id: 1, name: "Salaries", amount: 0, category: "Employee" },
    { id: 2, name: "Rent", amount: 0, category: "Operating" },
  ]);

  const [assets, setAssets] = useState([
    { id: 1, name: "Laptop", cost: 70000, yearOfPurchase: 2024, depreciationRate: 15 },
  ]);

  const [deductions, setDeductions] = useState({
    "80C": 0,
    "80D": 0,
    "80E": 0,
    "80G": 0,
    "80TTB": 0,
  });

  const [documents, setDocuments] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [message, setMessage] = useState("");

  // Configurable policy parameters
  const [policy, setPolicy] = useState({
    individualSlabs: [
      { upTo: 250000, rate: 0 },
      { upTo: 500000, rate: 0.05 },
      { upTo: 1000000, rate: 0.2 },
      { upTo: Infinity, rate: 0.3 },
    ],
    companyRate: 0.25,
    corporateSurchargePct: 0.12,
    matRatePct: 0.15,
    amtRatePct: 0.185,
    cessPct: 0.04,
    individualSurchargeBrackets: [
      { above: 5000000, surcharge: 0.1 },
      { above: 10000000, surcharge: 0.15 },
      { above: 20000000, surcharge: 0.25 },
      { above: 50000000, surcharge: 0.37 },
    ],
  });

  const uniqueId = () => Math.floor(Math.random() * 1e9);

  // ======= CRUD helpers =======
  function addIncomeRow() {
    setIncomeRows((r) => [...r, { id: uniqueId(), source: "", amount: 0, category: "Business" }]);
  }

  function addExpenseRow() {
    setExpenseRows((r) => [...r, { id: uniqueId(), name: "", amount: 0, category: "Operating" }]);
  }

  function addAsset() {
    setAssets((a) => [
      ...a,
      { id: uniqueId(), name: "", cost: 0, yearOfPurchase: new Date().getFullYear(), depreciationRate: 15 },
    ]);
  }

  function removeIncomeRow(id) {
    setIncomeRows((r) => r.filter((x) => x.id !== id));
  }

  function removeExpenseRow(id) {
    setExpenseRows((r) => r.filter((x) => x.id !== id));
  }

  function removeAsset(id) {
    setAssets((a) => a.filter((x) => x.id !== id));
  }

  // ======= Tax engine (uses exported helper functions) =======
  const totals = useMemo(() => {
    const totalIncome = incomeRows.reduce((s, r) => s + Number(r.amount || 0), 0);
    const totalExpenses = expenseRows.reduce((s, r) => s + Number(r.amount || 0), 0);
    const totalDep = computeDepreciation(assets);

    const bookProfit = totalIncome - totalExpenses; // before accounting dep differences
    const taxAdjustments = 0; // placeholder for addbacks/exemptions
    const businessTaxableProfit = Math.max(0, bookProfit - taxAdjustments);
    const totalDeductions = Object.values(deductions).reduce((s, v) => s + Number(v || 0), 0);
    const taxableForIndividual = Math.max(0, businessTaxableProfit - totalDeductions);

    let taxBreakdown = {
      baseTax: 0,
      surcharge: 0,
      cess: 0,
      mat: 0,
      amt: 0,
      finalTax: 0,
    };

    if (
      profile.businessType === "Individual" ||
      profile.businessType === "Proprietorship" ||
      profile.businessType === "Partnership"
    ) {
      const baseTax = computeSlabTax(taxableForIndividual, policy.individualSlabs);
      const surcharge = computeSurchargeForIndividual(baseTax, taxableForIndividual, policy.individualSurchargeBrackets);
      const cess = Math.round((baseTax + surcharge) * policy.cessPct);
      let finalTax = Math.round(baseTax + surcharge + cess);
      const amt = computeAMT(taxableForIndividual, policy);
      if (amt > finalTax) {
        finalTax = amt;
      }
      taxBreakdown = { baseTax, surcharge, cess, mat: 0, amt, finalTax };
    } else {
      const corp = computeCorporateTax(bookProfit, policy);
      const mat = computeMAT(bookProfit, policy);
      const finalTax = Math.max(corp.total, mat);
      taxBreakdown = { baseTax: corp.baseTax, surcharge: corp.surcharge, cess: corp.cess, mat, amt: 0, finalTax };
    }

    return {
      totalIncome,
      totalExpenses,
      totalDep,
      bookProfit,
      businessTaxableProfit,
      totalDeductions,
      taxableForIndividual,
      taxBreakdown,
    };
  }, [incomeRows, expenseRows, assets, deductions, profile, policy]);

  // ======= Recommendations =======
  function generateRecommendations() {
    const recs = [];
    const max80C = 150000;
    const used80C = Number(deductions["80C"] || 0);
    if (used80C < max80C) {
      recs.push({
        id: "80C",
        title: "Maximize 80C (₹1.5L limit)",
        detail: `You can invest up to ₹${(max80C - used80C).toLocaleString()} more in 80C instruments like PPF, ELSS, EPF or NSC to reduce taxable income.`,
      });
    }
    if ((deductions["80D"] || 0) === 0) {
      recs.push({
        id: "80D",
        title: "Claim Health Insurance (80D)",
        detail: "Paying health insurance premiums for self/family increases deduction under Section 80D.",
      });
    }
    if (profile.businessType === "Pvt Ltd" || profile.businessType === "LLP") {
      recs.push({
        id: "entity",
        title: "Salary vs Dividend Optimization",
        detail: "Compare tax on salary vs dividends; consider employer contributions to EPF and NPS.",
      });
      recs.push({
        id: "mat",
        title: "MAT watch",
        detail: "MAT (Section 115JB) applies at 15% on book profits; if MAT > normal tax, MAT provisions may apply — plan for MAT credit utilization.",
      });
    }
    if (totals.bookProfit < 0) {
      recs.push({
        id: "loss",
        title: "Carry forward losses",
        detail: "You have a loss — check whether it is eligible to be carried forward and set off against future profits.",
      });
    }
    if (totals.taxBreakdown.finalTax > 0 && totals.totalDeductions < 150000) {
      const target = 150000 - totals.totalDeductions;
      recs.push({
        id: "invest",
        title: "Immediate action: invest for 80C",
        detail: `Invest up to ₹${target.toLocaleString()} in 80C before ${profile.fy.split("-")[1] ? `March ${profile.fy.split("-")[1]}` : "end of FY"}.`,
      });
    }
    return recs;
  }
  const recommendations = useMemo(generateRecommendations, [deductions, profile, totals]);

  // ======= Document Upload =======
  function handleDocumentUpload(e) {
    const files = Array.from(e.target.files || []);
    const meta = files.map((f) => ({ id: uniqueId(), name: f.name, size: f.size }));
    setDocuments((d) => [...d, ...meta]);
  }

  // ======= PDF Export with jsPDF (preview capability) =======
  function exportPDF(preview = false) {
    const doc = new jsPDF({ unit: "pt", format: "a4" });
    const left = 40;
    let y = 40;
    doc.setFontSize(18);
    doc.text(`${profile.businessName} — Tax Summary (${profile.fy})`, left, y);
    y += 24;
    doc.setFontSize(12);
    doc.text(`Business Type: ${profile.businessType}`, left, y);
    y += 18;
    doc.text(`Total Income: ₹ ${totals.totalIncome.toLocaleString()}`, left, y);
    y += 16;
    doc.text(`Book Profit: ₹ ${Math.round(totals.bookProfit).toLocaleString()}`, left, y);
    y += 16;
    doc.text(
      `Taxable (after deductions): ₹ ${Math.round(totals.taxableForIndividual).toLocaleString()}`,
      left,
      y
    );
    y += 18;
    doc.text(`Tax Breakdown:`, left, y);
    y += 16;
    const tb = totals.taxBreakdown;
    doc.text(`Base Tax: ₹ ${tb.baseTax.toLocaleString()}`, left + 10, y);
    y += 14;
    doc.text(`Surcharge: ₹ ${tb.surcharge.toLocaleString()}`, left + 10, y);
    y += 14;
    doc.text(`Cess: ₹ ${tb.cess.toLocaleString()}`, left + 10, y);
    y += 14;
    if (tb.mat) {
      doc.text(`MAT: ₹ ${tb.mat.toLocaleString()}`, left + 10, y);
      y += 14;
    }
    if (preview) {
      const url = doc.output("bloburl");
      window.open(url, "_blank");
    } else {
      doc.save(`${profile.businessName || "tax-summary"}.pdf`);
    }
  }

  // ======= CSV & JSON exports =======
  function exportCSVData() {
    const csvParts = [];
    csvParts.push("Profile");
    csvParts.push(toCSV(profile));
    csvParts.push("\nIncomes");
    csvParts.push("Source,Category,Amount");
    incomeRows.forEach((r) => csvParts.push(`${r.source},${r.category},${r.amount}`));
    csvParts.push("\nExpenses");
    csvParts.push("Name,Category,Amount");
    expenseRows.forEach((r) => csvParts.push(`${r.name},${r.category},${r.amount}`));
    const blob = new Blob([csvParts.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${profile.businessName || "tax-data"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // ======= Save/Load Draft (localStorage) =======
  function saveDraft() {
    const key = `tax-draft-${profile.businessName || "local"}`;
    const payload = { profile, incomeRows, expenseRows, assets, deductions, documents };
    localStorage.setItem(key, JSON.stringify(payload));
    setMessage("Draft saved locally");
    setTimeout(() => setMessage(""), 2500);
  }

  function loadDraft() {
    const key = `tax-draft-${profile.businessName || "local"}`;
    const raw = localStorage.getItem(key);
    if (!raw) {
      setMessage("No draft found");
      setTimeout(() => setMessage(""), 2000);
      return;
    }
    try {
      const obj = JSON.parse(raw);
      setProfile(obj.profile);
      setIncomeRows(obj.incomeRows || []);
      setExpenseRows(obj.expenseRows || []);
      setAssets(obj.assets || []);
      setDeductions(obj.deductions || {});
      setDocuments(obj.documents || []);
      setMessage("Draft loaded");
      setTimeout(() => setMessage(""), 2000);
    } catch (e) {
      setMessage("Failed to load draft");
      setTimeout(() => setMessage(""), 2000);
    }
  }

  // ======= E-filing & DSC placeholders =======
  async function startEFilingFlow(payload) {
    console.log("EFiling placeholder payload", payload);
    setMessage("E-filing flow started (placeholder)");
    setTimeout(() => setMessage(""), 2500);
  }

  // ======= Handlers =======
  function updateIncome(id, field, value) {
    setIncomeRows((r) =>
      r.map((row) => (row.id === id ? ({ ...row, [field]: field === "amount" ? Number(value) : value } ) : row))
    );
  }

  function updateExpense(id, field, value) {
    setExpenseRows((r) =>
      r.map((row) => (row.id === id ? ({ ...row, [field]: field === "amount" ? Number(value) : value } ) : row))
    );
  }

  function updateAsset(id, field, value) {
    setAssets((a) =>
      a.map((x) =>
        x.id === id
          ? ({ ...x, [field]: field === "cost" || field === "depreciationRate" || field === "yearOfPurchase" ? Number(value) : value })
          : x
      )
    );
  }

  function updateDeduction(key, value) {
    setDeductions((d) => ({ ...d, [key]: Number(value) }));
  }

  // ======= Charts data =======
  const deductionChartData = useMemo(() => Object.keys(deductions).map((k) => ({ name: k, value: Number(deductions[k] || 0) })), [deductions]);

  const taxComponentData = useMemo(() => {
    const tb = totals.taxBreakdown;
    return [
      { name: "Base Tax", value: tb.baseTax },
      { name: "Surcharge", value: tb.surcharge },
      { name: "Cess", value: tb.cess },
      { name: "MAT", value: tb.mat },
      { name: "AMT", value: tb.amt },
    ];
  }, [totals]);

  const COLORS = ["#4F46E5", "#06B6D4", "#F59E0B", "#10B981", "#EF4444"];

  // ======= UI Components =======
  const Header = () => (
    <header className="flex items-center justify-between p-4 bg-white shadow-sm">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-md bg-gradient-to-r from-sky-500 to-indigo-500 flex items-center justify-center text-white font-bold">CA</div>
        <div>
          <div className="text-lg font-semibold">{profile.businessName || "Tax Workspace"}</div>
          <div className="text-xs text-muted-foreground">
            {profile.businessType} · FY {profile.fy}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <select value={profile.fy} onChange={(e) => setProfile((p) => ({ ...p, fy: e.target.value }))} className="border rounded px-2 py-1 text-sm">
          <option>2025-2026</option>
          <option>2024-2025</option>
          <option>2023-2024</option>
        </select>
        <button onClick={saveDraft} className="bg-gray-200 px-3 py-1 rounded">Save Draft</button>
        <button onClick={loadDraft} className="bg-gray-200 px-3 py-1 rounded">Load Draft</button>
        <button onClick={exportCSVData} className="bg-indigo-600 text-white px-3 py-1 rounded">Export CSV</button>
        <button onClick={() => exportPDF(false)} className="bg-emerald-600 text-white px-3 py-1 rounded">Export PDF</button>
      </div>
    </header>
  );

  const Sidebar = () => (
    <aside className="w-64 bg-slate-50 p-4 border-r">
      <div className="space-y-3">
        <div className="text-sm font-semibold">Navigation</div>
        <nav className="flex flex-col gap-2">
          {[
            { id: "overview", label: "Overview" },
            { id: "books", label: "Books (Income & Expenses)" },
            { id: "assets", label: "Assets & Depreciation" },
            { id: "deductions", label: "Deductions & Proofs" },
            { id: "taxcalc", label: "Tax Calculation" },
            { id: "recommend", label: "Recommendations" },
            { id: "itr", label: "ITR Preparation" },
            { id: "compliance", label: "Compliance Calendar" },
          ].map((i) => (
            <button key={i.id} onClick={() => setActiveTab(i.id)} className={`text-left px-3 py-2 rounded ${activeTab === i.id ? "bg-white shadow-sm" : "hover:bg-slate-100"}`}>
              {i.label}
            </button>
          ))}
        </nav>

        <div className="pt-4">
          <div className="text-xs text-muted-foreground font-medium">Quick Actions</div>
          <div className="flex gap-2 mt-2">
            <button onClick={() => { setActiveTab("taxcalc"); }} className="flex-1 px-3 py-2 bg-emerald-600 text-white rounded text-sm">Calculate Tax</button>
            <button onClick={() => { setActiveTab("recommend"); }} className="flex-1 px-3 py-2 bg-yellow-500 text-white rounded text-sm">Get Advice</button>
          </div>
        </div>

        <div className="mt-4 text-xs">
          <div className="font-medium">Engine Config (editable)</div>
          <div className="mt-2 space-y-2">
            <label className="text-xs">Corporate tax (%)</label>
            <input type="number" value={policy.companyRate * 100} onChange={(e) => setPolicy((p) => ({ ...p, companyRate: Number(e.target.value) / 100 }))} className="w-full border rounded px-2 py-1 text-sm" />
            <label className="text-xs mt-2">MAT rate (%)</label>
            <input type="number" value={policy.matRatePct * 100} onChange={(e) => setPolicy((p) => ({ ...p, matRatePct: Number(e.target.value) / 100 }))} className="w-full border rounded px-2 py-1 text-sm" />
            <label className="text-xs mt-2">Cess (%)</label>
            <input type="number" value={policy.cessPct * 100} onChange={(e) => setPolicy((p) => ({ ...p, cessPct: Number(e.target.value) / 100 }))} className="w-full border rounded px-2 py-1 text-sm" />
          </div>
        </div>
      </div>
    </aside>
  );

  const StatCard = ({ title, value, subtitle }) => (
    <div className="p-3 bg-white rounded shadow-sm border">
      <div className="text-xs text-muted-foreground">{title}</div>
      <div className="text-xl font-semibold">{value}</div>
      {subtitle && <div className="text-xs text-muted-foreground">{subtitle}</div>}
    </div>
  );

  // ======= Panels =======
  function OverviewPanel() {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-4 gap-4">
          <StatCard title="Total Income" value={`₹ ${totals.totalIncome.toLocaleString()}`} />
          <StatCard title="Total Expenses" value={`₹ ${totals.totalExpenses.toLocaleString()}`} />
          <StatCard title="Book Profit" value={`₹ ${Math.round(totals.bookProfit).toLocaleString()}`} />
          <StatCard title="Estimated Tax" value={`₹ ${totals.taxBreakdown.finalTax.toLocaleString()}`} subtitle={`Taxable: ₹${Math.round(totals.taxableForIndividual).toLocaleString()}`} />
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white p-4 rounded shadow-sm border col-span-2">
            <div className="font-semibold mb-2">Tax Components</div>
            <div style={{ height: 240 }}>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={taxComponentData}>
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value">
                    {taxComponentData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-white p-4 rounded shadow-sm border">
            <div className="font-semibold mb-2">Deductions Breakdown</div>
            <div style={{ height: 240 }}>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={deductionChartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                    {deductionChartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="flex justify-between items-center">
            <div className="font-semibold">Recent Documents</div>
            <div className="text-sm text-muted-foreground">{documents.length} files</div>
          </div>
          <div className="mt-2 space-y-1 text-sm">
            {documents.length === 0 && <div className="text-xs text-muted-foreground">No documents uploaded</div>}
            {documents.slice(-5).map((d) => (
              <div key={d.id} className="flex justify-between">
                <div>{d.name}</div>
                <div className="text-xs text-muted-foreground">{Math.round(d.size / 1024)} KB</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  function BooksPanel() {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <div className="font-semibold">Income Entries</div>
          <div>
            <button onClick={addIncomeRow} className="px-3 py-1 bg-sky-600 text-white rounded text-sm">Add Income</button>
            <button onClick={() => { setIncomeRows([{ id: uniqueId(), source: "Sales Revenue", amount: 0, category: "Business" }]); }} className="ml-2 px-3 py-1 bg-gray-200 rounded text-sm">Reset</button>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow-sm border">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left">
                <th className="p-2">Source</th>
                <th className="p-2">Category</th>
                <th className="p-2">Amount (₹)</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {incomeRows.map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="p-2"><input value={r.source} onChange={(e) => updateIncome(r.id, "source", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><input value={r.category} onChange={(e) => updateIncome(r.id, "category", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><input type="number" value={r.amount} onChange={(e) => updateIncome(r.id, "amount", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><button onClick={() => removeIncomeRow(r.id)} className="px-2 py-1 bg-red-500 text-white rounded text-xs">Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex justify-between items-center">
          <div className="font-semibold">Expense Entries</div>
          <div>
            <button onClick={addExpenseRow} className="px-3 py-1 bg-sky-600 text-white rounded text-sm">Add Expense</button>
            <button onClick={() => { setExpenseRows([{ id: uniqueId(), name: "Salaries", amount: 0, category: "Employee" }]); }} className="ml-2 px-3 py-1 bg-gray-200 rounded text-sm">Reset</button>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow-sm border">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left">
                <th className="p-2">Name</th>
                <th className="p-2">Category</th>
                <th className="p-2">Amount (₹)</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {expenseRows.map((r) => (
                <tr key={r.id} className="border-t">
                  <td className="p-2"><input value={r.name} onChange={(e) => updateExpense(r.id, "name", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><input value={r.category} onChange={(e) => updateExpense(r.id, "category", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><input type="number" value={r.amount} onChange={(e) => updateExpense(r.id, "amount", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><button onClick={() => removeExpenseRow(r.id)} className="px-2 py-1 bg-red-500 text-white rounded text-xs">Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function AssetsPanel() {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <div className="font-semibold">Fixed Assets & Depreciation</div>
          <div>
            <button onClick={addAsset} className="px-3 py-1 bg-sky-600 text-white rounded text-sm">Add Asset</button>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow-sm border">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left">
                <th className="p-2">Name</th>
                <th className="p-2">Cost (₹)</th>
                <th className="p-2">Year</th>
                <th className="p-2">Depn Rate (%)</th>
                <th className="p-2">Est Depn (₹)</th>
                <th className="p-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="p-2"><input value={a.name} onChange={(e) => updateAsset(a.id, "name", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><input type="number" value={a.cost} onChange={(e) => updateAsset(a.id, "cost", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><input type="number" value={a.yearOfPurchase} onChange={(e) => updateAsset(a.id, "yearOfPurchase", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2"><input type="number" value={a.depreciationRate} onChange={(e) => updateAsset(a.id, "depreciationRate", e.target.value)} className="w-full border rounded px-2 py-1" /></td>
                  <td className="p-2">₹ {Math.round((a.cost || 0) * ((a.depreciationRate || 0) / 100)).toLocaleString()}</td>
                  <td className="p-2"><button onClick={() => removeAsset(a.id)} className="px-2 py-1 bg-red-500 text-white rounded text-xs">Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  function DeductionsPanel() {
    return (
      <div className="space-y-4">
        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="font-semibold mb-2">Deductions</div>
          <div className="grid grid-cols-3 gap-4">
            {Object.keys(deductions).map((k) => (
              <div key={k} className="space-y-1">
                <div className="text-xs font-medium">{k}</div>
                <input type="number" value={deductions[k]} onChange={(e) => updateDeduction(k, Number(e.target.value))} className="w-full border rounded px-2 py-1" />
              </div>
            ))}
          </div>

          <div className="mt-4 text-sm text-muted-foreground">Attach proofs below to strengthen claims during assessment.</div>
          <div className="mt-2">
            <input type="file" multiple onChange={handleDocumentUpload} />
          </div>
        </div>
      </div>
    );
  }

  function TaxCalcPanel() {
    const tb = totals.taxBreakdown;
    return (
      <div className="space-y-4">
        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="flex justify-between items-center">
            <div>
              <div className="font-semibold">Tax Calculation</div>
              <div className="text-xs text-muted-foreground">Calculated using configurable policy parameters (demo engine)</div>
            </div>
            <div className="text-right">
              <div className="text-sm text-muted-foreground">Taxable Income</div>
              <div className="text-2xl font-bold">₹ {Math.round(totals.taxableForIndividual).toLocaleString()}</div>
              <div className="text-sm text-muted-foreground">Estimated Tax: ₹ {tb.finalTax.toLocaleString()}</div>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-medium">Book Profit</div>
              <div className="text-lg">₹ {Math.round(totals.bookProfit).toLocaleString()}</div>
            </div>
            <div>
              <div className="text-xs font-medium">Total Deductions</div>
              <div className="text-lg">₹ {Math.round(totals.totalDeductions).toLocaleString()}</div>
            </div>
          </div>

          <div className="mt-4">
            <button onClick={() => startEFilingFlow({ profile, totals })} className="px-4 py-2 bg-indigo-600 text-white rounded">Start Filing (Placeholder)</button>
            <button onClick={() => exportPDF(false)} className="ml-2 px-4 py-2 bg-emerald-600 text-white rounded">Export PDF</button>
            <button onClick={() => exportPDF(true)} className="ml-2 px-4 py-2 bg-gray-200 rounded">Preview PDF</button>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="font-semibold mb-2">Tax Audit Report (3CD-like summary)</div>
          <pre className="text-xs bg-slate-50 p-2 rounded max-h-48 overflow-auto">{generate3CDLikeSummary(profile, totals)}</pre>
        </div>
      </div>
    );
  }

  function RecommendationsPanel() {
    return (
      <div className="space-y-4">
        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="font-semibold mb-2">Personalized Recommendations</div>
          <div className="space-y-2">
            {recommendations.map((r) => (
              <div key={r.id} className="p-3 border rounded">
                <div className="font-medium">{r.title}</div>
                <div className="text-sm text-muted-foreground">{r.detail}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="font-semibold mb-2">What a CA would do next</div>
          <ol className="list-decimal list-inside text-sm space-y-1 text-muted-foreground">
            <li>Verify all proofs and cross-check Form 26AS / TDS statements.</li>
            <li>Recommend investments to utilize pending 80C / 80D limits.</li>
            <li>Propose remuneration structure if the entity is a Pvt Ltd / LLP.</li>
            <li>Prepare pre-filled ITR and validate before e-filing.</li>
            <li>Schedule compliance calendar and reminders.</li>
          </ol>
        </div>
      </div>
    );
  }

  function ITRPanel() {
    function downloadITR() {
      const itr = { profile, totals, incomeRows, expenseRows, deductions };
      const blob = new Blob([JSON.stringify(itr, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${profile.businessName || "ITR"}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }

    return (
      <div className="space-y-4">
        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="font-semibold mb-2">ITR Preparation (Pre-fill)</div>
          <div className="text-sm text-muted-foreground">This pre-fill allows editing before generating the final ITR-ready document.</div>

          <div className="mt-4 grid grid-cols-2 gap-4">
            <div>
              <div className="text-xs">Total Income</div>
              <div className="text-lg font-semibold">₹ {totals.totalIncome.toLocaleString()}</div>
            </div>
            <div>
              <div className="text-xs">Total Deductions</div>
              <div className="text-lg font-semibold">₹ {Math.round(totals.totalDeductions).toLocaleString()}</div>
            </div>
          </div>

          <div className="mt-4">
            <button onClick={downloadITR} className="px-3 py-2 bg-emerald-600 text-white rounded">Download ITR (JSON)</button>
            <button onClick={() => startEFilingFlow({ profile, totals, itrType: "ITR-3" })} className="ml-2 px-3 py-2 bg-indigo-600 text-white rounded">E-sign & File (Placeholder)</button>
          </div>
        </div>

        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="font-semibold mb-2">Validation Checklist</div>
          <ul className="list-disc list-inside text-sm text-muted-foreground">
            <li>PAN is provided and valid pattern</li>
            <li>All major incomes have supporting documents</li>
            <li>Deductions have proofs attached</li>
            <li>Form 16/26AS reconciled if salaried income exists</li>
          </ul>
        </div>
      </div>
    );
  }

  function CompliancePanel() {
    const reminders = [
      { id: 1, title: "TDS deposit", due: "07-07-2026" },
      { id: 2, title: "GST filing", due: "20-07-2026" },
      { id: 3, title: "ITR filing", due: "31-07-2026" },
    ];
    return (
      <div className="space-y-4">
        <div className="bg-white p-4 rounded shadow-sm border">
          <div className="font-semibold mb-2">Compliance Calendar</div>
          <div className="space-y-2">
            {reminders.map((r) => (
              <div key={r.id} className="flex justify-between p-2 border rounded">
                <div>
                  <div className="font-medium">{r.title}</div>
                  <div className="text-xs text-muted-foreground">Action: Ensure payment or return filed</div>
                </div>
                <div className="text-sm font-semibold">{r.due}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  // ======= Utilities =======
  function generate3CDLikeSummary(profileParam, totalsParam) {
    return `Tax Audit Summary (demo)
Company: ${profileParam.businessName}
FY: ${profileParam.fy}
Book Profit: ₹ ${Math.round(totalsParam.bookProfit).toLocaleString()}
Total Deductions: ₹ ${Math.round(totalsParam.totalDeductions).toLocaleString()}
Taxable: ₹ ${Math.round(totalsParam.taxableForIndividual).toLocaleString()}
Estimated Tax: ₹ ${Math.round(totalsParam.taxBreakdown.finalTax).toLocaleString()}
`;
  }

  // ======= Render =======
  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">
      <Header />
      <div className="flex">
        <Sidebar />
        <main className="flex-1 p-6">
          <div className="bg-transparent">
            {activeTab === "overview" && <OverviewPanel />}
            {activeTab === "books" && <BooksPanel />}
            {activeTab === "assets" && <AssetsPanel />}
            {activeTab === "deductions" && <DeductionsPanel />}
            {activeTab === "taxcalc" && <TaxCalcPanel />}
            {activeTab === "recommend" && <RecommendationsPanel />}
            {activeTab === "itr" && <ITRPanel />}
            {activeTab === "compliance" && <CompliancePanel />}
            <div className="mt-4 text-sm text-muted-foreground">{message}</div>
          </div>
        </main>
      </div>
    </div>
  );
}

// ----------------- Export helper aliases for unit testing -----------------
export {
  computeDepreciation as _computeDepreciation,
  computeSlabTax as _computeSlabTax,
  computeSurchargeForIndividual as _computeSurchargeForIndividual,
  computeCorporateTax as _computeCorporateTax,
  computeMAT as _computeMAT,
  computeAMT as _computeAMT,
};
