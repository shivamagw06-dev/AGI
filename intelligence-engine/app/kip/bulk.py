"""Bulk broker/newsletter ingest — PDF/DOCX/MD/Email/ZIP (P0 text extraction, no heavy deps)."""

from __future__ import annotations

import base64
import io
import zipfile
from email import message_from_string
from pathlib import Path

from app.kip.models import BulkIngestItem, DocumentType, IngestRequest


def expand_bulk_items(
    items: list[BulkIngestItem],
    *,
    zip_base64: str = "",
    default_broker: str = "",
    source_channel: str = "broker",
) -> list[IngestRequest]:
    requests: list[IngestRequest] = []
    for item in items:
        text = _decode_item(item)
        if not text.strip():
            continue
        requests.append(_to_request(item, text, default_broker=default_broker, source_channel=source_channel))

    if zip_base64:
        raw = base64.b64decode(zip_base64)
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            for name in zf.namelist():
                if name.endswith("/") or name.startswith("__MACOSX"):
                    continue
                data = zf.read(name)
                text = _bytes_to_text(name, data)
                if not text.strip():
                    continue
                fake = BulkIngestItem(
                    filename=name,
                    content=text,
                    broker=default_broker,
                    needs_ocr=_needs_ocr(name),
                )
                requests.append(
                    _to_request(fake, text, default_broker=default_broker, source_channel=source_channel)
                )
    return requests


def _to_request(
    item: BulkIngestItem,
    text: str,
    *,
    default_broker: str,
    source_channel: str,
) -> IngestRequest:
    dtype = _infer_type(item.filename, source_channel)
    title = item.title or Path(item.filename).stem.replace("_", " ") or "Untitled upload"
    return IngestRequest(
        title=title,
        content=text,
        source=source_channel if source_channel != "internal" else "agi_internal",
        document_type=dtype,
        broker=item.broker or default_broker,
        date=item.date,
        tickers=list(item.tickers),
        needs_ocr=item.needs_ocr or _needs_ocr(item.filename),
        ocr_text=text if (item.needs_ocr or _needs_ocr(item.filename)) else "",
        metadata={**(item.metadata or {}), "filename": item.filename, "mime_type": item.mime_type},
    )


def _decode_item(item: BulkIngestItem) -> str:
    if item.content.strip():
        if item.filename.lower().endswith((".eml", ".email")) or item.mime_type.startswith("message/"):
            return _email_to_text(item.content)
        return item.content
    if item.content_base64:
        raw = base64.b64decode(item.content_base64)
        return _bytes_to_text(item.filename or "upload.bin", raw)
    return ""


def _bytes_to_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith((".md", ".markdown", ".txt", ".csv")):
        return data.decode("utf-8", errors="ignore")
    if name.endswith((".eml", ".email")):
        return _email_to_text(data.decode("utf-8", errors="ignore"))
    if name.endswith(".docx"):
        return _docx_to_text(data)
    if name.endswith(".pdf"):
        # P1: lightweight extract — PDF text streams / provided OCR path
        return _pdf_to_text(data)
    # fallback utf-8
    try:
        return data.decode("utf-8")
    except Exception:
        return data.decode("latin-1", errors="ignore")


def _email_to_text(raw: str) -> str:
    msg = message_from_string(raw)
    parts: list[str] = []
    subject = msg.get("Subject", "")
    if subject:
        parts.append(f"Subject: {subject}")
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="ignore"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            parts.append(payload.decode(msg.get_content_charset() or "utf-8", errors="ignore"))
        elif isinstance(msg.get_payload(), str):
            parts.append(msg.get_payload())
    return "\n\n".join(p for p in parts if p)


def _docx_to_text(data: bytes) -> str:
    """Minimal DOCX reader via zip + word/document.xml text nodes."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="ignore")
    except Exception:
        return data.decode("utf-8", errors="ignore")
    # strip tags crudely
    out: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(xml):
        if xml[i] == "<":
            if buf:
                out.append("".join(buf))
                buf = []
            j = xml.find(">", i)
            tag = xml[i : j + 1] if j >= 0 else ""
            if tag in {"</w:p>", "<w:br/>", "<w:br />"}:
                out.append("\n")
            i = j + 1 if j >= 0 else i + 1
            continue
        buf.append(xml[i])
        i += 1
    if buf:
        out.append("".join(buf))
    text = "".join(out)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _pdf_to_text(data: bytes) -> str:
    """Best-effort PDF text extraction without external libs (BT/ET string literals)."""
    raw = data.decode("latin-1", errors="ignore")
    chunks: list[str] = []
    idx = 0
    while True:
        bt = raw.find("BT", idx)
        if bt < 0:
            break
        et = raw.find("ET", bt)
        if et < 0:
            break
        block = raw[bt:et]
        # (text) Tj  or  [(text)] TJ
        for part in _extract_pdf_strings(block):
            if part.strip():
                chunks.append(part)
        idx = et + 2
    if chunks:
        return "\n".join(chunks)
    # fallback: printable ascii runs
    runs = []
    cur = []
    for ch in raw:
        if 32 <= ord(ch) < 127:
            cur.append(ch)
        else:
            if len(cur) >= 4:
                runs.append("".join(cur))
            cur = []
    return "\n".join(runs[:400])


def _extract_pdf_strings(block: str) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(block):
        if block[i] == "(":
            i += 1
            buf: list[str] = []
            while i < len(block):
                if block[i] == "\\" and i + 1 < len(block):
                    buf.append(block[i + 1])
                    i += 2
                    continue
                if block[i] == ")":
                    break
                buf.append(block[i])
                i += 1
            out.append("".join(buf))
        i += 1
    return out


def _infer_type(filename: str, source_channel: str) -> DocumentType:
    name = (filename or "").lower()
    if source_channel == "newsletter":
        return DocumentType.NEWSLETTER
    if source_channel == "agi":
        return DocumentType.AGI_RESEARCH
    if source_channel == "internal":
        return DocumentType.AGI_NOTE
    if name.endswith((".eml", ".email")):
        return DocumentType.BROKER_EMAIL
    return DocumentType.BROKER_RESEARCH


def _needs_ocr(filename: str) -> bool:
    return (filename or "").lower().endswith(".pdf")
