"""AGI Institutional Accounting & Financial Analysis Exam (Level 1).

Difficulty target: CFA Level I + Investment Banking + Big Four.
Passing score: 90%.

Gate before Phase 3 (business strategy / valuation). Every answer in
this exam is produced by actually CALLING the Phase 1
(``financial_foundations``) and Phase 2 (``financial_statement_intelligence``)
engines — nothing here is a canned or hand-typed answer. If the engines
get something wrong, this exam is designed to catch it, not paper over
it with a scripted "correct" response.
"""

from __future__ import annotations

from institutional_accounting_exam.schema import EXAM_VERSION, MODULE_CODE, PROGRAMME

__all__ = ["EXAM_VERSION", "MODULE_CODE", "PROGRAMME"]
