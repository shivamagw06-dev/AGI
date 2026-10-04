import { rest } from './liveAlphaPersistence.js';
import { publicationRows } from './liveAlphaPublicationModel.js';
import { sessionState } from './liveAlphaSession.js';
let state={status:'awaiting_session',last_at:null,last_error:null,created:0};
export function publicationStatus(){return {...state};}
export async function publishAlphaSnapshot(entries,persistence,{request=rest,now=new Date()}={}){
 if(!sessionState(now).open)return {skipped:'market_closed'};
 if(persistence.some(p=>p.status==='failed'))return {skipped:'partial_engine_failure'};
 const stored=new Map(persistence.filter(p=>p.status==='stored').map(p=>[p.engine,p.run_id]));
 const core=['cross_sectional_momentum_v1','volume_liquidity_anomaly_v1','opening_range_expansion_v1','intraday_mean_reversion_v1'];
 if(!core.every(e=>stored.has(e)))return {skipped:'core_engines_incomplete'};
 const signals=entries.filter(e=>e.result&&stored.has(e.engine)).flatMap(e=>e.result.signals.map(s=>({...s,engine:e.engine,run_id:stored.get(e.engine),as_of:e.result.as_of})));
 const rows=publicationRows(signals,now);
 try{
  const result=await request('rpc/alpha_publish_snapshot',{body:{p_rows:rows},prefer:'return=representation'});
  state={status:'ready',last_at:now.toISOString(),last_error:null,created:state.created+Number(result?.created||0)};
  return result;
 }catch(error){state={...state,status:'degraded',last_at:now.toISOString(),last_error:'Publication storage failed'};throw error;}
}
