// server/notify-subscribers.cjs
// CommonJS module — drop into server/ and run with `node notify-subscribers.cjs`
// Requires server/.env with: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SENDGRID_API_KEY, SENDGRID_TEMPLATE_ID, FROM_EMAIL, BASE_URL, PORT

const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors'); // <-- added
const crypto = require('crypto');
const { createClient } = require('@supabase/supabase-js');
const sgMail = require('@sendgrid/mail');
require('dotenv').config({ path: './server/.env' });

const {
  SUPABASE_URL,
  SUPABASE_SERVICE_ROLE_KEY,
  SENDGRID_API_KEY,
  SENDGRID_TEMPLATE_ID,
  FROM_EMAIL,
  BASE_URL = 'https://agarwalglobalinvestments.com',
} = process.env;

if (!SUPABASE_URL || !SUPABASE_SERVICE_ROLE_KEY || !SENDGRID_API_KEY || !SENDGRID_TEMPLATE_ID || !FROM_EMAIL) {
  console.error('Missing one of required env vars: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SENDGRID_API_KEY, SENDGRID_TEMPLATE_ID, FROM_EMAIL');
  // continue but many features will fail
}

sgMail.setApiKey(SENDGRID_API_KEY);
const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY);

const app = express();
app.use(bodyParser.json({ limit: '1mb' }));

// Allow requests from your dev front-end (Vite). In prod set a strict origin.
// Development: allow all origins so Vite dev server can call this API.
app.use(cors({ origin: true })); // <-- added. Replace `true` with a string origin in production.


// -------------------- Helpers --------------------
function generateToken(len = 32) {
  return crypto.randomBytes(len).toString('hex'); // 64 chars for 32 bytes
}

function validEmail(e) {
  if (!e || typeof e !== 'string') return false;
  // simple email validation
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
}

function excerptFromHtml(html = '', maxChars = 300) {
  const txt = String(html).replace(/<\/?[^>]+(>|$)/g, ' ').replace(/\s+/g, ' ').trim();
  if (txt.length <= maxChars) return txt;
  return txt.slice(0, maxChars).trim() + '...';
}

function buildCommonTemplateData(article, subscriberEmail) {
  const {
    title,
    excerpt,
    slug,
    body,
    coverUrl,
    author,
    publishedAt,
    readTime,
    section,
  } = article || {};

  const resolvedExcerpt = excerpt || excerptFromHtml(body || '', 300);
  const articleUrl = slug ? `${BASE_URL.replace(/\/$/, '')}/article/${slug}` : (article?.articleUrl || BASE_URL);

  return {
    title: title || 'Untitled',
    excerpt: resolvedExcerpt,
    articleUrl,
    coverUrl: coverUrl || '',
    author: author || 'Agarwal Global Investments',
    publishedAt: publishedAt || new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    readTime: readTime || `${Math.max(1, Math.ceil((body || '').length / 900))} min`,
    section: section || 'Live Articles',
    siteUrl: BASE_URL,
    siteName: 'Agarwal Global Investments',
    preheader: (resolvedExcerpt || '').slice(0, 120),
    year: new Date().getFullYear(),
    // unsubscribe fields will be overridden per-subscriber
    unsubscribe: subscriberEmail ? `${BASE_URL.replace(/\/$/, '')}/unsubscribe?email=${encodeURIComponent(subscriberEmail)}` : `${BASE_URL.replace(/\/$/, '')}/unsubscribe`,
    unsubscribe_preferences: subscriberEmail ? `${BASE_URL.replace(/\/$/, '')}/unsubscribe-preferences?email=${encodeURIComponent(subscriberEmail)}` : `${BASE_URL.replace(/\/$/, '')}/unsubscribe-preferences`,
  };
}

function chunkArray(arr, size = 100) {
  const out = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

// -------------------- Routes --------------------

// Healthcheck
app.get('/health', (req, res) => res.json({ ok: true }));

// Subscribe endpoint — creates or re-activates a subscriber, returns unsubscribe token
// POST /api/subscribe { email }
app.post('/api/subscribe', async (req, res) => {
  try {
    const { email } = req.body || {};
    if (!validEmail(email)) return res.status(400).json({ error: 'Invalid email' });

    // generate token
    const token = generateToken(16);

    // upsert subscriber (insert or update)
    const payload = {
      email: email.toLowerCase(),
      is_active: true,
      unsubscribe_token: token,
    };

    const { data, error } = await supabase
      .from('subscribers')
      .upsert(payload, { onConflict: ['email'] })
      .select('id,email,unsubscribe_token,is_active,created_at')
      .single();

    if (error) {
      console.error('subscribe supabase error', error);
      return res.status(500).json({ error: 'database error' });
    }

    // optionally: send a welcome email (skip here)
    return res.json({ message: 'Subscribed', subscriber: { email: data.email, token: data.unsubscribe_token } });
  } catch (err) {
    console.error('subscribe error', err);
    return res.status(500).json({ error: 'internal error' });
  }
});

// Unsubscribe endpoint — by token (preferred) or email fallback
// POST /api/unsubscribe { token } OR { email }
app.post('/api/unsubscribe', async (req, res) => {
  try {
    const { token, email } = req.body || {};
    if (!token && !email) return res.status(400).json({ error: 'Provide token or email' });

    let filter;
    if (token) filter = supabase.from('subscribers').update({ is_active: false }).eq('unsubscribe_token', token);
    else filter = supabase.from('subscribers').update({ is_active: false }).eq('email', email.toLowerCase());

    const { data, error } = await filter.select('id,email,is_active').single();
    if (error) {
      // if single() fails because row not found, return friendly response
      if (error.code === 'PGRST116' || error.message?.includes('No rows')) {
        return res.status(404).json({ message: 'Subscriber not found' });
      }
      console.error('unsubscribe supabase error', error);
      return res.status(500).json({ error: 'database error' });
    }

    return res.json({ message: 'Unsubscribed', subscriber: { email: data.email } });
  } catch (err) {
    console.error('unsubscribe error', err);
    return res.status(500).json({ error: 'internal error' });
  }
});

// Notify subscribers — POST /api/notify-subscribers
// Payload: { articleId, title, slug, body, coverUrl, author, publishedAt, section, excerpt, readTime }
app.post('/api/notify-subscribers', async (req, res) => {
  try {
    const {
      articleId = null,
      title,
      slug,
      body = '',
      coverUrl = '',
      author,
      publishedAt,
      section,
      excerpt,
      readTime,
    } = req.body || {};

    if (!title || !slug) return res.status(400).json({ error: 'Missing required fields: title and slug' });

    // fetch active subscribers
    const { data: subscribers = [], error: subErr } = await supabase
      .from('subscribers')
      .select('email,unsubscribe_token')
      .eq('is_active', true);

    if (subErr) {
      console.error('fetch subscribers error', subErr);
      return res.status(500).json({ error: 'Failed to fetch subscribers' });
    }

    if (!subscribers || subscribers.length === 0) {
      return res.json({ message: 'No active subscribers' });
    }

    const article = { title, excerpt, slug, body, coverUrl, author, publishedAt, readTime, section };
    const msgs = subscribers.map((s) => {
      const email = s.email;
      const unsubscribeUrl = s.unsubscribe_token
        ? `${BASE_URL.replace(/\/$/, '')}/unsubscribe?token=${encodeURIComponent(s.unsubscribe_token)}`
        : `${BASE_URL.replace(/\/$/, '')}/unsubscribe?email=${encodeURIComponent(email)}`;
      const prefsUrl = s.unsubscribe_token
        ? `${BASE_URL.replace(/\/$/, '')}/unsubscribe-preferences?token=${encodeURIComponent(s.unsubscribe_token)}`
        : `${BASE_URL.replace(/\/$/, '')}/unsubscribe-preferences?email=${encodeURIComponent(email)}`;

      const dynamicData = {
        ...buildCommonTemplateData(article, email),
        unsubscribe: unsubscribeUrl,
        unsubscribe_preferences: prefsUrl,
      };

      return {
        to: email,
        from: FROM_EMAIL,
        templateId: SENDGRID_TEMPLATE_ID,
        dynamicTemplateData: dynamicData,
        headers: { 'List-Unsubscribe': `<${unsubscribeUrl}>` },
      };
    });

    // send in small batches to avoid hitting rate limits
    const BATCH_SIZE = 100;
    const DELAY_MS = 250;
    const batches = chunkArray(msgs, BATCH_SIZE);

    let sentCount = 0;
    const errors = [];

    for (const batch of batches) {
      const results = await Promise.all(
        batch.map((msg) =>
          sgMail
            .send(msg)
            .then(() => ({ ok: true, to: msg.to }))
            .catch((err) => {
              console.error('send error', msg.to, err?.response?.body || err?.toString?.() || err);
              errors.push({ to: msg.to, error: err?.response?.body || err?.toString?.() || err });
              return { ok: false, to: msg.to, error: err };
            })
        )
      );

      sentCount += results.filter((r) => r.ok).length;
      // slight throttle
      await new Promise((r) => setTimeout(r, DELAY_MS));
    }

    // write audit if possible
    try {
      await supabase.from('article_notifications').insert([
        { article_id: articleId, sent_at: new Date().toISOString(), recipient_count: subscribers.length, sent_count: sentCount },
      ]);
    } catch (e) {
      console.warn('audit insert failed (ignore if table missing)', e?.message || e);
    }

    return res.json({ message: 'Notifications processed', attempted: subscribers.length, sent: sentCount, failed: errors.length, sampleErrors: errors.slice(0, 10) });
  } catch (err) {
    console.error('notify-subscribers error', err);
    return res.status(500).json({ error: 'internal error' });
  }
});

// start server when run directly
if (require.main === module) {
  const PORT = parseInt(process.env.PORT || '3001', 10);
  app.listen(PORT, () => console.log(`Notify server listening on ${PORT}`));
}

module.exports = app;
