"""Merge Ownership Pack v2 into CID / company analysis without overwriting richer data."""

from __future__ import annotations

from typing import Any


def merge_ownership_into_dossier(dossier: dict[str, Any], pack: dict[str, Any]) -> dict[str, Any]:
    """Attach ownership evidence to CID so readiness_gate sees promoter/fii."""
    if not isinstance(dossier, dict) or not isinstance(pack, dict) or not pack.get("ok"):
        return dossier
    out = dict(dossier)
    ownership = dict(pack.get("ownership") or {})
    # Top-level keys consumed by readiness_gate
    out["ownership"] = {
        **ownership,
        "promoter": pack.get("promoter"),
        "fii": pack.get("fii"),
        "dii": pack.get("dii"),
        "mutual_funds": pack.get("mutual_funds"),
        "insurance": pack.get("insurance"),
        "public": pack.get("public"),
        "pledged": pack.get("promoter_pledge_pct"),
        "promoter_pledge": pack.get("promoter_pledge"),
        "as_of_quarter": pack.get("as_of_quarter"),
        "quarter_label": pack.get("quarter_label"),
        "intelligence": pack.get("intelligence"),
        "qoq": pack.get("qoq"),
        "history": pack.get("quarter_history") or [],
        "freshness": pack.get("freshness"),
        "lineage": pack.get("lineage"),
        "source": pack.get("source"),
        "engine": pack.get("engine"),
        "version": pack.get("version"),
        "missing": False,
    }
    out["shareholding"] = {
        "records": pack.get("quarter_history") or [],
        "latest": ownership,
        "promoter": pack.get("promoter"),
        "fii": pack.get("fii"),
        "dii": pack.get("dii"),
        "mutual_funds": pack.get("mutual_funds"),
        "insurance": pack.get("insurance"),
        "public": pack.get("public"),
        "pledged": pack.get("promoter_pledge_pct"),
        "as_of": pack.get("as_of_quarter"),
        "source": "ownership_intelligence",
    }
    mgmt = dict(out.get("management") or {})
    mgmt_own = dict(mgmt.get("ownership") or {})
    # Fill empties only
    for k, v in (
        ("promoter_holding", pack.get("promoter")),
        ("promoters", pack.get("promoter")),
        ("fii", pack.get("fii")),
        ("dii", pack.get("dii")),
        ("mutual_funds", pack.get("mutual_funds")),
        ("insurance", pack.get("insurance")),
        ("public", pack.get("public")),
        ("pledged_shares", pack.get("promoter_pledge_pct")),
        ("promoter_pledge", pack.get("promoter_pledge")),
    ):
        if mgmt_own.get(k) in (None, {}, []) and v is not None:
            mgmt_own[k] = v
    mgmt_own["historical_ownership"] = pack.get("quarter_history") or mgmt_own.get("historical_ownership") or []
    mgmt_own["ownership_intelligence"] = pack.get("intelligence")
    mgmt["ownership"] = mgmt_own
    if mgmt.get("promoter") in (None, "", {}) and pack.get("promoter") is not None:
        mgmt["promoter"] = {
            "holding_pct": pack.get("promoter"),
            "pledge_pct": pack.get("promoter_pledge_pct"),
            "pledged": pack.get("promoter_pledge"),
            "as_of": pack.get("as_of_quarter"),
            "source": "nse_shareholding",
        }
    out["management"] = mgmt
    out["ownership_intelligence"] = {
        "enabled": True,
        "ok": True,
        "pack": {
            "promoter": pack.get("promoter"),
            "fii": pack.get("fii"),
            "dii": pack.get("dii"),
            "mutual_funds": pack.get("mutual_funds"),
            "insurance": pack.get("insurance"),
            "public": pack.get("public"),
            "promoter_pledge": pack.get("promoter_pledge"),
            "promoter_pledge_pct": pack.get("promoter_pledge_pct"),
            "as_of_quarter": pack.get("as_of_quarter"),
            "intelligence": pack.get("intelligence"),
            "qoq": pack.get("qoq"),
            "freshness": pack.get("freshness"),
            "lineage": pack.get("lineage"),
            "confidence": pack.get("confidence"),
            "score": pack.get("score"),
            "evidence": pack.get("evidence"),
        },
    }
    # Evidence timeline breadcrumb
    timeline = list(out.get("evidence_timeline") or [])
    timeline.append(
        {
            "at": pack.get("generated_at"),
            "kind": "shareholding",
            "source": "ownership_intelligence",
            "summary": (pack.get("intelligence") or {}).get("reasoning"),
            "as_of": pack.get("as_of_quarter"),
        }
    )
    out["evidence_timeline"] = timeline[-200:]
    return out
