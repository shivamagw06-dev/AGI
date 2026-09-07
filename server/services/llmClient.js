/**
 * Soft LLM client for institutional briefings.
 * Prefers Google Gemini when GEMINI_API_KEY is set; falls back to OpenAI.
 * Returns null when no provider succeeds so callers keep deterministic copy.
 */

function geminiKey() {
  return (
    process.env.GEMINI_API_KEY
    || process.env.GOOGLE_GEMINI_API_KEY
    || process.env.GOOGLE_GENERATIVE_AI_API_KEY
    || process.env.GOOGLE_API_KEY
    || process.env.GENERATIVE_LANGUAGE_API_KEY
    || ''
  ).trim();
}

function openaiKey() {
  return (
    process.env.OPENAI_API_KEY
    || process.env.OPENAI_MARKET_BRIEFING_KEY
    || process.env.AGIB_OPENAI_API_KEY
    || ''
  ).trim();
}

function geminiModel() {
  return (process.env.GEMINI_MODEL || process.env.GOOGLE_GEMINI_MODEL || 'gemini-flash-latest').trim();
}

function openaiModel() {
  return (process.env.OPENAI_MARKET_BRIEFING_MODEL || process.env.OPENAI_MODEL || 'gpt-4.1-mini').trim();
}

export function llmProviderStatus() {
  return {
    gemini: Boolean(geminiKey()),
    openai: Boolean(openaiKey()),
    preferred: geminiKey() ? 'gemini' : openaiKey() ? 'openai' : null,
    geminiModel: geminiModel(),
    openaiModel: openaiModel(),
  };
}

function extractJsonObject(text = '') {
  const raw = String(text || '').trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    const start = raw.indexOf('{');
    const end = raw.lastIndexOf('}');
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(raw.slice(start, end + 1));
      } catch {
        return null;
      }
    }
    return null;
  }
}

async function completeWithGemini({ system, user, temperature = 0.25, json = true }) {
  const apiKey = geminiKey();
  if (!apiKey) return null;
  const model = geminiModel();
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`;
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    signal: AbortSignal.timeout(30_000),
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: system }] },
      contents: [{ role: 'user', parts: [{ text: user }] }],
      generationConfig: {
        temperature,
        ...(json ? { responseMimeType: 'application/json' } : {}),
      },
    }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`Gemini failed (${response.status})${detail ? `: ${detail.slice(0, 180)}` : ''}`);
  }
  const payload = await response.json();
  const text = payload?.candidates?.[0]?.content?.parts?.map((part) => part.text || '').join('') || '';
  return { provider: 'gemini', model, text, json: json ? extractJsonObject(text) : null };
}

async function completeWithOpenAi({ system, user, json = true }) {
  const apiKey = openaiKey();
  if (!apiKey) return null;
  const model = openaiModel();
  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: { Authorization: `Bearer ${apiKey}`, 'Content-Type': 'application/json' },
    signal: AbortSignal.timeout(30_000),
    body: JSON.stringify({
      model,
      ...(json ? { response_format: { type: 'json_object' } } : {}),
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: user },
      ],
    }),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => '');
    throw new Error(`OpenAI failed (${response.status})${detail ? `: ${detail.slice(0, 180)}` : ''}`);
  }
  const payload = await response.json();
  const text = payload?.choices?.[0]?.message?.content || '';
  return { provider: 'openai', model, text, json: json ? extractJsonObject(text) : null };
}

/**
 * @returns {Promise<{ provider: string, model: string, text: string, json: object|null }|null>}
 */
export async function completeChat({ system, user, temperature = 0.25, json = true } = {}) {
  const systemPrompt = String(system || '').trim();
  const userPrompt = typeof user === 'string' ? user : JSON.stringify(user ?? {});
  if (!systemPrompt || !userPrompt) return null;

  const errors = [];
  if (geminiKey()) {
    try {
      const result = await completeWithGemini({ system: systemPrompt, user: userPrompt, temperature, json });
      if (result && (!json || result.json)) return result;
      if (result) errors.push('Gemini returned non-JSON content');
    } catch (error) {
      errors.push(error.message);
      console.warn('[llm] Gemini unavailable:', error.message);
    }
  }

  if (openaiKey()) {
    try {
      const result = await completeWithOpenAi({ system: systemPrompt, user: userPrompt, temperature, json });
      if (result && (!json || result.json)) return result;
      if (result) errors.push('OpenAI returned non-JSON content');
    } catch (error) {
      errors.push(error.message);
      console.warn('[llm] OpenAI unavailable:', error.message);
    }
  }

  if (errors.length) {
    console.warn('[llm] All providers failed:', errors.join(' | '));
  }
  return null;
}

export async function completeJson(options) {
  const result = await completeChat({ ...options, json: true });
  return result?.json || null;
}
