"""Value coercion and formatting shared by the store, importer and validator.

Imported data arrives from collectors, Capital IQ exports and Excel paste
buffers. Everything is normalised once, here, so a column always holds one
type no matter where the value came from.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date, datetime, timezone
from typing import Any, Optional

from institutional_warehouse.schema import (
    BOOL,
    CURRENCY,
    DATE,
    DATETIME,
    INTEGER,
    JSON,
    NUMBER,
    PERCENT,
    Column,
)

_NULL_TOKENS = {"", "-", "--", "n/a", "na", "nan", "none", "null", "nm", "#n/a", "#value!"}
_NUM_CLEAN = re.compile(r"[,\s₹$€£%]")
_CRORE = re.compile(r"(cr|crore|crores)$", re.IGNORECASE)
_LAKH = re.compile(r"(lakh|lakhs|lac)$", re.IGNORECASE)
_MILLION = re.compile(r"(mn|million)$", re.IGNORECASE)
_BILLION = re.compile(r"(bn|billion)$", re.IGNORECASE)

_TRUE = {"1", "true", "t", "yes", "y", "active", "listed"}
_FALSE = {"0", "false", "f", "no", "n", "inactive"}

_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%Y/%m/%d",
    "%Y%m%d",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def today_iso() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def is_blank(raw: Any) -> bool:
    if raw is None:
        return True
    if isinstance(raw, float) and math.isnan(raw):
        return True
    if isinstance(raw, str) and raw.strip().lower() in _NULL_TOKENS:
        return True
    return False


def to_number(raw: Any) -> Optional[float]:
    if is_blank(raw):
        return None
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        value = float(raw)
        return None if math.isnan(value) or math.isinf(value) else value
    text = str(raw).strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    scale = 1.0
    if _CRORE.search(text):
        scale, text = 1e7, _CRORE.sub("", text).strip()
    elif _LAKH.search(text):
        scale, text = 1e5, _LAKH.sub("", text).strip()
    elif _BILLION.search(text):
        scale, text = 1e9, _BILLION.sub("", text).strip()
    elif _MILLION.search(text):
        scale, text = 1e6, _MILLION.sub("", text).strip()
    text = _NUM_CLEAN.sub("", text)
    if text in ("", "-", "+", "."):
        return None
    try:
        value = float(text) * scale
    except ValueError:
        return None
    if math.isnan(value) or math.isinf(value):
        return None
    return -value if negative else value


def to_date(raw: Any) -> Optional[str]:
    if is_blank(raw):
        return None
    if isinstance(raw, datetime):
        return raw.date().isoformat()
    if isinstance(raw, date):
        return raw.isoformat()
    text = str(raw).strip()
    if "T" in text:
        text = text.split("T", 1)[0]
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def to_datetime(raw: Any) -> Optional[str]:
    if is_blank(raw):
        return None
    if isinstance(raw, datetime):
        return raw.astimezone(timezone.utc).isoformat(timespec="seconds")
    text = str(raw).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat(timespec="seconds")
    except ValueError:
        iso_date = to_date(text)
        return f"{iso_date}T00:00:00+00:00" if iso_date else None


def to_bool(raw: Any) -> Optional[int]:
    if is_blank(raw):
        return None
    if isinstance(raw, bool):
        return 1 if raw else 0
    if isinstance(raw, (int, float)):
        return 1 if raw else 0
    text = str(raw).strip().lower()
    if text in _TRUE:
        return 1
    if text in _FALSE:
        return 0
    return None


def coerce(column: Column, raw: Any) -> Any:
    """Coerce a raw cell into the column's storage type."""
    if is_blank(raw):
        return None
    kind = column.type
    if kind in (NUMBER, CURRENCY, PERCENT):
        return to_number(raw)
    if kind == INTEGER:
        value = to_number(raw)
        return None if value is None else int(round(value))
    if kind == DATE:
        return to_date(raw)
    if kind == DATETIME:
        return to_datetime(raw)
    if kind == BOOL:
        return to_bool(raw)
    if kind == JSON:
        if isinstance(raw, (dict, list)):
            return json.dumps(raw, default=str)
        return str(raw)
    text = str(raw).strip()
    return text or None


def display(column: Column, stored: Any) -> Any:
    """Storage value -> API value (bools become real booleans, JSON is parsed)."""
    if stored is None:
        return None
    if column.type == BOOL:
        return bool(stored)
    if column.type == JSON:
        try:
            return json.loads(stored)
        except Exception:
            return stored
    return stored


def as_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def equalish(a: Any, b: Any) -> bool:
    """Change detection that tolerates float noise and str/number drift."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return True
        scale = max(abs(float(a)), abs(float(b)), 1.0)
        return abs(float(a) - float(b)) <= 1e-9 * scale
    return str(a).strip() == str(b).strip()


def normalise_entity(raw: Any) -> Optional[str]:
    if is_blank(raw):
        return None
    return str(raw).strip().upper()
