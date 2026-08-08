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
    ARA_MESAJ_BASLIGI, CEVAP_DILI, CHAT_KIPI_TALIMATI, DEVAM_DURTUSU,
    OTO_MODU_TALIMATI, PLAN_MODU_TALIMATI, PROMPT_KURALLARI_TALIMATI,
    SURDURME_TALIMATI,
)
from .i18n import t
from .memory import MemoryStore
from .tools import ToolCall, Workspace
from .usage import Kullanim

MAX_RESULT_CHARS = 14000

# Model arac cagirmadan ve <TASK_DONE> yazmadan durursa bu kadar kez durtulur.
# Sonrasinda dongu kapanir; yoksa iki taraf da bos bos konusup para yakar.
MAX_DURTU = 3

# Tur sayisi sinirsiz oldugu icin tek gercek tehlike, ilerlemeyen bir dongude
# takilip kalmak: ornegin FILE_EDIT'in ESKI blogu hic tutmuyor ve model ayni
# duzenlemeyi tekrar tekrar deniyor. Ayni basarisiz arac kumesi ust uste bu
# kadar tekrarlarsa dongu kesilir. Ilerleme oldugu surece sinir yoktur.
MAX_KISIR_TUR = 4

# Gecici API hatalarinda (429, 500, 503, kopan baglanti) tekrar deneme
YENIDEN_DENEME = 4
BEKLEME_SANIYE = [2, 5, 12, 25]

# TASK_DONE bir arac degil, dongu kontrolu. Govdesi olmadan da yazilabildigi
# icin "ac ve kapaniana kadar yut" mantigina sokulamaz: kapanis etiketi hic
# gelmezse cevabin geri kalani ekrana hic dusmezdi. Bunun yerine tek tek
# token olarak ayiklanir.
OPEN_TAGS = [f"<{ad}>" for ad in tools.TAG_NAMES if ad != "TASK_DONE"]
SESSIZ_TOKENLER = ["<TASK_DONE/>", "<TASK_DONE />", "<TASK_DONE>", "</TASK_DONE>"]

# Yarim gelmis bir etiketi beklerken tamponda tutulacak en fazla karakter
_EN_UZUN_ETIKET = max(len(t) for t in OPEN_TAGS + SESSIZ_TOKENLER) + 1


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

            # bitis bildirimi: sadece token atilir, metin akmaya devam eder
            sessiz = next((s for s in SESSIZ_TOKENLER if ust.startswith(s)), None)
            if sessiz:
                self.buf = self.buf[len(sessiz):]
                continue

            eslesen = next((t for t in OPEN_TAGS if ust.startswith(t)), None)
            if eslesen:
                self.buf = self.buf[len(eslesen):]
                self.inside = "</" + eslesen[1:]
                continue

            if len(self.buf) < _EN_UZUN_ETIKET and any(
                t.startswith(ust) for t in OPEN_TAGS + SESSIZ_TOKENLER
            ):
                return "".join(out)  # etiketin devami gelsin

            out.append(self.buf[0])
            self.buf = self.buf[1:]

    def flush(self) -> str:
        kalan = "" if self.inside else self.buf
        self.buf = ""
        self.inside = None
        return kalan


# Yedek metin izleri. Asil karar ApiError.gecici alanindan gelir; bu liste
# sadece o alani tasimayan (baska bir yerden gelen) hatalar icin kullanilir.
# Hata mesajlari arayuz diline cevrildigi icin metne bakmak tek basina yeterli
# degil: her iki dilin izleri de burada.
_GECICI_IZLER = (
    "429", "500", "502", "503", "504",
    "baglanti", "bağlantı", "connection",
    "zaman asimi", "zaman aşımı", "timeout", "timed out",
    "akis kesildi", "akış kesildi", "stream",
    "temporarily", "overload", "unavailable",
)
_KALICI_IZLER = ("401", "402", "403")


def _gecici_hata(exc: Exception) -> bool:
    """Beklemek fayda eder mi? Once yapisal alan, sonra metin izleri."""
    gecici = getattr(exc, "gecici", None)
    if gecici is not None:
        return bool(gecici)
    metin = str(exc).lower()
    if any(iz in metin for iz in _KALICI_IZLER):
        return False
    return any(iz in metin for iz in _GECICI_IZLER)


def build_system_prompt(
    cfg, workspace: Workspace, memory: MemoryStore | None, acik_dosyalar: list[str] | None = None
) -> str:
    parcalar = [cfg.system_prompt.strip()]

    # arayuz dili neyse cevap da o dilde olur
    parcalar.append(CEVAP_DILI.get(cfg.language, CEVAP_DILI["tr"]))

    # Chat kipi: arac protokolu ve proje baglami hic gonderilmez
    if cfg.kip == "chat":
        parcalar.append(CHAT_KIPI_TALIMATI.strip())
        if getattr(cfg, "use_prompt_rules", True):
            kalip = PROMPT_KURALLARI_TALIMATI.get(
                cfg.language, PROMPT_KURALLARI_TALIMATI["tr"]
            )
            parcalar.append(kalip.format(kurallar=cfg.etkin_prompt_kurallari).strip())
        bellek_metni = memory.as_prompt_block() if (memory and cfg.use_memory) else ""
        if bellek_metni:
            parcalar.append(bellek_metni)
        return "\n\n---\n\n".join(p for p in parcalar if p)

    if cfg.mode == "plan":
        parcalar.append(PLAN_MODU_TALIMATI.strip())
    elif cfg.mode == "oto":
        parcalar.append(OTO_MODU_TALIMATI.strip())

    # plan modunda zaten hicbir sey uygulanmaz, surdurme talimati anlamsiz olur
    if cfg.mode != "plan":
        parcalar.append(SURDURME_TALIMATI.strip())

    if getattr(cfg, "use_prompt_rules", True):
        kalip = PROMPT_KURALLARI_TALIMATI.get(
            cfg.language, PROMPT_KURALLARI_TALIMATI["tr"]
        )
        parcalar.append(kalip.format(kurallar=cfg.etkin_prompt_kurallari).strip())

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
    uyari = Signal(str)               # olumcul olmayan bilgi (yeniden deneme vb.)
    mesaj_alindi = Signal(str)        # calisirken eklenen mesaj isleme girdi
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

        # calisirken kullanicidan gelen ek mesajlar
        self._kilit = threading.Lock()
        self._bekleyen: list[str] = []
        self._kapandi = False

    # ---------- disaridan kontrol ----------

    def cancel(self) -> None:
        self.cancel_event.set()
        self._approval_result = False
        self._approval_event.set()

    def mesaj_ekle(self, metin: str) -> bool:
        """Ajan calisirken gelen mesaji sonraki tura ekler.

        Dongu kapandiysa False doner; o zaman arayuz mesaji kendi kuyruguna
        alip yeni bir kosu baslatir. Boylece hicbir mesaj kaybolmaz.
        """
        metin = (metin or "").strip()
        if not metin:
            return False
        with self._kilit:
            if self._kapandi:
                return False
            self._bekleyen.append(metin)
            return True

    def kalan_mesajlar(self) -> list[str]:
        """Dongu bittiginde islenmeden kalmis mesajlari verir."""
        with self._kilit:
            kalan, self._bekleyen = self._bekleyen, []
            return kalan

    def _bekleyenleri_isle(self) -> None:
        """Bekleyen kullanici mesajlarini bu turun baglamina katar."""
        with self._kilit:
            bekleyen, self._bekleyen = self._bekleyen, []
        for metin in bekleyen:
            self._yeni_mesajlar.append(
                {"role": "user", "content": f"{ARA_MESAJ_BASLIGI}\n{metin}"}
            )
            self.mesaj_alindi.emit(metin)

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
            self.failed.emit(f"{t('Beklenmeyen hata')}: {exc}")
        finally:
            with self._kilit:
                self._kapandi = True
            self.done.emit(self._yeni_mesajlar)

    # ---------- tek tur akisi ----------

    def _bir_tur(self, sistem: str) -> tuple[str, bool]:
        """Modelden bir cevap alir. (ham_metin, akis_tamamlandi) doner.

        Gecici bir API hatasi olur ve daha hic metin gelmediyse birkac kez
        yeniden denenir. Metnin ortasinda koptuysa tekrar denemek ayni metni
        iki kere yazdirir; o yuzden elde ne varsa onunla donulur ve dongu
        kaldigi yerden devam eder. "Bir anda kesiliyor" sorununun kaynagi
        buydu: tek bir gecici hata butun isi bitiriyordu.
        """
        istek = [{"role": "system", "content": sistem}] + self.messages + self._yeni_mesajlar

        for deneme in range(YENIDEN_DENEME):
            ham = ""
            suzgec = StreamTagFilter()
            try:
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
                        self.usage_reported.emit(
                            Kullanim.from_api(self.cfg.model, parca.usage)
                        )
                    if parca.reasoning:
                        self.delta_reasoning.emit(parca.reasoning)
                    if parca.content:
                        ham += parca.content
                        gorunur = suzgec.feed(parca.content)
                        if gorunur:
                            self.delta_content.emit(gorunur)
            except ApiError as exc:
                kalan = suzgec.flush()
                if kalan:
                    self.delta_content.emit(kalan)
                if ham.strip():
                    # yarim cevap geldi: tekrar denemek metni cogaltir
                    self.uyari.emit(
                        f"{t('Akış kesildi, kaldığı yerden devam ediliyor.')} ({exc})"
                    )
                    return ham, False
                if not _gecici_hata(exc) or deneme == YENIDEN_DENEME - 1:
                    raise
                sure = BEKLEME_SANIYE[min(deneme, len(BEKLEME_SANIYE) - 1)]
                self.uyari.emit(
                    f"{t('Bağlantı sorunu, tekrar deneniyor')} ({sure} sn) ({exc})"
                )
                if self.cancel_event.wait(sure):
                    return "", False
                continue

            kalan = suzgec.flush()
            if kalan:
                self.delta_content.emit(kalan)

            if not ham.strip() and not self.cancel_event.is_set():
                # model bos cevap dondu: bir kez daha sor
                if deneme < YENIDEN_DENEME - 1:
                    self.uyari.emit(t("Model boş cevap döndü, tekrar soruluyor."))
                    continue
            return ham, True

        return "", False

    # ---------- ana dongu ----------

    def _dongu(self) -> None:
        sistem = build_system_prompt(self.cfg, self.workspace, self.memory, self.open_files)

        if self.cfg.kip == "chat":
            self._sohbet_turu(sistem)
            return

        # 0 = sinirsiz. Kullanici Durdur demedigi surece is bitene kadar doner.
        limit = max(0, int(getattr(self.cfg, "max_iterations", 0) or 0))
        tur = 0
        durtu = 0
        onceki_imza: tuple | None = None
        kisir = 0

        while True:
            if self.cancel_event.is_set():
                return
            tur += 1
            if limit and tur > limit:
                self.failed.emit(
                    f"{t('İşlem belirlenen adım sayısında bitmedi ve durduruldu')} "
                    f"({limit}). "
                    + t("Sınırsız çalışması için Ayarlar'dan adım limitini 0 yap.")
                )
                return

            self.step_started.emit(tur)
            self._bekleyenleri_isle()

            ham, tamam = self._bir_tur(sistem)
            if self.cancel_event.is_set():
                return

            if not ham.strip():
                # bos cevabi gecmise yazmak her istekte tekrar gonderilen
                # anlamsiz bir tur birakiyor
                return

            self._yeni_mesajlar.append({"role": "assistant", "content": ham})
            self.step_text_done.emit(tools.strip_tool_calls(ham))

            cagrilar = tools.parse_tool_calls(ham)
            bitti = tools.gorev_bitti_mi(ham)

            if cagrilar:
                durtu = 0
                sonuclar = self._araclari_calistir(cagrilar)
                if self.cancel_event.is_set():
                    return
                self._yeni_mesajlar.append({"role": "user", "content": sonuclar})

                imza = tuple((c.kind, c.target, bool(c.ok)) for c in cagrilar)
                hepsi_basarisiz = all(not c.ok for c in cagrilar)
                if hepsi_basarisiz and imza == onceki_imza:
                    kisir += 1
                    if kisir >= MAX_KISIR_TUR:
                        self.failed.emit(t(
                            "Aynı işlem üst üste aynı hatayı verdi ve ilerleme "
                            "olmadı, döngü durduruldu. Araç kartındaki hataya "
                            "bakıp yeni bir yön ver."
                        ))
                        return
                else:
                    kisir = 0
                onceki_imza = imza
                continue

            if bitti or self.cfg.mode == "plan":
                return

            if not tamam:
                # akis yarida kesildi, araclar da yok: kaldigi yerden devam etsin
                durtu = 0
                self._yeni_mesajlar.append({
                    "role": "user",
                    "content": "Cevabin yarida kesildi. Kaldigin yerden devam et.",
                })
                continue

            # arac yok, bitis bildirimi yok: is ortada birakilmis olabilir
            durtu += 1
            if durtu > MAX_DURTU:
                return
            self._yeni_mesajlar.append({"role": "user", "content": DEVAM_DURTUSU})

    def _sohbet_turu(self, sistem: str) -> None:
        """Sohbet kipi: arac yok, tek cevap."""
        self.step_started.emit(1)
        ham, _ = self._bir_tur(sistem)
        if self.cancel_event.is_set() or not ham.strip():
            return
        self._yeni_mesajlar.append({"role": "assistant", "content": ham})
        self.step_text_done.emit(tools.strip_tool_calls(ham))

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
            "Yukaridaki sonuclara gore ise devam et. Bir sey hata verdiyse sebebini "
            "bul ve duzelt, pes etme. Is gercekten bittiyse kisa bir ozet yaz ve "
            "sonuna <TASK_DONE> ekle."
        )
        return "\n\n".join(bloklar)
