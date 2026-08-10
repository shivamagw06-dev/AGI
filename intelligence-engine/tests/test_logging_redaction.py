from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, redact_secrets


def test_redacts_provider_query_keys_and_bearer_tokens() -> None:
    raw = (
        "GET https://example.test/quote?symbol=ABC&token=secret-token-12345 "
        "&apikey=another-secret-67890 Authorization: Bearer bearer-secret-12345"
    )
    clean = redact_secrets(raw)
    assert "secret-token-12345" not in clean
    assert "another-secret-67890" not in clean
    assert "bearer-secret-12345" not in clean
    assert clean.count("[REDACTED]") == 3


def test_json_formatter_redacts_message_and_structured_extra() -> None:
    record = logging.LogRecord(
        "httpx",
        logging.INFO,
        __file__,
        1,
        "GET https://finnhub.io/quote?token=live-secret-12345",
        (),
        None,
    )
    record.extra = {
        "url": "https://fmp.test/x?apikey=fmp-secret-12345",
        "api_key": "opaque-provider-credential",
    }
    payload = json.loads(JsonFormatter().format(record))
    assert "live-secret-12345" not in payload["message"]
    assert "fmp-secret-12345" not in payload["extra"]["url"]
    assert payload["extra"]["api_key"] == "[REDACTED]"
