import { createHash } from 'node:crypto';

export const FEEDS = [
  { id: 'usgs', name: 'USGS earthquakes', url: 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson', homepage: 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php', description: 'Magnitude 4.5+ earthquakes in the past seven days. Preliminary locations and magnitudes may be revised.' },
  { id: 'eonet', name: 'NASA EONET', url: 'https://eonet.gsfc.nasa.gov/api/v3/events?days=30&status=all&limit=100', homepage: 'https://eonet.gsfc.nasa.gov/docs/v3', description: 'Up to 100 natural events from a 30-day query. Latest point location only; this is not a hazard footprint or complete storm track.' },
];
export const cleanText = (value, max = 500) => String(value ?? '').replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max);
export function safeUrl(value) {
  try {
    const u = new URL(String(value));
    if (u.protocol !== 'https:' || u.username || u.password || !u.hostname.includes('.') || /^(localhost|127\.|10\.|192\.168\.|169\.254\.)/.test(u.hostname)) return null;
    return u.href;
  } catch { return null; }
}
export function coordinate(value, max) {
  if (value === null || value === undefined || value === '' || typeof value === 'boolean') return null;
  const n = Number(value); return Number.isFinite(n) && Math.abs(n) <= max ? n : null;
}
export function dateValue(value) {
  if (value === null || value === undefined || value === '') return null;
  const d = new Date(value); return Number.isFinite(d.getTime()) ? d.toISOString() : null;
}
export function eventHash(event) {
  // Freshness timestamps are deliberately excluded: polling must not invalidate a review.
  return createHash('sha256').update(JSON.stringify([event.title, event.category, event.latitude, event.longitude, event.observed_at, event.source_url, event.source_status, event.magnitude ?? null])).digest('hex');
}
export function normaliseFeed(id, payload) {
  if (!['usgs','eonet'].includes(id)) throw new Error('Unknown source');
  if (id === 'usgs' && !Array.isArray(payload?.features)) throw new Error('Invalid USGS response');
  if (id === 'eonet' && !Array.isArray(payload?.events)) throw new Error('Invalid EONET response');
  const records = id === 'usgs' ? payload.features : payload.events;
  return [...new Map(records.slice(0,500).filter(r=>r && r.id).map(r=>[r.id,r])).values()].flatMap((r) => {
    let item;
    if (id === 'usgs') {
      const p = r.properties || {}; const c = r.geometry?.type === 'Point' ? r.geometry.coordinates : [];
      item = { external_id: cleanText(r.id, 160), title: cleanText(p.title, 300), category: 'Earthquake', latitude: coordinate(c?.[1], 90), longitude: coordinate(c?.[0], 180), observed_at: dateValue(p.time), source_updated_at: dateValue(p.updated), source_url: safeUrl(p.url), source_status: 'Reported', magnitude: Number.isFinite(p.mag) ? p.mag : null };
    } else {
      const points = (Array.isArray(r.geometry) ? r.geometry : []).filter(g => g.type === 'Point' && dateValue(g.date)).sort((a,b) => new Date(b.date) - new Date(a.date));
      const g = points[0];
      item = { external_id: cleanText(r.id, 160), title: cleanText(r.title, 300), category: cleanText(r.categories?.[0]?.title || 'Natural event', 80), latitude: coordinate(g?.coordinates?.[1],90), longitude: coordinate(g?.coordinates?.[0],180), observed_at: dateValue(g?.date), source_updated_at: null, source_url: safeUrl(r.sources?.find(s => safeUrl(s.url))?.url) || `https://eonet.gsfc.nasa.gov/api/v3/events/${encodeURIComponent(r.id)}`, source_status: r.closed ? 'Closed by source' : 'Open at source', magnitude: null };
    }
    if (!item.external_id || !item.title || !item.observed_at || item.latitude === null || item.longitude === null || !item.source_url) return [];
    const event = { ...item, provider: id, id: `${id}:${item.external_id}`, published_at: null };
    return [{ ...event, content_hash: eventHash(event) }];
  });
}
export function distanceKm(a, b) {
  const rad = n => n * Math.PI / 180;
  const dlat = rad(b.latitude - a.latitude), dlon = rad(b.longitude - a.longitude);
  const h = Math.sin(dlat/2)**2 + Math.cos(rad(a.latitude))*Math.cos(rad(b.latitude))*Math.sin(dlon/2)**2;
  return 6371 * 2 * Math.asin(Math.sqrt(Math.min(1, Math.max(0,h))));
}
export function matchAssets(event, assets, radiusKm = 100) {
  return assets.map(asset => ({ asset_id: asset.id, symbol: asset.symbol, company: asset.company, name: asset.name, distance_km: Math.round(distanceKm(event, asset)*10)/10, location_precision: asset.location_precision, basis: 'Geographic proximity only; operational impact is not established.' }))
    .filter(m => m.distance_km <= radiusKm).sort((a,b)=>a.distance_km-b.distance_km);
}
export function validateAsset(input) {
  const asset = Object.fromEntries(['symbol','company','name','sector','relationship','evidence_note','location_precision'].map(k=>[k,cleanText(input[k], k==='evidence_note'?1500:150)]));
  asset.symbol = asset.symbol.toUpperCase();
  asset.latitude = coordinate(input.latitude,90); asset.longitude = coordinate(input.longitude,180); asset.source_url = safeUrl(input.source_url);
  if (!/^[A-Z0-9&.-]{1,25}$/.test(asset.symbol) || !asset.company || !asset.name || !asset.sector || !asset.evidence_note || !asset.relationship || !asset.location_precision || !asset.source_url || asset.latitude===null || asset.longitude===null) throw new Error('A company, symbol, asset, sector, relationship, evidence, HTTPS source, coordinate precision and valid coordinates are required.');
  asset.confidence = input.confidence;
  if (!['confirmed','estimated'].includes(asset.confidence)) throw new Error('Choose confirmed or estimated relationship confidence.');
  return asset;
}
export function validateReview(input) {
  const review = { status: input.status, assessment: cleanText(input.assessment,3000), uncertainty: cleanText(input.uncertainty,1500), next_check: cleanText(input.next_check,1500), evidence_url: safeUrl(input.evidence_url), content_hash: cleanText(input.content_hash,64) };
  if (!['published','rejected'].includes(review.status) || !/^[a-f0-9]{64}$/.test(review.content_hash)) throw new Error('Choose a review decision and reload the current event before reviewing.');
  if (!review.assessment || (review.status==='published' && (!review.uncertainty || !review.next_check || !review.evidence_url))) throw new Error('Published assessments require an explanation, uncertainty, next evidence to check and an HTTPS evidence link.');
  return review;
}
