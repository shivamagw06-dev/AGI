"""PRP-02 Security Center diagnostics soft-slice."""

from __future__ import annotations

from typing import Any

from institutional_security import api_keys as keys_mod
from institutional_security import audit as audit_mod
from institutional_security import authentication as authn
from institutional_security import session as session_mod
from institutional_security.flags import flags_dict
from institutional_security.schema import (
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    PRP_PRODUCT,
    PRP_VERSION,
    PRP_WORKSTREAM_ID,
    SECURITY_ENGINE_VERSION,
)
from institutional_security.tenant import list_tenants


def security_center_board() -> dict[str, Any]:
    sess = session_mod.session_metrics()
    keys = keys_mod.api_key_metrics()
    aud = audit_mod.audit_metrics()
    return {
        "security_center": True,
        "active_sessions": sess.get("active_sessions"),
        "login_failures": sess.get("login_failures"),
        "login_ok": sess.get("login_ok"),
        "api_key_usage": keys.get("api_key_usage"),
        "api_keys_active": keys.get("api_keys_active"),
        "permission_changes": aud.get("permission_changes"),
        "audit_volume": aud.get("audit_volume"),
        "tenant_count": len(list_tenants()),
        "revoked_tokens": sess.get("revoked_tokens"),
        "authentication_latency_ms": authn.auth_latency_ms(),
        "recent_audit": aud.get("recent") or [],
        "guiding_principle": GUIDING_PRINCIPLE,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "adds_intelligence_engines": False,
        "enters_intelligence_layer": False,
    }


def build_diagnostics() -> dict[str, Any]:
    return {
        "workstream_id": PRP_WORKSTREAM_ID,
        "product": PRP_PRODUCT,
        "version": PRP_VERSION,
        "security_engine_version": SECURITY_ENGINE_VERSION,
        "flags": flags_dict(),
        **security_center_board(),
    }
