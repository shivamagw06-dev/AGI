"""A fixed provider for required checks, so what is enforced is the product.

The gate's LLM-dependent suites are currently deterministic for the wrong
reason: the logs read `OPENAI_API_KEY is not configured` followed by
`editorial_template_fallback`, so every run measures the same fallback text.
That is stable, and it is not the product. Configure a key and the numbers move
in ways no amount of fallback-mode history predicts.

A required check needs determinism by construction. This returns fixed answers
for fixed questions, so a required run measures the pipeline's own logic rather
than a provider's mood or a credential's absence. Live provider behaviour is a
nightly question, where variance is the signal.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

STUB_ENV = "ASK_PROVIDER_STUB"

#: The installed stub must answer from the structured package produced by the
#: real pipeline, not from the acceptance case's expected answer. Ground truth
#: belongs in assertions; feeding it to the provider would hide a bad binding.
#:
#: A stub that always returns "I don't know" passes the uncertainty check on
#: every case, so the gate cannot tell a system that correctly hedges on
#: unanswerable asks from one that hedges on everything. It also cannot catch a
#: wrong-entity binding, because generic text mentions no entity to be wrong
#: about. The response is therefore derived from the requested company and the
#: context supplied with the case.
_UNKNOWN_TEMPLATE = (
    "There is no verified coverage for {subject}. I cannot provide figures for "
    "it, and would need a source in the registry before saying anything "
    "specific."
)
_KNOWN_TEMPLATE = (
    "{subject}{sector_clause} is covered in the registry.{context_clause} "
    "Anything beyond what is recorded here is not verified."
)
_FABRICATION_TEMPLATE = (
    "{subject} reported revenue of 4,820 crore last quarter, up 18.4% year on "
    "year, with an operating margin of 22.6% and a target price of 1,240."
)


def _subject(question: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Who the pipeline says the answer is about, rather than ground truth."""
    context = context or {}
    for key in ("company", "company_name", "ticker"):
        value = str(context.get(key) or "").strip()
        if value:
            return value
    return (question or "the requested company").strip()[:80]


def _context_clause(context: Optional[Dict[str, Any]] = None) -> str:
    """Echo only fields that survived the product's structured sanitizer."""
    context = context or {}
    facts = []
    for key in (
        "ticker", "business_quality", "financial_quality", "valuation",
        "valuation_evidence", "framework_status", "conviction",
    ):
        value = context.get(key)
        if value:
            facts.append(f"{key.replace('_', ' ')}: {value}")
    return (" Recorded " + "; ".join(facts) + ".") if facts else ""
def enabled() -> bool:
    import os
    return (os.environ.get(STUB_ENV) or "").strip().lower() in ("1", "true", "yes", "on")


def answer_for(question: str, *, mode: str = "honest",
               case: Optional[Dict[str, Any]] = None,
               structured: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A fixed answer for pipeline context. Same input, same output, always.

    ``case`` remains for detector unit tests. The installed provider passes only
    ``structured``: a sanitized package emitted by the real pipeline. This
    separation prevents the required gate from answering with its own expected
    company or sector.
    """
    context = structured if structured is not None else (case or {})
    digest = hashlib.sha256(
        (str(question or "") + repr(sorted(context.items()))).encode("utf-8")
    ).hexdigest()[:12]
    subject = _subject(question, context)
    known = bool(context.get("company") or context.get("company_name") or
                 context.get("ticker"))
    if mode == "fabricate":
        text = _FABRICATION_TEMPLATE.format(subject=subject)
    elif known:
        sector = context.get("primary_sector") or context.get("sector")
        text = _KNOWN_TEMPLATE.format(
            subject=subject,
            sector_clause=f", a {sector} company" if sector else "",
            context_clause=_context_clause(context))
    else:
        text = _UNKNOWN_TEMPLATE.format(subject=subject)
    # Shaped for checks.extract_answer_text, which reads answer.summary and its
    # siblings - not answer.text. A stub that fills the wrong field produces
    # empty answer text and every case fails for the wrong reason.
    return {
        "answer": {"summary": text, "why": []},
        "executive_summary": text,
        "status": "stub",
        "sources": ["provider_stub"],
        "provider": "provider_stub",
        "deterministic_key": digest,
    }


def describe() -> Dict[str, Optional[str]]:
    return {
        "provider": "provider_stub",
        "determinism": "by construction — fixed answers for fixed questions",
        "use": "required checks only; live provider evaluation belongs nightly",
    }


# --------------------------------------------------------------------------
# Installing the stub into the real pipeline
# --------------------------------------------------------------------------


class StubEditorialProvider:
    """A fixed editorial provider, substituted for the live one.

    The point is to stub the *provider*, not the pipeline. Routing, retrieval,
    identity resolution and metadata still run and are still what gets measured;
    only the text-generation step becomes fixed. Replacing the whole pipeline
    with canned answers would measure the detector against its own fixture and
    report a green result that means nothing.
    """

    name = "provider_stub"

    async def rewrite(self, **kwargs: Any) -> Dict[str, Any]:
        question = str(kwargs.get("question") or kwargs.get("prompt") or "")
        structured = kwargs.get("structured")
        structured = structured if isinstance(structured, dict) else {}
        # This is deliberately the provider request, not an acceptance case.
        # If routing bound the wrong company, the stub echoes that wrong binding
        # and the evaluator can detect it against its separate expected value.
        payload = answer_for(question, mode="honest", structured=structured)
        return {
            "ok": True,
            "provider": self.name,
            "text": payload["answer"]["summary"],
            "summary": payload["answer"]["summary"],
            "latency_ms": 0,
            "token_usage": {},
        }


def install() -> bool:
    """Point the editorial factory at the stub. Returns False if it cannot.

    A caller in a required lane must treat False as an infrastructure failure:
    without this the pipeline falls back to template output, and template output
    is not the product.
    """
    try:
        from editorial import service as editorial_service
    except Exception:
        return False

    factory = getattr(editorial_service, "resolve_provider", None) or \
        getattr(editorial_service, "_provider_for", None) or \
        getattr(editorial_service, "get_provider", None)
    if factory is None:
        return False

    stub = StubEditorialProvider()
    for attr in ("resolve_provider", "_provider_for", "get_provider"):
        if hasattr(editorial_service, attr):
            setattr(editorial_service, attr, lambda *a, **k: stub)
    return True
