"""CheckpointManager — durable named checkpoints that survive restarts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from institutional_data.persistence.atomic import atomic_write_json, file_lock


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CheckpointManager:
    """Crash-safe checkpoint store under a durable root."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else self._default_root()
        (self.root / "checkpoints").mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_root() -> Path:
        import os

        kip = (os.getenv("KIP_DATA_DIR") or "").strip()
        if kip:
            return Path(kip) / "institutional_data"
        cgl = (os.getenv("CGL_STORE_ROOT") or "").strip()
        if cgl:
            return Path(cgl).parent / "institutional_data"
        return Path(__file__).resolve().parents[2] / "data" / "institutional_data"

    def path_for(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        return self.root / "checkpoints" / f"{safe}.json"

    def load(self, name: str) -> dict[str, Any]:
        path = self.path_for(name)
        if not path.exists():
            return {}
        try:
            import json

            return json.loads(path.read_text(encoding="utf-8")) or {}
        except Exception:
            # Recover from crashed tmp if present
            tmp = path.with_suffix(path.suffix + ".tmp")
            if tmp.exists():
                try:
                    import json

                    return json.loads(tmp.read_text(encoding="utf-8")) or {}
                except Exception:
                    return {}
            return {}

    def save(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self.path_for(name)
        body = {**(payload or {}), "checkpoint": name, "updated_at": _now(), "durable": True}
        with file_lock(path):
            atomic_write_json(path, body)
        return body

    def update(self, name: str, **fields: Any) -> dict[str, Any]:
        path = self.path_for(name)
        with file_lock(path):
            cur = self.load(name)
            body = {**cur, **fields, "checkpoint": name, "updated_at": _now(), "durable": True}
            atomic_write_json(path, body)
            return body

    def list_checkpoints(self) -> list[dict[str, Any]]:
        out = []
        for p in sorted((self.root / "checkpoints").glob("*.json")):
            if p.name.endswith(".lock"):
                continue
            meta = self.load(p.stem)
            out.append(
                {
                    "name": p.stem,
                    "updated_at": meta.get("updated_at"),
                    "bytes": p.stat().st_size if p.exists() else 0,
                }
            )
        return out

    def storage_usage(self) -> dict[str, Any]:
        total = 0
        files = 0
        for p in self.root.rglob("*"):
            if p.is_file() and not p.name.endswith(".lock"):
                total += p.stat().st_size
                files += 1
        return {"root": str(self.root), "bytes": total, "files": files, "mb": round(total / (1024 * 1024), 3)}
