const clean = (value) => String(value || '').trim();
const first = (...values) => values.map(clean).find(Boolean) || '';

function responseText(payload = {}) {
  if (payload.output_text) return String(payload.output_text);
  return (Array.isArray(payload.output) ? payload.output : [])
    .flatMap((item) => Array.isArray(item?.content) ? item.content : [])
    .map((item) => item?.text || '').join('');
}

function providerConfig(name = process.env.AGI_REASONING_PROVIDER || process.env.MODEL_PROVIDER || 'openai', env = process.env) {
  const provider = clean(name).toLowerCase();
  if (provider === 'openai') return { provider, key: first(env.OPENAI_API_KEY, env.AGIB_OPENAI_API_KEY) };
  if (provider === 'anthropic') return { provider, key: clean(env.ANTHROPIC_API_KEY) };
  if (provider === 'google' || provider === 'gemini') return { provider: 'google', key: first(env.GEMINI_API_KEY, env.GOOGLE_GEMINI_API_KEY, env.GOOGLE_API_KEY) };
  if (provider === 'local' || provider === 'future_agi') return { provider: 'local', key: clean(env.LOCAL_MODEL_API_KEY), baseUrl: clean(env.LOCAL_MODEL_BASE_URL).replace(/\/$/, '') };
  throw new Error(`unsupported_reasoning_provider:${provider}`);
}

export function reasoningProviderStatus(env = process.env) {
  const config = providerConfig(env.AGI_REASONING_PROVIDER || env.MODEL_PROVIDER || 'openai', env);
  return { provider: config.provider, configured: config.provider === 'local' ? Boolean(config.baseUrl) : Boolean(config.key) };
}

export async function structuredGenerate({ model, instructions, input, effort = 'medium', maxOutputTokens = 4_000, timeoutMs = 90_000, fetchImpl = fetch }) {
  const config = providerConfig();
  if (config.provider !== 'local' && !config.key) throw new Error(`${config.provider}_api_key_missing`);
  if (config.provider === 'local' && !config.baseUrl) throw new Error('local_model_base_url_missing');
  let url; let headers = { 'Content-Type': 'application/json' }; let body;
  if (config.provider === 'openai') {
    url = 'https://api.openai.com/v1/responses';
    headers.Authorization = `Bearer ${config.key}`;
    body = { model, instructions, input: `Return one valid JSON object only.\n\n${input}`, reasoning: { effort }, text: { format: { type: 'json_object' } }, max_output_tokens: maxOutputTokens, store: false };
  } else if (config.provider === 'anthropic') {
    url = 'https://api.anthropic.com/v1/messages';
    headers['x-api-key'] = config.key; headers['anthropic-version'] = '2023-06-01';
    body = { model, max_tokens: maxOutputTokens, system: instructions, messages: [{ role: 'user', content: `Return one valid JSON object only.\n\n${input}` }] };
  } else if (config.provider === 'google') {
    url = `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(config.key)}`;
    body = { systemInstruction: { parts: [{ text: instructions }] }, contents: [{ role: 'user', parts: [{ text: input }] }], generationConfig: { responseMimeType: 'application/json', maxOutputTokens } };
  } else {
    url = `${config.baseUrl}/v1/chat/completions`;
    if (config.key) headers.Authorization = `Bearer ${config.key}`;
    body = { model, response_format: { type: 'json_object' }, messages: [{ role: 'system', content: instructions }, { role: 'user', content: input }], max_tokens: maxOutputTokens, temperature: 0.1 };
  }
  const response = await fetchImpl(url, { method: 'POST', headers, signal: AbortSignal.timeout(timeoutMs), body: JSON.stringify(body) });
  const raw = await response.text();
  if (!response.ok) throw new Error(`${config.provider}_${response.status}:${raw.slice(0, 300)}`);
  const payload = JSON.parse(raw);
  if (payload.status === 'incomplete') throw new Error(`${config.provider}_incomplete:${payload.incomplete_details?.reason || 'output_limit'}`);
  if (config.provider === 'openai') return { text: responseText(payload), provider: config.provider, model: payload.model || model, response_id: payload.id || null, usage: payload.usage || {} };
  if (config.provider === 'anthropic') return { text: (payload.content || []).map((item) => item?.text || '').join(''), provider: config.provider, model: payload.model || model, response_id: payload.id || null, usage: payload.usage || {} };
  if (config.provider === 'google') return { text: payload.candidates?.[0]?.content?.parts?.map((part) => part.text || '').join('') || '', provider: config.provider, model: payload.modelVersion || model, response_id: null, usage: payload.usageMetadata || {} };
  return { text: payload.choices?.[0]?.message?.content || '', provider: config.provider, model: payload.model || model, response_id: payload.id || null, usage: payload.usage || {} };
}
