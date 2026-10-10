// Only aggregate metrics and explicitly public route groups leave this boundary.
// Never expose arbitrary paths, visitor identities or referring domains publicly.
const number=v=>Number.isFinite(Number(v))&&Number(v)>=0?Number(v):0;
const groups=[['/finance-tools','Tools directory'],['/tools/','Research calculators'],['/financial-modeling','Financial models'],['/institutions','Investor portfolios'],['/insider-activity','Insider activity'],['/research','Research'],['/article','Articles'],['/market','Markets']];
function groupRows(rows,key){const counts=new Map();for(const r of rows||[]){const label=key(String(r.label||''));counts.set(label,(counts.get(label)||0)+number(r.views));}return [...counts].map(([label,views])=>({label,views})).sort((a,b)=>b.views-a.views);}
export function publicWebsiteStats(data){
 const out={ok:true,timezone:'Asia/Kolkata',scope:'AGI website',updatedAt:data.updatedAt,trackingSince:data.trackingSince,days:data.days};
 for(const k of ['visitors','visits','pageviews','repeatVisitors','active','signups','downloads'])out[k]=number(data[k]);
 out.trend=(data.trend||[]).slice(0,90).map(r=>({date:String(r.date).slice(0,16),visitors:number(r.visitors),views:number(r.views)}));
 out.pages=groupRows(data.pages,label=>label==='/'?'Home':groups.find(([prefix])=>label===prefix||label.startsWith(prefix.endsWith('/')?prefix:prefix+'/'))?.[1]||'Other pages');
 out.channels=groupRows(data.referrers,label=>/^(www\.)?(google\.[a-z.]+|bing\.com|duckduckgo\.com|search\.yahoo\.com)$/.test(label)?'Search':/(^|\.)(linkedin\.com|facebook\.com|instagram\.com|twitter\.com|x\.com|t\.co|youtube\.com)$/.test(label)?'Social':label==='Direct / unknown'?'Direct / unknown':'Referral');
 for(const [field,allowed] of [['devices',['Desktop','Mobile','Tablet']],['browsers',['Chrome','Safari','Firefox','Edge','Opera','Samsung Internet','Other']],['operatingSystems',['Windows','macOS','iOS','Android','Linux','Other']]])out[field]=groupRows(data[field],label=>allowed.includes(label)?label:'Unknown');
 out.breakdownNote='Page and channel lists use the top 30 recorded entries; smaller sources may be omitted.';
 return out;
}
