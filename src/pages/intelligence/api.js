import { API_ORIGIN } from '@/config';
import { supabase } from '@/lib/supabaseClient';
export async function request(path, options={}, privateRequest=false) {
  const headers={'Content-Type':'application/json'};
  if(privateRequest){const {data}=await supabase.auth.getSession();if(!data?.session?.access_token)throw new Error('Please sign in first.');headers.Authorization=`Bearer ${data.session.access_token}`;}
  const response=await fetch(`${API_ORIGIN||''}/api/global-intelligence${path}`,{...options,headers,cache:'no-store',signal:options.signal||AbortSignal.timeout(45000)});
  const data=await response.json();if(!response.ok)throw new Error(data.error||'Could not load intelligence.');return data;
}
export const when=value=>value?new Date(value).toLocaleString('en-IN',{dateStyle:'medium',timeStyle:'short',timeZone:'Asia/Kolkata'})+' IST':'Not supplied';
