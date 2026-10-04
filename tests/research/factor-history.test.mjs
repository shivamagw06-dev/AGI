import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {factorWindow,startForPeriod} from '../../src/lib/factorHistory.mjs';
const data=JSON.parse(readFileSync(new URL('../../src/data/jpm-factor-history.json',import.meta.url)));
test('main-sheet returns retain the disclosed cache discrepancy',()=>{
 const r=factorWindow(data,'2025-12-31','2026-08-14');
 for(const check of data.reconciliation){assert.ok(Math.abs(r.returns[check.factor]-check.sourceReturnPct)<1e-9);assert.notEqual(check.sourceReturnPct,check.returnPct);}
 assert.equal(r.points.length,163);
});
test('one month uses 30 calendar days; calendar month offsets clamp',()=>{
 assert.equal(startForPeriod('2026-09-30','30D'),'2026-08-31');
 assert.equal(startForPeriod('2026-05-31','3M'),'2026-02-28');
 assert.equal(startForPeriod('2024-02-29','1Y'),'2023-02-28');
});
test('range rebases at prior close, compounds rather than sums',()=>{
 const d={baselineDate:'2026-01-01',asOf:'2026-01-06',keys:['x'],rows:[['2026-01-02',.5],['2026-01-05',.1],['2026-01-06',-.1]]};
 const r=factorWindow(d,'2026-01-03','2026-01-06');
 assert.equal(r.start,'2026-01-02');assert.ok(Math.abs(r.returns.x+1)<1e-10);assert.equal(r.points[0].x,100);
 assert.ok(factorWindow(d,'2026-01-06','2026-01-06').error);
 assert.ok(factorWindow(d,'2026-01-01','2026-01-07').error);
});
test('all source values finite, dates unique and ordered; no interior missing rows',()=>{
 assert.equal(data.rows.length,4368);assert.equal(data.rows.at(-1)[0],'2026-09-30');
 let prev=data.baselineDate;
 for(const [date,...values] of data.rows){assert.ok(date>prev);prev=date;assert.equal(values.length,5);values.forEach(v=>assert.ok(Number.isFinite(v)&&v>-1));}
 const r=factorWindow(data,data.baselineDate,data.asOf);assert.equal(r.points.length,4369);assert.equal(r.points[0].momentum,100);
});
