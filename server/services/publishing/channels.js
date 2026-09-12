/**
 * Research Distribution Engine — channel-specific summaries.
 * Does NOT rewrite research; creates distribution packs from the article.
 */

function stripHtml(html = '') {
  return String(html)
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<\/?[^>]+(>|$)/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function sentences(text, max = 6) {
  const parts = text
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return parts.slice(0, max);
}

function bullets(text, count = 10) {
  const lines = sentences(text, count * 2);
  const out = [];
  for (const line of lines) {
    if (out.length >= count) break;
    out.push(line.length > 140 ? `${line.slice(0, 137)}…` : line);
  }
  while (out.length < Math.min(3, count)) {
    out.push('See the full research note on AGI for evidence and confidence.');
  }
  return out.slice(0, count);
}

/**
 * Generate channel packs for one published article.
 */
export function generateChannelContent(article = {}) {
  const title = article.title || 'AGI Research Note';
  const bodyText = stripHtml(article.body || article.content || article.excerpt || '');
  const excerpt = (article.excerpt || bodyText).slice(0, 400);
  const site = (process.env.SITE_ORIGIN || process.env.BASE_URL || 'https://agarwalglobalinvestments.com').replace(/\/$/, '');
  const url = article.slug ? `${site}/article/${encodeURIComponent(article.slug)}` : article.url || site;
  const cover = article.coverUrl || article.cover_url || '';
  const section = article.section || 'Research';

  const oneMinute = sentences(excerpt || bodyText, 3).join(' ') || `${title} — institutional research now on AGI.`;
  const twoMinuteEmail = sentences(bodyText || excerpt, 5).join(' ') || oneMinute;
  const bulletPoints = bullets(bodyText || excerpt, 10);

  const linkedin = [
    `${title}`,
    '',
    oneMinute,
    '',
    'Key takeaways:',
    ...bulletPoints.slice(0, 3).map((b, i) => `${i + 1}. ${b}`),
    '',
    `Read the full note: ${url}`,
    '',
    '#AGI #Markets #Research',
  ].join('\n');

  const twitterThread = [
    `${title}\n\n${oneMinute.slice(0, 200)}${oneMinute.length > 200 ? '…' : ''}`,
    ...bulletPoints.slice(0, 4).map((b, i) => `${i + 1}/${Math.min(5, bulletPoints.length + 1)} ${b}`),
    `Full research: ${url}`,
  ];

  const telegram = [
    `*${title}*`,
    '',
    ...bulletPoints.slice(0, 10).map((b) => `• ${b}`),
    '',
    `Read: ${url}`,
  ].join('\n');

  const whatsapp = [
    `AGI Research — ${title}`,
    '',
    oneMinute,
    '',
    ...bulletPoints.slice(0, 5).map((b) => `• ${b}`),
    '',
    url,
  ].join('\n');

  const seoTitle = `${title} | AGI Research`.slice(0, 60);
  const seoDescription = (article.meta_description || oneMinute).slice(0, 155);
  const socialPreview = {
    title: seoTitle,
    description: seoDescription,
    image: cover,
    url,
    type: 'article',
  };

  return {
    newsletter_summary: twoMinuteEmail,
    one_minute_summary: oneMinute,
    linkedin_post: linkedin,
    twitter_thread: twitterThread,
    telegram_summary: telegram,
    whatsapp_channel: whatsapp,
    seo_title: seoTitle,
    seo_meta_description: seoDescription,
    social_preview: socialPreview,
    key_charts: (article.charts || []).slice(0, 3),
    related_research: article.related || [],
    article_url: url,
    section,
    disclaimer: 'Channel packs summarise distribution only — they do not rewrite the research thesis.',
  };
}

/** Optional OpenAI polish — fails soft to deterministic pack */
export async function maybeEnrichChannels(pack, article) {
  const key = process.env.OPENAI_API_KEY;
  if (!key) return pack;
  try {
    const resp = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${key}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
        temperature: 0.3,
        messages: [
          {
            role: 'system',
            content:
              'You produce channel-specific research distribution summaries. Do NOT rewrite the investment thesis. No buy/sell language. Return JSON only with keys: newsletter_summary, linkedin_post, telegram_summary, seo_meta_description.',
          },
          {
            role: 'user',
            content: JSON.stringify({
              title: article.title,
              excerpt: article.excerpt,
              draft: {
                newsletter_summary: pack.newsletter_summary,
                linkedin_post: pack.linkedin_post,
                telegram_summary: pack.telegram_summary,
                seo_meta_description: pack.seo_meta_description,
              },
            }),
          },
        ],
        response_format: { type: 'json_object' },
      }),
    });
    if (!resp.ok) return pack;
    const data = await resp.json();
    const text = data.choices?.[0]?.message?.content;
    if (!text) return pack;
    const parsed = JSON.parse(text);
    return {
      ...pack,
      newsletter_summary: parsed.newsletter_summary || pack.newsletter_summary,
      linkedin_post: parsed.linkedin_post || pack.linkedin_post,
      telegram_summary: parsed.telegram_summary || pack.telegram_summary,
      seo_meta_description: parsed.seo_meta_description || pack.seo_meta_description,
      enriched: true,
    };
  } catch {
    return pack;
  }
}
