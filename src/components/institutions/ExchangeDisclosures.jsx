import { useEffect, useState } from 'react';
const FEED = 'https://raw.githubusercontent.com/shivamagw06-dev/AGI/investor-valuation-data/investor-filings/latest.json';
export function useInvestorDisclosures(investorId, enabled) {
  const [data, setData] = useState(null);
  const [unavailable, setUnavailable] = useState(false);
  useEffect(() => {
    if (!enabled) return;
    const controller = new AbortController();
    const load = () => fetch(FEED, { cache: 'no-store', signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]) })
      .then(r => { if (!r.ok) throw Error('Unavailable'); return r.json(); })
      .then(value => {
        if (!controller.signal.aborted && value.schemaVersion === 1 && value.profiles && Number.isFinite(Date.parse(value.updatedAt))) { setData(value); setUnavailable(false); }
      }).catch(() => { if (!controller.signal.aborted) setUnavailable(true); });
    load();
    const timer = setInterval(() => { if (!document.hidden) load(); }, 60000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [enabled]);
  return { data: enabled ? data : null, profile: enabled ? data?.profiles?.[`in-${investorId}`] : null, unavailable };
}
