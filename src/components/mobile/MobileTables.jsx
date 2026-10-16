import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import usePhone from './usePhone';
import './mobile.css';

// Enrich existing semantic tables without copying data or changing their calculations.
// Only simple, one-header tables become labelled cards. Matrix/merged tables scroll.
export default function MobileTables() {
  const phone = usePhone();
  const { pathname } = useLocation();
  useEffect(() => {
    if (!phone) return;
    let frame;
    const cleanups = new Map();
    const scan = () => {
      document.querySelectorAll('table').forEach(table => {
        if (table.closest('[data-mobile-table="off"], .recharts-wrapper, [contenteditable="true"]')) return;
        const heads = [...(table.tHead?.rows || [])];
        const headers = heads.length === 1 ? [...heads[0].cells] : [];
        const labels = headers.map(h => h.textContent.trim());
        if (!headers.length) return;
        if (!cleanups.has(table)) cleanups.set(table, new Set());
        const cells = cleanups.get(table);
        const simple = headers.every(h => h.colSpan === 1 && h.rowSpan === 1) && !table.querySelector('tbody th');
        table.classList.toggle('mobile-data-table', simple);
        table.classList.toggle('mobile-matrix-table', !simple);
        if (!simple) return;
        for (const body of table.tBodies) for (const row of body.rows) {
          const normal = row.cells.length === labels.length && [...row.cells].every(c => c.colSpan === 1 && c.rowSpan === 1);
          row.classList.toggle('mobile-data-row', normal);
          row.classList.toggle('mobile-detail-row', !normal);
          if (normal) [...row.cells].forEach((cell, i) => {
            if (cell.dataset.mobileLabel !== labels[i]) cell.dataset.mobileLabel = labels[i];
            cells.add(cell);
          });
        }
      });
    };
    const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(scan); };
    const observer = new MutationObserver(schedule);
    observer.observe(document.getElementById('root'), {childList:true, subtree:true, characterData:true});
    scan();
    return () => {
      observer.disconnect(); cancelAnimationFrame(frame);
      for (const [table, cells] of cleanups) {
        table.classList.remove('mobile-data-table', 'mobile-matrix-table');
        table.querySelectorAll('tr').forEach(r => r.classList.remove('mobile-data-row','mobile-detail-row'));
        cells.forEach(c => delete c.dataset.mobileLabel);
      }
    };
  }, [phone, pathname]);
  return null;
}
