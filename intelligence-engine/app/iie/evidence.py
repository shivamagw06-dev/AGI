"""Evidence adapter — consume only verified / preferred EVE outputs (never raw docs)."""

from __future__ import annotations

from typing import Any

from app.iie.config import MIN_EVIDENCE_CONFIDENCE, PREFERRED_STATUSES


def _as_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    return {}


def evidence_ref(ev: dict[str, Any]) -> dict[str, Any]:
    prov = ev.get("provenance") or {}
    return {
        "evidence_id": ev.get("evidence_id") or "",
        "claim_text": (ev.get("value_text") or ev.get("claim_text") or "")[:300],
        "confidence": float(ev.get("confidence") or 0),
        "status": ev.get("verification_status") or ev.get("status") or "",
        "source_url": prov.get("url") or ev.get("source_url") or "",
        "fact_key": ev.get("fact_key") or "",
        "company_id": ev.get("company_id") or "",
        "company_symbol": ev.get("company_symbol") or "",
    }


class VerifiedEvidenceReader:
    """Read-only bridge to EVE (+ optional KF/KC enrichment metadata)."""

    def __init__(self, eve: Any | None = None, kc: Any | None = None, kf: Any | None = None) -> None:
        self.eve = eve
        self.kc = kc
        self.kf = kf

    def list_for_company(self, company_id: str, *, limit: int = 200) -> list[dict[str, Any]]:
        if not self.eve:
            return []
        try:
            pack = self.eve.list_evidence(company_id=company_id, limit=limit)
            rows = pack.get("evidence") if isinstance(pack, dict) else []
        except Exception:
            rows = []
        return self._filter(rows or [])

    def company_pack(self, key: str) -> dict[str, Any]:
        if not self.eve:
            return {}
        try:
            return self.eve.company_pack(key) or {}
        except Exception:
            return {}

    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        if not self.eve:
            return []
        try:
            res = self.eve.search(query, limit=limit)
            hits = res.get("hits") if isinstance(res, dict) else []
        except Exception:
            hits = []
        # Prefer evidence hits with confidence
        out = []
        for h in hits or []:
            if not isinstance(h, dict):
                continue
            if h.get("kind") == "conflict":
                continue
            conf = float(h.get("confidence") or h.get("score") or 0)
            if conf < MIN_EVIDENCE_CONFIDENCE:
                continue
            status = (h.get("verification_status") or "").lower()
            if status and status not in PREFERRED_STATUSES and status != "conflicted":
                # allow conflicted for explainability but not as primary
                continue
            out.append(h)
        return out

    def conflicts_for_company(self, company_id: str) -> list[dict[str, Any]]:
        if not self.eve:
            return []
        try:
            res = self.eve.conflicts(status="open")
            rows = res.get("conflicts") if isinstance(res, dict) else []
        except Exception:
            return []
        return [c for c in (rows or []) if isinstance(c, dict) and c.get("company_id") == company_id]

    def resolve_company(self, key: str) -> tuple[str, str, str]:
        """Return (company_id, symbol, name) via EVE pack / AOI soft resolution."""
        pack = self.company_pack(key)
        company_id = pack.get("company_id") or key
        symbol = pack.get("symbol") or ""
        # Prefer canonical company_id from evidence rows when pack key was a symbol.
        evidence_rows = pack.get("evidence") if isinstance(pack, dict) else None
        if evidence_rows:
            for row in evidence_rows:
                ev = row if isinstance(row, dict) else _as_dict(row)
                if ev.get("company_id"):
                    company_id = ev["company_id"]
                    symbol = symbol or ev.get("company_symbol") or ""
                    break
        if not evidence_rows:
            # Fallback: list by key as company_id
            listed = self.list_for_company(key, limit=5)
            if listed and listed[0].get("company_id"):
                company_id = listed[0]["company_id"]
                symbol = symbol or listed[0].get("company_symbol") or ""
        name = symbol or company_id
        # Soft KF enrichment (label only — do not override evidenced company_id)
        if self.kf is not None:
            try:
                hit = self.kf.search(key, limit=1)
                hits = hit.get("hits") if isinstance(hit, dict) else []
                if hits:
                    name = hits[0].get("label") or name
            except Exception:
                pass
        return str(company_id), str(symbol), str(name)

    def _filter(self, rows: list[Any]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in rows:
            ev = _as_dict(row)
            if not ev:
                continue
            status = (ev.get("verification_status") or "").lower()
            conf = float(ev.get("confidence") or 0)
            if status and status not in PREFERRED_STATUSES and status != "conflicted":
                continue
            if conf < MIN_EVIDENCE_CONFIDENCE and status != "verified":
                continue
            out.append(ev)
        # Highest confidence first
        out.sort(key=lambda e: -float(e.get("confidence") or 0))
        return out
