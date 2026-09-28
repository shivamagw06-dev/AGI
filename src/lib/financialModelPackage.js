import {unzipSync,zipSync,strFromU8,strToU8} from 'fflate';
import {createModelCalculator,modelHealth} from './financialModelEngine.js';
const esc=v=>String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&apos;');
const unesc=v=>v.replaceAll('&apos;',"'").replaceAll('&quot;','"').replaceAll('&lt;','<').replaceAll('&gt;','>').replaceAll('&amp;','&');
const attr=(xml,name)=>new RegExp(`(?:^|\\s)${name}="([^"]*)"`).exec(xml)?.[1];

export async function exportCurrentModel(bytes,catalog,model,scenario,overrides){
 const problems=modelHealth(model,catalog,overrides,scenario);if(problems.length)throw Error(problems[0]);
 // Retain the native package so Excel charts, validation and layout survive.
 const zip=unzipSync(new Uint8Array(bytes)),calc=createModelCalculator(catalog,scenario,overrides);
 let workbook=strFromU8(zip['xl/workbook.xml']);
 const keep=new Set(['Controls',model.name,'KPI Guide','ReadMe']),ids=new Set(),paths={};
 workbook=workbook.replace(/<(?:\w+:)?sheet\b[^>]*\/>/g,node=>{
  const name=unesc(attr(node,'name')||'');if(!keep.has(name))return '';
  const id=attr(node,'r:id');ids.add(id);paths[id]=name;return node;
 }).replace(/<(?:\w+:)?definedNames\b[\s\S]*?<\/(?:\w+:)?definedNames>/g,'');
 let rels=strFromU8(zip['xl/_rels/workbook.xml.rels']);
 rels=rels.replace(/<Relationship\b[^>]*\/>/g,node=>{
  const type=attr(node,'Type')||'';if(type.endsWith('/calcChain'))return '';
  if(!type.endsWith('/worksheet'))return node;
  const id=attr(node,'Id');if(!ids.has(id))return '';
  const target=attr(node,'Target');const path=target.startsWith('/')?target.slice(1):'xl/'+target;
  const name=paths[id];if(!catalog.sheets[name])return node;
  let xml=strFromU8(zip[path]);const replacements={};
  for(const [address,source] of Object.entries(catalog.sheets[name]))if(source.f||name==='Controls'&&address==='E5'||Object.hasOwn(overrides[name]||{},address)){
   const r=calc.safe(name,address);if(r.error)throw Error(`Cannot export ${name}!${address}: ${r.error}`);replacements[address]={value:r.value,formula:source.f};
  }
  for(const [address,value] of Object.entries(overrides[name]||{}))if(!replacements[address])replacements[address]={value};
  const cellXml=(address,prefix,style,{value,formula})=>`<${prefix}c r="${address}"${style?` s="${style}"`:''}${typeof value==='number'?'':' t="str"'}>${formula?`<${prefix}f>${esc(formula)}</${prefix}f>`:''}${value===null?'':`<${prefix}v>${esc(value)}</${prefix}v>`}</${prefix}c>`;
  xml=xml.replace(/<((?:\w+:)?)c\b([^>]*?)(?:\/>|>([\s\S]*?)<\/\1c>)/g,(whole,prefix,attrs)=>{
   const address=attr(attrs,'r');if(!Object.hasOwn(replacements,address))return whole;
   const patch=replacements[address];delete replacements[address];return cellXml(address,prefix,attr(attrs,'s'),patch);
  });
  xml=xml.replace(/<((?:\w+:)?)row\b([^>]*)>([\s\S]*?)<\/\1row>/g,(whole,prefix,attrs,body)=>{
   const n=attr(attrs,'r');const missing=Object.entries(replacements).filter(([a])=>a.match(/\d+$/)?.[0]===n);
   return missing.length?`<${prefix}row${attrs}>${body}${missing.map(([a,v])=>cellXml(a,prefix,null,v)).join('')}</${prefix}row>`:whole;
  });
  zip[path]=strToU8(xml);return node;
 });
 const prefix=/<(\w+:)?workbook\b/.exec(workbook)?.[1]||'';
 workbook=workbook.replace(/<(?:\w+:)?calcPr\b[^>]*\/>/g,'').replace(`</${prefix}workbook>`,`<${prefix}calcPr calcMode="auto" fullCalcOnLoad="1" forceFullCalc="1"/></${prefix}workbook>`);
 zip['xl/workbook.xml']=strToU8(workbook);zip['xl/_rels/workbook.xml.rels']=strToU8(rels);
 for(const path of Object.keys(zip).filter(p=>/\/charts\/.*\.xml$/.test(p))){
  let xml=strFromU8(zip[path]);xml=xml.replace(/<c:(num|str)Ref>([\s\S]*?)<\/c:\1Ref>/g,(whole,kind,body)=>{
   const f=unesc(/<c:f>(.*?)<\/c:f>/.exec(body)?.[1]||'');const match=/^'([^']+)'!\$([A-Z]+)\$(\d+):\$\2\$(\d+)$/.exec(f);
   if(!match||match[1]!==model.name)return whole;
   const values=Array.from({length:+match[4]-+match[3]+1},(_,i)=>calc.cell(model.name,match[2]+(+match[3]+i)));
   const cache=`<c:${kind}Cache>${kind==='num'?'<c:formatCode>General</c:formatCode>':''}<c:ptCount val="${values.length}"/>${values.map((v,i)=>`<c:pt idx="${i}"><c:v>${esc(v)}</c:v></c:pt>`).join('')}</c:${kind}Cache>`;
   return `<c:${kind}Ref>${body.replace(new RegExp(`<c:${kind}Cache>[\\s\\S]*?</c:${kind}Cache>`),cache)}</c:${kind}Ref>`;
  });zip[path]=strToU8(xml);
 }
 return new Blob([zipSync(zip,{level:6})],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
}
