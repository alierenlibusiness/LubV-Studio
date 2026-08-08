"""LUBV'nin elleri: dosya okuma/yazma/duzenleme/silme, arama, komut, web.

Butun dosya yollari proje kokune sabitlenir (sandbox); kok disina cikan istek reddedilir.
Model bu araclari cevabinin icine etiket yazarak cagirir, parser onlari sirayla toplar.
"""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from . import web

# Modele gonderilen agac/aramada atlanan klasorler (token israfini onler)
IGNORED_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".venv", "venv",
    "env", ".idea", ".vscode", "dist", "build", ".gradle", ".mypy_cache",
    ".pytest_cache", ".next", "target", ".dart_tool", ".expo", "coverage",
}

# Arayuzdeki dosya agacinda gizlenenler: kullanici dist/ build/ gibi
# klasorleri gormek ister, sadece gercekten gurultu olanlari sakliyoruz.
AGAC_GIZLI = {
    ".git", ".svn", ".hg", "__pycache__", ".mypy_cache", ".pytest_cache",
    "node_modules", ".venv", ".idea", ".gradle", ".dart_tool",
}
TEXT_SUFFIXES = {
    ".py", ".txt", ".md", ".json", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
    ".scss", ".java", ".kt", ".kts", ".gradle", ".xml", ".yml", ".yaml", ".toml",
    ".ini", ".cfg", ".sh", ".bat", ".ps1", ".c", ".h", ".cpp", ".hpp", ".cs",
    ".go", ".rs", ".rb", ".php", ".sql", ".env", ".gitignore", ".properties",
    ".csv", ".log", ".vue", ".svelte", ".dart", ".swift", ".lua", ".r", ".pro",
}
MAX_READ_BYTES = 500_000

TOOL_PROTOCOL = """
# ARACLAR (ZORUNLU FORMAT)

Bir sey yapman gerektiginde cevabinin icine asagidaki etiketleri yaz. Etiketler
otomatik calistirilir, sonuclari sana geri gonderilir, sonra ise devam edersin.
Kullaniciya "su dosyayi acar misin" deme; kendin ac, kendin oku, kendin yaz.

1) Dosya oku (satir numarali doner):
<FILE_READ>
klasor/dosya.py
</FILE_READ>

2) Dosyanin bir parcasini degistir - TERCIH EDILEN YONTEM:
<FILE_EDIT>
klasor/dosya.py
---ESKI---
degistirilecek tam metin (dosyada birebir gecmeli, benzersiz olmali)
---YENI---
yerine gelecek metin
</FILE_EDIT>

3) Yeni dosya olustur veya dosyanin tamamini degistir:
<FILE_WRITE>
klasor/dosya.py
---
dosyanin tam icerigi
</FILE_WRITE>

4) Klasor listele:
<FILE_LIST>
.
</FILE_LIST>

5) Projede metin ara:
<FILE_SEARCH>
aranacak metin
</FILE_SEARCH>

6) Dosya sil:
<FILE_DELETE>
klasor/dosya.py
</FILE_DELETE>

7) Terminal komutu calistir (proje klasorunde, Windows):
<RUN_COMMAND>
python -V
</RUN_COMMAND>

8) Internette ara (guncel bilgi, dokumantasyon, hata mesaji, surum):
<WEB_SEARCH>
python 3.13 asyncio taskgroup ornek
</WEB_SEARCH>

9) Bir web sayfasini ac ve oku:
<WEB_FETCH>
https://docs.python.org/3/library/asyncio-task.html
</WEB_FETCH>

10) Kalici bellege not yaz (kullanici tercihi, proje karari, mimari secim):
<MEMORY_ADD>
hatirlanacak tek cumlelik not
</MEMORY_ADD>

KURALLAR
- Yollar proje kokune goredir. Mutlak yol (C:\\...) veya .. kullanma.
- Bir dosyayi degistirmeden once MUTLAKA oku. Tahminle kod yazma.
- Kucuk degisiklik icin FILE_EDIT kullan; FILE_WRITE'i sadece yeni dosyada
  veya dosyayi bastan yazarken kullan.
- FILE_EDIT'te ESKI blogu dosyadaki metinle birebir ayni olmali (bosluklar dahil).
- Bir turda birden fazla arac cagirabilirsin, sirayla calistirilirlar.
- Bilmedigin veya emin olmadigin kutuphane/surum/hata icin once WEB_SEARCH yap.
- Is bittiginde etiketsiz, kisa bir ozet yaz: ne yaptin, sirada ne var.
"""

TOOL_LABELS = {
    "read": "Dosya okundu",
    "write": "Dosya yazıldı",
    "edit": "Dosya düzenlendi",
    "list": "Klasör listelendi",
    "search": "Projede arandı",
    "delete": "Dosya silindi",
    "run": "Komut çalıştırıldı",
    "websearch": "İnternette arandı",
    "webfetch": "Sayfa okundu",
    "memory": "Belleğe yazıldı",
}
TOOL_ICONS = {
    "read": "dosyalar",
    "write": "arti",
    "edit": "duzenle",
    "list": "liste",
    "search": "ara",
    "delete": "sil",
    "run": "terminal",
    "websearch": "kure",
    "webfetch": "baglanti",
    "memory": "bellek",
}


class SandboxError(Exception):
    pass


@dataclass
class ToolCall:
    kind: str
    target: str = ""           # yol, sorgu, url veya komut
    content: str = ""          # write icin icerik
    old: str = ""              # edit icin eski metin
    new: str = ""              # edit icin yeni metin
    ok: bool | None = None
    output: str = ""
    duration: float = 0.0
    approved: bool | None = None
    checkpoint_id: str = ""

    @property
    def label(self) -> str:
        return TOOL_LABELS.get(self.kind, self.kind)

    @property
    def icon(self) -> str:
        return TOOL_ICONS.get(self.kind, "ayarlar")

    @property
    def needs_approval_kind(self) -> str | None:
        return {
            "write": "write", "edit": "write",
            "delete": "delete", "run": "command",
        }.get(self.kind)

    @property
    def touches_file(self) -> bool:
        return self.kind in ("write", "edit", "delete")


# --------------------------------------------------------------------------
# Ayristirma
# --------------------------------------------------------------------------

TAG_NAMES = [
    "FILE_READ", "FILE_WRITE", "FILE_EDIT", "FILE_LIST", "FILE_SEARCH",
    "FILE_DELETE", "RUN_COMMAND", "WEB_SEARCH", "WEB_FETCH", "MEMORY_ADD",
]
_TAG_RE = re.compile(
    r"<(" + "|".join(TAG_NAMES) + r")>(.*?)</\1>",
    re.DOTALL | re.IGNORECASE,
)
_KIND_BY_TAG = {
    "FILE_READ": "read",
    "FILE_WRITE": "write",
    "FILE_EDIT": "edit",
    "FILE_LIST": "list",
    "FILE_SEARCH": "search",
    "FILE_DELETE": "delete",
    "RUN_COMMAND": "run",
    "WEB_SEARCH": "websearch",
    "WEB_FETCH": "webfetch",
    "MEMORY_ADD": "memory",
}
_EDIT_SPLIT_RE = re.compile(
    r"^\s*(?P<path>[^\n]+)\n\s*-{2,}\s*ESKI\s*-{2,}\s*\n(?P<old>.*?)\n?\s*-{2,}\s*YENI\s*-{2,}\s*\n(?P<new>.*)$",
    re.DOTALL | re.IGNORECASE,
)


def _kirp_kod_citasi(metin: str) -> str:
    """Model bazen icerigi ``` icine alir; onu ayikla."""
    satirlar = metin.split("\n")
    if not satirlar or not satirlar[0].strip().startswith("```"):
        return metin
    satirlar = satirlar[1:]
    # sondaki bos satirlari atlayarak kapanis citasini bul
    son = len(satirlar) - 1
    while son >= 0 and not satirlar[son].strip():
        son -= 1
    if son >= 0 and satirlar[son].strip().startswith("```"):
        satirlar = satirlar[:son]
    return "\n".join(satirlar).rstrip("\n") + "\n"


def parse_tool_calls(text: str) -> list[ToolCall]:
    """Cevaptaki arac etiketlerini gorunme sirasina gore cikarir."""
    calls: list[ToolCall] = []
    for match in _TAG_RE.finditer(text or ""):
        kind = _KIND_BY_TAG[match.group(1).upper()]
        body = match.group(2)

        if kind == "write":
            head, sep, content = body.partition("---")
            if not sep:
                head, _, content = body.strip().partition("\n")
            target = head.strip().strip("`").strip()
            content = _kirp_kod_citasi(content.lstrip("\r\n"))
            if target:
                calls.append(ToolCall(kind="write", target=target, content=content))

        elif kind == "edit":
            es = _EDIT_SPLIT_RE.match(body)
            if not es:
                continue
            target = es.group("path").strip().strip("`").strip()
            eski = es.group("old")
            yeni = es.group("new").rstrip("\n")
            if target and eski:
                calls.append(ToolCall(kind="edit", target=target, old=eski, new=yeni))

        else:
            target = body.strip().strip("`").strip()
            if target:
                calls.append(ToolCall(kind=kind, target=target))
    return calls


def strip_tool_calls(text: str) -> str:
    cleaned = _TAG_RE.sub("", text or "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# --------------------------------------------------------------------------
# Sandbox
# --------------------------------------------------------------------------

class Workspace:
    """Proje kokune kilitli dosya sistemi erisimi."""

    def __init__(self, root: str, checkpoints=None) -> None:
        self.root = Path(root).resolve() if root else None
        self.checkpoints = checkpoints

    # -- yol guvenligi --

    def resolve(self, rel: str) -> Path:
        if self.root is None:
            raise SandboxError("Proje klasoru secilmemis.")
        temiz = (rel or "").strip().strip('"').strip("'").replace("\\", "/")
        if temiz in ("", ".", "./"):
            return self.root
        aday = Path(temiz)
        if aday.is_absolute() or re.match(r"^[A-Za-z]:", temiz):
            cozulmus = aday.resolve()
        else:
            cozulmus = (self.root / aday).resolve()
        try:
            cozulmus.relative_to(self.root)
        except ValueError:
            raise SandboxError(f"'{rel}' proje klasorunun disinda, erisim reddedildi.") from None
        return cozulmus

    def rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.root)).replace("\\", "/")
        except Exception:
            return str(path)

    def _checkpoint(self, path: Path, action: str, note: str = "") -> str:
        if self.checkpoints is None:
            return ""
        try:
            return self.checkpoints.record(path, self.rel(path), action, note).id
        except Exception:
            return ""

    # -- okuma --

    def raw_text(self, rel: str) -> str:
        path = self.resolve(rel)
        return path.read_text(encoding="utf-8", errors="replace")

    def read_file(self, rel: str) -> tuple[bool, str]:
        path = self.resolve(rel)
        if not path.exists():
            benzer = self.find_files(f"*{Path(rel).name}*", limit=5)
            ek = f"\nBenzer dosyalar: {', '.join(benzer)}" if benzer else ""
            return False, f"Dosya bulunamadi: {rel}{ek}"
        if path.is_dir():
            return self.list_dir(rel)
        if path.stat().st_size > MAX_READ_BYTES:
            return False, f"Dosya cok buyuk ({path.stat().st_size // 1024} KB), okunmadi."
        try:
            data = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return False, f"Okunamadi: {exc}"
        numarali = "\n".join(
            f"{i:>4} | {satir}" for i, satir in enumerate(data.splitlines(), 1)
        )
        return True, numarali if numarali else "(dosya bos)"

    # -- yazma --

    def write_file(self, rel: str, content: str) -> tuple[bool, str]:
        path = self.resolve(rel)
        if path.is_dir():
            return False, f"{rel} bir klasor, uzerine yazilamaz."
        yeni_mi = not path.exists()
        self._checkpoint(path, "write", "tam yazma")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        except Exception as exc:
            return False, f"Yazilamadi: {exc}"
        satir = content.count("\n") + 1
        return True, (
            f"{self.rel(path)} {'olusturuldu' if yeni_mi else 'guncellendi'} "
            f"({satir} satir, {len(content)} karakter)."
        )

    def edit_file(self, rel: str, eski: str, yeni: str) -> tuple[bool, str]:
        path = self.resolve(rel)
        if not path.exists() or path.is_dir():
            return False, f"Duzenlenecek dosya yok: {rel}"
        try:
            icerik = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return False, f"Okunamadi: {exc}"

        hedef = eski
        if hedef not in icerik:
            # satir sonu / bosluk toleransi
            alternatif = eski.replace("\r\n", "\n").strip("\n")
            if alternatif and alternatif in icerik:
                hedef = alternatif
            else:
                return False, (
                    "ESKI blogu dosyada bulunamadi. Once dosyayi FILE_READ ile "
                    "tekrar oku ve birebir ayni metni gonder."
                )

        adet = icerik.count(hedef)
        if adet > 1:
            return False, (
                f"ESKI blogu dosyada {adet} kez geciyor, hangisi oldugu belirsiz. "
                "Daha fazla satir ekleyerek benzersiz hale getir."
            )

        self._checkpoint(path, "edit", "parca duzenleme")
        guncel = icerik.replace(hedef, yeni, 1)
        try:
            path.write_text(guncel, encoding="utf-8", newline="\n")
        except Exception as exc:
            return False, f"Yazilamadi: {exc}"

        onceki_satir = icerik[: icerik.index(hedef)].count("\n") + 1
        return True, (
            f"{self.rel(path)} guncellendi (satir ~{onceki_satir}, "
            f"{hedef.count(chr(10)) + 1} satir -> {yeni.count(chr(10)) + 1} satir)."
        )

    def delete_file(self, rel: str) -> tuple[bool, str]:
        path = self.resolve(rel)
        if path == self.root:
            return False, "Proje kokunu silemezsin."
        if not path.exists():
            return False, f"Bulunamadi: {rel}"
        try:
            if path.is_dir():
                import shutil

                shutil.rmtree(path)
                return True, f"{self.rel(path)} klasoru silindi."
            self._checkpoint(path, "delete", "silme")
            path.unlink()
            return True, f"{self.rel(path)} silindi."
        except Exception as exc:
            return False, f"Silinemedi: {exc}"

    # -- listeleme / arama --

    def list_dir(self, rel: str = ".") -> tuple[bool, str]:
        path = self.resolve(rel)
        if not path.is_dir():
            return False, f"Klasor degil: {rel}"
        klasorler, dosyalar = [], []
        try:
            for item in sorted(path.iterdir(), key=lambda p: p.name.lower()):
                if item.name in IGNORED_DIRS:
                    continue
                if item.is_dir():
                    klasorler.append(f"[K] {item.name}/")
                else:
                    dosyalar.append(f"[D] {item.name}  ({insan_boyut(item.stat().st_size)})")
        except Exception as exc:
            return False, f"Listelenemedi: {exc}"
        satirlar = klasorler + dosyalar
        return True, "\n".join(satirlar) if satirlar else "(bos klasor)"

    def tree(self, max_entries: int = 300) -> str:
        if self.root is None:
            return ""
        satirlar: list[str] = []

        def gez(klasor: Path, prefix: str = "") -> None:
            if len(satirlar) >= max_entries:
                return
            try:
                items = sorted(
                    (p for p in klasor.iterdir() if p.name not in IGNORED_DIRS),
                    key=lambda p: (p.is_file(), p.name.lower()),
                )
            except Exception:
                return
            for item in items:
                if len(satirlar) >= max_entries:
                    satirlar.append(f"{prefix}... (kirpildi)")
                    return
                if item.is_dir():
                    satirlar.append(f"{prefix}{item.name}/")
                    gez(item, prefix + "  ")
                else:
                    satirlar.append(f"{prefix}{item.name}")

        gez(self.root)
        return "\n".join(satirlar)

    def search(self, query: str, max_hits: int = 80) -> tuple[bool, str]:
        if self.root is None:
            return False, "Proje klasoru yok."
        desen = query.strip()
        if not desen:
            return False, "Bos arama."
        regex = re.compile(re.escape(desen), re.IGNORECASE)
        hits: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for name in filenames:
                path = Path(dirpath) / name
                if path.suffix.lower() not in TEXT_SUFFIXES:
                    continue
                try:
                    if path.stat().st_size > MAX_READ_BYTES:
                        continue
                    with path.open("r", encoding="utf-8", errors="ignore") as fh:
                        for no, satir in enumerate(fh, 1):
                            if regex.search(satir):
                                hits.append(f"{self.rel(path)}:{no}: {satir.strip()[:180]}")
                                if len(hits) >= max_hits:
                                    hits.append("... (daha fazla sonuc var)")
                                    return True, "\n".join(hits)
                except Exception:
                    continue
        return True, "\n".join(hits) if hits else f"'{desen}' icin sonuc yok."

    def find_files(self, pattern: str, limit: int = 200) -> list[str]:
        if self.root is None:
            return []
        out: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
            for name in filenames:
                if fnmatch.fnmatch(name.lower(), pattern.lower()):
                    out.append(self.rel(Path(dirpath) / name))
                    if len(out) >= limit:
                        return out
        return out

    # -- komut --

    def run_command(self, command: str, timeout: int = 60) -> tuple[bool, str]:
        if self.root is None:
            return False, "Proje klasoru yok."
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, f"Komut {timeout} saniyede bitmedi, iptal edildi."
        except Exception as exc:
            return False, f"Calistirilamadi: {exc}"
        cikti = ((proc.stdout or "") + (proc.stderr or "")).strip() or "(cikti yok)"
        if len(cikti) > 20000:
            cikti = cikti[:20000] + "\n... (cikti kirpildi)"
        return proc.returncode == 0, f"[cikis kodu {proc.returncode}]\n{cikti}"


# --------------------------------------------------------------------------
# Calistirici
# --------------------------------------------------------------------------

def execute(call: ToolCall, workspace: Workspace, memory=None, timeout: int = 60) -> ToolCall:
    basla = time.time()
    try:
        if call.kind == "read":
            call.ok, call.output = workspace.read_file(call.target)
        elif call.kind == "write":
            call.ok, call.output = workspace.write_file(call.target, call.content)
        elif call.kind == "edit":
            call.ok, call.output = workspace.edit_file(call.target, call.old, call.new)
        elif call.kind == "list":
            call.ok, call.output = workspace.list_dir(call.target)
        elif call.kind == "search":
            call.ok, call.output = workspace.search(call.target)
        elif call.kind == "delete":
            call.ok, call.output = workspace.delete_file(call.target)
        elif call.kind == "run":
            call.ok, call.output = workspace.run_command(call.target, timeout)
        elif call.kind == "websearch":
            call.ok, call.output = web.search(call.target)
        elif call.kind == "webfetch":
            call.ok, call.output = web.fetch(call.target)
        elif call.kind == "memory":
            if memory is None:
                call.ok, call.output = False, "Bellek kapali."
            else:
                memory.add(call.target)
                call.ok, call.output = True, f"Bellege eklendi: {call.target}"
        else:
            call.ok, call.output = False, f"Bilinmeyen arac: {call.kind}"
    except SandboxError as exc:
        call.ok, call.output = False, str(exc)
    except Exception as exc:
        call.ok, call.output = False, f"Beklenmeyen hata: {exc}"
    call.duration = time.time() - basla
    return call


def insan_boyut(n: float) -> str:
    for birim in ("B", "KB", "MB", "GB"):
        if n < 1024 or birim == "GB":
            return f"{n:.0f} {birim}" if birim == "B" else f"{n:.1f} {birim}"
        n /= 1024.0
    return f"{n:.0f} B"
