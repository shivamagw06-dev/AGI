import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
export const PLUS_PRICE=19900;
export const PLUS_DAYS=30;
export function canonicalReference(value){const s=String(value||'').trim().replace(/\s+/g,'').toUpperCase();return /^[A-Z0-9]{10,40}$/.test(s)?s:null;}
export function membershipActive(member,now=Date.now()){return !!member&&!member.revoked_at&&Number.isFinite(Date.parse(member.expires_at))&&Date.parse(member.starts_at)<=now&&Date.parse(member.expires_at)>now;}
export function plusAdmin(user){
 if(!user?.id)return false;
 const ids=[process.env.ADMIN_USER_ID,process.env.ADMIN_ID,process.env.VITE_ADMIN_ID,'c56e4d07-273c-49c9-86a5-a4445e687ece'].filter(Boolean);
 const emails=[...String(process.env.ADMIN_EMAILS||'').split(','),...String(process.env.VITE_ADMIN_EMAILS||'').split(','),'shivam.agw06@gmail.com'].map(x=>x.trim().toLowerCase());
 return ids.includes(user.id)||(!!user.email_confirmed_at&&emails.includes(String(user.email||'').toLowerCase()));
}
export function publicPlusConfig(row){return {enabled:row.enabled,checkoutEnabled:row.checkout_enabled&&!!row.payee_name&&/^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+$/.test(row.upi_id),upiId:row.upi_id,payeeName:row.payee_name,amountPaise:PLUS_PRICE,currency:'INR',durationDays:PLUS_DAYS,automaticRenewal:false};}
export function createPlusService(client=createSupabaseAdmin()){
 const requireClient=()=>{if(!client)throw Error('Subscription service unavailable');return client;};
 const result=async promise=>{const r=await promise;if(r.error)throw r.error;return r.data;};
 return {
  config:async()=>publicPlusConfig(await result(requireClient().from('agi_plus_settings').select('*').eq('id','agi_plus').single())),
  user:async token=>{const r=await requireClient().auth.getUser(token);if(r.error||!r.data?.user)throw Error('Invalid session');return r.data.user;},
  membership:async id=>result(requireClient().from('agi_plus_memberships').select('starts_at,expires_at,revoked_at').eq('user_id',id).maybeSingle()),
  payments:async id=>result(requireClient().from('agi_plus_payments').select('id,submitted_reference,amount_paise,currency,status,created_at,reviewed_at,review_note,access_expires_at').eq('user_id',id).order('created_at',{ascending:false}).limit(30)),
  submit:async(user,reference)=>{
   const c=await result(requireClient().from('agi_plus_settings').select('*').eq('id','agi_plus').single());
   if(!publicPlusConfig(c).checkoutEnabled)throw Error('Checkout is not available yet');
   const previous=await result(client.from('agi_plus_payments').select('id,status').eq('user_id',user.id).eq('submitted_reference',reference).maybeSingle());if(previous)return previous;
   return result(client.from('agi_plus_payments').insert({user_id:user.id,customer_email:user.email,submitted_reference:reference,amount_paise:PLUS_PRICE,currency:'INR'}).select('id,status').single());
  },
  queue:async()=>result(requireClient().from('agi_plus_payments').select('*').order('created_at',{ascending:false}).limit(200)),
  settings:async values=>result(requireClient().from('agi_plus_settings').update({...values,updated_at:new Date().toISOString()}).eq('id','agi_plus').select('*').single()),
  review:async(id,user,body)=>result(requireClient().rpc('agi_plus_review_payment',{payment_uuid:id,actor_uuid:user.id,decision:body.decision,bank_reference:body.reference,note:body.note})),
 };
}
