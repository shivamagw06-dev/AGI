# Ask orchestration fix — routing before retrieval

## Diagnosis (live smoke)

| Layer | Failure |
|-------|---------|
| Node → Engine | 6/8 prompts hit 90s abort → market-desk fallback |
| Intent / Entity | `SUMMARIZE` / `JSWSTEEL` / Theme-over-Meta |
| Reasoning | ICE executive was framework scaffolding (`Frameworks applied` / `Playbook`) |

## Fixes

1. **Node fallback honesty** (`server/services/askDeskFallback.js`, `server/routes/ui.js`)
   - Fallback no longer pretends the market blurb answers the research question
   - `ASK_ENGINE_TIMEOUT_MS` (default **120000**)
   - `ask_orchestration` metadata: `engine_reached`, `timeout_ms`, reason

2. **Ticker binding guard** (`app/ui/ticker_guard.py`, CAE planner, Kip stopwords)
   - Reject prose tokens (`SUMMARIZE`, `WHAT`, `CAPEX`, …)
   - Alias-bind Meta / Apple / Microsoft / Reliance / …
   - Soft packs cannot override an explicit company mention
   - Final sanitize before `SearchView`

3. **ICE executive** (`institutional_communication/renderers/engine.py`)
   - Lead with analysis / evidence / framework *reason*
   - Do not lead with Intent / Frameworks applied / Playbook checklist
   - UiService suppresses framework-meta ICE overwrite when a better executive exists

## Verify

```bash
cd intelligence-engine
pytest tests/test_ask_orchestration_guards.py institutional_communication/tests/test_ice.py -q

cd ..
node --test server/tests/askDeskFallback.test.js
```
