import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import createRouter from './screenerLibrary.js';
import { libraryDefinition, libraryImport, safeSourceUrl } from '../services/screenerLibrary.js';
const admin = { id:'c56e4d07-273c-49c9-86a5-a4445e687ece' }, user = { id:'member' };
const body = { asOf:'2026-10-28', text:'Stock\tSymbol\tPrice\nExample\tEXAMPLE\t10', sourceUrl:'https://example.com/screen' };
test('validates definitions and source URLs; the import uses the actual table, not client row counts', () => {
  assert.equal(libraryDefinition({display_name:'Custom screen',category:'Value'},'custom-screen').display_name,'Custom screen');
  assert.throws(()=>libraryDefinition({display_name:'Overwrite',category:'Value'},'low-pe'),/reserved/);
  for(const url of ['javascript:alert(1)','http://example.com','https://user:secret@example.com']) assert.throws(()=>safeSourceUrl(url),/HTTPS/);
  assert.equal(libraryImport({...body,rowCount:999,rows:[['fake']]}).rowCount,1);
  assert.throws(()=>libraryImport({...body,asOf:'2026-02-30'}),/valid data date/);
});
test('result APIs require a verified paid member; only an admin can create, preview or publish', async () => {
  let grants = false, published, created, calls = 0;
  const store = {
    catalogue: async()=>[{slug:'custom',display_name:'Custom',row_count:null}],
    definition: async slug=>slug==='custom'?{slug}:null,
    detail: async()=>{calls++;return {screen:{slug:'custom'},snapshot:{rows:[['private']]}};}, history:async()=>[],
    create:async(data,actor)=>{created={data,actor};return data;}, update:async()=>({}),
    publish:async(slug,data,actor)=>{published={slug,data,actor};return{id:1,row_count:data.rowCount,as_of:data.asOf};},
  };
  const billing = { user:async token=>{if(token==='invalid')throw Error();return token==='admin'?admin:user;}, config:async()=>({enabled:true}), membership:async()=>grants?{starts_at:'2026-01-01',expires_at:'2099-01-01'}:null };
  const app=express();app.use(express.json());app.use('/library',createRouter({store,billing}));
  const server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
  const base=`http://127.0.0.1:${server.address().port}/library`;
  const request=(path='',token,method='GET',data)=>fetch(base+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},body:data?JSON.stringify(data):undefined});
  try {
    assert.equal((await request()).status,200);
    assert.equal((await request('/custom')).status,401);
    assert.equal((await request('/custom','invalid')).status,401);
    assert.equal((await request('/custom','member')).status,402);assert.equal(calls,0);
    grants=true;assert.equal((await request('/custom','member')).status,200);
    assert.equal((await request('/custom/preview','member','POST',body)).status,403);
    assert.equal((await request('/custom/publish','member','POST',{...body,reviewed:true})).status,403);
    assert.equal((await request('/admin/catalogue','member')).status,403);
    assert.equal((await request('/custom/preview','admin','POST',body)).status,200);
    assert.equal((await request('/custom/publish','admin','POST',body)).status,400);
    assert.equal((await request('/custom/publish','admin','POST',{...body,reviewed:true,published_by:'spoof',rowCount:999})).status,200);
    assert.equal(published.actor,admin.id);assert.equal(published.data.rowCount,1);
    assert.equal((await request('/custom?snapshot=not-an-id','admin')).status,400);
    assert.equal((await request('/missing','admin','PATCH',{display_name:'Missing',category:'Value'})).status,404);
    assert.equal((await request('','admin','POST',{slug:'own-screen',display_name:'Own screen',category:'Value',created_by:'spoof'})).status,201);
    assert.equal(created.actor,admin.id);assert.equal(created.data.created_by,undefined);
  } finally {await new Promise(resolve=>server.close(resolve));}
});
