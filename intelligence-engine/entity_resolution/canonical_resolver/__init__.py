"""Canonical resolver — IKG authoritative, registry fallback, never guess."""

from __future__ import annotations

import time
from copy import deepcopy
from typing import Any

from entity_resolution.ambiguity_engine import evaluate_ambiguity
from entity_resolution.cache import cache_get, cache_set, make_key
from entity_resolution.confidence import score_match
from entity_resolution.context import apply_context, prior_from_payload
from entity_resolution.entity_registry import get_entity, lookup_alias
from entity_resolution.entity_registry.seed import AMBIGUOUS_STEMS
from entity_resolution.parser import parse_mentions
from entity_resolution.relationships import enrich_relationships
from entity_resolution.schema import ERE_VERSION, SPRINT


def _ikg_lookup(token: str) -> dict[str, Any] | None:
    try:
        from knowledge_graph.entity_resolution.resolve import resolve_entity

        hit = resolve_entity(token)
    except Exception:
        return None
    if not hit:
        return None
    node = hit.get("node") or {}
    matched_on = str(hit.get("matched_on") or "")
    token_l = (token or "").strip().lower()
    matched_l = matched_on.strip().lower()

    # Never accept IKG matches that collapse to an ambiguous stem while the
    # user typed a more specific phrase (IKG norm strips Ltd/Limited → "HDFC").
    for stem in AMBIGUOUS_STEMS:
        if matched_l == stem and token_l != stem and stem in token_l:
            return None
        if matched_l == stem and token_l != stem:
            return None

    # Map IKG node → canonical institutional entity
    ntype = str(node.get("type") or "company").lower()
    type_map = {
        "company": "Company",
        "sector": "Sector",
        "industry": "Industry",
        "index": "Broad Index",
        "etf": "ETF",
        "commodity": "Commodity",
        "currency": "Currency",
        "country": "Country",
        "person": "Person",
        "event": "Event",
        "theme": "Theme",
        "inflation": "Macro Variable",
        "interest_rate": "Macro Variable",
        "central_bank": "Institution",
        "government": "Government",
        "regulator": "Institution",
    }
    kg_id = hit.get("canonical_id") or node.get("id")
    # Prefer registry enrichment when ticker or kg id known
    ticker = node.get("ticker")
    reg = []
    if ticker:
        reg = lookup_alias(str(ticker))
    if not reg and kg_id:
        # Match registry rows linked to this graph node
        from entity_resolution.entity_registry import all_entities

        reg = [e for e in all_entities() if e.get("knowledge_graph_id") == kg_id]
    if not reg and token_l:
        reg = lookup_alias(token_l)
        # Only accept if same kg link or same ticker
        reg = [
            e
            for e in reg
            if e.get("knowledge_graph_id") == kg_id or (ticker and e.get("ticker") == ticker)
        ]
    if reg:
        ent = deepcopy(reg[0])
        ent["knowledge_graph_id"] = kg_id
        return {
            "entity": ent,
            "matched_on": "ikg+registry",
            "source": "ikg",
        }
    ent = {
        "id": f"IKG_{kg_id}",
        "canonical_name": node.get("label") or node.get("id"),
        "entity_type": type_map.get(ntype, "Company"),
        "ticker": ticker,
        "exchange": "NSE" if ticker and ntype == "company" else None,
        "country": node.get("country") or ("India" if ntype == "company" else None),
        "sector": node.get("sector"),
        "industry": node.get("industry"),
        "aliases": list(node.get("aliases") or []),
        "status": "active",
        "parent": None,
        "children": [],
        "knowledge_graph_id": kg_id,
        "peers": [],
        "indexes": [],
    }
    return {"entity": ent, "matched_on": matched_on or "ikg_id", "source": "ikg"}


def _registry_candidates(alias: str) -> list[dict[str, Any]]:
    out = []
    for ent in lookup_alias(alias):
        conf = score_match(alias=alias, entity=ent, matched_on="registry_alias", source="registry")
        out.append({"entity": ent, "confidence": conf, "matched_on": "registry_alias", "source": "registry"})
    return out


def _canonical_object(entity: dict[str, Any], confidence: float) -> dict[str, Any]:
    return {
        "id": entity.get("id"),
        "canonical_name": entity.get("canonical_name"),
        "entity_type": entity.get("entity_type"),
        "ticker": entity.get("ticker"),
        "exchange": entity.get("exchange"),
        "country": entity.get("country"),
        "sector": entity.get("sector"),
        "industry": entity.get("industry"),
        "aliases": list(entity.get("aliases") or []),
        "status": entity.get("status") or "active",
        "confidence": confidence,
        "parent": entity.get("parent"),
        "children": list(entity.get("children") or []),
        "knowledge_graph_id": entity.get("knowledge_graph_id"),
    }


def _normalize_query_token(question: str) -> str:
    q = (question or "").strip()
    # Ticker venue prefixes/suffixes
    if q.upper().startswith("NSE:") or q.upper().startswith("BSE:"):
        q = q.split(":", 1)[-1]
    if q.upper().endswith(".NS") or q.upper().endswith(".BO"):
        q = q[:-3]
    return q.strip()


def resolve_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    body = payload or {}
    prior = prior_from_payload(body)
    raw_q = (question or "").strip()
    q = _normalize_query_token(raw_q)
    cache_key = make_key(raw_q, prior.get("prior_entity_id"))
    if body.get("use_cache", True):
        cached = cache_get(cache_key)
        if cached:
            out = deepcopy(cached)
            out["cache_hit"] = True
            out["execution_time_ms"] = round((time.perf_counter() - started) * 1000, 3)
            return out

    mentions = parse_mentions(q)
    # Exact whole-string alias fallback (helps short tokens like AI / IT / Oil)
    if not mentions:
        from entity_resolution.alias_dictionary import normalize_alias

        exact = normalize_alias(q)
        for ent in lookup_alias(exact):
            mentions.append(
                {
                    "text": exact,
                    "alias": exact,
                    "start": 0,
                    "end": len(exact),
                    "registry_hint": ent["id"],
                    "ambiguous_stem": None,
                }
            )
    detected = [m.get("alias") for m in mentions]

    # Ambiguous stem present without longer disambiguator?
    ambiguous_stem = None
    for m in mentions:
        stem = m.get("ambiguous_stem")
        if not stem:
            continue
        # If another mention is a longer form of the same family, ignore stem
        longer = [
            x
            for x in mentions
            if x is not m
            and stem in str(x.get("alias") or "")
            and str(x.get("alias") or "") != stem
            and not str(x.get("registry_hint") or "").startswith("AMBIG::")
        ]
        if longer:
            continue
        ambiguous_stem = stem
        break

    candidates: list[dict[str, Any]] = []
    if not ambiguous_stem:
        for m in mentions:
            alias = str(m.get("alias") or "")
            hint = str(m.get("registry_hint") or "")
            if hint.startswith("AMBIG::"):
                continue
            reg_hits = _registry_candidates(alias)
            for c in reg_hits:
                if any((x.get("entity") or {}).get("id") == (c.get("entity") or {}).get("id") for x in candidates):
                    for i, x in enumerate(candidates):
                        if (x.get("entity") or {}).get("id") == (c.get("entity") or {}).get("id"):
                            if float(c["confidence"]) > float(x["confidence"]):
                                candidates[i] = {**c, "alias": alias}
                            break
                else:
                    candidates.append({**c, "alias": alias})

            # IKG authoritative enrichment — skip when registry already has an
            # exact alias hit unless IKG points at the same linked node.
            ikg = _ikg_lookup(alias)
            if ikg:
                ent = ikg["entity"]
                kg_id = ent.get("knowledge_graph_id")
                registry_exact = bool(reg_hits)
                same_link = any(
                    (x.get("entity") or {}).get("knowledge_graph_id") == kg_id
                    or (x.get("entity") or {}).get("id") == ent.get("id")
                    for x in reg_hits
                )
                if registry_exact and not same_link and str(ikg.get("matched_on") or "") != "ikg+registry":
                    pass
                else:
                    conf = score_match(
                        alias=alias,
                        entity=ent,
                        matched_on=str(ikg.get("matched_on") or "ikg"),
                        source="ikg",
                    )
                    candidates.append(
                        {
                            "entity": ent,
                            "confidence": conf,
                            "matched_on": ikg.get("matched_on"),
                            "source": "ikg",
                            "alias": alias,
                        }
                    )

    # If ambiguous stem, seed candidates from the stem family for context ranking
    if ambiguous_stem:
        from entity_resolution.entity_registry import ambiguous_matches

        for ent in ambiguous_matches(ambiguous_stem):
            conf = score_match(
                alias=ambiguous_stem,
                entity=ent,
                matched_on="ambiguous_stem",
                source="registry",
            )
            candidates.append(
                {
                    "entity": ent,
                    "confidence": min(conf, 0.68),
                    "matched_on": "ambiguous_stem",
                    "source": "registry",
                    "alias": ambiguous_stem,
                }
            )

    # Deduplicate equivalent candidates (prefer registry ids; merge on kg id)
    def _is_registry(eid: str) -> bool:
        return any(
            str(eid).startswith(p)
            for p in (
                "COMP_",
                "SECTOR_",
                "IDX_",
                "CMD_",
                "THEME_",
                "FX_",
                "MACRO_",
                "PF_",
                "INST_",
                "EVT_",
                "PERSON_",
                "METRIC_",
            )
        )

    ranked = sorted(
        candidates,
        key=lambda x: (
            0 if _is_registry(str((x.get("entity") or {}).get("id") or "")) else 1,
            -float(x.get("confidence") or 0),
        ),
    )
    deduped: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for c in ranked:
        ent = c.get("entity") or {}
        key2 = f"{ent.get('entity_type')}::{str(ent.get('canonical_name') or '').lower()}"
        key3 = f"ticker::{str(ent.get('ticker') or '').upper()}" if ent.get("ticker") else ""
        key4 = f"kg::{ent.get('knowledge_graph_id')}" if ent.get("knowledge_graph_id") else ""
        # Soft name collapse for Banks/Banking style labels
        soft = str(ent.get("canonical_name") or "").lower().replace(" services", "").rstrip("s")
        key5 = f"{ent.get('entity_type')}::soft::{soft}"
        if (
            key2 in seen_keys
            or (key3 and key3 in seen_keys)
            or (key4 and key4 in seen_keys)
            or key5 in seen_keys
        ):
            continue
        seen_keys.add(key2)
        seen_keys.add(key5)
        if key3:
            seen_keys.add(key3)
        if key4:
            seen_keys.add(key4)
        deduped.append(c)
    candidates = deduped

    candidates = apply_context(
        candidates,
        prior_entity_id=prior.get("prior_entity_id"),
        prior_sector=prior.get("prior_sector"),
    )

    best = candidates[0] if candidates else None
    best_conf = float((best or {}).get("confidence") or 0.0)
    second_conf = float(candidates[1]["confidence"]) if len(candidates) > 1 else 0.0
    margin = best_conf - second_conf

    # Context can uniquely resolve an otherwise ambiguous stem (never blind guess)
    context_resolved = bool(
        ambiguous_stem
        and prior.get("prior_entity_id")
        and best
        and float(best.get("context_boost") or 0) >= 0.1
        and best_conf >= 0.85
        and margin >= 0.08
    )

    amb = evaluate_ambiguity(
        stem=None if context_resolved else ambiguous_stem,
        candidates=candidates if not context_resolved else [best] if best else [],
        best_confidence=best_conf if (not ambiguous_stem or context_resolved) else min(best_conf, 0.68),
    )

    needs = bool(amb.get("needs_clarification")) and not context_resolved
    if context_resolved:
        needs = False

    entity_obj = None
    relationships = {}
    if not needs and best:
        ent = best["entity"]
        entity_obj = _canonical_object(ent, float(best["confidence"]))
        relationships = enrich_relationships(ent)

    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    conf_out = float(best_conf if not needs else amb.get("confidence") or best_conf)
    out = {
        "ok": True,
        "ere_version": ERE_VERSION,
        "sprint": SPRINT,
        "question": q,
        "detected_entities": detected,
        "mentions": mentions,
        "entity": (entity_obj or {}).get("canonical_name") if entity_obj else None,
        "entity_type": (entity_obj or {}).get("entity_type") if entity_obj else "Unknown",
        "ticker": (entity_obj or {}).get("ticker") if entity_obj else None,
        "exchange": (entity_obj or {}).get("exchange") if entity_obj else None,
        "country": (entity_obj or {}).get("country") if entity_obj else None,
        "sector": (entity_obj or {}).get("sector") if entity_obj else None,
        "industry": (entity_obj or {}).get("industry") if entity_obj else None,
        "confidence": conf_out,
        "confidence_pct": round(conf_out * 100, 1),
        "needs_clarification": needs,
        "possible_matches": [] if not needs else (amb.get("possible_matches") or []),
        "canonical_entity": entity_obj,
        "aliases": (entity_obj or {}).get("aliases") if entity_obj else [],
        "relationships": relationships,
        "knowledge_graph_id": (entity_obj or {}).get("knowledge_graph_id") if entity_obj else None,
        "knowledge_graph_linked": bool((entity_obj or {}).get("knowledge_graph_id")) if entity_obj else False,
        "clarification_status": "required" if needs else "clear",
        "execution_time_ms": elapsed_ms,
        "cache_hit": False,
        "source_of_truth": "ikg+registry",
        "never_guess": True,
        "research_blocked": needs,
        "routing_decision": (
            "Clarification required — no research begins."
            if needs
            else "Canonical entity resolved — pipeline may continue."
        ),
    }
    if body.get("use_cache", True) and not needs:
        cache_set(cache_key, out)
    return out


def resolve_token(token: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return resolve_question(token, payload)
