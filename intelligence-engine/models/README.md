# Financial Intelligence Model Library (FIML) v1.0

Shared institutional domain models for AGI.

**FIML is not an intelligence engine.** It is a reusable library. Architecture v1.0.1 remains locked.

## Layout

```text
models/
  accounting/ business/ industry/ competition/ capital_allocation/
  economics/ macro/ risk/ governance/ valuation/ forecasting/ decision/
```

Industry behaviour is configuration-driven via `industry/configs/*.json`.

## Interfaces

Every model exposes: `analyse` · `score` · `explain` · `compare` · `monitor` · `timeline` · `search` · `relationships`

## Consumption (no engine redesign)

```python
from models.consumers import for_ve, for_iie, for_irp, for_ask_agi
from models.registry import get_registry

reg = get_registry()
reg.analyse("accounting", {"company_symbol": "INFY", "cash_conversion": 0.95})
for_ve({"company_symbol": "INFY", "industry": "it_services"})
```

Facade APIs: `/v1/fiml/*` · Admin: `/admin/models`
