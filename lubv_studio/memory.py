"""Kalici bellek: LUBV'nin sohbetler arasi hatirladigi notlar.

Iki kapsam var:
  * global  -> her projede yuklenir      (~/.lubv_studio/memory/global.json)
  * proje   -> sadece o klasorde yuklenir (~/.lubv_studio/memory/<hash>.json)

Bellek dosyalari kullanicinin proje klasorunu kirletmez, hepsi ev dizininde durur.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import MEMORY_DIR

GLOBAL = "global"
PROJECT = "proje"


@dataclass
class MemoryEntry:
    text: str
    scope: str = PROJECT
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created: float = field(default_factory=time.time)

    @property
    def created_label(self) -> str:
        return time.strftime("%d.%m.%Y %H:%M", time.localtime(self.created))


def _project_file(project_root: str) -> Path:
    digest = hashlib.sha1((project_root or "bos").encode("utf-8")).hexdigest()[:16]
    return MEMORY_DIR / f"proje_{digest}.json"


def _global_file() -> Path:
    return MEMORY_DIR / "global.json"


def _read(path: Path) -> list[MemoryEntry]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[MemoryEntry] = []
    for item in raw:
        if isinstance(item, dict) and item.get("text"):
            out.append(
                MemoryEntry(
                    text=str(item["text"]),
                    scope=item.get("scope", PROJECT),
                    id=item.get("id", uuid.uuid4().hex[:12]),
                    created=float(item.get("created", time.time())),
                )
            )
    return out


def _write(path: Path, entries: list[MemoryEntry]) -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([asdict(e) for e in entries], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


class MemoryStore:
    """Global + proje bellegini birlikte yoneten kucuk depo."""

    def __init__(self, project_root: str = "") -> None:
        self.project_root = project_root
        self.reload()

    # ---------- yasam dongusu ----------

    def reload(self) -> None:
        self._global = _read(_global_file())
        self._project = _read(_project_file(self.project_root))

    def set_project(self, project_root: str) -> None:
        self.project_root = project_root
        self._project = _read(_project_file(project_root))

    def _bucket(self, scope: str) -> list[MemoryEntry]:
        return self._global if scope == GLOBAL else self._project

    def _persist(self, scope: str) -> None:
        if scope == GLOBAL:
            _write(_global_file(), self._global)
        else:
            _write(_project_file(self.project_root), self._project)

    # ---------- crud ----------

    def all(self) -> list[MemoryEntry]:
        return sorted(self._global + self._project, key=lambda e: e.created, reverse=True)

    def add(self, text: str, scope: str = PROJECT) -> MemoryEntry | None:
        text = (text or "").strip()
        if not text:
            return None
        bucket = self._bucket(scope)
        # ayni notu iki kere yazma
        for existing in bucket:
            if existing.text.strip().lower() == text.lower():
                return existing
        entry = MemoryEntry(text=text, scope=scope)
        bucket.append(entry)
        self._persist(scope)
        return entry

    def update(self, entry_id: str, text: str) -> None:
        for scope in (GLOBAL, PROJECT):
            for entry in self._bucket(scope):
                if entry.id == entry_id:
                    entry.text = text.strip()
                    self._persist(scope)
                    return

    def delete(self, entry_id: str) -> None:
        for scope in (GLOBAL, PROJECT):
            bucket = self._bucket(scope)
            for entry in list(bucket):
                if entry.id == entry_id:
                    bucket.remove(entry)
                    self._persist(scope)
                    return

    def clear(self, scope: str) -> None:
        self._bucket(scope).clear()
        self._persist(scope)

    # ---------- prompt'a enjeksiyon ----------

    def as_prompt_block(self) -> str:
        entries = self.all()
        if not entries:
            return ""
        lines = ["# KALICI BELLEK", "Onceki sohbetlerden hatirladiklarin:"]
        for entry in entries:
            etiket = "genel" if entry.scope == GLOBAL else "proje"
            lines.append(f"- ({etiket}) {entry.text}")
        return "\n".join(lines)
