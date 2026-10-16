const labels = { NIFTYBANK:'Banking', NIFTYIT:'IT', NIFTYAUTO:'Auto', NIFTYFMCG:'FMCG', NIFTYPHARMA:'Pharma', NIFTYMETAL:'Metals', NIFTYREALTY:'Realty', NIFTYPSUBANK:'PSU banks', FINNIFTY:'Financial services', NIFTYENERGY:'Energy', NIFTYMEDIA:'Media' };
const finite = value => value !== null && value !== undefined && value !== '' && Number.isFinite(Number(value));
const name = row => labels[row.sector] || row.sector;
export function sectorRotationSummary(rows = []) {
  const valid = rows.filter(r => finite(r.relative_20d) && finite(r.relative_60d));
  if (!valid.length) return 'No complete sector readings are available yet. The summary will appear when the next successful run supplies data.';
  const strongest = [...valid].sort((a,b) => Number(b.relative_20d)-Number(a.relative_20d))[0];
  const relative = Number(strongest.relative_20d);
  const sentences = [`${name(strongest)} has the strongest 20-day relative reading: ${Math.abs(relative).toFixed(2)} percentage points ${relative >= 0 ? 'ahead of' : 'behind'} Nifty.`];
  if (finite(strongest.return_20d) && Number(strongest.return_20d) < 0) sentences.push(`It still fell ${Math.abs(Number(strongest.return_20d)).toFixed(2)}% over those 20 trading days.`);
  const weakening = valid.filter(r => Number(r.relative_20d)<0 && Number(r.relative_60d)>=0);
  if (weakening.length) sentences.push(`Weakening: ${weakening.map(name).join(', ')}.`);
  return sentences.join(' ');
}
