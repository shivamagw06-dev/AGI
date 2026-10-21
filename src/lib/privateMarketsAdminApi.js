import { supabase } from '@/lib/supabaseClient';
import API_ORIGIN from '@/config';
const BASE=API_ORIGIN||'';
async function call(path,options={}){const{data}=await supabase.auth.getSession();const r=await fetch(BASE+'/api/pe/admin'+path,{...options,headers:{'Content-Type':'application/json',Authorization:'Bearer '+(data.session?.access_token||'')}});const body=await r.json().catch(()=>({}));if(!r.ok)throw Error(body.error||'Admin API '+r.status);return body}
export const pmAdminOverview=()=>call('/overview');
export const pmAdminPreview=body=>call('/imports/preview',{method:'POST',body:JSON.stringify(body)});
export const pmAdminApprove=body=>call('/imports/approve',{method:'POST',body:JSON.stringify(body)});
export const pmAdminReview=(id,status)=>call('/entity-review/'+id,{method:'PATCH',body:JSON.stringify({status})});
