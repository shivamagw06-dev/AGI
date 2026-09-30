// Local drafts are explicitly device-only and isolated by verified account ID.
const prefix='agi-financial-model-v2:';
export function modelStorageKey(userId){return prefix+userId;}
export function readBrowserModelStore(userId,version){try{const s=readModelStore(localStorage,userId);return s.draft&&s.draft.version!==version?{...s,legacyDraft:s.draft,draft:null}:s;}catch{return {schema:2,models:[],draft:null};}}
export function readModelStore(storage,userId){
 try{const value=JSON.parse(storage.getItem(modelStorageKey(userId))||'null');
  if(value?.schema===2&&Array.isArray(value.models))return value;
 }catch{/* A malformed draft never prevents opening the studio. */}
 return {schema:2,models:[],draft:null};
}
export function writeModelStore(storage,userId,store){storage.setItem(modelStorageKey(userId),JSON.stringify(store));}
export function saveModelVersion(store,payload,id){
 const name=payload.name.trim();if(!name||name.length>100)throw Error('Use a model name between 1 and 100 characters.');
 const existing=store.models.find(m=>m.id===id);
 if(!existing&&store.models.length>=30)throw Error('This browser holds 30 models. Export and remove an old model before saving another.');
 const version={...payload,name,time:new Date().toISOString()};
 const model={id:existing?.id||globalThis.crypto.randomUUID(),name,versions:[...(existing?.versions||[]),version].slice(-20)};
 return {...store,models:[...store.models.filter(m=>m.id!==model.id),model]};
}
