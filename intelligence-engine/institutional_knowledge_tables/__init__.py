"""AGIB V1.5 — Institutional Knowledge Tables (IKT).

Versioned structured facts per company. Documents are evidence; these
tables are the memory. Never fabricate values — absent facts stay
NULL / "missing", never inferred.
"""

from institutional_knowledge_tables.schema import TABLE_DEFS, table_fields, valid_table
from institutional_knowledge_tables.store import (
    company_record,
    delete_company,
    get_field_history,
    get_table,
    list_companies,
    upsert_fact,
)

__all__ = [
    "TABLE_DEFS",
    "company_record",
    "delete_company",
    "get_field_history",
    "get_table",
    "list_companies",
    "table_fields",
    "upsert_fact",
    "valid_table",
]
