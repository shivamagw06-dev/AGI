import { createSupabaseAdmin } from '../../lib/supabaseAdmin.js';
import { matchAssets, validateAsset, validateReview } from './model.js';
let client;
export function database() { client ||= createSupabaseAdmin(); if (!client) throw new Error('Global Intelligence storage is unavailable.'); return client; }
export async function result(query) { const {data,error}=await query; if(error) throw error; return data; }
export async function snapshot({admin=false}={}) {
  const [events,assets,sources,reviews] = await Promise.all([
    result(database().from('gi_events').select('*').gte('observed_at',new Date(Date.now()-30*86400000).toISOString()).order('observed_at',{ascending:false}).limit(300)),
    result(database().from('gi_assets').select(admin?'*':'id,symbol,company,name,sector,relationship,evidence_note,source_url,confidence,latitude,longitude,location_precision,verified_at,active').eq('active',true).order('company').limit(1000)),
    result(database().from('gi_sources').select(admin?'id,name,last_attempt_at,last_success_at,last_count,last_error,status':'id,name,last_attempt_at,last_success_at,last_count,status').order('id')),
    result(admin ? database().from('gi_reviews').select('*').limit(1000) : database().from('gi_reviews').select('event_id,status,assessment,uncertainty,next_check,evidence_url,content_hash,reviewed_at').eq('status','published').limit(1000)),
  ]);
  const allReviews = reviews;
  return { generated_at:new Date().toISOString(), radius_km:100, assets, sources, events:events.map(e=>{
    const review=allReviews.find(r=>r.event_id===e.id);
    const current=review?.content_hash===e.content_hash;
    return {...e,matches:matchAssets(e,assets),review:current?review:null,review_state:current?review.status:(review?'needs_recheck':'pending')};
  }), coverage:'Pilot asset list; 100 km proximity is a research filter, not a hazard boundary. USGS: M4.5+ / 7 days. EONET: up to 100 events / 30-day query. Source publication timestamps may be unavailable.' };
}
export async function saveAsset(input,actor) {
  const asset=validateAsset(input);
  return result(database().from('gi_assets').insert({...asset,verified_by:actor,verified_at:new Date().toISOString()}).select('*').single());
}
export async function reviewEvent(id,input,actor) {
  const review=validateReview(input);
  return result(database().rpc('gi_review_event',{p_event_id:id,p_hash:review.content_hash,p_status:review.status,p_assessment:review.assessment,p_uncertainty:review.uncertainty,p_next_check:review.next_check,p_evidence_url:review.evidence_url,p_actor:actor}));
}
