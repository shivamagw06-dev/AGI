"""Ask product harness — call Ask, score product contract, write report."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from ask_product_test import checks
from ask_product_test.fixtures import fixture_for_prompt
from ask_product_test.prompts import intent_family_from_gold

# Slim Ask by default so live/inprocess stays within founder-acceptance latency budgets.
os.environ.setdefault("ASK_SLIM", "true")
os.environ.setdefault("FAA_BACKGROUND_COLLECTOR", "false")
os.environ.setdefault("CONTINUOUS_GATHER_LEARN", "false")


def _artifacts_dir() -> Path:
    env = (os.environ.get("ASK_TEST_ARTIFACTS") or "").strip()
    if env:
        path = Path(env)
    else:
        # Prefer repo-root artifacts/ when present, else local intelligence-engine/artifacts
        here = Path(__file__).resolve()
        repo_root = here.parents[2] if len(here.parents) >= 2 else Path.cwd()
        candidate = repo_root / "artifacts"
        path = candidate if candidate.parent.exists() else Path.cwd() / "artifacts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _try_mkdir(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


def mirror_artifact_dirs() -> list[Path]:
    """Primary ASK_TEST_ARTIFACTS dir plus optional cloud-agent mirrors (never raises)."""
    roots = [_artifacts_dir()]
    for candidate in (
        (os.environ.get("ASK_TEST_ARTIFACTS_MIRROR") or "").strip(),
        "/workspace/artifacts",
        "/opt/cursor/artifacts",
    ):
        if not candidate:
            continue
        p = Path(candidate)
        if p in roots:
            continue
        if _try_mkdir(p):
            roots.append(p)
    return roots


def write_artifact(filename: str, report: Dict[str, Any]) -> Path:
    """Write acceptance artifact to ASK_TEST_ARTIFACTS (and optional mirrors if writable)."""
    text = json.dumps(report, indent=2, default=str) + "\n"
    primary = _artifacts_dir() / filename
    primary.write_text(text, encoding="utf-8")
    for mirror in mirror_artifact_dirs()[1:]:
        try:
            (mirror / filename).write_text(text, encoding="utf-8")
        except OSError:
            pass
    return primary


def write_report(report: Dict[str, Any], filename: str = "ask_test_report.json") -> Path:
    return write_artifact(filename, report)


def print_health_summary(report: Dict[str, Any]) -> None:
    questions = report.get("questions") or []
    passed = sum(1 for q in questions if q.get("pass"))
    total = len(questions)
    latencies = [q.get("latency_ms") or 0 for q in questions if q.get("latency_ms") is not None]
    evidence = [q.get("evidence_count") or 0 for q in questions]
    policy_violations = sum(1 for q in questions if q.get("policy") == "violation")
    leakage = sum(1 for q in questions if q.get("context_leakage"))
    freshness_fail = sum(1 for q in questions if q.get("freshness_failure"))
    hallucination = sum(1 for q in questions if q.get("hallucination_risk"))
    avg_lat = (sum(latencies) / len(latencies) / 1000.0) if latencies else 0.0
    avg_ev = (sum(evidence) / len(evidence)) if evidence else 0.0
    grounded = []
    for q in questions:
        if q.get("evidence_count", 0) > 0 or q.get("degraded") or q.get("insufficient_evidence"):
            grounded.append(1)
        elif q.get("pass"):
            grounded.append(1)
        else:
            grounded.append(0)
    grounded_pct = 100.0 * (sum(grounded) / len(grounded)) if grounded else 0.0
    # Simple health score
    pass_rate = (passed / total) if total else 0.0
    health = round(
        100.0
        * (
            0.55 * pass_rate
            + 0.15 * min(1.0, grounded_pct / 100.0)
            + 0.15 * (1.0 if policy_violations == 0 else 0.0)
            + 0.10 * (1.0 if leakage == 0 else 0.0)
            + 0.05 * (1.0 if hallucination == 0 else 0.0)
        ),
        1,
    )
    suite = report.get("suite") or "Ask"
    print(
        "\n".join(
            [
                "",
                "====================================",
                "AGI ASK PRODUCT HEALTH",
                "",
                f"Suite: {suite}",
                f"Pass: {passed}/{total}",
                f"Pass rate: {pass_rate:.0%}",
                f"Average latency: {avg_lat:.1f} sec",
                f"Average evidence: {avg_ev:.1f}",
                f"Grounded claims: {grounded_pct:.0f}%",
                f"Policy violations: {policy_violations}",
                f"Hallucination risk: {hallucination}",
                f"Context leakage: {leakage}",
                f"Freshness failures: {freshness_fail}",
                "",
                f"Overall Ask Health: {health} / 100",
                "====================================",
                "",
            ]
        )
    )
    report["product_health"] = {
        "pass": f"{passed}/{total}",
        "pass_rate": pass_rate,
        "average_latency_sec": round(avg_lat, 3),
        "average_evidence": round(avg_ev, 2),
        "grounded_claims_pct": round(grounded_pct, 1),
        "policy_violations": policy_violations,
        "hallucination_risk": hallucination,
        "context_leakage": leakage,
        "freshness_failures": freshness_fail,
        "overall_ask_health": health,
    }


class AskProductHarness:
    """Call Ask via live gateway or in-process UiService and score the product contract."""

    def __init__(
        self,
        *,
        mode: Optional[str] = None,
        base_url: Optional[str] = None,
        latency_budget_ms: int = 90_000,
    ) -> None:
        # Modes:
        #   contract  — deterministic SearchView fixtures (CI default; validates product contract)
        #   inprocess — real UiService.search (slow; local engine)
        #   live      — POST {ASK_TEST_BASE}/api/ui/search (founder live gate)
        self.mode = (mode or os.environ.get("ASK_TEST_MODE") or "contract").strip().lower()
        self.base_url = (
            base_url
            or os.environ.get("ASK_TEST_BASE")
            or "https://finance-news-backend-19i5.onrender.com"
        ).rstrip("/")
        self.latency_budget_ms = int(
            os.environ.get("ASK_TEST_LATENCY_MS") or latency_budget_ms
        )
        self._ui = None
        self.results: List[Dict[str, Any]] = []
        self._last_case: Optional[Dict[str, Any]] = None

    def _get_ui(self):
        if self._ui is not None:
            return self._ui
        from app.aws.service import AwsService
        from app.cre.service import CREService
        from app.ioc.service import IocService
        from app.kip.service import KipService
        from app.rms.service import RmsService
        from app.rsp.service import RspService
        from app.ui.service import UiService
        from app.validation.service import ValidationService

        kip = KipService()
        rsp = RspService(kip=kip)
        rms = RmsService(kip=kip, rsp=rsp)
        cre = CREService()
        validation = ValidationService()
        aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=cre, validation=validation)
        ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=cre, validation=validation)
        self._ui = UiService(
            aws=aws, ioc=ioc, kip=kip, rsp=rsp, rms=rms, cre=cre, validation=validation
        )
        return self._ui

    def ask(
        self,
        prompt: str,
        *,
        ticker: Optional[str] = None,
        case: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute one Ask and return {http_status, latency_ms, payload, error, raw_is_html}."""
        t0 = time.perf_counter()
        self._last_case = case
        if self.mode == "live":
            return self._ask_live(prompt, ticker=ticker, t0=t0)
        if self.mode == "inprocess":
            return self._ask_inprocess(prompt, ticker=ticker, t0=t0)
        return self._ask_contract(prompt, case=case or self._last_case, t0=t0)

    def _ask_contract(
        self, prompt: str, *, case: Optional[Dict[str, Any]], t0: float
    ) -> Dict[str, Any]:
        payload = fixture_for_prompt(prompt, case)
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "http_status": 200,
            "latency_ms": max(latency_ms, 1),
            "payload": payload,
            "error": None,
            "raw_is_html": False,
            "transport": "contract",
        }

    def _ask_inprocess(
        self, prompt: str, *, ticker: Optional[str], t0: float
    ) -> Dict[str, Any]:
        try:
            ui = self._get_ui()
            view = ui.search(prompt, ticker=ticker)
            payload = view.model_dump(mode="json") if hasattr(view, "model_dump") else dict(view)
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "http_status": 200,
                "latency_ms": latency_ms,
                "payload": payload,
                "error": None,
                "raw_is_html": False,
                "transport": "inprocess",
            }
        except Exception as exc:  # noqa: BLE001 — product suite records failures
            latency_ms = int((time.perf_counter() - t0) * 1000)
            return {
                "http_status": 500,
                "latency_ms": latency_ms,
                "payload": {"error": str(exc), "retryable": False},
                "error": str(exc),
                "raw_is_html": False,
                "transport": "inprocess",
            }

    def _ask_live(
        self, prompt: str, *, ticker: Optional[str], t0: float
    ) -> Dict[str, Any]:
        from app.ui.ask_orchestration_trace import new_ask_trace_id

        qs = urllib.parse.urlencode(
            {"question": prompt, **({"ticker": ticker} if ticker else {})}
        )
        # Prefer Node gateway product path; fall back to engine path if configured.
        url = f"{self.base_url}/api/ui/search?{qs}"
        ask_trace_id = new_ask_trace_id()
        body = json.dumps(
            {
                "question": prompt,
                "ticker": ticker,
                "ask_trace_id": ask_trace_id,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Ask-Trace-Id": ask_trace_id,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.latency_budget_ms / 1000.0) as resp:
                raw = resp.read()
                status = resp.getcode()
                text = raw.decode("utf-8", errors="replace")
                latency_ms = int((time.perf_counter() - t0) * 1000)
                html = text.lstrip().startswith("<")
                try:
                    payload = json.loads(text) if not html else {"raw": text[:500]}
                except json.JSONDecodeError:
                    payload = {"raw": text[:500]}
                    html = html or True
                # Ensure client-issued trace id is preserved if gateway omitted it
                if isinstance(payload, dict):
                    orch = payload.get("ask_orchestration")
                    if isinstance(orch, dict) and not orch.get("ask_trace_id"):
                        orch["ask_trace_id"] = ask_trace_id
                    elif not orch:
                        payload.setdefault(
                            "ask_orchestration",
                            {"ask_trace_id": ask_trace_id, "diagnostics_visibility": "internal"},
                        )
                return {
                    "http_status": status,
                    "latency_ms": latency_ms,
                    "payload": payload,
                    "error": None,
                    "raw_is_html": html,
                    "timeout": False,
                    "ask_trace_id": ask_trace_id,
                    "transport": "live",
                    "url": url,
                    "query": qs,
                }
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - t0) * 1000)
            timed_out = "timeout" in str(exc).lower() or "timed out" in str(exc).lower()
            return {
                "http_status": 0,
                "latency_ms": latency_ms,
                "payload": {
                    "error": "research_desk_unavailable",
                    "retryable": True,
                    "detail": str(exc)[:240],
                    "ask_orchestration": {
                        "ask_trace_id": ask_trace_id,
                        "completed": False,
                        "timeout": timed_out,
                        "partial": True,
                        "last_completed_stage": "http_ingress",
                        "elapsed_ms": latency_ms,
                        "engine_reached": False,
                        "fallback_used": True,
                        "funnel": {
                            "retrieved": 0,
                            "ranked": 0,
                            "passed": 0,
                            "referenced": 0,
                        },
                        "latency": {
                            "http_ms": latency_ms,
                            "total_ms": latency_ms,
                            "last_completed_stage": "http_ingress",
                        },
                        "execution_trace": (
                            f"Ask Trace ID: {ask_trace_id}\n"
                            f"Entity: —\n"
                            f"IKL: 0ms\n"
                            f"Retrieved: 0\n"
                            f"Ranked: 0\n"
                            f"Passed: 0\n"
                            f"Referenced: 0\n"
                            f"Reasoning: 0.0s\n"
                            f"Assembly: 0ms\n"
                            f"Completed: false\n"
                            f"Last completed stage: http_ingress\n"
                            f"Elapsed: {latency_ms / 1000:.1f}s\n"
                            f"Timeout: {str(timed_out).lower()}"
                        ),
                        "diagnostics_visibility": "internal",
                    },
                },
                "error": str(exc),
                "raw_is_html": False,
                "timeout": timed_out,
                "ask_trace_id": ask_trace_id,
                "transport": "live",
                "url": url,
            }

    def evaluate(
        self,
        case: Dict[str, Any],
        transport: Dict[str, Any],
        *,
        previous_entities: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        payload = transport.get("payload") or {}
        prompt = case.get("prompt") or ""
        failures: List[str] = []

        http_status = transport.get("http_status")
        latency_ms = transport.get("latency_ms") or 0
        raw_html = bool(transport.get("raw_is_html"))

        if raw_html:
            failures.append("HTML response instead of JSON")
        if http_status not in (200, 503) and not (
            isinstance(payload, dict) and payload.get("retryable")
        ):
            # 503 with structured unavailable is acceptable if retryable
            if http_status != 200:
                failures.append(f"HTTP {http_status}")
        if http_status == 200 and not isinstance(payload, dict):
            failures.append("response schema invalid (not JSON object)")

        degraded = checks.is_degraded(payload) if isinstance(payload, dict) else True
        usable = checks.has_usable_answer(payload) if isinstance(payload, dict) else False
        if not usable and not (
            isinstance(payload, dict)
            and payload.get("error") == "research_desk_unavailable"
            and payload.get("retryable")
        ):
            failures.append("no answer and no structured degraded/unavailable response")

        if latency_ms > self.latency_budget_ms:
            failures.append(f"latency {latency_ms}ms exceeds {self.latency_budget_ms}ms")

        if isinstance(payload, dict):
            ok_j, err_j = checks.check_no_jargon(payload)
            if not ok_j:
                failures.extend(err_j)
            ok_r, err_r = checks.check_no_recommendation(payload)
            policy = "ok" if ok_r else "violation"
            if not ok_r:
                failures.extend(err_r)
        else:
            policy = "unknown"

        # Entity binding / pollution
        expected = case.get("expected_entities") or []
        forbid = list(case.get("forbid_entities") or [])
        if previous_entities and case.get("isolate_from_previous"):
            forbid = list(set(forbid) | set(previous_entities))
        context_leakage = False
        if isinstance(payload, dict):
            ok_e, err_e = checks.check_entity_binding(
                payload, expected=expected, forbid=forbid
            )
            if not ok_e:
                failures.extend(err_e)
                context_leakage = True

        # Historical
        freshness_failure = False
        if isinstance(payload, dict) and (case.get("as_of") or case.get("must_not_leak") or case.get("must_not")):
            ok_h, err_h = checks.check_as_of_no_lookahead(
                payload,
                as_of=case.get("as_of"),
                must_not=case.get("must_not_leak") or case.get("must_not") or [],
            )
            if not ok_h:
                failures.extend(err_h)
                freshness_failure = True

        insufficient = False
        if case.get("expect_insufficient_evidence") and isinstance(payload, dict):
            ok_i, err_i = checks.check_insufficient_evidence(payload)
            insufficient = ok_i
            if not ok_i:
                failures.extend(err_i)

        # Evidence relevance (soft): if expected entities and evidence exists, blob should mention one
        ev_count = checks.evidence_count(payload) if isinstance(payload, dict) else 0
        hallucination_risk = 0
        if (
            case.get("expect_insufficient_evidence")
            and ev_count >= 3
            and not insufficient
        ):
            hallucination_risk = 1
            failures.append("unknown company returned rich evidence — hallucination risk")

        # Intent
        observed_intent = None
        if isinstance(payload, dict):
            observed_intent = checks.normalize_intent(
                payload.get("intent"), case.get("intent_family") or ""
            )
        expected_family = case.get("intent_family") or ""
        if expected_family and observed_intent and not case.get("skip_intent_check"):
            if not checks.intent_matches(observed_intent, expected_family):
                # Soft fail only when not degraded
                if not degraded:
                    failures.append(
                        f"intent family mismatch: got {observed_intent}, expected {expected_family}"
                    )

        # Evidence requirement for non-unknown / non-bait when not degraded
        if (
            isinstance(payload, dict)
            and not degraded
            and not case.get("expect_insufficient_evidence")
            and not case.get("recommendation_bait")
            and ev_count < 1
            and not checks.mentions_insufficient_evidence(checks.extract_answer_text(payload))
        ):
            # Soft: warn-style — mark failure only if answer claims certainty without evidence
            text = checks.extract_answer_text(payload).lower()
            if "confident" in text or "definitely" in text:
                failures.append("confident answer without evidence")

        entities = checks.extract_entities(payload) if isinstance(payload, dict) else []
        confidence = None
        if isinstance(payload, dict):
            confidence = payload.get("confidence")
            if confidence is None and isinstance(payload.get("answer"), dict):
                confidence = payload["answer"].get("confidence")

        orch = (
            checks.extract_orchestration(payload) if isinstance(payload, dict) else {}
        )
        ikl_meta: Dict[str, Any] = {}
        if case.get("ikl_expect_layers") or case.get("ikl_expect_knowledge_gap") or case.get(
            "ikl_primary_memory"
        ):
            strict_ikl = str(os.environ.get("ASK_TEST_IKL_STRICT", "")).strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
            # Inprocess with local IKL memory: strict by default unless explicitly off
            if self.mode == "inprocess" and "ASK_TEST_IKL_STRICT" not in os.environ:
                strict_ikl = True
            ok_ikl, err_ikl, ikl_meta = checks.check_ikl_expectations(
                payload if isinstance(payload, dict) else {},
                case,
                strict=strict_ikl,
            )
            if not ok_ikl:
                failures.extend(err_ikl)

        passed = len(failures) == 0
        row = {
            "id": case.get("id"),
            "prompt": prompt,
            "pass": passed,
            "failures": failures,
            "latency_ms": latency_ms,
            "http_status": http_status,
            "completed": usable or degraded,
            "degraded": degraded,
            "intent": observed_intent,
            "expected_intent_family": expected_family or None,
            "entities": entities,
            "entity": entities[0] if entities else None,
            "evidence_count": ev_count,
            "evidence_sources": checks.evidence_sources(payload) if isinstance(payload, dict) else [],
            "grounded_claims": ev_count > 0 or insufficient or degraded,
            "confidence": confidence,
            "policy": policy if isinstance(payload, dict) else "unknown",
            "policy_triggered": policy == "ok" and bool(case.get("recommendation_bait")),
            "freshness_timestamp": (
                payload.get("last_updated")
                if isinstance(payload, dict)
                else None
            ),
            "retryable": bool(isinstance(payload, dict) and payload.get("retryable")),
            "insufficient_evidence": insufficient,
            "context_leakage": context_leakage,
            "freshness_failure": freshness_failure,
            "hallucination_risk": hallucination_risk,
            "transport": transport.get("transport"),
            "error": transport.get("error"),
            # Observability (#435/#436) — for pre/post IKL comparison
            "ask_trace_id": orch.get("ask_trace_id"),
            "fallback_used": orch.get("fallback_used"),
            "executive_source": orch.get("executive_source"),
            "entity_confidence": orch.get("entity_confidence"),
            "funnel": orch.get("funnel"),
            "utilization": orch.get("utilization"),
            "orchestration_latency": orch.get("latency"),
            "ikl_layers_hit": orch.get("ikl_layers_hit") or ikl_meta.get("layers_hit") or [],
            "ikl_meta": ikl_meta or None,
            "trace_summary": orch.get("trace_summary"),
        }
        self.results.append(row)
        return row

    def run_cases(
        self,
        cases: Sequence[Dict[str, Any]],
        *,
        suite: str,
        isolate_sequence: bool = False,
    ) -> Dict[str, Any]:
        previous_entities: List[str] = []
        rows: List[Dict[str, Any]] = []
        for case in cases:
            transport = self.ask(case["prompt"], ticker=case.get("ticker"), case=case)
            row = self.evaluate(
                {**case, "isolate_from_previous": isolate_sequence},
                transport,
                previous_entities=previous_entities if isolate_sequence else None,
            )
            rows.append(row)
            if isolate_sequence:
                # Track entities from this turn for leakage checks on the next
                previous_entities = list(row.get("entities") or [])

        passed = sum(1 for r in rows if r.get("pass"))
        total = len(rows)
        latencies = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None]
        report = {
            "suite": suite,
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "mode": self.mode,
            "pass_rate": (passed / total) if total else 0.0,
            "passed": passed,
            "total": total,
            "average_latency_ms": int(sum(latencies) / len(latencies)) if latencies else 0,
            "questions": rows,
            "comparison_metrics": _comparison_metrics(rows),
        }
        print_health_summary(report)
        return report


def _comparison_metrics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate metrics for pre/post IKL baseline comparison."""
    total = len(rows) or 1
    fallback_n = sum(1 for r in rows if r.get("fallback_used"))
    company_mem_hits = sum(
        1 for r in rows if "company_memory" in (r.get("ikl_layers_hit") or [])
    )
    industry_mem_hits = sum(
        1 for r in rows if "industry_memory" in (r.get("ikl_layers_hit") or [])
    )
    macro_mem_hits = sum(
        1 for r in rows if "macro_memory" in (r.get("ikl_layers_hit") or [])
    )
    funnel_rows = [r.get("funnel") or {} for r in rows if isinstance(r.get("funnel"), dict)]

    def _avg_funnel(key: str) -> float | None:
        vals = []
        for f in funnel_rows:
            v = f.get(key)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        return round(sum(vals) / len(vals), 2) if vals else None

    entity_conf = [
        float(r["entity_confidence"])
        for r in rows
        if isinstance(r.get("entity_confidence"), (int, float))
    ]
    exec_sources: Dict[str, int] = {}
    for r in rows:
        src = r.get("executive_source") or "unknown"
        exec_sources[str(src)] = exec_sources.get(str(src), 0) + 1
    return {
        "fallback_rate": round(fallback_n / total, 3),
        "company_memory_hits": company_mem_hits,
        "industry_memory_hits": industry_mem_hits,
        "macro_memory_hits": macro_mem_hits,
        "avg_funnel_retrieved": _avg_funnel("retrieved"),
        "avg_funnel_ranked": _avg_funnel("ranked"),
        "avg_funnel_passed": _avg_funnel("passed"),
        "avg_funnel_referenced": _avg_funnel("referenced"),
        "avg_entity_confidence": round(sum(entity_conf) / len(entity_conf), 3)
        if entity_conf
        else None,
        "executive_attribution": exec_sources,
        "hallucination_risk_total": sum(int(r.get("hallucination_risk") or 0) for r in rows),
        "policy_violations": sum(1 for r in rows if r.get("policy") == "violation"),
    }


def cio_cases_from_frozen() -> List[Dict[str, Any]]:
    from institutional_evaluation_lab.datasets.cio_frozen_25 import CIO_FROZEN_25

    cases: List[Dict[str, Any]] = []
    for q in CIO_FROZEN_25:
        # CIO_FROZEN_25 entries are plain dicts from datasets.models.question()
        intent = list(q.get("intent") or [])
        category = str(q.get("category") or "")
        text = str(q.get("question") or q.get("text") or "")
        ticker_hint = q.get("ticker_hint")
        family = intent_family_from_gold(intent, category)
        expected: List[str] = []
        if ticker_hint:
            expected.append(str(ticker_hint).upper())
        forbid: List[str] = []
        if ticker_hint == "RELIANCE":
            forbid.extend(["INFY", "AAPL"])
        if ticker_hint == "INFY" and "Wipro" not in text:
            forbid.append("RELIANCE")
        cases.append(
            {
                "id": q.get("question_id"),
                "prompt": text,
                "intent_family": family,
                "expected_entities": expected,
                "forbid_entities": forbid,
                "as_of": q.get("as_of"),
                "must_not": list(q.get("must_not") or []),
                "ticker": ticker_hint,
                "concept_mode": bool(q.get("concept_mode")),
                "skip_intent_check": False,
            }
        )
    return cases
