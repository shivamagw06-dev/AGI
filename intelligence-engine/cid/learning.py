"""Learn dossier form from successful generations and provide a no-credit fallback."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from cid.coverage import compute_coverage
from cid.dossier_spec import DOSSIER_SPEC_VERSION, SECTIONS, audit_research
from cid.persistence import save_version
from cid.store import get_cid_store

PROFILE_VERSION = "cid-style-learning-v1"
_LOCK = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _path() -> Path:
    root = Path(os.environ.get("KIP_DATA_DIR") or "/tmp") / "cid_learning"
    root.mkdir(parents=True, exist_ok=True)
    return root / "dossier_style_profile.json"


def load_profile() -> dict[str, Any]:
    try:
        profile = json.loads(_path().read_text())
        return profile if isinstance(profile, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def learn_from_success(research: dict[str, Any]) -> dict[str, Any]:
    """Learn form and depth only; never retain company-specific prose."""
    sections = research.get("sections") if isinstance(research.get("sections"), dict) else {}
    observation = {
        "narrative_words": len(str(research.get("long_company_narrative") or "").split()),
        "summary_words": len(str(research.get("executive_summary") or "").split()),
        "section_words": {
            name: len(str(section.get("summary") or "").split())
            for name, section in sections.items() if isinstance(section, dict)
        },
        "section_claims": {
            name: len(section.get("claims") or [])
            for name, section in sections.items() if isinstance(section, dict)
        },
        "section_evidence": {
            name: len(section.get("evidence_ids") or [])
            for name, section in sections.items() if isinstance(section, dict)
        },
    }
    with _LOCK:
        profile = load_profile()
        count = int(profile.get("successful_examples") or 0)

        def avg(old: float, new: float) -> float:
            return round(((old * count) + new) / (count + 1), 2)

        profile.update(
            {
                "version": PROFILE_VERSION,
                "successful_examples": count + 1,
                "updated_at": _now(),
                "narrative_words": avg(float(profile.get("narrative_words") or 0), observation["narrative_words"]),
                "summary_words": avg(float(profile.get("summary_words") or 0), observation["summary_words"]),
                "section_order": list(sections),
                "policy": "learn_form_depth_and_evidence_density_never_company_prose",
            }
        )
        for key in ("section_words", "section_claims", "section_evidence"):
            prior = profile.get(key) if isinstance(profile.get(key), dict) else {}
            profile[key] = {
                name: avg(float(prior.get(name) or 0), float(value))
                for name, value in observation[key].items()
            }
        temp = _path().with_suffix(".tmp")
        temp.write_text(json.dumps(profile, indent=2, sort_keys=True))
        temp.replace(_path())
        return profile


def readiness() -> dict[str, Any]:
    profile = load_profile()
    examples = int(profile.get("successful_examples") or 0)
    minimum = max(1, int(os.environ.get("CID_FALLBACK_MIN_EXAMPLES", "1")))
    if examples >= 25:
        maturity = "mature"
    elif examples >= 5:
        maturity = "developing"
    elif examples:
        maturity = "initial"
    else:
        maturity = "untrained"
    return {
        "ready": examples >= minimum,
        "successful_examples": examples,
        "minimum_examples": minimum,
        "profile_version": profile.get("version") or PROFILE_VERSION,
        "maturity": maturity,
        "quality_status": "structural_fallback_not_model_equivalence",
    }


def _sentences(value: Any, limit: int = 3) -> list[str]:
    if value in (None, "", [], {}):
        return []
    text = json.dumps(value, ensure_ascii=False, default=str) if not isinstance(value, str) else value
    text = re.sub(r"[{}\[\]\"]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return [part.strip(" ,:") for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()][:limit]


def _block(dossier: dict[str, Any], key: str) -> Any:
    warehouse = dossier.get("warehouse_evidence") if isinstance(dossier.get("warehouse_evidence"), dict) else {}
    return dossier.get(key) or warehouse.get(key)


def compose(ticker: str, dossier: dict[str, Any], *, reason: str) -> dict[str, Any]:
    """Create a cited deterministic dossier using the learned presentation profile."""
    profile = load_profile()
    identity = dossier.get("identity") or {}
    company = identity.get("company_name") or ticker
    # Use the exact addressable IDs exposed to the OpenAI generator. Optional
    # blocks shift their W numbers, so fixed IDs would create false citations.
    from cid.openai_dossier import evidence_rows

    rows = evidence_rows(dossier)
    ids = {str(row.get("kind")): str(row.get("id")) for row in rows}
    warehouse_id = ids.get("warehouse_evidence")
    section_sources = {
        "company_identity": (ids.get("identity"), identity),
        "business_model": (ids.get("business_profile"), dossier.get("business_profile")),
        "industry_economics": (ids.get("industry_intelligence") or ids.get("sector_framework"), dossier.get("industry_intelligence") or dossier.get("sector_framework")),
        "competitive_position": (ids.get("peer_comparison"), dossier.get("peer_comparison")),
        "management_governance": (ids.get("management"), dossier.get("management")),
        "financial_performance": (ids.get("financial_statements"), dossier.get("financial_statements")),
        "sector_kpis": (ids.get("sector_kpis"), dossier.get("sector_kpis")),
        "earnings_quality": (ids.get("financial_metrics"), dossier.get("financial_metrics")),
        "capital_allocation": (ids.get("financial_statements"), dossier.get("financial_statements")),
        "balance_sheet_risk": (ids.get("financial_statements"), dossier.get("financial_statements")),
        "valuation": (ids.get("valuation"), dossier.get("valuation")),
        "scenarios": (ids.get("scenario_analysis") or ids.get("valuation"), dossier.get("scenario_analysis") or (dossier.get("valuation") or {}).get("scenarios")),
        "catalysts": (ids.get("announcements"), dossier.get("announcements")),
        "risks": (warehouse_id, _block(dossier, "research_intelligence")),
        "causal_map": (ids.get("causal_intelligence"), dossier.get("causal_intelligence")),
        "market_implied_expectations": (ids.get("valuation"), dossier.get("valuation")),
        "thesis_change_conditions": (warehouse_id, _block(dossier, "research_intelligence")),
        "monitoring_dashboard": (warehouse_id, dossier.get("evidence_timeline")),
        "evidence_gaps": (ids.get("evidence_completion") or ids.get("identity"), dossier.get("evidence_completion") or dossier.get("missing_evidence")),
        "sources_provenance": (warehouse_id, dossier.get("evidence_timeline") or dossier.get("warehouse_evidence")),
    }
    sections: dict[str, Any] = {}
    narrative_parts = [
        f"{company} is covered through AGI's institutional warehouse under ticker {ticker}.",
    ]
    for name in SECTIONS:
        eid, source = section_sources.get(name, (None, None))
        facts = _sentences(source, limit=max(1, round(float((profile.get("section_claims") or {}).get(name) or 2))))
        summary = " ".join(facts) if facts else f"AGI does not yet hold sufficient verified evidence for {name.replace('_', ' ')}."
        evidence_ids = [eid] if facts and eid else []
        sections[name] = {
            "summary": summary[:1800],
            "claims": facts[:10],
            "evidence_ids": evidence_ids,
            "confidence": 0.62 if facts else 0.2,
            "status": "SUPPORTED" if facts and eid else "DATA_REQUIRED",
            "missing_fields": [] if facts and eid else [name],
        }
        if facts and name != "evidence_gaps":
            narrative_parts.append(summary)
    narrative = " ".join(narrative_parts)[:7000]
    cited = list(dict.fromkeys(eid for section in sections.values() for eid in section["evidence_ids"]))
    now = _now()
    research = {
        "executive_summary": " ".join(narrative_parts[:4])[:2400],
        "long_company_narrative": narrative,
        "long_company_narrative_evidence_ids": cited,
        "long_company_narrative_confidence": 0.58,
        "sections": sections,
        "generated_at": now,
        "provider": "agi",
        "model": "deterministic_learned_dossier_composer",
        "generator_version": "cid-openai-v2",
        "composer_version": PROFILE_VERSION,
        "dossier_spec_version": DOSSIER_SPEC_VERSION,
        "evidence_count": len(cited),
        "policy": "learned_structure_grounded_fallback",
        "fallback_reason": reason,
        "quality_status": "not_equivalent_to_openai_model_reasoning",
        "learned_from_examples": int(profile.get("successful_examples") or 0),
        "learning_maturity": readiness().get("maturity"),
    }
    research["quality_audit"] = audit_research(research)
    updated = dict(dossier)
    updated["openai_research"] = research
    updated["dossier_generation"] = {
        "status": "complete_fallback",
        "generated_at": now,
        "generator_version": "cid-openai-v2",
        "model": research["model"],
    }
    updated.update(compute_coverage(updated))
    stored = get_cid_store().put(updated)
    persistence = save_version(stored)
    return {
        "ok": bool(persistence.get("persisted")),
        "ticker": ticker,
        "research": research,
        "persistence": persistence,
        "dossier": stored,
        "fallback": True,
    }
