import test from 'node:test';
import assert from 'node:assert/strict';
import {readModelStore,writeModelStore,saveModelVersion} from './financialModelStorage.js';
test('drafts are account isolated and restore exact zero/null assumptions',()=>{
 const data=new Map(),storage={getItem:k=>data.get(k),setItem:(k,v)=>data.set(k,v)};
 let store=readModelStore(storage,'one');store.draft={overrides:{IT:{E13:0,E14:null}},version:'v1'};
 writeModelStore(storage,'one',store);assert.deepEqual(readModelStore(storage,'one').draft,store.draft);assert.equal(readModelStore(storage,'two').draft,null);
 data.set('agi-financial-model-v2:one','broken');assert.equal(readModelStore(storage,'one').models.length,0);
});
test('named model versions are immutable snapshots with bounded history',()=>{
 let store={schema:2,models:[],draft:null};store=saveModelVersion(store,{name:'Client',overrides:{E13:0}});const id=store.models[0].id;
 for(let i=0;i<25;i++)store=saveModelVersion(store,{name:'Client',overrides:{E13:i}},id);
 assert.equal(store.models.length,1);assert.equal(store.models[0].versions.length,20);assert.equal(store.models[0].versions[0].overrides.E13,5);assert.equal(store.models[0].versions.at(-1).overrides.E13,24);
 assert.throws(()=>saveModelVersion(store,{name:' '},id));
});
