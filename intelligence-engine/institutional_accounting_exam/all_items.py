"""The full 30-item exam: Section A-E's 25 numbered questions + Section
F-J's 5 composite tasks (each composite task is worth 20 raw points,
same weight as a full 5-question section — see the brief's own
per-section "(20)" scoring)."""

from __future__ import annotations

from institutional_accounting_exam.schema import ExamItem
from institutional_accounting_exam.section_a_accounting import SECTION_A_ITEMS
from institutional_accounting_exam.section_be_scenarios import SECTION_BE_ITEMS
from institutional_accounting_exam.section_fj_composite import SECTION_FJ_ITEMS

ALL_EXAM_ITEMS: list[ExamItem] = [*SECTION_A_ITEMS, *SECTION_BE_ITEMS, *SECTION_FJ_ITEMS]


def items_by_section(section: str) -> list[ExamItem]:
    return [i for i in ALL_EXAM_ITEMS if i.section == section]
