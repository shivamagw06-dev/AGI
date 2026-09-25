// Deliberately bounded Excel-expression interpreter. Never eval user input.
const parsed=new Map();
const tokenPattern=/\s*(?:('(?:[^']|'')+'!\$?[A-Z]+\$?\d+|\$?[A-Z]+\$?\d+)|([0-9]+(?:\.[0-9]*)?(?:[eE][+-]?\d+)?)|("(?:[^"]|"")*")|([A-Z][A-Z0-9_.]*)|(<=|>=|<>|[+\-*/^=<>(),:]))/gy;
function parse(formula){
 if(parsed.has(formula))return parsed.get(formula);
 const tokens=[];let pos=0;const text=formula.replace(/^=/,'').trim();
 while(pos<text.length){tokenPattern.lastIndex=pos;const m=tokenPattern.exec(text);if(!m)throw Error(`Unsupported formula near ${text.slice(pos,30)}`);tokens.push({type:m[1]?'ref':m[2]?'number':m[3]?'string':m[4]?'name':'op',value:m[1]||m[2]||m[3]||m[4]||m[5]});pos=tokenPattern.lastIndex;}
 let i=0;const peek=()=>tokens[i]?.value;const take=(v)=>{if(peek()!==v)throw Error(`Expected ${v}`);i++;};
 function atom(){const t=tokens[i++];if(!t)throw Error('Incomplete formula');if(t.type==='number')return{type:'literal',value:Number(t.value)};if(t.type==='string')return{type:'literal',value:t.value.slice(1,-1).replaceAll('""','"')};if(t.type==='ref'){if(peek()===':'){i++;const end=tokens[i++];if(end?.type!=='ref')throw Error('Invalid range');return{type:'range',start:t.value,end:end.value};}return{type:'ref',value:t.value};}if(t.value==='('){const n=expression();take(')');return n;}if(t.value==='-'||t.value==='+')return{type:'unary',op:t.value,child:atom()};if(t.type==='name'){take('(');const args=[];if(peek()!==')'){do{args.push(expression());if(peek()!==',')break;i++;}while(true);}take(')');return{type:'call',name:t.value,args};}throw Error('Unsupported formula token');}
 function power(){let node=atom();if(peek()==='^'){i++;node={type:'binary',op:'^',left:node,right:power()};}return node;}
 function product(){let node=power();while(['*','/'].includes(peek())){const op=tokens[i++].value;node={type:'binary',op,left:node,right:power()};}return node;}
 function sum(){let node=product();while(['+','-'].includes(peek())){const op=tokens[i++].value;node={type:'binary',op,left:node,right:product()};}return node;}
 function expression(){let node=sum();while(['=','<>','<','>','<=','>='].includes(peek())){const op=tokens[i++].value;node={type:'binary',op,left:node,right:sum()};}return node;}
 const ast=expression();if(i!==tokens.length)throw Error('Unexpected formula suffix');parsed.set(formula,ast);return ast;
}
const numeric=v=>{if(typeof v!=='number'||!Number.isFinite(v))throw Error('A required input is missing or invalid');return v;};
export function createModelCalculator(catalog,scenario=1,overrides={}){
 if(![1,2,3].includes(scenario))throw Error('Invalid scenario');
 const cache=new Map(),visiting=new Set();
 function refParts(ref,current){const cleaned=ref.replaceAll('$','');const at=cleaned.lastIndexOf('!');return at<0?[current,cleaned]:[cleaned.slice(0,at).slice(1,-1).replaceAll("''","'"),cleaned.slice(at+1)];}
 function cell(sheet,address){if(sheet==='Controls'&&address==='E5')return scenario;const key=sheet+'!'+address;if(cache.has(key)){const x=cache.get(key);if(x instanceof Error)throw x;return x;}if(visiting.has(key))throw Error('Circular formula');visiting.add(key);try{let v;const source=catalog.sheets[sheet]?.[address];if(Object.hasOwn(overrides[sheet]||{},address))v=overrides[sheet][address];else if(source?.f)v=evaluate(parse(source.f),sheet);else v=source?.v??null;if(typeof v==='number'&&!Number.isFinite(v))throw Error('Result is outside the supported numeric range');cache.set(key,v);return v;}catch(error){cache.set(key,error);throw error;}finally{visiting.delete(key);}}
 function evaluate(n,sheet){
  if(n.type==='literal')return n.value;
  if(n.type==='ref')return cell(...refParts(n.value,sheet));
  if(n.type==='range'){const[sh,a]=refParts(n.start,sheet),[endSheet,b]=refParts(n.end,sh);if(endSheet!==sh)throw Error('Cross-sheet ranges unsupported');const am=a.match(/([A-Z]+)(\d+)/),bm=b.match(/([A-Z]+)(\d+)/);const col=s=>[...s].reduce((x,c)=>x*26+c.charCodeAt(0)-64,0);const name=x=>{let s='';while(x){x--;s=String.fromCharCode(65+x%26)+s;x=Math.floor(x/26);}return s;};const result=[];for(let r=+am[2];r<=+bm[2];r++)for(let c=col(am[1]);c<=col(bm[1]);c++)result.push(()=>cell(sh,name(c)+r));return{range:result};}
  if(n.type==='unary')return(n.op==='-'?-1:1)*numeric(evaluate(n.child,sheet));
  if(n.type==='binary'){const a=evaluate(n.left,sheet),b=evaluate(n.right,sheet);if(['=','<>'].includes(n.op))return n.op==='='?a===b:a!==b;const x=numeric(a),y=numeric(b);switch(n.op){case'+':return x+y;case'-':return x-y;case'*':return x*y;case'/':if(y===0)throw Error('Denominator is zero');return x/y;case'^':return x**y;case'<':return x<y;case'>':return x>y;case'<=':return x<=y;case'>=':return x>=y;default:throw Error('Invalid operator');}}
  if(n.type==='call'){
   const ev=i=>evaluate(n.args[i],sheet);
   if(n.name==='IF')return ev(0)?ev(1):ev(2);
   if(n.name==='CHOOSE'){const i=numeric(ev(0));if(!Number.isInteger(i)||i<1||i>=n.args.length)throw Error('Invalid choice');return ev(i);}
   if(n.name==='INDEX'){const a=ev(0),i=numeric(ev(1));if(!a.range||!Number.isInteger(i)||i<1||i>a.range.length)throw Error('Invalid index');return a.range[i-1]();}
   if(n.name==='NA')throw Error('Complete the selected scenario assumptions');
   const args=n.args.flatMap((_,i)=>{const v=ev(i);return v?.range?v.range.map(f=>f()):[v];});
   if(n.name==='COUNT')return args.filter(v=>typeof v==='number'&&Number.isFinite(v)).length;
   if(n.name==='SUM')return args.reduce((x,v)=>x+numeric(v),0);
   if(n.name==='MAX')return Math.max(...args.map(numeric));if(n.name==='MIN')return Math.min(...args.map(numeric));
   throw Error(`Unsupported function ${n.name}`);
  }
  throw Error('Invalid formula');
 }
 return{cell,safe:(sheet,address)=>{try{return{value:cell(sheet,address),error:null};}catch(e){return{value:null,error:e.message};}}};
}
export function modelInputErrors(model,catalog,overrides,scenario){const errors=[];for(const row of model.inputs){if(row.case&&row.case!==scenario)continue;for(const ref of row.refs){const value=Object.hasOwn(overrides?.[model.name]||{},ref)?overrides[model.name][ref]:catalog.sheets[model.name][ref].v;if(typeof value!=='number'||!Number.isFinite(value))errors.push(`${row.label}: enter a number`);else if(value<0&&!/growth|change|working capital|contract asset/.test(row.label.toLowerCase()))errors.push(`${row.label}: use a non-negative value`);else if(row.format.includes('%')&&value>1&&!/growth/.test(row.label.toLowerCase()))errors.push(`${row.label}: enter a rate no higher than 100%`);}}return [...new Set(errors)];}
export function formatModelValue(value,format='General'){
 if(value===null||value===undefined)return '—';if(typeof value!=='number')return String(value);
 const percentage=format.includes('%'),multiple=format.includes('"x"');const decimals=format.includes('0.00')?2:1;
 const v=percentage?value*100:value;const result=new Intl.NumberFormat('en-IN',{minimumFractionDigits:decimals,maximumFractionDigits:decimals}).format(Math.abs(v));
 return `${v<0?'(' :''}${result}${percentage?'%':multiple?'x':''}${v<0?')':''}`;
}
