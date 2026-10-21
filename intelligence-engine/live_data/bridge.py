"""Soft-wire validated LIDI outputs into Knowledge Factory surfaces.

Never calls reasoning. Never invents metrics. Updates existing object types only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from live_data import store
from live_data.schema import LIDI_VERSION


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def publish_to_knowledge_factory(
    *,
    as_of: Optional[str] = None,
    bhavcopy: Optional[Dict[str, Any]] = None,
    announcements: Optional[Dict[str, Any]] = None,
    corporate_actions: Optional[Dict[str, Any]] = None,
    macro: Optional[Dict[str, Any]] = None,
    ir: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Write Knowledge Objects + Evidence Pack stubs from validated LIDI outputs."""
    day = as_of or _now()[:10]
    objects: Dict[str, List[Dict[str, Any]]] = {
        "COMPANY": [],
        "CORPORATE_EVENT": [],
        "MACRO": [],
        "HISTORICAL": [],
        "TIMELINE": [],
        "ALTERNATIVE_DATA": [],
        "EXPECTATION": [],
    }
    packs: List[Dict[str, Any]] = []

    if bhavcopy and bhavcopy.get("rows"):
        hist = {
            "object_type": "HISTORICAL",
            "as_of": day,
            "source": "NSE_BHAVCOPY",
            "collector": "lidi_nse_bhavcopy_v1",
            "row_count": len(bhavcopy["rows"]),
            "sample_tickers": [r.get("ticker") for r in bhavcopy["rows"][:20]],
            "rows": bhavcopy["rows"][:500],
            "provenance": {
                "official_source": "NSE India",
                "collector": "lidi_nse_bhavcopy_v1",
                "validated": True,
                "derived_from": ["OHLC", "volume", "value"],
                "confidence": 0.9,
                "version": LIDI_VERSION,
            },
            "available_from": day,
            "retrieved_at": _now(),
            "effective_date": day,
            "source_version": LIDI_VERSION,
            "fixture": False,
        }
        objects["HISTORICAL"].append(hist)
        for r in bhavcopy["rows"][:50]:
            objects["COMPANY"].append(
                {
                    "object_type": "COMPANY",
                    "ticker": r.get("ticker") or r.get("symbol"),
                    "last_price": r.get("close"),
                    "volume": r.get("volume"),
                    "return_1d": r.get("return_1d"),
                    "liquidity_bucket": r.get("liquidity_bucket"),
                    "as_of": r.get("trade_date") or day,
                    "source": "NSE_BHAVCOPY",
                    "fixture": False,
                    "provenance": hist["provenance"],
                }
            )
        packs.append(
            {
                "pack_id": f"lidi-bhavcopy-{day}",
                "kind": "MARKET_PRICES",
                "source": "NSE_BHAVCOPY",
                "as_of": day,
                "object_refs": ["HISTORICAL", "COMPANY"],
                "row_count": len(bhavcopy["rows"]),
                "fixture": False,
                "provenance": hist["provenance"],
            }
        )

    if announcements and announcements.get("events"):
        objects["CORPORATE_EVENT"].extend(announcements["events"])
        objects["TIMELINE"].append(
            {
                "object_type": "TIMELINE",
                "as_of": day,
                "source": "NSE_ANNOUNCEMENTS",
                "events": announcements["events"][:100],
                "fixture": False,
            }
        )
        packs.append(
            {
                "pack_id": f"lidi-announcements-{day}",
                "kind": "CORPORATE_EVENTS",
                "source": "NSE_ANNOUNCEMENTS",
                "as_of": day,
                "row_count": len(announcements["events"]),
                "fixture": False,
            }
        )

    if corporate_actions and corporate_actions.get("events"):
        objects["CORPORATE_EVENT"].extend(corporate_actions["events"])
        packs.append(
            {
                "pack_id": f"lidi-corp-actions-{day}",
                "kind": "CORPORATE_ACTIONS",
                "source": "BSE_CORPORATE_ACTIONS",
                "as_of": day,
                "row_count": len(corporate_actions["events"]),
                "fixture": False,
            }
        )

    if macro and macro.get("observations"):
        objects["MACRO"].extend(macro["observations"])
        packs.append(
            {
                "pack_id": f"lidi-rbi-macro-{day}",
                "kind": "MACRO",
                "source": "RBI_DBIE",
                "as_of": day,
                "row_count": len(macro["observations"]),
                "fixture": False,
            }
        )

    if ir and ir.get("documents"):
        for d in ir["documents"]:
            ot = d.get("object_type") or "COMPANY"
            if ot not in objects:
                ot = "COMPANY"
            objects[ot].append(d)
        packs.append(
            {
                "pack_id": f"lidi-company-ir-{day}",
                "kind": "COMPANY_FILINGS",
                "source": "COMPANY_IR",
                "as_of": day,
                "row_count": len(ir["documents"]),
                "fixture": False,
            }
        )

    store.write_objects(day, objects)
    store.write_evidence_packs(day, packs)

    kf_soft: Dict[str, Any] = {"attempted": False}
    try:
        from knowledge_factory.events import emit  # type: ignore

        emit(
            "lidi.validated.publish",
            {
                "as_of": day,
                "packs": [p["pack_id"] for p in packs],
                "object_counts": {k: len(v) for k, v in objects.items()},
                "lidi_version": LIDI_VERSION,
            },
        )
        kf_soft = {"attempted": True, "emitted": "lidi.validated.publish"}
    except Exception as exc:  # noqa: BLE001
        kf_soft = {"attempted": True, "emitted": False, "error": str(exc)[:200]}

    return {
        "as_of": day,
        "object_counts": {k: len(v) for k, v in objects.items()},
        "pack_count": len(packs),
        "pack_ids": [p["pack_id"] for p in packs],
        "knowledge_factory_soft": kf_soft,
        "fixture": False,
        "fixture_collectors_disabled_for_lidi_sources": True,
    }


def soft_research_office_signal(publish_result: Dict[str, Any]) -> Dict[str, Any]:
    """Optional soft signal for Research Office — knowledge only, no recommendations."""
    return {
        "attempted": True,
        "result": "noop",
        "note": "Research Office consumes LIDI packs via scheduler after_ready / disk packs.",
        "packs": publish_result.get("pack_ids"),
        "as_of": publish_result.get("as_of"),
    }
