"""Secrets / token / session encryption helpers (PRP-02)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from typing import Optional


def _pepper() -> bytes:
    raw = os.environ.get("AGI_PRP_02_SECRET") or "agib-prp02-dev-secret-not-for-prod"
    return raw.encode("utf-8")


def hash_secret(value: str, *, salt: Optional[str] = None) -> str:
    """One-way hash for passwords / API key material at rest."""
    s = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        value.encode("utf-8"),
        (s.encode("utf-8") + _pepper()),
        120_000,
    )
    return f"pbkdf2:{s}:{base64.urlsafe_b64encode(digest).decode('ascii')}"


def verify_secret(value: str, stored: str) -> bool:
    try:
        kind, salt, _ = stored.split(":", 2)
        if kind != "pbkdf2":
            return False
        return hmac.compare_digest(hash_secret(value, salt=salt), stored)
    except Exception:
        return False


def encrypt_at_rest(plaintext: str) -> str:
    """
    Symmetric seal for tokens / session payloads.
    Dev-grade XOR+HMAC seal; production should swap for KMS/AES-GCM.
    """
    key = hashlib.sha256(_pepper()).digest()
    data = plaintext.encode("utf-8")
    stream = hashlib.sha256(key + b"stream").digest()
    out = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(data))
    mac = hmac.new(key, out, hashlib.sha256).digest()[:16]
    return "v1:" + base64.urlsafe_b64encode(mac + out).decode("ascii")


def decrypt_at_rest(token: str) -> Optional[str]:
    try:
        if not token.startswith("v1:"):
            return None
        raw = base64.urlsafe_b64decode(token[3:].encode("ascii"))
        mac, out = raw[:16], raw[16:]
        key = hashlib.sha256(_pepper()).digest()
        expect = hmac.new(key, out, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(mac, expect):
            return None
        stream = hashlib.sha256(key + b"stream").digest()
        data = bytes(b ^ stream[i % len(stream)] for i, b in enumerate(out))
        return data.decode("utf-8")
    except Exception:
        return None


def new_token(prefix: str = "tok") -> str:
    return f"{prefix}_{secrets.token_urlsafe(24)}"


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
