"""Text extraction for PDF / EPUB / DOCX / Markdown — transient only.

Extracted raw text is used for chapter/concept detection then discarded.
Never persisted as a searchable book corpus.
"""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


def extract_text(
    *,
    filename: str = "",
    content: str = "",
    content_bytes: bytes | None = None,
) -> dict[str, Any]:
    """
    Return {"text": str, "format": str, "pages_approx": int}.
    Prefers provided plain content; otherwise decodes by extension.
    """
    name = (filename or "upload.txt").lower()
    if content and content.strip():
        fmt = _format_from_name(name)
        if fmt == "markdown" or name.endswith((".md", ".markdown", ".txt")):
            return {"text": content, "format": "markdown", "pages_approx": max(1, len(content) // 1800)}
        return {"text": content, "format": fmt, "pages_approx": max(1, len(content) // 1800)}

    raw = content_bytes or b""
    if not raw:
        return {"text": "", "format": "empty", "pages_approx": 0}

    if name.endswith(".pdf"):
        return _pdf_to_text(raw)
    if name.endswith(".docx"):
        return _docx_to_text(raw)
    if name.endswith(".epub"):
        return _epub_to_text(raw)
    if name.endswith((".md", ".markdown", ".txt")):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="ignore")
        return {"text": text, "format": "markdown", "pages_approx": max(1, len(text) // 1800)}
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1", errors="ignore")
    return {"text": text, "format": "text", "pages_approx": max(1, len(text) // 1800)}


def _format_from_name(name: str) -> str:
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith(".docx"):
        return "docx"
    if name.endswith(".epub"):
        return "epub"
    if name.endswith((".md", ".markdown")):
        return "markdown"
    return "text"


def _pdf_to_text(raw: bytes) -> dict[str, Any]:
    # Prefer pypdf when available; otherwise empty (caller may supply OCR text)
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw))
        n_pages = len(reader.pages)
        # Cap pages for extraction speed/memory; still report full page count.
        # Large textbooks (Damodaran ACF ~981p, Mankiw ~887p) need deep coverage.
        max_pages = min(n_pages, 900)
        parts: list[str] = []
        for i in range(max_pages):
            try:
                parts.append(reader.pages[i].extract_text() or "")
            except Exception:
                continue
        # Sample mid + tail pages if truncated so end-matter is not lost
        if n_pages > max_pages:
            mid = n_pages // 2
            sample_idxs = set(range(max(max_pages, n_pages - 20), n_pages))
            sample_idxs.update(range(max(0, mid - 5), min(n_pages, mid + 5)))
            for i in sorted(sample_idxs):
                if i < max_pages:
                    continue
                try:
                    parts.append(reader.pages[i].extract_text() or "")
                except Exception:
                    continue
        text = "\n\n".join(parts)
        if len(text) > 900_000:
            text = text[:900_000]
        meta = {}
        try:
            info = reader.metadata or {}
            meta = {
                "title": str(getattr(info, "title", None) or info.get("/Title") or "") if info else "",
                "author": str(getattr(info, "author", None) or info.get("/Author") or "") if info else "",
                "creator": str(getattr(info, "creator", None) or "") if info else "",
            }
        except Exception:
            meta = {}
        return {
            "text": text,
            "format": "pdf",
            "pages_approx": n_pages,
            "pages_processed": max_pages if n_pages > max_pages else n_pages,
            "metadata": meta,
        }
    except Exception:
        return {"text": "", "format": "pdf", "pages_approx": 0, "needs_ocr": True}


def _docx_to_text(raw: bytes) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paras = []
        for p in root.findall(".//w:p", ns):
            texts = [t.text or "" for t in p.findall(".//w:t", ns)]
            line = "".join(texts).strip()
            if line:
                paras.append(line)
        text = "\n".join(paras)
        return {"text": text, "format": "docx", "pages_approx": max(1, len(text) // 1800)}
    except Exception:
        return {"text": "", "format": "docx", "pages_approx": 0}


def _epub_to_text(raw: bytes) -> dict[str, Any]:
    try:
        parts: list[str] = []
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for name in zf.namelist():
                if not name.lower().endswith((".xhtml", ".html", ".htm")):
                    continue
                try:
                    data = zf.read(name).decode("utf-8", errors="ignore")
                except Exception:
                    continue
                # Strip tags lightly
                data = re.sub(r"(?is)<script.*?>.*?</script>", " ", data)
                data = re.sub(r"(?is)<style.*?>.*?</style>", " ", data)
                data = re.sub(r"(?s)<[^>]+>", " ", data)
                data = re.sub(r"\s+", " ", data).strip()
                if data:
                    parts.append(data)
        text = "\n\n".join(parts)
        return {"text": text, "format": "epub", "pages_approx": max(1, len(text) // 1800)}
    except Exception:
        return {"text": "", "format": "epub", "pages_approx": 0}


def load_path(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return extract_text(filename=p.name, content_bytes=p.read_bytes() if p.exists() else b"")
