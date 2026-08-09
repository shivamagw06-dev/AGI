import { getLiveAlphaWorkspace } from './liveAlphaWorkspace.js';

function config(){const url=String(process.env.SUPABASE_URL||'').trim().replace(/\/$/,''),key=String(process.env.SUPABASE_SERVICE_ROLE_KEY||'').trim();if(!url||!key)throw new Error('Research pipeline health requires Supabase credentials.');return{url,key};}
async function countRows(table,query=''){const{url,key}=config();const response=await fetch(`${url}/rest/v1/${table}?select=id${query?`&${query}`:''}`,{method:'HEAD',headers:{apikey:key,Authorization:`Bearer ${key}`,Prefer:'count=exact'}});if(!response.ok){const error=new Error(`Pipeline health count failed for ${table} (${response.status}).`);error.status=response.status;throw error;}const range=response.headers.get('content-range')||'*/0';return Number(range.split('/').at(-1))||0;}

export function derivePipelineStatus({scheduler,counts,upstoxHealthy,growwHealthy}){
  if (scheduler?.last_error || scheduler?.status==='degraded') return 'DEGRADED';
  if (!scheduler?.enabled) return 'DISABLED';
  if (counts.events===0) return upstoxHealthy||growwHealthy?'STANDBY':'WAITING_FOR_FEEDS';
  const complete=counts.memory>=counts.events&&counts.feature_snapshots>=counts.events&&counts.forecasts>=counts.feature_snapshots*3;
  return complete?'HEALTHY':'PROCESSING';
}

export async function getResearchPipelineHealth({schedulerStatus,workspace}={}){
  const data=workspace||await getLiveAlphaWorkspace();
  const [events,outcomes,memory,changes,featureSnapshots,forecasts,forecastOutcomes,rankings,crossSections]=await Promise.all([
    countRows('research_confluence_events'),countRows('research_confluence_outcomes'),countRows('research_memory_states'),countRows('research_memory_changes'),countRows('research_feature_snapshots'),countRows('research_forecasts'),countRows('research_forecast_outcomes'),countRows('research_forecast_rankings'),countRows('research_forecast_cross_section_metrics'),
  ]);
  const upstoxEngines=new Set((data?.runs||[]).map((run)=>run.engine).filter(Boolean));
  const growwStrategies=new Set((data?.groww?.runs||[]).map((run)=>run.strategy).filter(Boolean));
  const counts={events,outcomes,memory,changes,feature_snapshots:featureSnapshots,forecasts,forecast_outcomes:forecastOutcomes,rankings,cross_sections:crossSections};
  const status=derivePipelineStatus({scheduler:schedulerStatus,counts,upstoxHealthy:upstoxEngines.size,growwHealthy:growwStrategies.size});
  return {
    generated_at:new Date().toISOString(),status,research_only:true,execution_enabled:false,
    feeds:{market_feed:data?.readiness?.status==='ready'?'READY':String(data?.readiness?.status||'UNKNOWN').toUpperCase(),upstox_strategies:{healthy:upstoxEngines.size,expected:5,engines:[...upstoxEngines]},groww_strategies:{healthy:growwStrategies.size,expected:2,strategies:[...growwStrategies]}},
    latest_cycle:{candidates:schedulerStatus?.last_capture?.candidates||0,eligible_confluence:schedulerStatus?.last_capture?.eligible||0,persisted:schedulerStatus?.last_capture?.events||0,rejected:schedulerStatus?.last_capture?.rejected||{},outcomes_completed:schedulerStatus?.last_completion?.completed||0},
    totals:counts,
    integrity:{memory_coverage:events?Number((memory/events).toFixed(3)):null,feature_snapshot_coverage:events?Number((featureSnapshots/events).toFixed(3)):null,forecasts_per_snapshot:featureSnapshots?Number((forecasts/featureSnapshots).toFixed(3)):null,duplicate_protection:'DATABASE_UNIQUE_CONSTRAINTS'},
    scheduler:schedulerStatus,
  };
}
