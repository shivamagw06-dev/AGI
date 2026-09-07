"""KIP snapshot persistence — round-trip and integrity checks."""

from __future__ import annotations

from pathlib import Path

from app.kip.models import DocumentMetadata, InvestmentMetadata, KipChunk, KipDocument
from app.kip.persist import integrity_report, load_store, save_store, verify_document_retrievable
from app.kip.store import KipStore


def _seed(store: KipStore) -> str:
    doc = KipDocument(
        document_id="doc_persist_test01",
        lineage_id="lin_persist_test01",
        article_id="article-persist-1",
        content="ROIC and WACC persistence test for institutional memory.",
        cleaned_content="ROIC and WACC persistence test for institutional memory.",
        document=DocumentMetadata(title="Persist Test Note", document_type="agi_note"),
        investment=InvestmentMetadata(tickers=["TESTCO"], themes=["valuation"]),
    )
    chunks = [
        KipChunk(
            chunk_id="chk_persist_1",
            document_id=doc.document_id,
            lineage_id=doc.lineage_id,
            text=doc.cleaned_content,
            embedding=[0.1] * 8,
            tickers=["TESTCO"],
            themes=["valuation"],
        )
    ]
    store.put_document(doc, chunks)
    return doc.document_id


def test_kip_snapshot_roundtrip(tmp_path: Path):
    path = tmp_path / "kip_snapshot.json"
    store = KipStore()
    doc_id = _seed(store)
    saved = save_store(store, path=path)
    assert saved["ok"] is True
    assert saved["documents"] == 1
    assert path.exists()

    restored = KipStore()
    loaded = load_store(restored, path=path)
    assert loaded["ok"] is True
    assert loaded["loaded"] is True
    assert restored.get_document(doc_id) is not None
    assert len(restored.chunks) == 1
    assert verify_document_retrievable(restored, doc_id)["retrievable"] is True

    report = integrity_report(restored)
    assert report["healthy"] is True
    assert report["stats"]["vector_chunks"] == 1


def test_integrity_detects_missing_doc(tmp_path: Path):
    store = KipStore()
    _seed(store)
    report = integrity_report(store, expected_document_ids=["doc_missing_xyz"])
    assert report["healthy"] is False
    assert "doc_missing_xyz" in report["expected_missing_ids"]


def test_persistence_config_requires_env(monkeypatch, tmp_path: Path):
    from app.kip import persist as persist_mod

    monkeypatch.delenv("KIP_DATA_DIR", raising=False)
    monkeypatch.delenv("KIP_ALLOW_EPHEMERAL", raising=False)
    cfg = persist_mod.persistence_config()
    assert cfg["configured"] is False
    assert cfg["durable"] is False
    assert cfg["warning"] and "Persistent KIP storage is disabled" in cfg["warning"]

    # /var/data/* is the Render durable mount convention (not under /tmp or project src).
    monkeypatch.setenv("KIP_DATA_DIR", "/var/data/kip")
    cfg2 = persist_mod.persistence_config()
    assert cfg2["configured"] is True
    assert cfg2["durable"] is True
    assert cfg2["looks_ephemeral"] is False

    # Package-local /tmp-style paths remain ephemeral even if explicitly set.
    monkeypatch.setenv("KIP_DATA_DIR", str(tmp_path / "kip"))
    cfg3 = persist_mod.persistence_config()
    assert cfg3["configured"] is True
    assert cfg3["durable"] is False


def test_enforce_fails_in_production_without_dir(monkeypatch):
    from app.kip import persist as persist_mod
    import pytest

    monkeypatch.delenv("KIP_DATA_DIR", raising=False)
    monkeypatch.delenv("KIP_ALLOW_EPHEMERAL", raising=False)
    monkeypatch.delenv("KIP_REQUIRE_PERSISTENT", raising=False)
    # Default: warn-only so Free→Starter upgrades can succeed before a disk exists.
    cfg = persist_mod.enforce_persistent_kip_or_raise(app_env="production")
    assert cfg["durable"] is False

    monkeypatch.setenv("KIP_REQUIRE_PERSISTENT", "1")
    with pytest.raises(RuntimeError, match="KIP_REQUIRE_PERSISTENT"):
        persist_mod.enforce_persistent_kip_or_raise(app_env="production")

    monkeypatch.setenv("KIP_ALLOW_EPHEMERAL", "1")
    cfg2 = persist_mod.enforce_persistent_kip_or_raise(app_env="production")
    assert cfg2["allow_ephemeral"] is True


def test_legacy_snapshot_migrates_to_durable_dir(monkeypatch, tmp_path: Path):
    from app.kip import persist as persist_mod

    legacy_dir = tmp_path / "legacy"
    durable_dir = tmp_path / "durable"
    legacy_dir.mkdir()
    durable_dir.mkdir()
    legacy_snap = legacy_dir / "kip_snapshot.json"

    store = KipStore()
    doc_id = _seed(store)
    save_store(store, path=legacy_snap)

    monkeypatch.setenv("KIP_DATA_DIR", str(durable_dir))
    monkeypatch.setattr(persist_mod, "_legacy_default_snapshot_path", lambda: legacy_snap)

    restored = KipStore()
    loaded = load_store(restored)
    assert loaded["loaded"] is True
    assert loaded["source"] == "disk_legacy_migrate"
    assert restored.get_document(doc_id) is not None
    assert (durable_dir / "kip_snapshot.json").exists()
