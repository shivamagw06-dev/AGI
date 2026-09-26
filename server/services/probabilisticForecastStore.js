import { FORECAST_HORIZONS, generateProbabilisticForecast, settleForecast } from './probabilisticForecast.js';
import { buildDailyCrossSectionalFeatureSnapshots } from './crossSectionalForecastFeatures.js';
import { summarizeForecastValidation } from './forecastValidationReport.js';
import { sharedCandleBook } from './candlePriceBook.js';
import { calculateConfluenceOutcome, confluenceHorizonDueAt } from './confluenceOutcomeValidation.js';
import { sessionState } from './liveAlphaSession.js';
import { publishedBefore } from './liveAlphaOutcomeSettlement.js';
function config(){const url=String(process.env.SUPABASE_URL||'').trim().replace(/\/$/,''),key=String(process.env.SUPABASE_SERVICE_ROLE_KEY||'').trim();if(!url||!key)throw new Error('Forecast storage requires Supabase credentials.');return{url,key};}
async function rest(table,{method='GET',query='',body,prefer}={}){const{url,key}=config();const response=await fetch(`${url}/rest/v1/${table}${query?`?${query}`:''}`,{method,headers:{apikey:key,Authorization:`Bearer ${key}`,'Content-Type':'application/json',...(prefer?{Prefer:prefer}:{})},body:body==null?undefined:JSON.stringify(body)});if(!response.ok){const error=new Error(`Forecast storage failed (${response.status}): ${(await response.text()).slice(0,240)}`);error.status=response.status;throw error;}const text=await response.text();return text?JSON.parse(text):[];}

export function selectDailyForecastEvents(events=[]){
  const latest=new Map();
  for(const event of events){const symbol=String(event.symbol||'').trim().toUpperCase(),date=String(event.captured_at||'').slice(0,10);if(!symbol||!date)continue;const key=`${symbol}|${date}`,prior=latest.get(key);if(!prior||Date.parse(event.captured_at)>Date.parse(prior.captured_at))latest.set(key,{...event,symbol});}
  return [...latest.values()].sort((a,b)=>String(a.captured_at).localeCompare(String(b.captured_at))||a.symbol.localeCompare(b.symbol));
}

/** Every row of a query, past PostgREST's silent 1000-row response cap. */
async function pagedRows(table, query, { pageSize = 1000, max = 200_000 } = {}) {
  const rows = [];
  while (rows.length < max) {
    const page = await rest(table, { query: `${query}&limit=${pageSize}&offset=${rows.length}` });
    rows.push(...page);
    if (page.length < pageSize) break;
  }
  return rows;
}

export async function syncProbabilisticForecasts({limit=2000}={}){
  const events=await rest('research_confluence_events',{query:`select=*&order=captured_at.desc&limit=${Math.min(1000,limit)}`});
  const dailyEvents=selectDailyForecastEvents(events),dailyInputs=buildDailyCrossSectionalFeatureSnapshots(dailyEvents);
  // Only the days being forecast, read in full: an unfiltered read stopped at
  // 1000 of ~1500 forecasts a day, so a rerun re-inserted days it had done.
  const earliest=dailyInputs.map((row)=>String(row.captured_at)).sort()[0];
  const existingForecasts=earliest?await pagedRows('research_forecasts',`select=symbol,forecast_time&is_canonical=eq.true&forecast_time=gte.${encodeURIComponent(new Date(Date.parse(earliest)-86_400_000).toISOString())}&order=id.asc`):[];
  const seenDays=new Set(existingForecasts.map((row)=>`${String(row.symbol||'').toUpperCase()}|${String(row.forecast_time||'').slice(0,10)}`)),expectedUniverse=Math.max(1,Number(process.env.FORECAST_EXPECTED_UNIVERSE_SIZE||200)),latestDate=dailyInputs.map((row)=>String(row.captured_at).slice(0,10)).sort().at(-1),latestSize=dailyInputs.filter((row)=>String(row.captured_at).slice(0,10)===latestDate).length; const summary={scanned:events.length,daily_candidates:dailyEvents.length,latest_cross_section_size:latestSize,expected_universe_size:expectedUniverse,coverage_pct:Number((100*latestSize/expectedUniverse).toFixed(2)),coverage_ready:latestSize>=Math.ceil(expectedUniverse*0.8),feature_version:dailyInputs[0]?.feature_version||null,snapshots_created:0,forecasts_created:0};
  for(const input of dailyInputs){const dayKey=`${input.symbol}|${String(input.captured_at).slice(0,10)}`;if(seenDays.has(dayKey))continue;const snapshot=(await rest('research_feature_snapshots',{method:'POST',query:'on_conflict=confluence_event_id',body:input,prefer:'resolution=ignore-duplicates,return=representation'}))?.[0];if(!snapshot)continue;const forecasts=FORECAST_HORIZONS.map((h)=>({...generateProbabilisticForecast(input,h),feature_snapshot_id:snapshot.id}));await rest('research_forecasts',{method:'POST',query:'on_conflict=confluence_event_id,horizon',body:forecasts,prefer:'resolution=ignore-duplicates,return=minimal'});seenDays.add(dayKey);summary.snapshots_created+=1;summary.forecasts_created+=forecasts.length;}
  return summary;
}

/**
 * Score forecasts from price history once their horizon has closed.
 *
 * Forecasts used to wait for the matching confluence outcome, but that queue
 * holds 3.5 million rows (an event every five minutes per stock) and settles
 * 200 per cycle, so after five weeks 120 of 18,588 forecasts were scored.
 * A forecast needs only its own event's anchors and two prices at the due
 * close, so it is priced directly: the stock's and its sector's returns from
 * the event to the horizon's official close, one daily-candle request per
 * instrument and month from the shared candle book.
 *
 * Each cycle reads the unscored forecasts that are due and works until a
 * time budget runs out; the next cycle carries on. A forecast whose event was
 * captured outside a session or cannot be priced is left unscored and
 * counted, never given an invented result.
 */
let lastIdleSettlement=0;
export async function settleDueForecasts({now=new Date(),book=sharedCandleBook(),budgetMs=150_000,request=rest,force=false}={}){
  // A backlog is worked every cycle; once nothing is left, look hourly.
  if(!force&&Date.now()-lastIdleSettlement<60*60_000)return{status:'skipped',reason:'no_backlog_within_the_hour'};
  const started=Date.now(),published=Date.parse(publishedBefore(now));
  const summary={completed:0,not_due:0,skipped:{},by_horizon:{},budget_exhausted:false};
  const skip=(reason)=>{summary.skipped[reason]=(summary.skipped[reason]||0)+1;};
  const select='select=id,horizon,expected_alpha_pct,probability_positive,research_forecast_outcomes(id),event:research_confluence_events!confluence_event_id(captured_at,instrument_key,sector_instrument_key,benchmark_instrument_key,price_at_signal,sector_index_at_signal,benchmark_at_signal)';
  for(const horizon of FORECAST_HORIZONS){
    const forecasts=[];
    for(let offset=0;;offset+=1000){
      const page=await request('research_forecasts',{query:`${select}&is_canonical=eq.true&horizon=eq.${horizon}&research_forecast_outcomes=is.null&forecast_time=lt.${encodeURIComponent(publishedBefore(now))}&order=forecast_time.asc&limit=1000&offset=${offset}`});
      forecasts.push(...page);if(page.length<1000)break;
    }
    const rows=[];
    for(const forecast of forecasts){
      if(Date.now()-started>budgetMs){summary.budget_exhausted=true;break;}
      const event=forecast.event;
      if(!event?.captured_at){skip('event_missing');continue;}
      if(!sessionState(event.captured_at).open){skip('event_outside_session');continue;}
      const dueAt=confluenceHorizonDueAt(event.captured_at,horizon);
      if(Date.parse(dueAt)>=published){summary.not_due+=1;continue;}
      // Every forecast horizon ends at a session close: price it at the official close.
      const dueDay=new Date(Date.parse(dueAt)+5.5*60*60_000).toISOString().slice(0,10);
      const [stock,sector,benchmark]=await Promise.all([book.closeOn(event.instrument_key,dueDay),book.closeOn(event.sector_instrument_key,dueDay),book.closeOn(event.benchmark_instrument_key,dueDay)]);
      const gap=[['stock',stock],['sector',sector],['benchmark',benchmark]].find(([,quote])=>quote.price==null);
      if(gap){skip(`${gap[0]}_${gap[1].reason}`);continue;}
      let outcome;
      try{outcome=calculateConfluenceOutcome({priceAtSignal:event.price_at_signal,futurePrice:stock.price,benchmarkAtSignal:event.benchmark_at_signal,futureBenchmark:benchmark.price,sectorAtSignal:event.sector_index_at_signal,futureSector:sector.price});}
      catch{skip('invalid_anchor');continue;}
      rows.push(settleForecast(forecast,{observed_at:stock.candle_end,sector_adjusted_alpha_pct:outcome.sector_adjusted_alpha_pct}));
    }
    if(rows.length)await request('research_forecast_outcomes',{method:'POST',query:'on_conflict=forecast_id',body:rows,prefer:'resolution=ignore-duplicates,return=minimal'});
    summary.by_horizon[horizon]=rows.length;summary.completed+=rows.length;
    if(summary.budget_exhausted)break;
  }
  lastIdleSettlement=summary.completed||summary.budget_exhausted?0:Date.now();
  return summary;
}

export async function getCompanyForecasts(symbol,{limit=30}={}){const ticker=String(symbol||'').trim().toUpperCase();const rows=await rest('research_forecasts',{query:`select=*,outcome:research_forecast_outcomes(*)&symbol=eq.${encodeURIComponent(ticker)}&is_canonical=eq.true&order=forecast_time.desc&limit=${Math.min(200,limit)}`});return{symbol:ticker,generated_at:new Date().toISOString(),research_only:true,forecasts:rows};}
export async function getForecastValidation({horizon}={}){
  const filter=horizon?`&forecast.horizon=eq.${encodeURIComponent(horizon)}`:'';
  const rows=await pagedRows('research_forecast_outcomes',`select=forecast_id,observed_at,actual_alpha_pct,forecast:research_forecasts!inner(symbol,horizon,forecast_time,expected_alpha_pct,probability_positive,confidence,market_regime,is_canonical)&forecast.is_canonical=eq.true${filter}&order=forecast_id.asc`);
  return summarizeForecastValidation(rows,{horizon:horizon||'all'});
}
