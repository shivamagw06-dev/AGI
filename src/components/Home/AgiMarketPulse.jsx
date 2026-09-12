import useMarketDashboard from '@/hooks/useMarketDashboard';

function PulseRow({ label, value, highlight }) {
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-[#eeeeee] last:border-0">
      <span className="text-xs text-[#767676]">{label}</span>
      <span className={`text-sm font-bold ${highlight ? 'text-[#111111]' : 'text-[#333333]'}`}>
        {value ?? '—'}
      </span>
    </div>
  );
}

export default function AgiMarketPulse() {
  const { pulse, outlook, loading } = useMarketDashboard();

  if (loading) {
    return (
      <div className="border border-[#dddddd] p-5 animate-pulse">
        <div className="h-4 w-32 bg-[#eee] mb-4" />
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-6 bg-[#eee]" />
          ))}
        </div>
      </div>
    );
  }

  const p = pulse || {};
  const reasons = p.reasons || outlook?.reasons || [];

  return (
    <div className="border border-[#dddddd] bg-white">
      <div className="px-5 py-4 border-b border-[#eeeeee]">
        <h2 className="text-sm font-bold text-[#111111]">AGI Market Pulse</h2>
        <p className="text-[11px] text-[#767676] mt-0.5">
          Proprietary analytics · AGI Score {p.agiMarketScore ?? outlook?.agiMarketScore ?? '—'}/100
        </p>
      </div>

      <div className="px-5 py-2">
        <PulseRow
          label="Market Outlook"
          value={`${p.outlookBadge || ''} ${p.outlook || 'Neutral'}`.trim()}
          highlight
        />
        <PulseRow label="Confidence" value={p.confidence ? `${p.confidence}%` : '—'} highlight />
        <PulseRow label="Momentum" value={p.momentum} />
        <PulseRow label="Risk" value={p.risk} />
        <PulseRow label="Volatility" value={p.volatility} />
        <PulseRow label="Opening Bias" value={p.openingBias} />
        <PulseRow label="Market Breadth" value={p.marketBreadth} />
        <PulseRow label="Top Sector" value={p.topSector} />
        <PulseRow label="Weakest Sector" value={p.weakestSector} />
      </div>

      {reasons.length > 0 && (
        <div className="px-5 py-4 bg-[#fafafa] border-t border-[#eeeeee]">
          <p className="text-[10px] font-bold uppercase tracking-wide text-[#767676] mb-2">Reasons</p>
          <ul className="space-y-1.5">
            {reasons.map((r, i) => (
              <li key={i} className="text-xs text-[#444444] flex items-start gap-1.5">
                <span>{r.type === 'positive' ? '✓' : '✗'}</span>
                <span>{r.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="px-5 py-2.5 border-t border-[#eeeeee] text-[10px] text-[#767676]">
        Updated {p.updatedLabel || 'recently'} · Not raw exchange data
      </div>
    </div>
  );
}
