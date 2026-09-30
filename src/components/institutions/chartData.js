export function portfolioChartData(investors) {
 const additions = new Map(), sectors = new Map();
 let sectorCount = 0;
 for (const row of investors) {
  const seen = new Set();
  for (const entry of row.bought || []) {
   const name = entry.label.replace(/[↑↓]/g,'').replace(/\s*[+−-]?\s*[\d,.]+\s*%\s*$/,'').trim();
   const key = name.toLowerCase().replace(/\s+/g,' ');
   if (!key || key==='—' || key==='-' || seen.has(key)) continue;
   seen.add(key);
   const prior=additions.get(key);
   additions.set(key,{key,name,count:(prior?.count||0)+1});
  }
  const choices = (row.sectors || []).map(x=>{
   const match=x.label.match(/^(.*?)\s*\(([\d.]+)%\)/);
   return match ? {name:match[1].trim(),weight:Number(match[2])}:null;
  }).filter(x=>x&&Number.isFinite(x.weight)&&x.weight>0&&x.weight<=100).sort((a,b)=>b.weight-a.weight);
  if(choices.length){sectorCount++;sectors.set(choices[0].name,(sectors.get(choices[0].name)||0)+1);}
 }
 const ranked=[...sectors].map(([name,count])=>({name,count})).sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name));
 const displayed=ranked.slice(0,5);
 if(ranked.length>5)displayed.push({name:'Other sectors',count:ranked.slice(5).reduce((n,x)=>n+x.count,0)});
 return {changes:investors.filter(x=>typeof x.change==='number'&&Number.isFinite(x.change)),additions:[...additions.values()].sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name)).slice(0,5),sectors:displayed,sectorCount};
}
