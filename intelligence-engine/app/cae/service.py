"""CAE service facade — unified context assembly for Ask AGI."""

from __future__ import annotations

from typing import Any

from app.cae.assembler import CaeAssembler
from app.cae.config import DEFAULT_TOKEN_BUDGET
from app.cae.flags import CaeFlags
from app.cae.planner import plan_query
from app.cae.retrieval import CaeRetriever
from app.cae.store import CaeStore
from app.core.config import get_settings


class CaeService:
    """Context Assembly Engine — orchestrates intelligence engines; never reasons."""

    def __init__(
        self,
        *,
        flags: CaeFlags | None = None,
        store: CaeStore | None = None,
        kf: Any | None = None,
        kc: Any | None = None,
        aoi: Any | None = None,
        eve: Any | None = None,
        iie: Any | None = None,
        fle: Any | None = None,
        mee: Any | None = None,
        fre: Any | None = None,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
    ) -> None:
        self.flags = flags or CaeFlags.from_settings(get_settings())
        self.store = store or CaeStore()
        self.kf = kf
        self.kc = kc
        self.aoi = aoi
        self.eve = eve
        self.iie = iie
        self.fle = fle
        self.mee = mee
        self.fre = fre
        self.retriever = CaeRetriever(
            kf=kf,
            kc=kc,
            aoi=aoi,
            eve=eve,
            iie=iie,
            fle=fle,
            mee=mee,
            fre=fre,
            parallel=self.flags.cae_parallel,
        )
        self.assembler = CaeAssembler(
            self.store,
            self.retriever,
            use_cache=self.flags.cae_cache,
            compress=self.flags.cae_compress,
            token_budget=token_budget,
            aoi=aoi,
            eve=eve,
        )

    def bind(self, **engines: Any) -> None:
        for name, eng in engines.items():
            if hasattr(self, name):
                setattr(self, name, eng)
            if hasattr(self.retriever, name):
                setattr(self.retriever, name, eng)
        if "aoi" in engines:
            self.assembler.aoi = engines["aoi"]
        if "eve" in engines:
            self.assembler.eve = engines["eve"]

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.cae else "disabled",
            "layer": "Context Assembly Engine",
            "programme": "CAE",
            "version": "cae-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "ask_agi_gateway_before_reasoning",
            "no_redesign": [
                "kf1",
                "kcv1",
                "aoi",
                "eve",
                "iie",
                "fle",
                "mee",
                "kip",
                "irp",
                "rsp",
                "ask_agi",
            ],
            "orchestrates": ["kf", "kc", "aoi", "eve", "iie", "fle", "mee"],
            "future_engines": ["pmo", "ime", "rme", "ams"],
            "never_reasons": True,
            "flags": self.flags.as_dict(),
            "snapshot": self.store.snapshot() if self.flags.cae else {},
            "metrics": self.store.metrics.model_dump(),
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        recent = [
            self.store.packages[pid].to_dict()
            for pid in reversed(self.store.recent_ids[-30:])
            if pid in self.store.packages
        ]
        return {
            "programme": "CAE",
            "architecture_status": "v1.0.1 LOCKED",
            "metrics": self.store.metrics.model_dump(),
            "snapshot": self.store.snapshot(),
            "live_requests": recent,
            "cache": self.store.cache_stats(),
            "audit": [a.to_dict() for a in self.store.audit[-30:]],
        }

    def query_plan(self, query: str, *, ticker: str | None = None) -> dict[str, Any]:
        self._require()
        return plan_query(query, ticker=ticker, aoi=self.aoi).to_dict()

    def retrieve(self, query: str, *, ticker: str | None = None) -> dict[str, Any]:
        self._require()
        plan = plan_query(query, ticker=ticker, aoi=self.aoi)
        items, contribs = self.retriever.retrieve(query, plan.engines, limit=8)
        return {
            "plan": plan.to_dict(),
            "count": len(items),
            "items": [i.to_dict() for i in items],
            "engine_contributions": [c.to_dict() for c in contribs],
        }

    def context(self, query: str, *, ticker: str | None = None, use_cache: bool | None = None) -> dict[str, Any]:
        self._require()
        pkg = self.assembler.assemble(query, ticker=ticker, use_cache=use_cache)
        return pkg.to_dict()

    def assemble_for_ask_agi(self, query: str, *, ticker: str | None = None) -> dict[str, Any]:
        """Primary Ask AGI gateway — one unified package + soft-compat fields."""
        self._require()
        if not self.flags.cae_ask_agi_gateway:
            raise RuntimeError("CAE Ask AGI gateway disabled")
        pkg = self.assembler.assemble(query, ticker=ticker)
        data = pkg.to_dict()
        soft = data.get("soft_fields") or {}
        # Ensure FAPI package is present even on cache hits (additive; never blocks CAE).
        if not (isinstance(soft.get("finance_academy"), dict) and soft["finance_academy"].get("concept_ids")):
            try:
                from academy.fapi.production import package_for_query

                soft["finance_academy"] = package_for_query(
                    query, engine="cae", ticker=ticker or (data.get("plan") or {}).get("primary_ticker")
                )
            except Exception:
                soft.setdefault("finance_academy", {"enabled": False, "concept_ids": []})
        return {
            "package": data,
            "soft_fields": soft,
            "finance_academy": soft.get("finance_academy") or {},
            "primary_ticker": (data.get("plan") or {}).get("primary_ticker") or ticker,
            "answer_policy": "unified_context_before_reasoning",
            "guidance": {
                "single_orchestration_call": True,
                "do_not_bypass_to_individual_engines": True,
                "preserve_engine_independence": True,
                "academy_before_reasoning": True,
            },
        }

    def explain(self, package_id: str) -> dict[str, Any]:
        self._require()
        return self.assembler.explain_package(package_id)

    def cache(self, *, action: str = "stats") -> dict[str, Any]:
        self._require()
        if not self.flags.cae_cache:
            raise RuntimeError("CAE cache disabled")
        if action == "clear":
            n = self.store.cache_clear()
            return {"cleared": n}
        return self.store.cache_stats()

    def metrics(self) -> dict[str, Any]:
        self._require()
        return {
            "metrics": self.store.metrics.model_dump(),
            "snapshot": self.store.snapshot(),
        }

    def search(self, query: str, *, limit: int = 20) -> dict[str, Any]:
        self._require()
        q = (query or "").lower().strip()
        hits = []
        for pid in reversed(self.store.recent_ids):
            pkg = self.store.packages.get(pid)
            if not pkg:
                continue
            blob = f"{pkg.query} {pkg.query_summary} {' '.join(pkg.entities)}".lower()
            if q in blob or any(tok in blob for tok in q.split() if len(tok) > 2):
                hits.append(
                    {
                        "kind": "context_package",
                        "id": pkg.package_id,
                        "label": pkg.query_summary[:80],
                        "score": float((pkg.confidence_summary or {}).get("average_confidence") or 0.5),
                        "snippet": pkg.query,
                        "latency_ms": pkg.assembly_latency_ms,
                        "cache_hit": pkg.cache_hit,
                    }
                )
            if len(hits) >= limit:
                break
        return {"query": query, "hits": hits, "count": len(hits)}

    def get_package(self, package_id: str) -> dict[str, Any]:
        self._require()
        pkg = self.store.get_package(package_id)
        if not pkg:
            raise KeyError(f"Package '{package_id}' not found")
        return pkg.to_dict()

    def _require(self) -> None:
        if not self.flags.cae:
            raise RuntimeError("CAE is disabled (CAE=false)")
