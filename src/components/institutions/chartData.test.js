import test from 'node:test';
import assert from 'node:assert/strict';
import {portfolioChartData} from './chartData.js';
test('counts additions once per investor and excludes missing changes',()=>{
 const data=portfolioChartData([{name:'A',change:null,bought:[{label:'Stock +2%'},{label:'Stock ↑ 3%'}],sectors:[{label:'Tech (20%)'},{label:'Banking (80%)'}]},{name:'B',change:0,bought:[{label:'Stock 1%'}],sectors:[]}]);
 assert.equal(data.changes.length,1);assert.equal(data.additions[0].count,2);assert.equal(data.additions[0].name,'Stock');assert.deepEqual(data.sectors,[{name:'Banking',count:1}]);assert.equal(data.sectorCount,1);
});
test('sector grouping preserves total counts and empty data stays empty',()=>{
 const data=portfolioChartData(Array.from({length:8},(_,i)=>({sectors:[{label:`Sector ${i} (50%)`}]})));
 assert.equal(data.sectors.length,6);assert.equal(data.sectors.reduce((n,x)=>n+x.count,0),8);
 assert.deepEqual(portfolioChartData([]),{changes:[],additions:[],sectors:[],sectorCount:0});
});
