"""Source Registry — dynamic priority / health / filing-type selection (FSE-02.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from financial_statements_engine.collection.source_layer import config as cfg
from financial_statements_engine.collection.source_layer.base import SourceAdapter
from financial_statements_engine.util import now_iso


@dataclass
class SourceRegistration:
    source_id: str
    display_name: str
    priority: int
    adapter_factory: Callable[[], SourceAdapter]
    supported_filing_types: tuple[str, ...]
    supported_date_range: tuple[str | None, str | None] = (None, None)
    auth_required: bool = False
    rate_limit_per_min: int | None = None
    enabled_fn: Callable[[], bool] = field(default=lambda: True)
    status: str = "registered"

    def enabled(self) -> bool:
        try:
            return bool(self.enabled_fn())
        except Exception:
            return False


_REGISTRY: dict[str, SourceRegistration] = {}
_ADAPTER_CACHE: dict[str, SourceAdapter] = {}


def register(reg: SourceRegistration) -> None:
    _REGISTRY[reg.source_id] = reg


def get_registration(source_id: str) -> SourceRegistration | None:
    return _REGISTRY.get(source_id)


def get_adapter(source_id: str) -> SourceAdapter | None:
    reg = _REGISTRY.get(source_id)
    if not reg or not reg.enabled():
        return None
    if source_id not in _ADAPTER_CACHE:
        _ADAPTER_CACHE[source_id] = reg.adapter_factory()
    return _ADAPTER_CACHE[source_id]


def list_registrations() -> list[SourceRegistration]:
    return sorted(_REGISTRY.values(), key=lambda r: r.priority)


def select_sources(
    *,
    filing_type: str | None = None,
    healthy_only: bool = True,
) -> list[SourceAdapter]:
    """Highest-priority enabled (+ optionally healthy) adapters first."""
    out: list[SourceAdapter] = []
    for reg in list_registrations():
        if not reg.enabled():
            continue
        if filing_type and filing_type not in reg.supported_filing_types and "financial_statements" not in reg.supported_filing_types:
            # allow wildcards via xbrl/annual/quarterly aliases
            aliases = {
                "annual": "annual_report",
                "quarterly": "quarterly_results",
                "annual_report": "annual_report",
                "quarterly_results": "quarterly_results",
                "xbrl": "xbrl",
            }
            ft = aliases.get(str(filing_type).lower(), filing_type)
            if ft not in reg.supported_filing_types and "*" not in reg.supported_filing_types:
                continue
        adapter = get_adapter(reg.source_id)
        if adapter is None:
            continue
        if healthy_only:
            try:
                h = adapter.health()
                if h.get("status") not in ("ok", "degraded", "ready"):
                    continue
            except Exception:
                continue
        out.append(adapter)
    return out


def registry_rows() -> list[dict[str, Any]]:
    from financial_statements_engine.collection.source_layer.metrics import source_stats

    rows = []
    stats = source_stats()
    for reg in list_registrations():
        adapter = None
        health: dict[str, Any] = {"status": "disabled"}
        if reg.enabled():
            try:
                adapter = get_adapter(reg.source_id)
                health = adapter.health() if adapter else {"status": "unavailable"}
            except Exception as exc:  # noqa: BLE001
                health = {"status": "error", "error": str(exc)[:120]}
        st = stats.get(reg.source_id) or {}
        rows.append(
            {
                "source_name": reg.display_name,
                "source_id": reg.source_id,
                "priority": reg.priority,
                "status": "enabled" if reg.enabled() else "disabled",
                "health": health.get("status"),
                "health_detail": health,
                "success_rate_pct": st.get("success_rate_pct"),
                "average_download_time_ms": st.get("average_download_time_ms"),
                "supported_filing_types": list(reg.supported_filing_types),
                "supported_date_range": list(reg.supported_date_range),
                "auth_required": reg.auth_required,
                "rate_limit_per_min": reg.rate_limit_per_min,
                "attempts": st.get("attempts", 0),
                "successes": st.get("successes", 0),
                "failures": st.get("failures", 0),
            }
        )
    return rows


def registry_manifest() -> dict[str, Any]:
    return {
        "workstream_id": "FSE-02.3",
        "sources": registry_rows(),
        "selection_policy": "highest_priority_enabled_healthy_supporting_filing_type",
        "flags": {
            "ENABLE_MCA": cfg.enable_mca(),
            "ENABLE_NSE": cfg.enable_nse(),
            "ENABLE_BSE": cfg.enable_bse(),
            "ENABLE_IR": cfg.enable_ir(),
            "SOURCE_TIMEOUT": cfg.source_timeout_s(),
            "MAX_DOWNLOAD_RETRIES": cfg.max_download_retries(),
        },
        "as_of": now_iso(),
    }


def reset_registry_for_tests() -> None:
    """Clear adapter cache (tests). Registrations remain."""
    _ADAPTER_CACHE.clear()


def _ensure_defaults_registered() -> None:
    if _REGISTRY:
        return
    from financial_statements_engine.collection.source_layer.bse.adapter import BseSourceAdapter
    from financial_statements_engine.collection.source_layer.investor_relations.adapter import IrSourceAdapter
    from financial_statements_engine.collection.source_layer.mca.adapter import McaSourceAdapter
    from financial_statements_engine.collection.source_layer.nse.adapter import NseSourceAdapter

    register(
        SourceRegistration(
            source_id="mca_xbrl",
            display_name="MCA XBRL",
            priority=1,
            adapter_factory=McaSourceAdapter,
            supported_filing_types=("xbrl", "annual_report", "financial_statements", "consolidated", "standalone"),
            enabled_fn=cfg.enable_mca,
            auth_required=False,
            rate_limit_per_min=30,
        )
    )
    register(
        SourceRegistration(
            source_id="nse_official",
            display_name="NSE Official Filing",
            priority=2,
            adapter_factory=NseSourceAdapter,
            supported_filing_types=("xbrl", "quarterly_results", "annual_report", "financial_statements", "consolidated", "standalone"),
            enabled_fn=cfg.enable_nse,
            rate_limit_per_min=60,
        )
    )
    register(
        SourceRegistration(
            source_id="bse_official",
            display_name="BSE Official Filing",
            priority=3,
            adapter_factory=BseSourceAdapter,
            supported_filing_types=("xbrl", "quarterly_results", "annual_report", "financial_statements", "pdf"),
            enabled_fn=cfg.enable_bse,
            rate_limit_per_min=60,
        )
    )
    register(
        SourceRegistration(
            source_id="company_ir",
            display_name="Company Investor Relations",
            priority=4,
            adapter_factory=IrSourceAdapter,
            supported_filing_types=("annual_report", "quarterly_results", "financial_statements", "pdf"),
            enabled_fn=cfg.enable_ir,
            rate_limit_per_min=20,
        )
    )


# Register defaults on import
_ensure_defaults_registered()
