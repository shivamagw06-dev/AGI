export const PLUS_AMOUNT=199;
export function isPlusToolPath(pathname=''){
 const p=String(pathname).split('?')[0].replace(/\/+$/,'')||'/';
 if(p==='/sections/deal-tracker'||p==='/updates/pre-market')return true;
 const free=['/','/research','/live-articles','/research-notes','/opinions-editorials','/insights','/companies','/equity-research','/market-updates','/company-updates','/about','/contact','/business','/events','/events-webinars','/login','/verify-email','/forgot-password','/reset-password','/unlock-pin','/privacy','/terms','/disclaimer','/sebi-disclosure','/pricing','/subscribe','/account/subscription','/account/security','/profile/edit','/404'];
 if(free.includes(p))return false;
 if(['/article/','/category/','/updates/','/sections/','/u/','/admin/'].some(prefix=>p.startsWith(prefix))||p==='/admin')return false;
 return true;
}
export function upiPaymentUri(config){
 if(!config?.checkoutEnabled||!config.payeeName||!config.upiId)return null;
 return 'upi://pay?'+new URLSearchParams({pa:config.upiId,pn:config.payeeName,am:'199.00',cu:'INR',tn:'AGI Plus 30 days'}).toString();
}
export function plusReturnPath(value){return typeof value==='string'&&value.startsWith('/')&&!value.startsWith('//')&&!/[\\\r\n]/.test(value)?value:'/tools';}
