import test from 'node:test';
import assert from 'node:assert/strict';
import {publicWebsiteStats} from './publicWebsiteStats.js';
import {analyticsClientInfo} from '../../src/lib/analyticsClientInfo.js';
test('public statistics project only coarse aggregates',()=>{
 const result=publicWebsiteStats({ok:true,days:1,visitors:3,active:1,secret:'private',visitorIds:['person'],pages:[{label:'/portfolio/private-owner',views:2},{label:'/institutions/in/alice',views:3},{label:'/finance-tools',views:5}],referrers:[{label:'private.internal-company.example',views:2},{label:'google.com',views:4}],browsers:[{label:'Chrome',views:4},{label:'private-user-agent',views:1}],trend:[{date:'2026-09-28T10:00',visitors:3,views:5,ids:['secret']} ]});
 const json=JSON.stringify(result);for(const forbidden of ['private-owner','alice','internal-company','private-user-agent','visitorIds','secret'])assert.ok(!json.includes(forbidden));
 assert.equal(result.visitors,3);assert.equal(result.pages.find(r=>r.label==='Tools directory').views,5);assert.equal(result.channels.find(r=>r.label==='Search').views,4);assert.equal(result.browsers.find(r=>r.label==='Unknown').views,1);
});
test('client metadata uses coarse enums',()=>{assert.deepEqual(analyticsClientInfo('Mozilla Windows Chrome/123 Edg/123'),{browser:'Edge',os:'Windows'});assert.deepEqual(analyticsClientInfo('iPhone Safari/604'),{browser:'Safari',os:'iOS'});assert.deepEqual(analyticsClientInfo('private custom device'),{browser:'Other',os:'Other'});});
