"""Exam factory — builds ACS exam banks from topic × company matrices."""

from __future__ import annotations

from academy.certification.benchmark_suite.companies import BENCHMARK_COMPANIES
from academy.certification.schema import ExamSpec


def rotate_companies(n: int) -> list[dict]:
    firms = BENCHMARK_COMPANIES
    return [firms[i % len(firms)] for i in range(n)]


def build_topic_exams(
    *,
    analyst: str,
    level: int,
    topics: list[str],
    target: int,
    question_tmpl: str,
    must_tokens: dict[str, list[str]] | None = None,
    prefix: str | None = None,
) -> list[ExamSpec]:
    """Generate up to `target` exams by cycling topics across benchmark companies."""
    prefix = prefix or f"acs_{analyst[:3]}"
    must_tokens = must_tokens or {}
    out: list[ExamSpec] = []
    companies = rotate_companies(max(target, len(topics)))
    i = 0
    while len(out) < target:
        topic = topics[i % len(topics)]
        co = companies[i % len(companies)]
        tokens = list(must_tokens.get(topic) or topic.lower().split()[:3])
        # ensure company token for application-style prompts
        tokens.append(co["name"].split()[0].lower())
        q = question_tmpl.format(topic=topic, company=co["name"], ticker=co["ticker"])
        out.append(
            ExamSpec(
                exam_id=f"{prefix}_l{level}_{i+1:03d}",
                level=level,
                analyst=analyst,
                question=q,
                company=co["name"],
                ticker=co["ticker"],
                topic=topic,
                must_include=tokens[:6],
                tags=[analyst, topic.lower().replace(" ", "_")],
            )
        )
        i += 1
    return out


def build_concept_exams(concepts: list[str], *, level: int = 1) -> list[ExamSpec]:
    out = []
    for i, c in enumerate(concepts):
        out.append(
            ExamSpec(
                exam_id=f"acs_l1_{i+1:03d}_{c.lower().replace(' ', '_')[:24]}",
                level=level,
                analyst="general",
                question=f"Explain {c}: definition, purpose, why it matters, evidence required, when to use, when NOT to use, limitations, related concepts, examples and counter examples.",
                topic=c,
                must_include=[c.lower(), "definition", "when", "limitation", "example"],
                tags=["concept_recall", c.lower().replace(" ", "_")],
            )
        )
    return out
