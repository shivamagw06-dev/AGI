"""Connector registry — single place to resolve institutional connectors."""

from __future__ import annotations

from typing import Any

from institutional_data.connectors.base import Connector
from institutional_data.connectors.bse import BSECorporateActionsConnector
from institutional_data.connectors.financials import FinancialStatementsConnector
from institutional_data.connectors.ir_discovery import IRDiscoveryConnector
from institutional_data.connectors.rbi import RBIMacroConnector
from institutional_data.connectors.shareholding import ShareholdingConnector


class NSEBhavcopyConnector(Connector):
    connector_id = "lidi_nse_bhavcopy_v1"
    source_id = "nse_bhavcopy"
    official_source = "NSE India"

    def collect(self, **kwargs: Any):
        from institutional_data.connectors.base import ConnectorResult
        from live_data.collectors.nse_bhavcopy import collect_nse_bhavcopy

        env = collect_nse_bhavcopy(**{k: kwargs[k] for k in ("as_of", "injected_csv", "allow_recorded_sample") if k in kwargs})
        rows = ((env.get("payload") or {}).get("rows") or [])
        return ConnectorResult(
            ok=bool(env.get("ok")),
            connector_id=self.connector_id,
            source_id=self.source_id,
            records=rows,
            mode=str(env.get("mode") or "live"),
            error=env.get("error"),
            diagnostics={"legacy_envelope": True},
            coverage_pct=100.0 if env.get("ok") else 0.0,
        )

    def validate(self, records, **kwargs):
        return {"ok": bool(records), "accepted": len(records)}

    def normalize(self, records, **kwargs):
        return records

    def store(self, records, **kwargs):
        return {"delegated": "legacy_collector", "n": len(records)}


class NSEAnnouncementsConnector(Connector):
    connector_id = "lidi_nse_announcements_v1"
    source_id = "nse_announcements"
    official_source = "NSE India"

    def collect(self, **kwargs: Any):
        from institutional_data.connectors.base import ConnectorResult
        from live_data.collectors.nse_announcements import collect_nse_announcements

        env = collect_nse_announcements(
            **{k: kwargs[k] for k in ("injected_json", "allow_recorded_sample") if k in kwargs}
        )
        payload = env.get("payload") or {}
        rows = payload.get("announcements") or payload.get("items") or payload.get("rows") or []
        return ConnectorResult(
            ok=bool(env.get("ok")),
            connector_id=self.connector_id,
            source_id=self.source_id,
            records=list(rows or []),
            mode=str(env.get("mode") or "live"),
            error=env.get("error"),
            diagnostics={"legacy_envelope": True},
        )

    def validate(self, records, **kwargs):
        return {"ok": True, "accepted": len(records)}

    def normalize(self, records, **kwargs):
        return records

    def store(self, records, **kwargs):
        return {"delegated": "legacy_collector", "n": len(records)}


_REGISTRY: dict[str, type[Connector]] = {
    "bse_corporate_actions": BSECorporateActionsConnector,
    "rbi_dbie": RBIMacroConnector,
    "financial_statements": FinancialStatementsConnector,
    "shareholding": ShareholdingConnector,
    "company_ir": IRDiscoveryConnector,
    "nse_bhavcopy": NSEBhavcopyConnector,
    "nse_announcements": NSEAnnouncementsConnector,
}


def get_connector(source_id: str) -> Connector:
    cls = _REGISTRY.get(source_id)
    if not cls:
        raise KeyError(f"unknown_connector:{source_id}")
    return cls()


def all_connectors() -> list[Connector]:
    return [cls() for cls in _REGISTRY.values()]
