"""FIML service facade — exposes the model library without being an engine."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.fiml.flags import FimlFlags
from app.fiml.store import FimlStore
from models import consumers
from models.industry.model import list_industries
from models.registry import ModelRegistry, get_registry


class FimlService:
    """Library access layer for institutional domain models."""

    def __init__(
        self,
        *,
        flags: FimlFlags | None = None,
        store: FimlStore | None = None,
        registry: ModelRegistry | None = None,
    ) -> None:
        self.flags = flags or FimlFlags.from_settings(get_settings())
        self.store = store or FimlStore()
        self.registry = registry or get_registry()

    def _require(self) -> None:
        if not self.flags.fiml:
            raise RuntimeError("FIML is disabled (FIML=false)")

    def _remember(self, domain: str, result: dict[str, Any]) -> dict[str, Any]:
        if self.flags.fiml_persist_analyses:
            self.store.add(domain, result)
        return result

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.flags.fiml else "disabled",
            "layer": "Financial Intelligence Model Library",
            "programme": "FIML",
            "version": "fiml-v1.0.0",
            "architecture_status": "v1.0.1 LOCKED",
            "not_an_engine": True,
            "position": "shared_domain_model_library",
            "no_redesign": [
                "kf1",
                "kcv1",
                "aoi",
                "eve",
                "iie",
                "fle",
                "mee",
                "ve",
                "cae",
                "ib",
                "kip",
                "irp",
                "rsp",
                "ask_agi",
            ],
            "domains": [m["domain"] for m in self.registry.list_models()],
            "industry_configs": list_industries(),
            "flags": self.flags.as_dict(),
            "snapshot": self.store.snapshot() if self.flags.fiml else {},
            "metrics": self.store.metrics.model_dump(),
            "dependency_graph": self.registry.dependency_graph() if self.flags.fiml else {},
        }

    def dashboard(self) -> dict[str, Any]:
        self._require()
        recent = list(reversed(self.store.history[-30:]))
        return {
            "programme": "FIML",
            "not_an_engine": True,
            "models": self.registry.list_models(),
            "industries": list_industries(),
            "metrics": self.store.metrics.model_dump(),
            "recent_analyses": recent,
            "dependency_graph": self.registry.dependency_graph(),
            "modules": [
                "Accounting",
                "Business",
                "Industry",
                "Competition",
                "Capital Allocation",
                "Economics",
                "Risk",
                "Governance",
                "Decision",
                "Model Registry",
                "Version History",
                "Coverage Dashboard",
                "Quality Scores",
                "Dependency Graph",
            ],
        }

    def list_models(self) -> dict[str, Any]:
        self._require()
        return {"models": self.registry.list_models(), "count": len(self.registry.list_models())}

    def analyse(self, domain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        result = self.registry.analyse(domain, payload or {})
        return self._remember(domain, result)

    def score(self, domain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        return self.registry.score(domain, payload or {})

    def explain(self, domain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        return self.registry.explain(domain, payload or {})

    def compare(self, domain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        data = payload or {}
        left = data.get("left") or {}
        right = data.get("right") or {}
        if not left or not right:
            raise RuntimeError("compare requires left and right payloads")
        return self.registry.compare(domain, left, right)

    def monitor(self, domain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        return self.registry.monitor(domain, payload or {})

    def timeline(self, domain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        return self.registry.timeline(domain, payload or {})

    def relationships(self, domain: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        return self.registry.relationships(domain, payload or {})

    def search(self, q: str, *, domain: str | None = None, limit: int = 20) -> dict[str, Any]:
        self._require()
        return self.registry.search(q, domain=domain, limit=limit)

    def bundle(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require()
        out = self.registry.analyse_bundle(payload or {})
        if out.get("decision"):
            self._remember("decision", out["decision"])
        return out

    def consumer(self, engine: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Demonstrate engine consumption contracts without modifying engines."""
        self._require()
        key = (engine or "").lower().strip()
        mapping = {
            "eve": consumers.for_eve,
            "iie": consumers.for_iie,
            "fle": consumers.for_fle,
            "mee": consumers.for_mee,
            "ve": consumers.for_ve,
            "cae": consumers.for_cae,
            "irp": consumers.for_irp,
            "ask_agi": consumers.for_ask_agi,
            "ask-agi": consumers.for_ask_agi,
            "kf": lambda p: {"consumer": "KF", "industry": self.registry.analyse("industry", p), "business": self.registry.analyse("business", p)},
        }
        fn = mapping.get(key)
        if not fn:
            raise KeyError(f"Unknown consumer engine: {engine}")
        return fn(payload or {})

    def industries(self) -> dict[str, Any]:
        self._require()
        return {"industries": list_industries(), "count": len(list_industries())}

    def metrics(self) -> dict[str, Any]:
        self._require()
        return {"metrics": self.store.metrics.model_dump(), "snapshot": self.store.snapshot()}

    def graph(self) -> dict[str, Any]:
        self._require()
        return self.registry.dependency_graph()
