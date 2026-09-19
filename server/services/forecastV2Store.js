import { buildPointInTimeTrainingRows, buildWalkForwardFolds, evaluateCrossSection, rankForecastCrossSection, summarizeRankIc } from './forecastV2Validation.js';
function config(){const url=String(process.env.SUPABASE_URL||'').trim().replace(/\/$/,''),key=String(process.env.SUPABASE_SERVICE_ROLE_KEY||'').trim();if(!url||!key)throw new Error('Forecast V2 storage requires Supabase credentials.');return{url,key};}
async function rest(table,{method='GET',query='',body,prefer}={}){const{url,key}=config();const response=await fetch(`${url}/rest/v1/${table}${query?`?${query}`:''}`,{method,headers:{apikey:key,Authorization:`Bearer ${key}`,'Content-Type':'application/json',...(prefer?{Prefer:prefer}:{})},body:body==null?undefined:JSON.stringify(body)});if(!response.ok){const error=new Error(`Forecast V2 storage failed (${response.status}): ${(await response.text()).slice(0,240)}`);error.status=response.status;throw error;}const text=await response.text();return text?JSON.parse(text):[];}
const groupKey=(row)=>`${String(row.forecast_time).slice(0,10)}|${row.horizon}`;
const round=(value,digits=6)=>Number(Number(value).toFixed(digits));

async function pagedRows(table,query,{pageSize=1000,max=200_000}={}){const rows=[];while(rows.length<max){const page=await rest(table,{query:`${query}&limit=${pageSize}&offset=${rows.length}`});rows.push(...page);if(page.length<pageSize)break;}return rows;}
const CROSS_SECTION_WINDOW_DAYS=40,CROSS_SECTION_INTERVAL_MS=60*60_000;
let lastCrossSectionSync=0;

/**
 * Rank each day's forecasts and score the ranking once outcomes arrive.
 *
 * This read the oldest 1000 forecasts, under one day of the ~1500 written
 * daily, so later days were never ranked or scored. It now reads the last 40
 * days in full (the 20-day horizon settles inside that), once an hour.
 */
export async function syncForecastCrossSections({now=new Date(),force=false}={}){
  if(!force&&Date.now()-lastCrossSectionSync<CROSS_SECTION_INTERVAL_MS)return{status:'skipped',reason:'synced_within_the_hour'};
  const since=encodeURIComponent(new Date(now.getTime()-CROSS_SECTION_WINDOW_DAYS*86_400_000).toISOString());
  const [forecasts,outcomes]=await Promise.all([
    pagedRows('research_forecasts',`select=id,symbol,horizon,forecast_time,expected_alpha_pct&is_canonical=eq.true&forecast_time=gte.${since}&order=id.asc`),
    pagedRows('research_forecast_outcomes',`select=forecast_id,actual_alpha_pct,forecast:research_forecasts!inner(forecast_time)&forecast.forecast_time=gte.${since}&order=forecast_id.asc`),
  ]);
  const groups=new Map();for(const row of forecasts){const key=groupKey(row);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(row);}const output={groups:groups.size,forecasts:forecasts.length,outcomes:outcomes.length,rankings:0,metrics:0};
  for(const [key,rows] of groups){const [forecastDate,horizon]=key.split('|'),rankings=rankForecastCrossSection(rows);if(rankings.length){await rest('research_forecast_rankings',{method:'POST',query:'on_conflict=forecast_id',body:rankings,prefer:'resolution=merge-duplicates,return=minimal'});output.rankings+=rankings.length;}const metric=evaluateCrossSection(rows,outcomes);if(metric.observations>=3){await rest('research_forecast_cross_section_metrics',{method:'POST',query:'on_conflict=forecast_date,horizon',body:{forecast_date:forecastDate,horizon,...metric},prefer:'resolution=merge-duplicates,return=minimal'});output.metrics+=1;}}
  lastCrossSectionSync=Date.now();
  return output;
}

export function latestForecastRankingRows(rows=[],limit=500){
  const latest=new Map();
  for(const row of rows){
    const symbol=String(row.symbol||'').trim().toUpperCase();if(!symbol)continue;
    const timestamp=Date.parse(row.forecast?.forecast_time||row.created_at||0)||0;
    const existing=latest.get(symbol),existingTimestamp=Date.parse(existing?.forecast?.forecast_time||existing?.created_at||0)||0;
    if(!existing||timestamp>existingTimestamp)latest.set(symbol,{...row,symbol});
  }
  const ranked=[...latest.values()].sort((a,b)=>Number(b.forecast?.expected_alpha_pct??-Infinity)-Number(a.forecast?.expected_alpha_pct??-Infinity)||Number(a.forecast_rank||Infinity)-Number(b.forecast_rank||Infinity)||a.symbol.localeCompare(b.symbol));
  const n=ranked.length;
  return ranked.slice(0,Math.min(5000,limit)).map((row,index)=>{const rank=index+1,percentile=n===1?1:1-index/(n-1);return{...row,forecast_rank:rank,universe_size:n,percentile:round(percentile),decile:Math.min(10,Math.max(1,Math.ceil(percentile*10)))};});
}
export async function getForecastRanking({date,horizon='5d',limit=500}={}){const target=date||new Date().toISOString().slice(0,10),rows=await rest('research_forecast_rankings',{query:`select=*,forecast:research_forecasts!inner(*)&forecast.is_canonical=eq.true&forecast_date=eq.${target}&horizon=eq.${encodeURIComponent(horizon)}&order=created_at.desc&limit=5000`});return latestForecastRankingRows(rows,limit);}
export async function getRankIcHealth({horizon='5d',limit=252}={}){const rows=await rest('research_forecast_cross_section_metrics',{query:`select=*&horizon=eq.${encodeURIComponent(horizon)}&order=forecast_date.desc&limit=${Math.min(2000,limit)}`});return{horizon,...summarizeRankIc(rows),latest:rows[0]||null,history:rows};}
export async function getWalkForwardDataset({horizon='5d',minimumTrainPeriods=20,minimumUniverseSize=100,limit=10000}={}){const [allSnapshots,forecasts,outcomes]=await Promise.all([rest('research_feature_snapshots',{query:`select=*&is_canonical=eq.true&limit=${Math.min(10000,limit)}`}),rest('research_forecasts',{query:`select=*&is_canonical=eq.true&horizon=eq.${encodeURIComponent(horizon)}&limit=${Math.min(10000,limit)}`}),rest('research_forecast_outcomes',{query:`select=*&limit=${Math.min(10000,limit)}`})]);const snapshots=allSnapshots.filter((row)=>Number(row.features?.cross_sectional?.universe_size||0)>=minimumUniverseSize),rows=buildPointInTimeTrainingRows(snapshots,forecasts,outcomes),dates=rows.map((row)=>String(row.as_of).slice(0,10));return{horizon,rows,folds:buildWalkForwardFolds(dates,{minimumTrainPeriods}),observations:rows.length,minimum_universe_size:minimumUniverseSize,excluded_low_coverage_snapshots:allSnapshots.length-snapshots.length,coverage_ready:snapshots.length>0,point_in_time_safe:true};}
