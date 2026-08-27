# AGIB v4.0 — AI-Native Institutional Research Workspace

`/ask` is no longer a research-note dashboard. It is a **conversation with a CIO**.

## Experience

Follows **[Response Constitution v1.0](./AGIB_RESPONSE_CONSTITUTION_v1.md)** — human-first institutional research:

1. **Direct Answer** — answers the question first; horizon, confidence %, confidence explanation  
2. **Why AGIB thinks this** — every point includes a reason  
3. **Investment Thesis** — Business · Growth · Financial Quality · Valuation · Risks · Catalysts  
4. **Bull vs Bear Case** — both sides, always  
5. **Bottom Line** — one clear conclusion  
6. **Supporting Intelligence** — clickable chips that reveal evidence layers  
7. **Suggested Follow-up Questions** — continue the conversation  
8. **Right rail** — conviction scores, refresh, recent research  

## Files

| Piece | Path |
| --- | --- |
| Page | `src/pages/AskAgiPage.jsx` |
| Workspace | `src/components/AskAgi/InstitutionalChatWorkspace.jsx` |
| Styles | `src/components/AskAgi/institutionalChat.css` |
| Chat adapter | `src/components/AskAgi/adapters/mapChatAnswer.js` |
| Pack mapper (reuse) | `src/components/AskAgi/adapters/mapSearchPack.js` |

Legacy `ResearchWorkspace.jsx` remains in the repo but is not mounted on `/ask`.

## Design tokens

- Dark navy sidebar (`#0b1f33`)
- White / soft canvas conversation
- Deep blue primary, institutional green, amber warning, muted red
- Source Serif 4 + IBM Plex Sans
- No neon, glassmorphism, or crypto aesthetics
