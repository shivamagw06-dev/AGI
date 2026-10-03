"""VE service facade — institutional valuation for Ask AGI consult."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.ve.config import SUPPORTED_MODELS
from app.ve.engines import MODEL_PLUGINS, sensitivity_grid
from app.ve.flags import VeFlags
from app.ve.pipeline import VePipeline
from app.ve.store import VeStore


class VeService:
    """Valuation Engine — after FLE/MEE structured intel; before reasoning. Never trades."""

    def __init__(
        self,
        *,
        flags: VeFlags | None = None,
        store: VeStore | None = None,
        eve: Any | None = None,
        iie: Any | None = None,
        fle: Any | None = None,
        mee: Any | None = None,
        aoi: Any | None = None,
        ib: Any | None = None,
    ) -> None:
        self.flags = flags or VeFlags.from_settings(get_settings())
        self.store = store or VeStore()
        self.eve = eve
        self.iie = iie
        self.fle = fle
        self.mee = mee
        self.aoi = aoi
        self.ib = ib
        self.pipeline = VePipeline(
            self.store,
            eve=eve,
            iie=iie,
            fle=fle,
            mee=mee,
            aoi=aoi,
            ib=ib,
            scenarios=self.flags.ve_scenarios,
            sensitivity=self.flags.ve_sensitivity,
            relative=self.flags.ve_relative,
        )

    def bind(self, **engines: Any) -> None:
        for name, eng in engines.items():
            if hasattr(self, name):
                setattr(self, name, eng)
            if hasattr(self.pipeline, name):
                setattr(self.pipeline, name, eng)

    def _require(self) -> None:
        if not self.flags.ve:
            raise RuntimeError("VE is disabled (VE=false)")

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.ve else "disabled",
            "layer": "Valuation Engine",
            "programme": "VE",
            "version": "ve-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "after_fle_mee_before_cae_reasoning",
            "mission": "What is this business worth?",
            "never_executes_trades": True,
            "never_consumes_raw_documents": True,
            "no_redesign": [
                "kf1",
                "kcv1",
                "aoi",
                "eve",
                "iie",
                "fle",
                "mee",
                "cae",
                "ib",
                "kip",
                "irp",
                "rsp",
                "ask_agi",
            ],
            "inputs": ["eve", "iie", "fle", "mee"],
            "models": list(SUPPORTED_MODELS),
            "plugin_models": sorted(MODEL_PLUGINS.keys()),
            "flags": self.flags.as_dict(),
            "snapshot": self.store.snapshot() if self.flags.ve else {},
            "metrics": self.store.metrics.model_dump(),
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        latest = self.store.active_valuations()
        latest_sorted = sorted(latest, key=lambda v: v.created_at, reverse=True)
        return {
            "programme": "VE",
            "architecture_status": "v1.0.1 LOCKED",
            "metrics": self.store.metrics.model_dump(),
            "snapshot": self.store.snapshot(),
            "latest_valuations": [v.to_dict() for v in latest_sorted[:40]],
            "undervalued": [
                v.to_dict()
                for v in latest_sorted
                if v.margin_of_safety and v.margin_of_safety.undervalued
            ][:20],
            "models": list(SUPPORTED_MODELS),
            "audit": list(reversed(self.store.audit[-30:])),
            "modules": [
                "Valuation Dashboard",
                "DCF Explorer",
                "Relative Valuation",
                "Historical Multiples",
                "Sensitivity Analysis",
                "Assumption Registry",
                "Scenario Comparison",
                "Margin of Safety",
                "Peer Comparison",
            ],
        }

    def value(
        self,
        key: str,
        *,
        models: list[str] | None = None,
        market_price: float | None = None,
        trigger: str = "manual",
        fiscal_year: str | None = None,
    ) -> dict[str, Any]:
        self._require()
        return self.pipeline.value_company(
            key,
            models=models,
            market_price=market_price,
            trigger=trigger,
            fiscal_year=fiscal_year,
        )

    def company(self, key: str, *, value_if_empty: bool = True) -> dict[str, Any]:
        self._require()
        hist = self.store.history_for_company(key)
        if not hist and value_if_empty and self.flags.ve_auto_value:
            created = self.value(key, trigger="auto")
            latest = created["valuation"]
            hist = self.store.history_for_company(created["company_id"]) or self.store.history_for_company(
                created["company_symbol"]
            )
        else:
            latest_obj = hist[-1] if hist else None
            latest = latest_obj.to_dict() if latest_obj else {}
        return {
            "company_id": (hist[-1].company_id if hist else key),
            "company_symbol": (hist[-1].company_symbol if hist else key.upper()),
            "latest": latest if isinstance(latest, dict) else {},
            "history": [h.to_dict() for h in hist],
            "versions": len(hist),
            "answer_policy": "valuation_before_reasoning",
        }

    def model(self, model_name: str, key: str, *, market_price: float | None = None) -> dict[str, Any]:
        self._require()
        if model_name not in MODEL_PLUGINS:
            raise KeyError(f"Unknown model: {model_name}")
        out = self.value(key, models=[model_name, "dcf_fcff"], market_price=market_price, trigger="model_api")
        val = out["valuation"]
        match = next((m for m in val.get("models") or [] if m.get("model") == model_name), None)
        return {
            "model": model_name,
            "result": match or {},
            "valuation_id": val.get("valuation_id"),
            "company_symbol": val.get("company_symbol"),
            "intrinsic_value": (match or {}).get("intrinsic_value") or val.get("intrinsic_value"),
            "assumptions": val.get("assumptions") or [],
            "explainability": val.get("explainability") or {},
        }

    def history(self, key: str, *, limit: int = 50) -> dict[str, Any]:
        self._require()
        hist = self.store.history_for_company(key)[-max(1, min(limit, 200)) :]
        return {
            "company": key.upper(),
            "history": [h.to_dict() for h in hist],
            "count": len(hist),
            "fiscal_years": sorted({h.fiscal_year for h in hist}),
        }

    def scenarios(self, key: str) -> dict[str, Any]:
        self._require()
        pack = self.company(key, value_if_empty=True)
        latest = pack.get("latest") or {}
        return {
            "company_symbol": pack.get("company_symbol"),
            "valuation_id": latest.get("valuation_id"),
            "scenarios": latest.get("scenarios") or [],
            "intrinsic_value": latest.get("intrinsic_value"),
            "margin_of_safety": latest.get("margin_of_safety") or {},
        }

    def compare(self, key: str, peers: list[str] | None = None) -> dict[str, Any]:
        self._require()
        pack = self.company(key, value_if_empty=True)
        latest = pack.get("latest") or {}
        peer_rows = list(latest.get("peers") or [])
        if peers:
            from app.ve.engines import build_peer_rows

            peer_rows = [
                p.to_dict()
                for p in build_peer_rows(pack.get("company_symbol") or key, [p.upper() for p in peers])
            ]
        subject = next(
            (p for p in peer_rows if p.get("symbol") == (pack.get("company_symbol") or "").upper()),
            None,
        )
        return {
            "company_symbol": pack.get("company_symbol"),
            "subject": subject or {},
            "peers": peer_rows,
            "metrics": ["pe", "ev_ebitda", "ev_sales", "pb", "roce", "roe", "growth", "margin", "leverage", "fcf_yield"],
            "intrinsic_value": latest.get("intrinsic_value"),
            "market_price": latest.get("market_price"),
            "relative_models": [
                m for m in (latest.get("models") or []) if str(m.get("model", "")).startswith("relative_")
            ],
        }

    def sensitivity(self, key: str) -> dict[str, Any]:
        self._require()
        pack = self.company(key, value_if_empty=True)
        latest = pack.get("latest") or {}
        points = latest.get("sensitivity") or []
        if not points and latest.get("assumptions"):
            amap = {a["name"]: float(a["value"]) for a in latest.get("assumptions") or []}
            points = [p.to_dict() for p in sensitivity_grid(amap, base_revenue_cr=150000.0)]
        # Rank parameters by absolute impact
        ranked: dict[str, float] = {}
        for p in points:
            ranked[p["parameter"]] = max(ranked.get(p["parameter"], 0.0), abs(float(p.get("change_pct") or 0)))
        top = sorted(ranked.items(), key=lambda kv: -kv[1])
        return {
            "company_symbol": pack.get("company_symbol"),
            "valuation_id": latest.get("valuation_id"),
            "sensitivity": points,
            "most_sensitive_assumptions": [{"parameter": k, "max_abs_change_pct": v} for k, v in top],
            "base_intrinsic_value": latest.get("intrinsic_value"),
        }

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        q = (query or "").strip().upper()
        hits = []
        for v in self.store.active_valuations():
            blob = f"{v.company_symbol} {v.company_id} {v.fiscal_year} {v.primary_model}".upper()
            if q and q not in blob and not any(tok in blob for tok in q.split() if len(tok) >= 2):
                continue
            hits.append(
                {
                    "valuation_id": v.valuation_id,
                    "company_symbol": v.company_symbol,
                    "intrinsic_value": v.intrinsic_value,
                    "market_price": v.market_price,
                    "margin_of_safety": v.margin_of_safety.to_dict() if v.margin_of_safety else {},
                    "confidence": v.confidence,
                    "fiscal_year": v.fiscal_year,
                    "version": v.version,
                }
            )
        hits.sort(key=lambda h: h.get("confidence") or 0, reverse=True)
        return {"query": query, "hits": hits[: max(1, min(limit, 100))], "count": len(hits)}

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Ask AGI soft retrieval — valuation before reasoning."""
        self._require()
        search = self.search(query, limit=limit)
        resolved = None
        if self.aoi is not None:
            try:
                co = self.aoi.registry.resolve(query)
                if co:
                    resolved = co.nse_symbol or co.company_id
            except Exception:
                resolved = None
        if resolved is None:
            for tok in (query or "").upper().split():
                if len(tok) >= 2 and tok.isalpha():
                    if self.store.history_for_company(tok) or self.flags.ve_auto_value:
                        resolved = tok
                        break
        company_pack = self.company(resolved, value_if_empty=True) if resolved else {}
        latest = company_pack.get("latest") or {}
        mos = latest.get("margin_of_safety") or {}
        # FAPI + SIF soft attach — sector-aware valuation methodology for Ask AGI
        finance_academy: dict = {}
        sector_intelligence: dict = {}
        try:
            from academy.fapi.production import attach_for_engine

            finance_academy = attach_for_engine("ve", query).get("finance_academy") or {}
            sector_intelligence = finance_academy.get("sector_intelligence") or {}
        except Exception:
            finance_academy = {}
        if not sector_intelligence:
            try:
                from sif.production import attach_for_engine as sif_attach

                sector_intelligence = sif_attach("ve", query).get("sector_intelligence") or {}
            except Exception:
                sector_intelligence = {}
        sif_val = (sector_intelligence.get("valuation_framework") or {}) if sector_intelligence else {}

        return {
            "answer_policy": "valuation_before_reasoning",
            "guidance": {
                "use_intrinsic_value_first": True,
                "surface_margin_of_safety": True,
                "surface_key_assumptions": True,
                "surface_sensitivity": True,
                "never_execute_trades": True,
                "academy_methodology_for_wacc": True,
                "sector_preferred_methodology": sif_val.get("methodology") or [],
                "sector_preferred_multiples": sif_val.get("preferred_multiples") or [],
                "primary_method": sif_val.get("primary_method"),
            },
            "company": company_pack,
            "latest_valuation": latest,
            "historical_valuation": (company_pack.get("history") or [])[-limit:],
            "scenarios": latest.get("scenarios") or [],
            "margin_of_safety": mos,
            "relative_valuation": [m for m in (latest.get("models") or []) if str(m.get("model", "")).startswith("relative_")],
            "assumptions": latest.get("assumptions") or [],
            "sensitivity_highlights": (latest.get("sensitivity") or [])[:8],
            "explainability": latest.get("explainability") or {},
            "search": search,
            "finance_academy": finance_academy,
            "sector_intelligence": sector_intelligence,
            "questions": {
                "is_undervalued": bool(mos.get("undervalued")),
                "intrinsic_value": latest.get("intrinsic_value"),
                "market_price": latest.get("market_price"),
                "key_assumptions": [a.get("name") for a in (latest.get("assumptions") or [])[:6]],
                "preferred_valuation_method": sif_val.get("primary_method"),
            },
        }

    def on_bus_event(self, event: Any, _sub: Any = None) -> None:
        """Soft IB subscriber — recalculate when verified/forecast/event intel changes."""
        if not self.flags.ve or not self.flags.ve_ibus_updates:
            return
        payload = getattr(event, "payload", None) or {}
        if not isinstance(payload, dict):
            payload = {}
        symbol = str(payload.get("company_symbol") or getattr(event, "aggregate_id", "") or "").upper()
        if not symbol or len(symbol) < 2:
            return
        try:
            self.value(symbol, trigger="bus_event")
            self.store.metrics.bus_triggered += 1
        except Exception:
            return

    def get_valuation(self, valuation_id: str) -> dict[str, Any]:
        self._require()
        obj = self.store.get(valuation_id)
        if not obj:
            raise KeyError(f"Valuation '{valuation_id}' not found")
        return obj.to_dict()
