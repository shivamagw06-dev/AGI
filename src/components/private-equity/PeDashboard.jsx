import {
  Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

const CHART_COLORS = ['#c9a227', '#d4af37', '#8b7355', '#6b7280', '#4b5563', '#374151'];

function KpiGrid({ kpis }) {
  const cards = [
    { label: 'PE Firms Covered', value: kpis.firmsCovered },
    { label: 'Portfolio Companies', value: kpis.portfolioCompanies?.toLocaleString() },
    { label: 'Active Funds', value: kpis.activeFunds },
    { label: 'Recent Transactions', value: kpis.recentTransactions },
    { label: 'Exits YTD', value: kpis.exitsYtd },
    { label: 'Industries', value: kpis.industriesCovered },
    { label: 'Countries', value: kpis.countriesCovered },
    { label: 'KG Relationships', value: kpis.knowledgeGraphEdges?.toLocaleString() },
  ];
  return (
    <div className="pe-kpi-grid">
      {cards.map((c) => (
        <div key={c.label} className="pe-glass pe-kpi">
          <div className="pe-kpi-value">{c.value}</div>
          <div className="pe-kpi-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

function TransactionTable({ rows }) {
  return (
    <div className="pe-table-wrap pe-glass">
      <table className="pe-table">
        <thead>
          <tr>
            <th>Buyer</th>
            <th>Target</th>
            <th>Deal Value</th>
            <th>EV</th>
            <th>Industry</th>
            <th>Country</th>
            <th>Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.buyer}</td>
              <td>{r.target}</td>
              <td className="pe-gold">{r.dealValue}</td>
              <td>{r.enterpriseValue}</td>
              <td>{r.industry}</td>
              <td>{r.country}</td>
              <td>{r.date}</td>
              <td><span className="pe-badge">{r.status}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FundCards({ funds }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {funds.map((f) => (
        <div key={f.id} className="pe-glass p-4">
          <div className="font-semibold text-sm">{f.name}</div>
          <div className="grid grid-cols-2 gap-2 mt-3 text-xs text-[var(--pe-text-muted)]">
            <span>Vintage {f.vintage}</span>
            <span className="pe-gold font-semibold">{f.fundSize}</span>
            <span>{f.strategy}</span>
            <span>{f.status}</span>
            <span className="col-span-2">GP: {f.gp}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function SectorHeatmap({ sectors, activeSector, onSelect }) {
  return (
    <div className="pe-sector-grid">
      {sectors.map((s) => (
        <button
          key={s.name}
          type="button"
          onClick={() => onSelect(s.name === activeSector ? null : s.name)}
          className={`pe-glass pe-sector-card ${activeSector === s.name ? 'active' : ''}`}
        >
          <div className="text-xs font-medium">{s.name}</div>
          <div className="pe-sector-heat" style={{ width: `${s.heat}%`, margin: '8px auto 0' }} />
        </button>
      ))}
    </div>
  );
}

function GeoDistribution({ regions }) {
  return (
    <div>
      {regions.map((r) => (
        <div key={r.id} className="pe-geo-bar">
          <span className="w-28 text-xs">{r.name}</span>
          <div className="pe-geo-bar-track">
            <div className="pe-geo-bar-fill" style={{ width: `${r.pct}%` }} />
          </div>
          <span className="text-xs w-8 text-right">{r.pct}%</span>
        </div>
      ))}
    </div>
  );
}

function AiInsightsPanel({ insights }) {
  const rows = Object.values(insights || {});
  return (
    <div className="pe-glass p-4">
      {rows.map((item) => (
        <div key={item.label} className="pe-insight-row">
          <div>
            <div className="text-[var(--pe-text-muted)] text-xs">{item.label}</div>
            <div className="font-medium mt-0.5">{item.value}</div>
            {item.detail && <div className="text-xs text-[var(--pe-text-muted)] mt-0.5">{item.detail}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}

function CaseStudyCards({ items }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {items.map((c) => (
        <div key={c.id} className="pe-glass p-4">
          <span className="pe-badge">{c.sector}</span>
          <h4 className="text-sm font-semibold mt-2">{c.title}</h4>
          <p className="text-xs text-[var(--pe-text-muted)] mt-2"><strong>Thesis:</strong> {c.thesis}</p>
          <p className="text-xs text-[var(--pe-text-muted)] mt-1"><strong>Value:</strong> {c.valueCreation}</p>
        </div>
      ))}
    </div>
  );
}

export default function PeDashboard({
  data,
  activeSector,
  onSectorSelect,
}) {
  if (!data) return null;

  const sectorChart = data.sectors?.slice(0, 6).map((s) => ({ name: s.name, value: s.heat })) || [];

  return (
    <main className="pe-col-main space-y-8">
      <section>
        <p className="pe-eyebrow mb-2">Institutional Research Terminal</p>
        <h1 className="pe-title text-3xl md:text-4xl">Private Equity Intelligence</h1>
        <p className="text-[var(--pe-text-muted)] mt-3 max-w-2xl text-sm leading-relaxed">
          Global Private Equity Research, Portfolio Intelligence, Transactions, Fund Analytics and Institutional Insights.
        </p>
      </section>

      <section className="pe-section">
        <KpiGrid kpis={data.kpis} />
      </section>

      <section className="pe-section">
        <h2 className="pe-section-title">Recent Transactions</h2>
        <TransactionTable rows={data.transactions} />
      </section>

      <section className="pe-section">
        <h2 className="pe-section-title">Latest Fund Activity</h2>
        <FundCards funds={data.funds} />
      </section>

      <section className="pe-section">
        <h2 className="pe-section-title">Sector Heatmap</h2>
        <SectorHeatmap sectors={data.sectors} activeSector={activeSector} onSelect={onSectorSelect} />
      </section>

      <section className="pe-section grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <h2 className="pe-section-title">Geographic Distribution</h2>
          <div className="pe-glass p-4">
            <GeoDistribution regions={data.regions} />
          </div>
        </div>
        <div>
          <h2 className="pe-section-title">Sector Activity</h2>
          <div className="pe-glass pe-chart-card">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={sectorChart}>
                <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} angle={-25} textAnchor="end" height={60} />
                <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
                <Tooltip contentStyle={{ background: '#12141a', border: '1px solid rgba(255,255,255,0.1)' }} />
                <Bar dataKey="value" fill="#c9a227" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </section>

      <section className="pe-section">
        <h2 className="pe-section-title">Latest Case Studies</h2>
        <CaseStudyCards items={data.caseStudies} />
      </section>

      <section className="pe-section">
        <h2 className="pe-section-title">AI Insights Panel</h2>
        <AiInsightsPanel insights={data.aiInsights} />
      </section>
    </main>
  );
}

export function PeFirmAnalytics({ analytics }) {
  if (!analytics) return null;
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="pe-glass pe-chart-card">
        <h4 className="text-sm font-semibold mb-3">Portfolio by Industry</h4>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={analytics.byIndustry.slice(0, 6)} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name }) => name?.slice(0, 12)}>
              {analytics.byIndustry.slice(0, 6).map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: '#12141a', border: '1px solid rgba(255,255,255,0.1)' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="pe-glass pe-chart-card">
        <h4 className="text-sm font-semibold mb-3">Investments by Year</h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={analytics.byYear.slice(-8)}>
            <XAxis dataKey="name" tick={{ fill: '#9ca3af', fontSize: 10 }} />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} />
            <Bar dataKey="value" fill="#c9a227" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
