"""Sag taraftaki sohbet paneli: mod secimi, akis, arac kartlari, besteci."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from . import usage as usage_mod
from .agent import AgentWorker
from .config import KIPLER, MODLAR
from .icons import ikon
from .i18n import t
from .theme import C, GRADYAN, GRADYAN_HOVER
from .tools import ToolCall, Workspace
from .widgets import (
    ApprovalDialog, Badge, IconButton, MessageBubble, ReasoningBox, ToolCard,
)


class Composer(QPlainTextEdit):
    """Enter gonderir, Shift+Enter alt satira gecer, kutu icerige gore buyur."""

    gonder = Signal()
    dur = Signal()

    TABAN = 66
    TAVAN = 190
    DUGME = 30

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Composer")
        self.setPlaceholderText(t("LUBV'ye ne yapmasını istiyorsun?"))
        self.setToolTip(t("Enter gönderir, Shift+Enter alt satıra geçer"))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(self.TABAN)
        self.textChanged.connect(self._boy_ayarla)

        # gonder dugmesi kutunun icinde, sag altta durur
        self.dugme = QToolButton(self)
        self.dugme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.dugme.setFixedSize(self.DUGME, self.DUGME)
        self.dugme.setIconSize(QSize(16, 16))
        self.dugme.clicked.connect(self._dugmeye_basildi)
        self.calisiyor = False
        self.durumu_yaz(False)

    def _dugmeye_basildi(self) -> None:
        self.dur.emit() if self.calisiyor else self.gonder.emit()

    def durumu_yaz(self, calisiyor: bool) -> None:
        """Dugme calisirken 'durdur', bosken 'gonder' olur."""
        self.calisiyor = calisiyor
        if calisiyor:
            self.dugme.setIcon(ikon("dur", "#FFFFFF", 14))
            self.dugme.setToolTip(t("Durdur  (Esc)"))
            renk, hover = C["red"], "#FF6E6E"
        else:
            self.dugme.setIcon(ikon("gonder", "#06140A", 16))
            self.dugme.setToolTip(t("Gönder  (Enter)"))
            renk, hover = GRADYAN, GRADYAN_HOVER
        self.dugme.setStyleSheet(
            f"QToolButton{{background:{renk}; border:none; border-radius:{self.DUGME // 2}px;}}"
            f"QToolButton:hover{{background:{hover};}}"
            f"QToolButton:disabled{{background:{C['bg3']};}}"
        )

    def _boy_ayarla(self) -> None:
        satir = max(1, self.document().blockCount())
        yukseklik = satir * self.fontMetrics().lineSpacing() + 26
        self.setFixedHeight(max(self.TABAN, min(self.TAVAN, int(yukseklik))))
        self._dugmeyi_yerlestir()

    def _dugmeyi_yerlestir(self) -> None:
        bosluk = 8
        self.dugme.move(
            self.width() - self.DUGME - bosluk,
            self.height() - self.DUGME - bosluk,
        )

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._dugmeyi_yerlestir()
        # metin dugmenin altina girmesin
        self.setViewportMargins(0, 0, self.DUGME + 6, 0)

    def keyPressEvent(self, event):  # noqa: N802
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.gonder.emit()
            return
        super().keyPressEvent(event)


class KipSelector(QFrame):
    """Code / Chat: uygulamanin iki calisma bicimi."""

    degisti = Signal(str)

    def __init__(self, aktif: str = "code", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("KipSelector")
        self.setStyleSheet(
            f"QFrame#KipSelector{{background:{C['bg2']}; border:1px solid {C['line2']};"
            f"border-radius:8px;}}"
        )
        duzen = QHBoxLayout(self)
        duzen.setContentsMargins(2, 2, 2, 2)
        duzen.setSpacing(2)
        self.grup = QButtonGroup(self)
        self.grup.setExclusive(True)
        self.dugmeler: dict[str, QPushButton] = {}

        for anahtar, (ad, aciklama) in KIPLER.items():
            dugme = QPushButton(t(ad))
            dugme.setCheckable(True)
            dugme.setCursor(Qt.CursorShape.PointingHandCursor)
            dugme.setToolTip(t(aciklama))
            dugme.setFixedHeight(22)
            dugme.setStyleSheet(
                f"""
                QPushButton {{
                    background: transparent; border: none; border-radius: 6px;
                    padding: 1px 12px; font-size: 11.5px; font-weight: 700;
                    color: {C['muted']}; min-height: 14px;
                }}
                QPushButton:hover {{ color: {C['text2']}; }}
                QPushButton:checked {{ background: {GRADYAN}; color: #06140A; }}
                """
            )
            dugme.clicked.connect(lambda _=False, a=anahtar: self.degisti.emit(a))
            self.grup.addButton(dugme)
            self.dugmeler[anahtar] = dugme
            duzen.addWidget(dugme)

        self.dugmeler[aktif if aktif in self.dugmeler else "code"].setChecked(True)

    def ayarla(self, anahtar: str) -> None:
        if anahtar in self.dugmeler:
            self.dugmeler[anahtar].setChecked(True)


class ModeSelector(QFrame):
    """Plan / Onaylı / Otomatik secici (sadece Code kipinde gorunur)."""

    degisti = Signal(str)

    def __init__(self, aktif: str = "onay", parent=None) -> None:
        super().__init__(parent)
        duzen = QHBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(5)
        self.grup = QButtonGroup(self)
        self.grup.setExclusive(True)
        self.dugmeler: dict[str, QPushButton] = {}

        for anahtar, (ad, aciklama) in MODLAR.items():
            dugme = QPushButton(t(ad))
            dugme.setCheckable(True)
            dugme.setCursor(Qt.CursorShape.PointingHandCursor)
            dugme.setToolTip(t(aciklama))
            dugme.setFixedHeight(23)
            dugme.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            dugme.setStyleSheet(self._stil(anahtar))
            dugme.clicked.connect(lambda _=False, a=anahtar: self._sec(a))
            self.grup.addButton(dugme)
            self.dugmeler[anahtar] = dugme
            duzen.addWidget(dugme)

        self.dugmeler[aktif if aktif in self.dugmeler else "onay"].setChecked(True)

    @staticmethod
    def _stil(anahtar: str) -> str:
        vurgu, sonuk = {
            "plan": (C["cyan"], C["cyan_dim"]),        # notr: hicbir sey degismez
            "onay": (C["accent"], C["accent_dim"]),    # yesil: kontrollu ilerle
            "oto": (C["amber"], C["amber_dim"]),       # amber: dikkat, sormadan yapar
        }[anahtar]
        return f"""
        QPushButton {{
            background: transparent; border: 1px solid {C['line2']};
            border-radius: 7px; padding: 2px 10px; font-size: 11.5px;
            font-weight: 700; color: {C['muted']}; min-height: 16px;
        }}
        QPushButton:hover {{ color: {C['text2']}; border-color: {C['line3']}; }}
        QPushButton:checked {{
            background: {sonuk}; border-color: {vurgu}; color: {vurgu};
        }}
        """

    def _sec(self, anahtar: str) -> None:
        self.degisti.emit(anahtar)

    def ayarla(self, anahtar: str) -> None:
        if anahtar in self.dugmeler:
            self.dugmeler[anahtar].setChecked(True)


class ChatPanel(QFrame):
    """Sohbet + ajan dongusu."""

    durum = Signal(str)
    dosya_degisti = Signal(str)          # ajan bir dosyaya dokundu
    proje_degisti = Signal()             # agac tazelensin
    bellek_degisti = Signal()
    kullanim_degisti = Signal()
    calisma_durumu = Signal(bool)
    kip_degisti = Signal(str)

    def __init__(self, cfg, memory, checkpoints, usage_store, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.memory = memory
        self.checkpoints = checkpoints
        self.usage = usage_store

        self.gecmis: list[dict] = []
        self.worker: AgentWorker | None = None
        self.aktif_balon: MessageBubble | None = None
        self.aktif_dusunce: ReasoningBox | None = None
        self.arac_kartlari: dict[int, ToolCard] = {}
        self.baglam_dosyalari: list[str] = []

        self.setMinimumWidth(360)
        duzen = QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(0)

        duzen.addWidget(self._baslik_serit())
        duzen.addWidget(self._mod_serit())
        duzen.addWidget(self._akis(), 1)
        duzen.addWidget(self._besteci(), 0)

        self.yeni_sohbet(ilk=True)

    # ------------------------------------------------------------------
    # Arayuz parcalari
    # ------------------------------------------------------------------

    def _baslik_serit(self) -> QWidget:
        serit = QFrame()
        serit.setObjectName("TopBar")
        serit.setFixedHeight(38)
        d = QHBoxLayout(serit)
        d.setContentsMargins(10, 0, 6, 0)
        d.setSpacing(8)

        baslik = QLabel("LUBV")
        baslik.setObjectName("TopTitle")
        baslik.setStyleSheet(f"color:{C['violet']}; letter-spacing:1.2px;")

        self.kip_secici = KipSelector(self.cfg.kip)
        self.kip_secici.degisti.connect(self._kip_degisti)

        self.model_rozet = Badge(self._model_kisa(), "accent")
        self.model_rozet.setToolTip(t("Modeli Ayarlar panelinden değiştirebilirsin"))

        yeni = IconButton("arti", t("Yeni sohbet, geçmişi temizler"))
        yeni.clicked.connect(lambda: self.yeni_sohbet())

        d.addWidget(baslik)
        d.addSpacing(4)
        d.addWidget(self.kip_secici)
        d.addStretch(1)
        d.addWidget(self.model_rozet)
        d.addWidget(yeni)
        return serit

    def _mod_serit(self) -> QWidget:
        """Plan / Onaylı / Otomatik: kendi satirinda, esit genislikte."""
        self.mod_kutu = QFrame()
        self.mod_kutu.setObjectName("TopBar")
        self.mod_kutu.setFixedHeight(32)
        d = QHBoxLayout(self.mod_kutu)
        d.setContentsMargins(10, 0, 10, 0)
        d.setSpacing(0)

        self.mod_secici = ModeSelector(self.cfg.mode)
        self.mod_secici.degisti.connect(self._mod_degisti)
        d.addWidget(self.mod_secici)

        self.mod_kutu.setVisible(self.cfg.kip == "code")
        return self.mod_kutu

    def _akis(self) -> QWidget:
        self.kaydirma = QScrollArea()
        self.kaydirma.setWidgetResizable(True)
        self.kaydirma.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.kaydirma.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.govde = QWidget()
        self.govde.setObjectName("ChatBody")
        self.akis = QVBoxLayout(self.govde)
        self.akis.setContentsMargins(12, 10, 12, 10)
        self.akis.setSpacing(6)
        # bastaki esneme mesajlari alta yaslar: bos alan altta degil ustte kalir
        self.akis.addStretch(1)

        self.kaydirma.setWidget(self.govde)
        return self.kaydirma

    def _yaslamayi_ac(self) -> None:
        """Basa esneme koyar (mesajlar alta yaslanir)."""
        if self.akis.count() == 0 or self.akis.itemAt(0).widget() is not None:
            self.akis.insertStretch(0, 1)

    def _yaslamayi_kapat(self) -> None:
        """Bos durum ekrani ortada dursun diye esnemeyi kaldirir."""
        if self.akis.count() and self.akis.itemAt(0).widget() is None:
            self.akis.takeAt(0)

    def _besteci(self) -> QWidget:
        kutu = QFrame()
        kutu.setObjectName("BottomBar")
        kutu.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        d = QVBoxLayout(kutu)
        d.setContentsMargins(10, 8, 10, 8)
        d.setSpacing(6)

        self.baglam_serit = QFrame()
        self.baglam_duzen = QHBoxLayout(self.baglam_serit)
        self.baglam_duzen.setContentsMargins(0, 0, 0, 0)
        self.baglam_duzen.setSpacing(5)
        self.baglam_serit.setVisible(False)

        self.giris = Composer()
        self.giris.gonder.connect(self.gonder)
        self.giris.dur.connect(self.durdur)

        # calisirken beliren ince durum satiri
        self.durum_etiketi = QLabel("")
        self.durum_etiketi.setObjectName("StatusText")
        self.durum_etiketi.setVisible(False)

        d.addWidget(self.baglam_serit)
        d.addWidget(self.durum_etiketi)
        d.addWidget(self.giris)
        return kutu

    # ------------------------------------------------------------------
    # Akisa ekleme
    # ------------------------------------------------------------------

    def _ekle(self, widget: QWidget) -> None:
        self._bos_durumu_kaldir()
        self._yaslamayi_ac()
        self.akis.addWidget(widget)
        QTimer.singleShot(30, self._en_alta)

    def _en_alta(self) -> None:
        cubuk = self.kaydirma.verticalScrollBar()
        cubuk.setValue(cubuk.maximum())

    def _sistem_notu(self, metin: str, tone: str = "") -> None:
        kutu = QFrame()
        kutu.setObjectName("SystemBubble")
        d = QHBoxLayout(kutu)
        d.setContentsMargins(12, 8, 12, 8)
        etiket = QLabel(metin)
        etiket.setWordWrap(True)
        etiket.setStyleSheet(
            f"color:{C['red'] if tone == 'red' else C['muted']}; font-size:12.5px;"
        )
        d.addWidget(etiket)
        self._ekle(kutu)

    def temizle_akis(self) -> None:
        self.bos_kutu = None
        while self.akis.count():
            item = self.akis.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def yeni_sohbet(self, ilk: bool = False) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.durdur()
        self.gecmis = []
        self.arac_kartlari = {}
        self.aktif_balon = None
        self.aktif_dusunce = None
        self.temizle_akis()
        self._bos_durum()
        if not ilk:
            self.durum.emit(t("Yeni sohbet başladı."))

    def _bos_durum(self) -> None:
        """Sohbet bosken ortada duran sade karsilama."""
        self.bos_kutu = QWidget()
        d = QVBoxLayout(self.bos_kutu)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(4)
        d.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ad = QLabel("LUBV")
        ad.setStyleSheet(
            f"color:{C['violet']}; font-size:22px; font-weight:800; letter-spacing:4px;"
        )
        ad.setAlignment(Qt.AlignmentFlag.AlignCenter)

        alt = QLabel(
            t("Ne yapmamı istiyorsan aşağıya yaz")
            if self.cfg.kip == "code"
            else t("Ne konuşmak istersin?")
        )
        alt.setObjectName("EmptyState")
        alt.setAlignment(Qt.AlignmentFlag.AlignCenter)

        d.addStretch(1)
        d.addWidget(ad)
        d.addWidget(alt)
        d.addStretch(1)
        self._yaslamayi_kapat()
        self.akis.addWidget(self.bos_kutu, 1)

    def _bos_durumu_kaldir(self) -> None:
        kutu = getattr(self, "bos_kutu", None)
        if kutu is not None:
            kutu.setParent(None)
            kutu.deleteLater()
            self.bos_kutu = None

    # ------------------------------------------------------------------
    # Baglam dosyalari
    # ------------------------------------------------------------------

    def baglam_ekle(self, yol: str) -> None:
        if yol in self.baglam_dosyalari:
            return
        self.baglam_dosyalari.append(yol)
        self._baglam_ciz()
        self.durum.emit(t("Bağlama eklendi: ") + Path(yol).name)

    def _baglam_ciz(self) -> None:
        while self.baglam_duzen.count():
            item = self.baglam_duzen.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.baglam_dosyalari:
            self.baglam_serit.setVisible(False)
            return

        self.baglam_serit.setVisible(True)
        for yol in self.baglam_dosyalari:
            cip = QPushButton(Path(yol).name)
            cip.setIcon(ikon("atac", C["muted"], 12))
            cip.setToolTip(f"{yol}\nKaldırmak için tıkla")
            cip.setStyleSheet(
                f"QPushButton{{background:{C['bg3']}; border:1px solid {C['line2']};"
                f"border-radius:7px; padding:2px 8px; font-size:11px;"
                f"color:{C['text2']}; min-height:14px;}}"
                f"QPushButton:hover{{color:{C['red']}; border-color:{C['red']};}}"
            )
            cip.clicked.connect(lambda _=False, y=yol: self._baglam_kaldir(y))
            self.baglam_duzen.addWidget(cip)
        self.baglam_duzen.addStretch(1)

    def _baglam_kaldir(self, yol: str) -> None:
        if yol in self.baglam_dosyalari:
            self.baglam_dosyalari.remove(yol)
            self._baglam_ciz()

    def _baglam_metni(self) -> str:
        if not self.baglam_dosyalari:
            return ""
        alan = Workspace(self.cfg.project_root)
        parcalar = ["[KULLANICININ EKLEDIGI DOSYALAR]"]
        for yol in self.baglam_dosyalari:
            try:
                icerik = Path(yol).read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                icerik = f"(okunamadi: {exc})"
            if len(icerik) > 20000:
                icerik = icerik[:20000] + "\n... (kirpildi)"
            parcalar.append(f"--- {alan.rel(Path(yol))} ---\n{icerik}")
        return "\n\n".join(parcalar) + "\n\n"

    # ------------------------------------------------------------------
    # Gonderme
    # ------------------------------------------------------------------

    def _kip_degisti(self, anahtar: str) -> None:
        self.cfg.kip = anahtar
        self.cfg.save()
        self.mod_kutu.setVisible(anahtar == "code")
        ad, aciklama = KIPLER[anahtar]
        self.durum.emit(f"{t(ad)}: {t(aciklama)}")
        self.giris.setPlaceholderText(
            t("LUBV'ye ne yapmasını istiyorsun?") if anahtar == "code"
            else t("Ne konuşmak istersin?")
        )
        self.kip_degisti.emit(anahtar)

    def _mod_degisti(self, anahtar: str) -> None:
        self.cfg.mode = anahtar
        self.cfg.save()
        ad, aciklama = MODLAR[anahtar]
        self.durum.emit(f"{t(ad)}{t(' modu')}: {t(aciklama)}")

    def _model_kisa(self) -> str:
        return self.cfg.model.replace("deepseek-", "").upper()

    def model_rozetini_tazele(self) -> None:
        self.model_rozet.setText(self._model_kisa())

    def gonder(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        metin = self.giris.toPlainText().strip()
        if not metin:
            return

        # sohbet kipinde proje klasoru sart degil, sadece anahtar yeter
        if self.cfg.kip == "chat":
            if not self.cfg.api_key.strip():
                self._sistem_notu(
                    t("API anahtarı girilmemiş. Ayarlar panelinden ekle."), "red"
                )
                return
        else:
            hazir, sebep = self.cfg.is_ready()
            if not hazir:
                self._sistem_notu(sebep, "red")
                return

        self.giris.clear()
        self._ekle(MessageBubble("user", metin))

        tam_mesaj = self._baglam_metni() + metin
        self.baglam_dosyalari = []
        self._baglam_ciz()

        self.gecmis.append({"role": "user", "content": tam_mesaj})
        self._gecmisi_kirp()
        self._calistir()

    def _gecmisi_kirp(self) -> None:
        limit = max(6, self.cfg.history_limit)
        if len(self.gecmis) > limit:
            self.gecmis = self.gecmis[-limit:]

    def _calistir(self) -> None:
        self.aktif_balon = None
        self.aktif_dusunce = None
        self.arac_kartlari = {}

        acik = []
        pencere = self.window()
        if hasattr(pencere, "sekmeler"):
            alan = Workspace(self.cfg.project_root)
            acik = [alan.rel(Path(y)) for y in pencere.sekmeler.acik_yollar()]

        self.worker = AgentWorker(
            self.cfg, self.gecmis, self.memory,
            checkpoints=self.checkpoints, open_files=acik,
        )
        self.worker.delta_content.connect(self._metin_geldi)
        self.worker.delta_reasoning.connect(self._dusunce_geldi)
        self.worker.step_started.connect(self._tur_basladi)
        self.worker.tool_started.connect(self._arac_basladi)
        self.worker.tool_finished.connect(self._arac_bitti)
        self.worker.approval_request.connect(self._onay_sor)
        self.worker.usage_reported.connect(self._kullanim_geldi)
        self.worker.memory_changed.connect(self.bellek_degisti.emit)
        self.worker.failed.connect(self._hata)
        self.worker.done.connect(self._bitti)

        self._mesgul(True)
        self.worker.start()

    def durdur(self) -> None:
        if self.worker is not None:
            self.worker.cancel()
            self.durum_etiketi.setText("durduruluyor…")

    def _mesgul(self, calisiyor: bool) -> None:
        self.giris.durumu_yaz(calisiyor)
        self.durum_etiketi.setVisible(calisiyor)
        self.calisma_durumu.emit(calisiyor)
        if not calisiyor:
            self.durum_etiketi.setText("")

    # ------------------------------------------------------------------
    # Worker sinyalleri
    # ------------------------------------------------------------------

    def _tur_basladi(self, tur: int) -> None:
        self.aktif_balon = None
        self.aktif_dusunce = None
        if self.cfg.kip == "chat":
            self.durum_etiketi.setText(t("yanıtlıyor"))
        else:
            self.durum_etiketi.setText(
                t("adım ") + str(tur) + "  ·  "
                + t(MODLAR[self.cfg.mode][0]).lower() + t(" modu")
            )

    def _balon_hazirla(self) -> MessageBubble:
        if self.aktif_balon is None:
            self.aktif_balon = MessageBubble("assistant", "")
            self._ekle(self.aktif_balon)
        return self.aktif_balon

    def _metin_geldi(self, parca: str) -> None:
        self._balon_hazirla().append(parca)
        self._en_alta()

    def _dusunce_geldi(self, parca: str) -> None:
        if not self.cfg.show_reasoning:
            return
        if self.aktif_dusunce is None:
            self.aktif_dusunce = ReasoningBox()
            self._ekle(self.aktif_dusunce)
        self.aktif_dusunce.append(parca)

    def _arac_basladi(self, call: ToolCall) -> None:
        if self.aktif_dusunce is not None:
            self.aktif_dusunce.bitir()
            self.aktif_dusunce = None
        if self.aktif_balon is not None and self.aktif_balon.bos_mu():
            self.aktif_balon.setVisible(False)
        self.aktif_balon = None

        kart = ToolCard(call)
        self.arac_kartlari[id(call)] = kart
        self._ekle(kart)
        self.durum_etiketi.setText(f"{call.label.lower()}: {call.target[:40]}")

    def _arac_bitti(self, call: ToolCall) -> None:
        kart = self.arac_kartlari.get(id(call))
        if kart is None:
            kart = ToolCard(call)
            self._ekle(kart)
        kart.tamamla(call)

        if call.touches_file and call.ok:
            self.dosya_degisti.emit(call.target)
            self.proje_degisti.emit()
        if call.kind == "memory" and call.ok:
            self.bellek_degisti.emit()

    def _onay_sor(self, call: ToolCall) -> None:
        eski = ""
        if call.kind in ("write", "delete"):
            try:
                alan = Workspace(self.cfg.project_root)
                eski = alan.raw_text(call.target)
            except Exception:
                eski = ""

        diyalog = ApprovalDialog(call, eski, parent=self.window())
        sonuc = diyalog.exec()

        if sonuc == ApprovalDialog.HEP_ONAYLA:
            tur = call.needs_approval_kind
            alan_adi = {
                "write": "auto_approve_write",
                "delete": "auto_approve_delete",
                "command": "auto_approve_command",
            }.get(tur or "")
            if alan_adi:
                setattr(self.cfg, alan_adi, True)
                self.cfg.save()
                self.durum.emit(t("Bu tür işlemler artık sorulmadan yapılacak."))
            onay = True
        else:
            onay = sonuc == ApprovalDialog.DialogCode.Accepted

        if self.worker is not None:
            self.worker.resolve_approval(onay)

    def _kullanim_geldi(self, kullanim) -> None:
        self.usage.ekle(kullanim)
        self.kullanim_degisti.emit()
        self.durum_etiketi.setText(
            f"{usage_mod.token_kisa(kullanim.girdi + kullanim.cikti)} token · "
            f"{usage_mod.para(kullanim.maliyet)}"
        )

    def _hata(self, mesaj: str) -> None:
        self._sistem_notu(mesaj, "red")

    def _bitti(self, yeni_mesajlar: list) -> None:
        if self.aktif_dusunce is not None:
            self.aktif_dusunce.bitir()
        if self.aktif_balon is not None and self.aktif_balon.bos_mu():
            self.aktif_balon.setVisible(False)

        self.gecmis.extend(yeni_mesajlar)
        self._gecmisi_kirp()
        self._mesgul(False)
        self.worker = None
        self.proje_degisti.emit()
        QTimer.singleShot(60, self._en_alta)

    # ------------------------------------------------------------------

    def kapaniyor(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(2500)
