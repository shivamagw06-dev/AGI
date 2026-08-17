import { Router } from 'express';
import { getPeFirm, getPeOverview, getPeOpportunities, getPeInvestors, getPeInvestor, getPeIntelligence, listPeFirms } from '../services/peIntelligenceService.js';
import { approvePrivateMarketsImport, getPrivateMarketsAdminOverview, previewPrivateMarketsImport, resolvePrivateMarketsEntity } from '../services/privateMarketsAdminService.js';

export default function createPeIntelligenceRouter() {
  const router = Router();
  const requireAdmin=async(req,res,next)=>{try{const token=String(req.headers.authorization||'').replace(/^Bearer\s+/i,'');const url=String(process.env.SUPABASE_URL||'').replace(/\/$/,''),key=String(process.env.SUPABASE_SERVICE_ROLE_KEY||'');if(!token||!url||!key)return res.status(401).json({error:'Unauthorized'});const check=await fetch(url+'/auth/v1/user',{headers:{apikey:key,Authorization:'Bearer '+token}});const user=await check.json();const ids=[process.env.ADMIN_ID,process.env.VITE_ADMIN_ID,'c56e4d07-273c-49c9-86a5-a4445e687ece'].filter(Boolean),emails=[...(process.env.ADMIN_EMAILS||'').split(','),...(process.env.VITE_ADMIN_EMAILS||'').split(',')].map(x=>x.trim().toLowerCase()).filter(Boolean);if(!check.ok||(!ids.includes(user.id)&&!emails.includes(String(user.email||'').toLowerCase())))return res.status(403).json({error:'Admin access required'});req.adminUser=user;next()}catch(error){res.status(401).json({error:'Authorization failed'})}};

  router.get('/overview', async (req, res) => {
    try {
      return res.json(await getPeOverview({ sector: req.query.sector || null, scope: req.query.scope || 'core', search: req.query.search || '', limit: req.query.limit || 500 }));
    } catch (error) {
      console.error('[pe-intelligence] overview failed', error);
      return res.status(503).json({ error: 'Private Markets evidence is temporarily unavailable.' });
    }
  });

  router.get('/firms', (_req, res) => {
    return res.json({ firms: listPeFirms() });
  });
  router.get('/opportunities', async (req,res)=>{try{return res.json(await getPeOpportunities(req.query))}catch(error){return res.status(503).json({error:error.message})}});
  router.get('/investors', async (req,res)=>{try{return res.json(await getPeInvestors(req.query))}catch(error){return res.status(503).json({error:error.message})}});
  router.get('/investors/:id', async (req,res)=>{try{const row=await getPeInvestor(req.params.id);return row?res.json(row):res.status(404).json({error:'Investor not found'})}catch(error){return res.status(503).json({error:error.message})}});
  router.get('/intelligence', async (_req,res)=>{try{return res.json(await getPeIntelligence())}catch(error){return res.status(503).json({error:error.message})}});
  router.get('/admin/overview',requireAdmin,async(_req,res)=>{try{return res.json(await getPrivateMarketsAdminOverview())}catch(error){return res.status(503).json({error:error.message})}});
  router.post('/admin/imports/preview',requireAdmin,async(req,res)=>{try{return res.json(await previewPrivateMarketsImport(req.body||{}))}catch(error){return res.status(400).json({error:error.message})}});
  router.post('/admin/imports/approve',requireAdmin,async(req,res)=>{try{return res.json(await approvePrivateMarketsImport(req.body||{}))}catch(error){return res.status(400).json({error:error.message})}});
  router.patch('/admin/entity-review/:id',requireAdmin,async(req,res)=>{try{return res.json(await resolvePrivateMarketsEntity(req.params.id,req.body?.status))}catch(error){return res.status(400).json({error:error.message})}});

  router.get('/firms/:slug', (req, res) => {
    const firm = getPeFirm(req.params.slug);
    if (!firm) return res.status(404).json({ error: 'Firm not found' });
    return res.json(firm);
  });

  return router;
}
