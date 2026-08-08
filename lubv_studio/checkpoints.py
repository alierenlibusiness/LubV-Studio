"""Geri alma: LUBV'nin dokundugu her dosyanin onceki hali saklanir.

Her yazma/silme/duzenleme oncesi dosyanin eski icerigi bir kontrol noktasina
yazilir. Kullanici tek tikla o degisikligi geri alabilir.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import APP_DIR

CHECKPOINT_DIR = APP_DIR / "checkpoints"
INDEX_PATH = CHECKPOINT_DIR / "index.json"
MAX_KAYIT = 300


@dataclass
class Checkpoint:
    rel_path: str
    abs_path: str
    action: str                    # write | edit | delete
    existed: bool                  # islem oncesi dosya var miydi
    blob: str = ""                 # eski icerigin saklandigi dosya adi
    project_root: str = ""
    note: str = ""
    reverted: bool = False
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created: float = field(default_factory=time.time)

    @property
    def time_label(self) -> str:
        return time.strftime("%H:%M:%S", time.localtime(self.created))

    @property
    def action_label(self) -> str:
        return {"write": "yazma", "edit": "düzenleme", "delete": "silme"}.get(
            self.action, self.action
        )


class CheckpointStore:
    def __init__(self, project_root: str = "") -> None:
        self.project_root = project_root
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        self.items: list[Checkpoint] = []
        self.load()

    # ---------- kalicilik ----------

    def load(self) -> None:
        self.items = []
        if not INDEX_PATH.exists():
            return
        try:
            ham = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            return
        for item in ham:
            try:
                self.items.append(Checkpoint(**item))
            except Exception:
                continue

    def save(self) -> None:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        kayitlar = self.items[-MAX_KAYIT:]
        INDEX_PATH.write_text(
            json.dumps([asdict(c) for c in kayitlar], ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        self.items = kayitlar

    # ---------- kayit ----------

    def record(self, path: Path, rel: str, action: str, note: str = "") -> Checkpoint:
        vardi = path.exists() and path.is_file()
        blob_ad = ""
        if vardi:
            try:
                icerik = path.read_bytes()
                blob_ad = f"{uuid.uuid4().hex[:16]}.bak"
                (CHECKPOINT_DIR / blob_ad).write_bytes(icerik)
            except Exception:
                blob_ad = ""
                vardi = False

        nokta = Checkpoint(
            rel_path=rel,
            abs_path=str(path),
            action=action,
            existed=vardi,
            blob=blob_ad,
            project_root=self.project_root,
            note=note,
        )
        self.items.append(nokta)
        self.save()
        return nokta

    # ---------- geri alma ----------

    def previous_content(self, nokta: Checkpoint) -> str:
        if not nokta.existed or not nokta.blob:
            return ""
        yol = CHECKPOINT_DIR / nokta.blob
        if not yol.exists():
            return ""
        try:
            return yol.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return ""

    def revert(self, checkpoint_id: str) -> tuple[bool, str]:
        nokta = next((c for c in self.items if c.id == checkpoint_id), None)
        if nokta is None:
            return False, "Kontrol noktasi bulunamadi."
        if nokta.reverted:
            return False, "Bu degisiklik zaten geri alinmis."

        hedef = Path(nokta.abs_path)
        try:
            if nokta.existed:
                icerik = self.previous_content(nokta)
                hedef.parent.mkdir(parents=True, exist_ok=True)
                hedef.write_text(icerik, encoding="utf-8", newline="\n")
                mesaj = f"{nokta.rel_path} eski haline dondu."
            else:
                # dosya bu islemle olusmustu -> sil
                if hedef.exists():
                    hedef.unlink()
                mesaj = f"{nokta.rel_path} silindi (LUBV olusturmustu)."
        except Exception as exc:
            return False, f"Geri alinamadi: {exc}"

        nokta.reverted = True
        self.save()
        return True, mesaj

    def for_project(self, project_root: str) -> list[Checkpoint]:
        kok = str(Path(project_root).resolve()) if project_root else ""
        return [
            c for c in reversed(self.items)
            if not kok or str(Path(c.project_root or "").resolve() if c.project_root else "") == kok
        ]

    def purge(self) -> None:
        for c in self.items:
            if c.blob:
                try:
                    (CHECKPOINT_DIR / c.blob).unlink(missing_ok=True)
                except Exception:
                    pass
        self.items = []
        self.save()
