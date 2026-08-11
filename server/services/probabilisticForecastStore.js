import { FORECAST_HORIZONS, createPointInTimeFeatures, generateProbabilisticForecast, settleForecast } from './probabilisticForecast.js';
function config(){const url=String(process.env.SUPABASE_URL||'').trim().replace(/\/$/,''),key=String(process.env.SUPABASE_SERVICE_ROLE_KEY||'').trim();if(!url||!key)throw new Error('Forecast storage requires Supabase credentials.');return{url,key};}
async function rest(table,{method='GET',query='',body,prefer}={}){const{url,key}=config();const response=await fetch(`${url}/rest/v1/${table}${query?`?${query}`:''}`,{method,headers:{apikey:key,Authorization:`Bearer ${key}`,'Content-Type':'application/json',...(prefer?{Prefer:prefer}:{})},body:body==null?undefined:JSON.stringify(body)});if(!response.ok){const error=new Error(`Forecast storage failed (${response.status}): ${(await response.text()).slice(0,240)}`);error.status=response.status;throw error;}const text=await response.text();return text?JSON.parse(text):[];}

export function selectDailyForecastEvents(events=[]){
  const latest=new Map();
  for(const event of events){const symbol=String(event.symbol||'').trim().toUpperCase(),date=String(event.captured_at||'').slice(0,10);if(!symbol||!date)continue;const key=`${symbol}|${date}`,prior=latest.get(key);if(!prior||Date.parse(event.captured_at)>Date.parse(prior.captured_at))latest.set(key,{...event,symbol});}
  return [...latest.values()].sort((a,b)=>String(a.captured_at).localeCompare(String(b.captured_at))||a.symbol.localeCompare(b.symbol));
}

export async function syncProbabilisticForecasts({limit=2000}={}){
  const [events,existingForecasts]=await Promise.all([rest('research_confluence_events',{query:`select=*&order=captured_at.desc&limit=${Math.min(5000,limit)}`}),rest('research_forecasts',{query:'select=symbol,forecast_time&is_canonical=eq.true&limit=10000'})]);
  const dailyEvents=selectDailyForecastEvents(events),seenDays=new Set(existingForecasts.map((row)=>`${String(row.symbol||'').toUpperCase()}|${String(row.forecast_time||'').slice(0,10)}`)); const summary={scanned:events.length,daily_candidates:dailyEvents.length,snapshots_created:0,forecasts_created:0};
  for(const event of dailyEvents){const dayKey=`${event.symbol}|${String(event.captured_at).slice(0,10)}`;if(seenDays.has(dayKey))continue;const input=createPointInTimeFeatures(event);const snapshot=(await rest('research_feature_snapshots',{method:'POST',body:input,prefer:'return=representation'}))?.[0];if(!snapshot)continue;const forecasts=FORECAST_HORIZONS.map((h)=>({...generateProbabilisticForecast(input,h),feature_snapshot_id:snapshot.id}));await rest('research_forecasts',{method:'POST',body:forecasts,prefer:'return=minimal'});seenDays.add(dayKey);summary.snapshots_created+=1;summary.forecasts_created+=forecasts.length;}
  return summary;
}

export async function settleDueForecasts({limit=500}={}){
  const forecasts=await rest('research_forecasts',{query:`select=*&is_canonical=eq.true&order=forecast_time.asc&limit=${Math.min(2000,limit)}`});
  const existing=await rest('research_forecast_outcomes',{query:'select=forecast_id&limit=5000'}); const settled=new Set(existing.map((row)=>row.forecast_id)); let completed=0;
  for(const forecast of forecasts){if(settled.has(forecast.id))continue;const outcome=(await rest('research_confluence_outcomes',{query:`select=*&event_id=eq.${forecast.confluence_event_id}&horizon=eq.${forecast.horizon}&status=eq.completed&limit=1`}))?.[0];if(!outcome)continue;await rest('research_forecast_outcomes',{method:'POST',body:settleForecast(forecast,outcome),prefer:'return=minimal'});completed+=1;}
  return {scanned:forecasts.length,completed};
}

export async function getCompanyForecasts(symbol,{limit=30}={}){const ticker=String(symbol||'').trim().toUpperCase();const rows=await rest('research_forecasts',{query:`select=*,outcome:research_forecast_outcomes(*)&symbol=eq.${encodeURIComponent(ticker)}&is_canonical=eq.true&order=forecast_time.desc&limit=${Math.min(200,limit)}`});return{symbol:ticker,generated_at:new Date().toISOString(),research_only:true,forecasts:rows};}
export async function getForecastValidation({horizon,limit=5000}={}){const filter=horizon?`&forecast.horizon=eq.${encodeURIComponent(horizon)}`:'';const rows=await rest('research_forecast_outcomes',{query:`select=*,forecast:research_forecasts!inner(symbol,horizon,forecast_time,expected_alpha_pct,probability_positive,confidence,market_regime)&forecast.is_canonical=eq.true&order=observed_at.desc&limit=${Math.min(10000,limit)}${filter}`});const completed=rows.length;if(!completed)return{horizon:horizon||'all',observations:0,calibrated:false};const mae=rows.reduce((s,r)=>s+Math.abs(Number(r.forecast_error)),0)/completed,brier=rows.reduce((s,r)=>s+Number(r.brier_score),0)/completed,accuracy=rows.filter((r)=>r.direction_correct).length/completed;return{horizon:horizon||'all',observations:completed,directional_accuracy:Number((accuracy*100).toFixed(2)),mae:Number(mae.toFixed(4)),brier_score:Number(brier.toFixed(4)),calibrated:completed>=100};}
