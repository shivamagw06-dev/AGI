import {Router} from 'express';
import {createClient} from '@supabase/supabase-js';
import ws from 'ws';
import {fileURLToPath} from 'node:url';

const library=fileURLToPath(new URL('../assets/financial-models/Indian_Sector_Financial_Model_Library.xlsx',import.meta.url));
let authClient;
async function authenticateUser(token){
 const url=(process.env.SUPABASE_URL||process.env.VITE_SUPABASE_URL||'').trim();
 const key=process.env.SUPABASE_PUBLISHABLE_KEY||process.env.SUPABASE_ANON_KEY||process.env.SUPABASE_SERVICE_ROLE_KEY;
 if(!url||!key){const error=Error('Downloads are temporarily unavailable. Please try again later.');error.status=503;throw error;}
 authClient??=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false},realtime:{transport:ws}});
 const{data,error}=await authClient.auth.getUser(token);
 if(error||!data?.user)return null;
 return data.user;
}

export default function createFinancialModelsRouter({authenticate=authenticateUser,file=library}={}){
 const router=Router();
 router.use(async(req,res,next)=>{
  res.set('Cache-Control','private, no-store');res.set('Vary','Authorization');
  const token=/^Bearer\s+([^\s]+)$/i.exec(req.get('authorization')||'')?.[1];
  if(!token)return res.status(401).json({error:'Sign in to access financial models.'});
  try{
   const user=await authenticate(token);
   if(!user?.id||user.is_anonymous)return res.status(401).json({error:'Sign in with your AGI account to access financial models.'});
   if(!user.email_confirmed_at)return res.status(403).json({error:'Verify your account email before accessing financial models.'});
   next();
  }catch(error){if(!res.headersSent)res.status(503).json({error:'Account verification is temporarily unavailable. Please try again shortly.'});}
 });
 router.get('/catalog',(req,res)=>res.sendFile(fileURLToPath(new URL('../assets/financial-models/financialModels.json',import.meta.url))));
 router.get('/library',(req,res)=>res.download(file,'AGI_Indian_Sector_Model_Library.xlsx',error=>{if(error&&!res.headersSent)res.status(503).json({error:'The Excel library is temporarily unavailable.'});}));
 return router;
}
