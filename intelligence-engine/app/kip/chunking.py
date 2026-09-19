"""Document chunking for hybrid retrieval."""

from __future__ import annotations

from app.kip.embeddings import embed_text, tokenize
from app.kip.models import KipChunk, KipDocument


def chunk_document(doc: KipDocument, *, dim: int = 256, max_chars: int = 700, overlap: int = 80) -> list[KipChunk]:
    text = doc.cleaned_content or doc.content or ""
    if not text.strip():
        return []
    pieces = _split(text, max_chars=max_chars, overlap=overlap)
    chunks: list[KipChunk] = []
    for i, piece in enumerate(pieces):
        tokens = tokenize(piece)
        chunks.append(
            KipChunk(
                document_id=doc.document_id,
                lineage_id=doc.lineage_id,
                version=doc.document.version,
                ordinal=i,
                text=piece,
                tokens=tokens,
                embedding=embed_text(piece, dim=dim),
                tickers=list(doc.investment.tickers),
                themes=list(doc.investment.themes),
                sectors=list(doc.investment.sectors),
            )
        )
    return chunks


def _split(text: str, *, max_chars: int, overlap: int) -> list[str]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paras:
        paras = [text.strip()]
    out: list[str] = []
    buf = ""
    for p in paras:
        if not buf:
            buf = p
            continue
        if len(buf) + 2 + len(p) <= max_chars:
            buf = f"{buf}\n\n{p}"
        else:
            out.append(buf)
            # overlap tail
            tail = buf[-overlap:] if overlap and len(buf) > overlap else ""
            buf = f"{tail}\n\n{p}".strip() if tail else p
    if buf:
        out.append(buf)
    # hard-split oversized
    final: list[str] = []
    for piece in out:
        if len(piece) <= max_chars:
            final.append(piece)
            continue
        start = 0
        while start < len(piece):
            end = min(len(piece), start + max_chars)
            final.append(piece[start:end])
            if end >= len(piece):
                break
            start = max(0, end - overlap)
    return final
