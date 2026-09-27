import {useEffect,useRef} from 'react';
import {useLocation} from 'react-router-dom';
import {trackWebsiteEvent} from '@/lib/websiteAnalytics';
export default function WebsiteTracker(){
 useEffect(()=>{const signup=()=>trackWebsiteEvent('signup_completed','/signup');window.addEventListener('agi:signup-completed',signup);return()=>window.removeEventListener('agi:signup-completed',signup);},[]);
 const {pathname}=useLocation();const last=useRef('');
 useEffect(()=>{if(last.current===pathname)return;last.current=pathname;trackWebsiteEvent('page_view',pathname);},[pathname]);
 return null;
}
