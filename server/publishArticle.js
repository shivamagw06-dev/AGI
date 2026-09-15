// server/publishArticle.js
import express from 'express';
import { createClient } from '@supabase/supabase-js';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
app.use(express.json());

// create Supabase admin client
const supabaseAdmin = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_SERVICE_ROLE_KEY
);

// endpoint: POST /publish
app.post('/publish', async (req, res) => {
  const { id } = req.body;
  if (!id) return res.status(400).json({ error: 'Missing article ID' });

  const { data, error } = await supabaseAdmin
    .from('articles')
    .update({ status: 'published' })
    .eq('id', id);

  if (error) {
    console.error('Supabase error:', error);
    return res.status(500).json({ error });
  }

  res.json({ success: true, data });
});

// start server
app.listen(4000, () => {
  console.log('✅ Server running on http://localhost:4000');
});
