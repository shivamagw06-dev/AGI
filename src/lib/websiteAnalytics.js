import {analyticsClientInfo} from './analyticsClientInfo';
import { API_ORIGIN } from '@/config';
const KEY='agi_site_visitor_v1', SESSION='agi_site_session_v1';
export function trackWebsiteEvent(event,path=window.location.pathname) {
 try {
  if(!['agarwalglobalinvestments.com','www.agarwalglobalinvestments.com'].includes(window.location.hostname)||navigator.doNotTrack==='1'||navigator.globalPrivacyControl||localStorage.getItem('agi_analytics_optout')==='1'||path.startsWith('/admin'))return;
  const now=Date.now();let visitor=JSON.parse(localStorage.getItem(KEY)||'null');
  if(!visitor||now-visitor.created>90*86400000){visitor={id:crypto.randomUUID(),created:now};localStorage.setItem(KEY,JSON.stringify(visitor));}
  let session=JSON.parse(localStorage.getItem(SESSION)||'null');
  if(!session||now-session.at>30*60000)session={id:crypto.randomUUID()};session.at=now;localStorage.setItem(SESSION,JSON.stringify(session));
  let referrer=session.referrer;
  if(referrer===undefined){referrer=document.referrer?new URL(document.referrer).hostname:'';if(referrer===window.location.hostname)referrer='';session.referrer=referrer;localStorage.setItem(SESSION,JSON.stringify(session));}
  const body={...analyticsClientInfo(navigator.userAgent),id:event==='signup_completed'?`${visitor.id}-signup`:crypto.randomUUID(),visitor:visitor.id,session:session.id,event,path:path.split('?')[0].split('#')[0],referrer,device:/ipad|tablet/i.test(navigator.userAgent)?'Tablet':/mobi|android/i.test(navigator.userAgent)?'Mobile':'Desktop'};
  fetch(`${API_ORIGIN||''}/api/intelligence/website-analytics/event`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),keepalive:true,credentials:'omit'}).catch(()=>{});
 } catch { /* Analytics must never interrupt the website. */ }
}
