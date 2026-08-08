"""Ajan dongusu: modele sor -> arac cagrilarini calistir -> sonuclari geri ver -> tekrar.

Butun is arka plan thread'inde doner, arayuze sinyallerle konusur.
Onay gerektiren islemlerde (dosya yazma/silme, komut) thread durur ve
arayuzden gelen cevabi bekler.
"""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, QThread, Signal

from . import platform_, tools
from .api import ApiError, DeepSeekClient
from .config import (
    CEVAP_DILI, CHAT_KIPI_TALIMATI, OTO_MODU_TALIMATI, PLAN_MODU_TALIMATI,
)
from .memory import MemoryStore
from .tools import ToolCall, Workspace
from .usage import Kullanim

MAX_RESULT_CHARS = 14000

OPEN_TAGS = [f"<{ad}>" for ad in tools.TAG_NAMES]


class StreamTagFilter:
    """Akis sirasinda arac etiketlerini gizler, sadece kullaniciya gosterilecek metni verir."""

    def __init__(self) -> None:
        self.buf = ""
        self.inside: str | None = None

    def feed(self, chunk: str) -> str:
        self.buf += chunk
        out: list[str] = []
        while True:
            if self.inside:
                idx = self.buf.upper().find(self.inside)
                if idx == -1:
                    return "".join(out)
                self.buf = self.buf[idx + len(self.inside):]
                self.inside = None
                continue

            idx = self.buf.find("<")
            if idx == -1:
                out.append(self.buf)
                self.buf = ""
                return "".join(out)

            out.append(self.buf[:idx])
            self.buf = self.buf[idx:]
            ust = self.buf.upper()

            eslesen = next((t for t in OPEN_TAGS if ust.startswith(t)), None)
            if eslesen:
                self.buf = self.buf[len(eslesen):]
                self.inside = "</" + eslesen[1:]
                continue

            if len(self.buf) < 16 and any(t.startswith(ust) for t in OPEN_TAGS):
                return "".join(out)  # etiketin devami gelsin

            out.append(self.buf[0])
            self.buf = self.buf[1:]

    def flush(self) -> str:
        kalan = "" if self.inside else self.buf
        self.buf = ""
        self.inside = None
        return kalan


def build_system_prompt(
    cfg, workspace: Workspace, memory: MemoryStore | None, acik_dosyalar: list[str] | None = None
) -> str:
    parcalar = [cfg.system_prompt.strip()]

    # arayuz dili neyse cevap da o dilde olur
    parcalar.append(CEVAP_DILI.get(cfg.language, CEVAP_DILI["tr"]))

    # Chat kipi: arac protokolu ve proje baglami hic gonderilmez
    if cfg.kip == "chat":
        parcalar.append(CHAT_KIPI_TALIMATI.strip())
        bellek_metni = memory.as_prompt_block() if (memory and cfg.use_memory) else ""
        if bellek_metni:
            parcalar.append(bellek_metni)
        return "\n\n---\n\n".join(p for p in parcalar if p)

    if cfg.mode == "plan":
        parcalar.append(PLAN_MODU_TALIMATI.strip())
    elif cfg.mode == "oto":
        parcalar.append(OTO_MODU_TALIMATI.strip())

    bellek = memory.as_prompt_block() if (memory and cfg.use_memory) else ""
    if bellek:
        parcalar.append(bellek)

    if workspace.root is not None:
        agac = workspace.tree(max_entries=300)
        proje = [
            "# PROJE",
            f"Kok klasor: {workspace.root}",
            f"Tarih: {time.strftime('%d.%m.%Y')}",
            f"Isletim sistemi: {platform_.isletim_sistemi()}, "
            f"kabuk: {platform_.kabuk_adi()}",
        ]
        if acik_dosyalar:
            proje.append("Kullanicinin editorde acik dosyalari: " + ", ".join(acik_dosyalar))
        proje.append("\nDosya agaci:\n" + (agac or "(bos klasor)"))
        parcalar.append("\n".join(proje))

    parcalar.append(tools.TOOL_PROTOCOL.strip())
    return "\n\n---\n\n".join(p for p in parcalar if p)


class AgentWorker(QThread):
    # akis
    delta_content = Signal(str)      # gosterilecek metin parcasi
    delta_reasoning = Signal(str)    # reasoner dusunce parcasi
    step_started = Signal(int)       # kacinci tur
    step_text_done = Signal(str)     # o turun temiz metni

    # araclar
    approval_request = Signal(object)   # ToolCall
    tool_started = Signal(object)       # ToolCall
    tool_finished = Signal(object)      # ToolCall
    memory_changed = Signal()

    # sonuc
    usage_reported = Signal(object)   # Kullanim
    failed = Signal(str)
    done = Signal(list)   # gecmise eklenecek mesajlar

    def __init__(
        self,
        cfg,
        messages: list[dict],
        memory: MemoryStore,
        checkpoints=None,
        open_files: list[str] | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.cfg = cfg
        self.messages = list(messages)
        self.memory = memory
        self.open_files = open_files or []
        self.workspace = Workspace(cfg.project_root, checkpoints=checkpoints)
        self.client = DeepSeekClient(cfg.api_key, cfg.base_url)

        self.cancel_event = threading.Event()
        self._approval_event = threading.Event()
        self._approval_result = False
        self._yeni_mesajlar: list[dict] = []

    # ---------- disaridan kontrol ----------

    def cancel(self) -> None:
        self.cancel_event.set()
        self._approval_result = False
        self._approval_event.set()

    def resolve_approval(self, onay: bool) -> None:
        self._approval_result = bool(onay)
        self._approval_event.set()

    def _onay_iste(self, call: ToolCall) -> bool:
        tur = call.needs_approval_kind
        if tur is None:
            return True
        if self.cfg.mode == "oto":
            return True
        otomatik = {
            "write": self.cfg.auto_approve_write,
            "delete": self.cfg.auto_approve_delete,
            "command": self.cfg.auto_approve_command,
        }[tur]
        if otomatik:
            return True
        self._approval_event.clear()
        self.approval_request.emit(call)
        while not self._approval_event.wait(0.1):
            if self.cancel_event.is_set():
                return False
        return self._approval_result

    # ---------- ana dongu ----------

    def run(self) -> None:  # QThread giris noktasi
        try:
            self._dongu()
        except ApiError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # beklenmedik hata arayuzu cokertmesin
            self.failed.emit(f"Beklenmeyen hata: {exc}")
        finally:
            self.done.emit(self._yeni_mesajlar)

    def _dongu(self) -> None:
        sistem = build_system_prompt(self.cfg, self.workspace, self.memory, self.open_files)
        # sohbet kipinde arac dongusu yok, tek cevap verilir
        tur_limiti = 1 if self.cfg.kip == "chat" else max(1, self.cfg.max_iterations)

        for tur in range(1, tur_limiti + 1):
            if self.cancel_event.is_set():
                return

            self.step_started.emit(tur)
            istek = [{"role": "system", "content": sistem}] + self.messages + self._yeni_mesajlar

            ham = ""
            suzgec = StreamTagFilter()
            for parca in self.client.stream(
                istek,
                model=self.cfg.model,
                temperature=self.cfg.temperature,
                max_tokens=self.cfg.max_tokens,
                thinking=self.cfg.thinking,
                cancel=self.cancel_event,
            ):
                if self.cancel_event.is_set():
                    break
                if parca.usage:
                    self.usage_reported.emit(Kullanim.from_api(self.cfg.model, parca.usage))
                if parca.reasoning:
                    self.delta_reasoning.emit(parca.reasoning)
                if parca.content:
                    ham += parca.content
                    gorunur = suzgec.feed(parca.content)
                    if gorunur:
                        self.delta_content.emit(gorunur)

            kalan = suzgec.flush()
            if kalan:
                self.delta_content.emit(kalan)

            self._yeni_mesajlar.append({"role": "assistant", "content": ham})
            self.step_text_done.emit(tools.strip_tool_calls(ham))

            if self.cancel_event.is_set():
                return

            if self.cfg.kip == "chat":
                return

            cagrilar = tools.parse_tool_calls(ham)
            if not cagrilar:
                return  # is bitti

            sonuclar = self._araclari_calistir(cagrilar)
            if self.cancel_event.is_set():
                return

            self._yeni_mesajlar.append({"role": "user", "content": sonuclar})

        if self.cfg.kip == "chat":
            return

        # tur limiti doldu
        self.failed.emit(
            f"Islem {self.cfg.max_iterations} turda bitmedi ve durduruldu. "
            "Ayarlar'dan tur limitini artirabilirsin."
        )

    def _araclari_calistir(self, cagrilar: list[ToolCall]) -> str:
        bloklar: list[str] = ["[ARAC SONUCLARI]"]
        bellek_degisti = False

        for call in cagrilar:
            if self.cancel_event.is_set():
                break

            # plan modunda degistirici araclar calistirilmaz
            if self.cfg.mode == "plan" and call.needs_approval_kind is not None:
                call.approved = False
                call.ok = False
                call.output = (
                    "PLAN MODU: bu islem engellendi. Sadece plan cikar, "
                    "kullanici modu degistirince uygularsin."
                )
                self.tool_finished.emit(call)
                bloklar.append(f"### {call.kind}: {call.target}\nENGELLENDI (plan modu)")
                continue

            if not self._onay_iste(call):
                call.approved = False
                call.ok = False
                call.output = "Kullanici bu islemi reddetti."
                self.tool_finished.emit(call)
                bloklar.append(
                    f"### {call.kind}: {call.target}\nREDDEDILDI - kullanici izin vermedi. "
                    "Baska bir yol dene veya kullaniciya sor."
                )
                continue

            call.approved = True
            self.tool_started.emit(call)
            tools.execute(
                call,
                self.workspace,
                memory=self.memory if self.cfg.use_memory else None,
                timeout=self.cfg.command_timeout,
            )
            if call.kind == "memory" and call.ok:
                bellek_degisti = True
            self.tool_finished.emit(call)

            cikti = call.output or ""
            if len(cikti) > MAX_RESULT_CHARS:
                cikti = cikti[:MAX_RESULT_CHARS] + "\n... (sonuc kirpildi)"
            durum = "BASARILI" if call.ok else "HATA"
            bloklar.append(f"### {call.kind}: {call.target}\n{durum}\n{cikti}")

        if bellek_degisti:
            self.memory_changed.emit()

        bloklar.append(
            "Yukaridaki sonuclara gore ise devam et. Baska arac gerekmiyorsa "
            "kullaniciya kisa bir ozet yaz."
        )
        return "\n\n".join(bloklar)
