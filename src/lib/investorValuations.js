import { useEffect, useState } from 'react';

export function useInvestorValuations() {
  const [snapshot, setSnapshot] = useState(null);
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const load = () => fetch('https://raw.githubusercontent.com/shivamagw06-dev/AGI/investor-valuation-data/investor-valuations/latest.json', {
      cache: 'no-store', signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
    }).then(r => { if (!r.ok) throw Error('Unavailable'); return r.json(); })
      .then(data => { if (active && data.schemaVersion === 1 && data.profiles && Number.isFinite(Date.parse(data.updatedAt))) setSnapshot(data); })
      .catch(() => { /* Published disclosure data remains available if pricing is down. */ });
    load();
    const timer = setInterval(() => { if (!document.hidden) load(); }, 60000);
    return () => { active = false; controller.abort(); clearInterval(timer); };
  }, []);
  return snapshot;
}

export async function valuationFingerprint(profile) {
  const inputs = [profile.reportPeriod ?? null, profile.rows.map(r => ['stock', 'quantity', 'security', 'cusip'].map(k => r[k] ?? null))];
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(JSON.stringify(inputs)));
  return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
}
export function valuationMoney(value, country) {
  if (!Number.isFinite(value)) return 'Not priced';
  return `${country === 'IN' ? '₹' : '$'}${(value / (country === 'IN' ? 1e7 : 1e6)).toLocaleString('en-IN', { maximumFractionDigits: 2 })} ${country === 'IN' ? 'Cr' : 'M'}`;
}
export function valuationTime(value) {
  return new Date(value).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' }) + ' IST';
}
export function valuationStale(snapshot) {
  return !snapshot || Date.now() - Date.parse(snapshot.updatedAt) > 36 * 3600000;
}
