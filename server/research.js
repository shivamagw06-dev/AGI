// server/research.js
import express from "express";
import dotenv from "dotenv";

dotenv.config();
const router = express.Router();

// Use global fetch (Node 18+) if present; otherwise dynamically import node-fetch v3
let fetchFn = globalThis.fetch;
async function ensureNodeFetch() {
  if (!fetchFn) {
    const mod = await import("node-fetch");
    // node-fetch v3 default export is the fetch function
    fetchFn = mod.default;
  }
  return fetchFn;
}

/**
 * fetchWithTimeout
 * - works with globalThis.fetch or node-fetch
 * - timeout in ms (default 15000)
 */
async function fetchWithTimeout(url, opts = {}, timeoutMs = 15000) {
  // ensure fetchFn is available if not already
  if (!fetchFn) await ensureNodeFetch();

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const merged = { ...opts, signal: controller.signal };
    const response = await fetchFn(url, merged);
    clearTimeout(id);
    return response;
  } catch (err) {
    clearTimeout(id);
    throw err;
  }
}

/**
 * Config / env
 * - PERPLEXITY_KEY: server-side secret
 * - PERPLEXITY_URL: endpoint to call (default to Perplexity Chat Completions)
 * - INDIANAPI_KEY: key for IndianAPI (server-side)
 */
const PERPLEXITY_KEY = (process.env.PERPLEXITY_KEY || process.env.PERPLEXITY_API_KEY || process.env.VITE_PERPLEXITY_KEY || "").trim();
const PERPLEXITY_URL = process.env.PERPLEXITY_URL || "https://api.perplexity.ai/chat/completions";

const INDIANAPI_BASE = process.env.INDIANAPI_BASE || "https://stock.indianapi.in";
const INDIANAPI_KEY = (process.env.INDIANAPI_KEY || process.env.VITE_INDIANAPI_KEY || "").trim();

/* ---------- helpers for IndianAPI ---------- */
function makeIndianHeaders() {
  const h = {
    Accept: "application/json",
    "Content-Type": "application/json",
    "User-Agent": "AGIB-Research/1.0",
  };
  if (INDIANAPI_KEY) h["x-api-key"] = INDIANAPI_KEY;
  return h;
}

/**
 * fetchIndian
 * - path: string like "/stock?name=RELIANCE" or "stock?name=RELIANCE"
 * - returns parsed JSON when possible, otherwise raw text
 */
async function fetchIndian(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  const url = `${INDIANAPI_BASE}${p}`;
  try {
    const r = await fetchWithTimeout(url, { method: "GET", headers: makeIndianHeaders() }, 15_000);
    const text = await r.text().catch(() => "");
    const ct = (r.headers.get("content-type") || "").toLowerCase();

    if (!text) return null;

    if (ct.includes("json") || ct.includes("+json")) {
      try {
        return JSON.parse(text);
      } catch (e) {
        // return raw text if parse fails
        return text;
      }
    }

    return text;
  } catch (err) {
    console.warn("[fetchIndian] fetch failed:", err?.message || err);
    return null;
  }
}

/* ---------- build prompt ---------- */
function buildPrompt(ticker, sourceData) {
  const lines = [];
  lines.push(`Provide a short investor-facing summary and a one-line recommendation for the following ticker: ${ticker}`);
  lines.push("");
  lines.push("Source data (do not hallucinate beyond these facts):");

  // Keep the payload reasonably sized — stringify and truncate to ~3000 chars
  try {
    const sd = JSON.stringify(sourceData || {}, null, 2);
    lines.push(sd.length > 3000 ? sd.slice(0, 3000) + "\n<<truncated>>" : sd);
  } catch (e) {
    lines.push("<<failed to stringify source data>>");
  }

  lines.push("");
  lines.push("Return JSON ONLY with these fields:");
  lines.push("  - one_liner (string): one-line recommendation or summary");
  lines.push("  - summary (string): short paragraph investor-facing summary");
  lines.push("  - citation_snippets (optional array): [{source, url}]");
  lines.push("");
  lines.push("Important: respond only with valid JSON. Do not include explanatory text.");
  return lines.join("\n");
}

/* ---------- call Perplexity ---------- */
async function callPerplexity(prompt) {
  if (!PERPLEXITY_KEY) throw new Error("PERPLEXITY_KEY not configured on server");
  // payload follows Perplexity chat completions / sonar model pattern
  const payload = {
    model: "sonar",
    messages: [
      { role: "system", content: "You are a factual research assistant that returns JSON." },
      { role: "user", content: prompt }
    ],
    temperature: 0.1,
    max_tokens: 800,
  };

  const res = await fetchWithTimeout(PERPLEXITY_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${PERPLEXITY_KEY}`,
      Accept: "application/json",
    },
    body: JSON.stringify(payload),
  }, 25_000);

  const rawText = await res.text().catch(() => "");
  const ct = (res.headers.get("content-type") || "").toLowerCase();

  if (!rawText) throw new Error(`Empty response from Perplexity (status ${res.status})`);

  // If the response is JSON, parse and return it
  if (ct.includes("json") || ct.includes("+json")) {
    try {
      return JSON.parse(rawText);
    } catch (e) {
      // fallback to raw text wrapped
      return { raw: rawText, parse_error: e.message };
    }
  }

  // Some Perplexity responses return plain text (choices[].message.content)
  // Attempt to extract a JSON block (array or object)
  const jsonMatch = rawText.match(/(\{[\s\S]*\}|\[[\s\S]*\])/);
  if (jsonMatch) {
    try {
      return JSON.parse(jsonMatch[0]);
    } catch (e) {
      // if parsing fails, return raw with match info
      return { raw: rawText, matched: jsonMatch[0].slice(0, 200), parse_error: e.message };
    }
  }

  // final fallback: return raw text
  return { raw: rawText };
}

/* ---------- research endpoint ---------- */
/**
 * POST /research/summary
 * body: { ticker: "RELIANCE", mode: "short" }
 * query: ?ticker=RELIANCE
 */
router.post("/summary", async (req, res) => {
  const ticker = (req.body && (req.body.ticker || req.body.symbol)) || req.query.ticker || null;
  const mode = (req.body && req.body.mode) || req.query.mode || "short";

  if (!ticker) return res.status(400).json({ error: "Missing ticker in body or ?ticker" });

  try {
    // Fetch upstream pieces in parallel (best-effort — each may return null)
    const fetches = [
      fetchIndian(`/stock?name=${encodeURIComponent(ticker)}`),
      fetchIndian(`/historical_data?symbol=${encodeURIComponent(ticker)}&period=1yr&filter=price`),
      fetchIndian(`/stock_target_price?stock_id=${encodeURIComponent(ticker)}`),
      fetchIndian(`/commodities`),
    ];

    const results = await Promise.all(fetches.map(p => p.catch(err => { console.warn("upstream part failed", err); return null; })));

    const stockData = results[0] || null;
    const historical = results[1] || null;
    const priceTarget = results[2] || null;
    const commodities = results[3] || null;

    // Build a concise source_data snapshot (avoid huge payload)
    const source_data = {
      stockData: stockData ? (typeof stockData === "object" ? stockData : { raw: String(stockData).slice(0, 1000) }) : null,
      historical: historical ? (Array.isArray(historical) ? historical.slice(0, 120) : (typeof historical === "object" ? historical : { raw: String(historical).slice(0, 1000) })) : null,
      priceTarget: priceTarget ? (typeof priceTarget === "object" ? priceTarget : { raw: String(priceTarget).slice(0, 500) }) : null,
      commodities: Array.isArray(commodities) ? commodities.slice(0, 12) : (commodities || null),
    };

    // If Perplexity is configured, call it
    if (PERPLEXITY_KEY) {
      try {
        const prompt = buildPrompt(ticker, source_data);
        const llmResp = await callPerplexity(prompt);

        // llmResp might be an object with fields or nested under choices/message (when raw shape returned)
        // Try to normalize probable fields
        let one_liner = null;
        let summary = null;
        let citation_snippets = null;

        if (typeof llmResp === "object" && !Array.isArray(llmResp)) {
          // Common direct fields
          one_liner = llmResp.one_liner || llmResp.oneLine || llmResp.oneLiner || llmResp.one_liner_text || null;
          summary = llmResp.summary || llmResp.answer || llmResp.text || null;
          citation_snippets = llmResp.citation_snippets || llmResp.citations || llmResp.citation || null;

          // If llmResp.choices (OpenAI-style), try extract
          if (!one_liner && Array.isArray(llmResp.choices) && llmResp.choices[0]) {
            const content = llmResp.choices[0].message?.content || llmResp.choices[0].text || null;
            if (content) {
              const match = String(content).match(/(\{[\s\S]*\}|\[[\s\S]*\])/);
              if (match) {
                try {
                  const j = JSON.parse(match[0]);
                  one_liner = one_liner || j.one_liner || j.oneLine || null;
                  summary = summary || j.summary || j.answer || null;
                  citation_snippets = citation_snippets || j.citation_snippets || j.citations || null;
                } catch (e) {
                  // ignore parse error
                }
              } else {
                summary = summary || String(content).slice(0, 2000);
              }
            }
          }
        } else if (typeof llmResp === "string") {
          // If Perplexity returned a string, attempt to extract JSON
          const match = llmResp.match(/(\{[\s\S]*\}|\[[\s\S]*\])/);
          if (match) {
            try {
              const j = JSON.parse(match[0]);
              one_liner = j.one_liner || j.oneLine || null;
              summary = j.summary || j.answer || null;
              citation_snippets = j.citation_snippets || j.citations || null;
            } catch (e) {
              summary = llmResp.slice(0, 2000);
            }
          } else {
            summary = llmResp.slice(0, 2000);
          }
        }

        if (!one_liner && summary) {
          one_liner = typeof summary === "string" ? summary.split(".")[0].slice(0, 160) : null;
        }
        if (!summary && one_liner) summary = one_liner;

        return res.json({
          one_liner,
          summary,
          citation_snippets,
          source_data,
          raw: llmResp,
          mode,
        });
      } catch (err) {
        console.error("Perplexity call failed:", err?.message || err);
        // fallback to snapshot
        return res.json({
          one_liner: `Perplexity call failed: ${String(err?.message || err).slice(0, 180)}`,
          summary: "Perplexity unavailable; returning internal snapshot.",
          source_data,
          raw: null,
          mode,
        });
      }
    }

    // No Perplexity: return internal snapshot only
    return res.json({
      one_liner: `No Perplexity key; returning internal data for ${ticker}`,
      summary: "No Perplexity key; partial data included.",
      source_data,
      raw: null,
      mode,
    });
  } catch (err) {
    console.error("research route failure:", err?.message || err);
    return res.status(500).json({ error: "research failed", detail: String(err?.message || err) });
  }
});

export default router;
