import test from 'node:test';
import assert from 'node:assert/strict';
import { numeric, sourceDate, normalizeResearchSnapshot, ownershipPeriods, buildScreenerIntelligence as build } from './screenerIntelligence.js';
const now='2026-10-28T12:00:00Z';
const snap=(columns,rows,more={})=>({id:1,as_of:'2026-10-28',created_at:now,columns,rows,...more});
test('missing values remain missing, date parsing rejects invalid calendar days',()=>{
  for(const v of ['',null,'-','N/A','Infinity',false])assert.equal(numeric(v),null);
  assert.equal(numeric('1,234.5%'),1234.5);assert.equal(numeric('−4.2'),-4.2);assert.equal(numeric('0'),0);
  assert.equal(sourceDate('30 Sep, 2026'),'2026-09-30');assert.equal(sourceDate('2026-02-30'),null);assert.equal(sourceDate('31 Feb, 2026'),null);
});
test('growth metrics use positive baselines and exclude unavailable denominators',()=>{
  const r=build({slug:'agi-growth-candidates',snapshot:snap(['Stock Name','Forecaster Estimates 1Y forward EPS Annual','Forecaster Estimates 2Y forward EPS Annual'],[['A','10','15'],['B','0','5'],['C','','10'],['D','-5','5']]),now});
  assert.equal(r.cards[0].value,'50%');assert.match(r.cards[0].detail,/1 of 4/);assert.equal(r.cards[1].value,'Unavailable');
});
test('ownership freshness uses completed quarter, preserving older and non-quarter-end observations',()=>{
  const s=normalizeResearchSnapshot('fii-holding-increases',snap(['Stock Name','Shareholding Date'],[['A','30 Sep, 2026'],['B','31 Dec, 2022'],['C','17 Oct, 2026'],['D','-']]));
  assert.deepEqual(ownershipPeriods(s.rows,s.as_of),{expected:'2026-09-30',current:1,older:1,other:1,missing:1});
  const r=build({slug:'fii-holding-increases',snapshot:snap(['Stock Name','Shareholding Date'],[['A','31 Dec, 2022']]),now});assert.match(r.evidence[0],/Mixed/);
});
test('cross-screen context separates identifiers and provisional names, excludes different dates and historical views',()=>{
  const target=snap(['Stock Name','Stock Code'],[['Same','AAA'],['Name only','']]);
  const universe=[{...snap(['Stock Name','Stock Code'],[['Same','BBB'],['Name only','']]),slug:'other',display_name:'Other'},{...snap(['Stock Name','Stock Code'],[['Same','AAA']],{as_of:'2026-10-15'}),slug:'old'}];
  const r=build({slug:'volume-breakouts',snapshot:target,universe,now});assert.equal(r.overlaps.length,1);assert.equal(r.overlaps[0].identified,0);assert.equal(r.overlaps[0].provisional,1);
  assert.equal(build({slug:'volume-breakouts',snapshot:target,universe,historical:true,now}).overlaps.length,0);
});
test('new identity coverage withholds apparent churn; stable IDs track changes',()=>{
  const old=snap(['Stock Name'],[['A']]);const current=snap(['Stock Name','Stock Code'],[['A','AAA']]);
  assert.equal(build({slug:'golden-cross',snapshot:current,previous:old,now}).changes.available,false);
  const r=build({slug:'golden-cross',snapshot:current,previous:snap(['Stock Name','Stock Code'],[['B','BBB']]),now});assert.equal(r.changes.added,1);assert.equal(r.changes.removed,1);
});
test('legacy FCF zeros do not count as positive; stale source dates are not refreshed by recalculation',()=>{
  const r=build({slug:'cash-flow',snapshot:{id:1,as_of:'2026-10-15',rows:[{stock:'A',fcf:[1,2,3,4,5,6]},{stock:'B',fcf:[0,2,3,4,5,6]}]},now});
  assert.equal(r.cards[0].value,'1 / 2');assert.equal(r.ageDays,13);assert.match(r.evidence[0],/13 calendar days/);assert.match(r.performance,/not measured/);
});
test('relative strength distinguishes absolute losses; provider score is not confidence',()=>{
  const r=build({slug:'relative-strength',snapshot:snap(['Stock Name','Qtr Change %','Sector Qtr Change %'],[['A','-2','-5'],['B','5','1']]),now});assert.equal(r.cards[0].value,'3.5 pp');assert.equal(r.cards[1].value,'1');
  assert.match(build({slug:'momentum',snapshot:{id:1,as_of:'2026-10-28',rows:[{stock:'A',score:99,relativeWeekChange:2}]},now}).cards[0].detail,/not a probability/);
});
test('All-Weather counts related factor membership provisionally, with no historical look-ahead',()=>{
  const universe=['agi-momentum-candidates','agi-value-candidates','agi-growth-candidates','agi-quality-candidates'].map((slug,i)=>({...snap(['Stock Name'],i===3?[['A']]:[['A'],['B']]),slug}));
  const snapshot=snap(['Stock Name'],[['A'],['B']]);
  const r=build({slug:'agi-all-weather-candidates',snapshot,universe,now});assert.equal(r.cards[0].value,'1');assert.equal(r.cards[1].value,'2');assert.match(r.cards[0].detail,/Provisional/);
  assert.equal(build({slug:'agi-all-weather-candidates',snapshot,universe,historical:true,now}).cards[0].value,'Unavailable');
});
test('ownership overlaps exclude mismatched reporting periods even when import dates agree',()=>{
  const snapshot=snap(['Stock Name','Stock Code','Shareholding Date'],[['A','AAA','30 Sep, 2026'],['B','BBB','31 Mar, 2025']]);
  const other={...snap(['Stock Name','Stock Code','Shareholding Date'],[['A','AAA','30 Sep, 2026'],['B','BBB','30 Sep, 2026']]),slug:'dii-holding-increases'};
  const r=build({slug:'fii-holding-increases',snapshot,universe:[other],now});assert.equal(r.overlaps[0].identified,1);assert.equal(r.overlaps[0].period,'2026-09-30');
});
