"""Ana pencere: sol rail + yan panel + kod editoru + terminal + sag sohbet."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QSplitter, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from . import usage as usage_mod
from .api import ApiError, DeepSeekClient
from .balance import BalanceWatcher
from .checkpoints import CheckpointStore
from .chat import ChatPanel
from .config import APP_NAME, APP_VERSION, MODLAR, Config
from .editor import EditorTabs, WelcomeView
from .icons import ikon
from .memory import MemoryStore
from .panels import (
    BrainPanel, CheckpointPanel, ExplorerPanel, MemoryPanel, SessionPanel,
    SettingsPanel,
)
from .sessions import SessionStore
from .terminal import GitPanel, Terminal
from .i18n import t
from .theme import C, qss
from .widgets import Badge, BalanceBadge

# Ipuclari t() ile modul yuklenirken cevrilirse dil ayari daha okunmadigi icin
# Ingilizce arayuzde bile Turkce kaliyordu. Anahtarlar burada, ceviri kullanim
# aninda yapiliyor.
RAIL = [
    ("dosyalar", "Dosyalar"),
    ("oturum", "Oturumlar, geçmiş sohbetler"),
    ("git", "Kaynak kontrol ve GitHub"),
    ("bellek", "Bellek"),
    ("beyin", "Beyin, sistem prompt"),
    ("geri", "Geri al"),
    ("ayarlar", "Ayarlar ve harcama"),
]


class MainWindow(QMainWindow):
    def __init__(self, cfg: Config) -> None:
        super().__init__()
        self.cfg = cfg
        self.memory = MemoryStore(cfg.project_root)
        self.checkpoints = CheckpointStore(cfg.project_root)
        self.usage = usage_mod.UsageStore()
        self.sessions = SessionStore()
        self.yeniden_baslat = False

        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1024, 640)
        self.setStyleSheet(qss())

        self._arayuzu_kur()
        self._kisayollar()
        self._pencereyi_yerlestir()
        self._bakiyeyi_baslat()

        if cfg.project_root and Path(cfg.project_root).is_dir():
            self.projeyi_ac(cfg.project_root, kaydet=False)
        else:
            QTimer.singleShot(350, self.klasor_sec)

        self._son_oturumu_geri_yukle()
        QTimer.singleShot(800, self._modelleri_cek)

    def _son_oturumu_geri_yukle(self) -> None:
        """Uygulama kapanmadan once acik olan sohbeti geri getirir."""
        kimlik = (self.cfg.last_session_id or "").strip()
        if not kimlik:
            return
        kayit = self.sessions.yukle(kimlik)
        if kayit is None or kayit.bos_mu:
            return
        # baska bir projenin sohbetiyle acilip kafa karistirmasin
        if kayit.proje and self.cfg.project_root:
            if Path(kayit.proje) != Path(self.cfg.project_root):
                return
        self._oturum_ac(kimlik)

    # ------------------------------------------------------------------
    # Arayuz
    # ------------------------------------------------------------------

    def _pencereyi_yerlestir(self) -> None:
        """Pencereyi ekrana sigdirir, panelleri oranli boler, ortalar.

        Kullanici daha once pencereyi boyutlandirdiysa o duzen geri yuklenir;
        ilk acilista asagidaki oranli yerlesim kullanilir.
        """
        if self._duzeni_geri_yukle():
            return

        ekran = QApplication.primaryScreen()
        alan = ekran.availableGeometry() if ekran else None
        if alan is None:
            self.resize(1440, 880)
            return

        genislik = min(1680, int(alan.width() * 0.94))
        yukseklik = min(1000, int(alan.height() * 0.94))
        self.resize(genislik, yukseklik)
        self.move(
            alan.left() + (alan.width() - genislik) // 2,
            alan.top() + (alan.height() - yukseklik) // 2,
        )

        # yatay: yan panel sabit dar, sohbet orta, editor kalani alir
        kullanilabilir = genislik - 46
        yan = max(230, min(300, int(kullanilabilir * 0.19)))
        sohbet = max(340, min(440, int(kullanilabilir * 0.27)))
        self.bolucu.setSizes([yan, kullanilabilir - yan - sohbet, sohbet])

        # dikey: terminal alt seritte kalsin
        terminal = max(150, min(220, int(yukseklik * 0.22)))
        self.merkez_bolucu.setSizes([yukseklik - terminal, terminal])

    # ---------- pencere duzeninin kaliciligi ----------

    def _duzeni_geri_yukle(self) -> bool:
        """Kayitli pencere boyutu ve bolucu konumlarini uygular.

        Ekran duzeni degismis olabilir (monitor cikarilmis, cozunurluk
        dusmus): geri yuklenen pencere gorunur alanin disinda kalirsa kayit
        yok sayilir, yoksa uygulama ekran disinda aciliyor.
        """
        ham = (self.cfg.window_geometry or "").strip()
        if not ham:
            return False
        try:
            veri = QByteArray.fromBase64(ham.encode("ascii"))
            if not self.restoreGeometry(veri):
                return False
        except Exception:
            return False

        ekran = QApplication.primaryScreen()
        alan = ekran.availableGeometry() if ekran else None
        if alan is not None and not alan.intersects(self.frameGeometry()):
            return False   # eski konum artik ekranda degil, varsayilana don

        bolucu = (self.cfg.splitter_state or "").strip()
        if bolucu:
            try:
                yatay, _, dikey = bolucu.partition("|")
                if yatay:
                    self.bolucu.restoreState(QByteArray.fromBase64(yatay.encode("ascii")))
                if dikey:
                    self.merkez_bolucu.restoreState(
                        QByteArray.fromBase64(dikey.encode("ascii"))
                    )
            except Exception:
                pass
        return True

    def _duzeni_kaydet(self) -> None:
        try:
            self.cfg.window_geometry = bytes(self.saveGeometry().toBase64()).decode("ascii")
            self.cfg.splitter_state = "|".join((
                bytes(self.bolucu.saveState().toBase64()).decode("ascii"),
                bytes(self.merkez_bolucu.saveState().toBase64()).decode("ascii"),
            ))
        except Exception:
            pass

    def _arayuzu_kur(self) -> None:
        kok = QWidget()
        kok.setObjectName("Root")
        self.setCentralWidget(kok)

        dikey = QVBoxLayout(kok)
        dikey.setContentsMargins(0, 0, 0, 0)
        dikey.setSpacing(0)
        dikey.addWidget(self._ust_serit())

        govde = QHBoxLayout()
        govde.setContentsMargins(0, 0, 0, 0)
        govde.setSpacing(0)

        govde.addWidget(self._rail())

        self.bolucu = QSplitter(Qt.Orientation.Horizontal)
        self.bolucu.setChildrenCollapsible(False)
        self.bolucu.setHandleWidth(1)

        self.yan_panel = self._yan_panel()
        self.merkez = self._merkez()
        self.sohbet = ChatPanel(
            self.cfg, self.memory, self.checkpoints, self.usage,
            sessions=self.sessions, parent=self,
        )
        self._sohbeti_bagla()

        self.bolucu.addWidget(self.yan_panel)
        self.bolucu.addWidget(self.merkez)
        self.bolucu.addWidget(self.sohbet)
        self.bolucu.setStretchFactor(0, 0)
        self.bolucu.setStretchFactor(1, 1)
        self.bolucu.setStretchFactor(2, 0)

        govde.addWidget(self.bolucu, 1)
        dikey.addLayout(govde, 1)
        dikey.addWidget(self._durum_serit())

    def _ust_serit(self) -> QWidget:
        """Pencerenin en ustunde duran serit: proje, bakiye, oturum harcamasi.

        Bakiye burada surekli gorunur ve arka planda kendiliginden yenilenir;
        kalan kredi icin hicbir panele girmek gerekmez.
        """
        serit = QFrame()
        serit.setObjectName("HeaderBar")
        serit.setFixedHeight(34)
        d = QHBoxLayout(serit)
        d.setContentsMargins(12, 0, 10, 0)
        d.setSpacing(8)

        marka = QLabel(APP_NAME)
        marka.setObjectName("TopTitle")
        marka.setStyleSheet(f"color:{C['accent']}; letter-spacing:0.6px;")

        self.ust_proje = QLabel("")
        self.ust_proje.setObjectName("TopPath")

        self.ust_kip = Badge("", "accent")
        self.ust_kip.setToolTip(t("Çalışma kipi"))

        self.ust_oturum_maliyet = QLabel("")
        self.ust_oturum_maliyet.setObjectName("StatusText")
        self.ust_oturum_maliyet.setToolTip(t("Bu oturumda harcanan"))

        self.bakiye_rozet = BalanceBadge()
        self.bakiye_rozet.yenile_istendi.connect(self.bakiyeyi_yenile)
        self.bakiye_rozet.setVisible(bool(self.cfg.show_balance))

        d.addWidget(marka)
        d.addWidget(self.ust_proje, 1)
        d.addWidget(self.ust_kip)
        d.addWidget(self.ust_oturum_maliyet)
        d.addWidget(self.bakiye_rozet)
        return serit

    # ------------------------------------------------------------------
    # Bakiye
    # ------------------------------------------------------------------

    def _bakiyeyi_baslat(self) -> None:
        # Bilerek parent verilmiyor: ag istegi sirasinda pencere kapanirsa Qt
        # cocuk QThread'i hala calisirken yok ediyor ve uygulama abort ediyordu.
        # Referansi Python tarafinda tutuyoruz, sahipligi Qt'ye vermiyoruz.
        self.bakiye_izleyici = BalanceWatcher(self.cfg)
        self.bakiye_izleyici.guncellendi.connect(self._bakiye_geldi)
        self.bakiye_izleyici.start()

    def bakiyeyi_yenile(self) -> None:
        izleyici = getattr(self, "bakiye_izleyici", None)
        if izleyici is not None:
            izleyici.hemen_yenile()

    def _bakiye_geldi(self, bakiye) -> None:
        self.bakiye_rozet.durum_yaz(bakiye)
        if hasattr(self, "ayar_panel"):
            self.ayar_panel.bakiyeyi_yaz(bakiye)

    def _rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("Rail")
        rail.setFixedWidth(46)
        d = QVBoxLayout(rail)
        d.setContentsMargins(0, 6, 0, 6)
        d.setSpacing(2)

        self.rail_dugmeleri: dict[str, QToolButton] = {}
        for anahtar, ipucu in RAIL:
            dugme = QToolButton()
            dugme.setObjectName("RailButton")
            dugme.setToolTip(t(ipucu))
            dugme.setCheckable(True)
            dugme.setCursor(Qt.CursorShape.PointingHandCursor)
            dugme.setFixedSize(QSize(46, 40))
            dugme.setIconSize(QSize(20, 20))
            dugme.setIcon(ikon(anahtar, C["muted"], 20))
            dugme.clicked.connect(lambda _=False, a=anahtar: self.panel_sec(a))
            self.rail_dugmeleri[anahtar] = dugme
            d.addWidget(dugme)
            if anahtar == "geri":
                d.addStretch(1)

        self._rail_ikonlari_boya("dosyalar")
        self.rail_dugmeleri["dosyalar"].setChecked(True)
        return rail

    def _rail_ikonlari_boya(self, aktif: str) -> None:
        for anahtar, dugme in self.rail_dugmeleri.items():
            secili = dugme.isChecked() if anahtar != aktif else True
            if anahtar != aktif:
                secili = False
            dugme.setIcon(ikon(anahtar, C["accent"] if secili else C["muted"], 20))

    def _yan_panel(self) -> QWidget:
        sarmal = QFrame()
        sarmal.setObjectName("SidePanel")
        sarmal.setMinimumWidth(240)
        sarmal.setMaximumWidth(560)
        d = QVBoxLayout(sarmal)
        d.setContentsMargins(0, 0, 0, 0)

        self.panel_yigin = QStackedWidget()

        self.gezgin = ExplorerPanel()
        self.gezgin.dosya_ac.connect(self.dosya_ac)
        self.gezgin.klasor_degistir.connect(self.klasor_sec)
        self.gezgin.baglama_ekle.connect(lambda y: self.sohbet.baglam_ekle(y))

        self.oturum_panel = SessionPanel(self.sessions)
        self.oturum_panel.oturum_secildi.connect(self._oturum_ac)
        self.oturum_panel.yeni_istendi.connect(lambda: self.sohbet.yeni_sohbet())
        self.oturum_panel.bildirim.connect(self.durum_yaz)

        self.git_panel = GitPanel()
        self.git_panel.komut_istendi.connect(self._terminalde_calistir)

        self.bellek_panel = MemoryPanel(self.memory)
        self.bellek_panel.degisti.connect(lambda: self.durum_yaz(t("Bellek güncellendi.")))

        self.beyin_panel = BrainPanel(self.cfg)
        self.beyin_panel.kaydedildi.connect(self.durum_yaz)

        self.geri_panel = CheckpointPanel(self.checkpoints, self.cfg)
        self.geri_panel.geri_alindi.connect(self._geri_alindi)

        self.ayar_panel = SettingsPanel(self.cfg, self.usage)
        self.ayar_panel.bildirim.connect(self.durum_yaz)
        self.ayar_panel.baglanti_test.connect(self.baglantiyi_test_et)
        self.ayar_panel.degisti.connect(self._ayarlar_degisti)
        self.ayar_panel.dil_degisti.connect(self._dili_degistir)

        # sira RAIL ile birebir ayni olmali, panel_sec indekse gore secer
        for widget in (
            self.gezgin, self.oturum_panel, self.git_panel, self.bellek_panel,
            self.beyin_panel, self.geri_panel, self.ayar_panel,
        ):
            self.panel_yigin.addWidget(widget)

        d.addWidget(self.panel_yigin)
        return sarmal

    def _merkez(self) -> QWidget:
        self.merkez_bolucu = QSplitter(Qt.Orientation.Vertical)
        self.merkez_bolucu.setHandleWidth(1)
        self.merkez_bolucu.setChildrenCollapsible(False)

        self.editor_yigin = QStackedWidget()
        self.karsilama = WelcomeView()
        self.sekmeler = EditorTabs(font_size=self.cfg.editor_font_size)
        self.sekmeler.durum_degisti.connect(self._editor_durumu)
        self.sekmeler.dosya_kaydedildi.connect(
            lambda y: self.durum_yaz(t("Kaydedildi: ") + Path(y).name)
        )
        self.editor_yigin.addWidget(self.karsilama)
        self.editor_yigin.addWidget(self.sekmeler)

        self.terminal = Terminal()
        self.terminal.setMinimumHeight(120)

        self.merkez_bolucu.addWidget(self.editor_yigin)
        self.merkez_bolucu.addWidget(self.terminal)
        self.merkez_bolucu.setStretchFactor(0, 1)
        self.merkez_bolucu.setStretchFactor(1, 0)
        return self.merkez_bolucu

    def _durum_serit(self) -> QWidget:
        serit = QFrame()
        serit.setObjectName("StatusBar")
        serit.setFixedHeight(24)
        d = QHBoxLayout(serit)
        d.setContentsMargins(10, 0, 10, 0)
        d.setSpacing(14)

        def ayrac() -> QLabel:
            etiket = QLabel("│")
            etiket.setStyleSheet(f"color:{C['line2']}; font-size:10px;")
            return etiket

        self.durum_proje = QLabel(t("proje seçilmedi"))
        self.durum_proje.setObjectName("StatusStrong")
        self.durum_mesaj = QLabel("")
        self.durum_mesaj.setObjectName("StatusText")
        self.durum_imlec = QLabel("")
        self.durum_imlec.setObjectName("StatusText")
        self.durum_maliyet = QLabel("")
        self.durum_maliyet.setObjectName("StatusText")
        self.durum_model = QLabel("")
        self.durum_model.setObjectName("StatusText")

        d.addWidget(self.durum_proje)
        d.addWidget(self.durum_mesaj, 1)
        d.addWidget(self.durum_imlec)
        d.addWidget(ayrac())
        d.addWidget(self.durum_maliyet)
        d.addWidget(ayrac())
        d.addWidget(self.durum_model)
        self._durum_tazele()
        return serit

    def _sohbeti_bagla(self) -> None:
        self.sohbet.durum.connect(self.durum_yaz)
        self.sohbet.dosya_degisti.connect(self._ajan_dosyaya_dokundu)
        self.sohbet.proje_degisti.connect(self._proje_tazele)
        self.sohbet.bellek_degisti.connect(self.bellek_panel_tazele)
        self.sohbet.kullanim_degisti.connect(self._durum_tazele)
        self.sohbet.komut_calisti.connect(self._ajan_komutu)
        self.sohbet.oturum_degisti.connect(self.oturum_panel.tazele)
        self.sohbet.kip_degisti.connect(lambda _: self._durum_tazele())
        # istek biter bitmez bakiye tazelensin, harcama aninda gorunsun
        self.sohbet.calisma_durumu.connect(self._calisma_durumu)

    def _kisayollar(self) -> None:
        def kisayol(dizi: str, islev) -> None:
            QShortcut(QKeySequence(dizi), self, activated=islev)

        kisayol("Ctrl+S", self.sekmeler.aktifi_kaydet)
        kisayol("Ctrl+Shift+S", lambda: self.durum_yaz(
            f"{self.sekmeler.hepsini_kaydet()}" + t(" dosya kaydedildi.")
        ))
        kisayol("Ctrl+B", self.yan_paneli_degistir)
        kisayol("Ctrl+`", self.terminali_degistir)
        kisayol("Ctrl+J", self.terminali_degistir)
        kisayol("Ctrl+O", self.klasor_sec)
        kisayol("Ctrl+N", lambda: self.sohbet.yeni_sohbet())
        kisayol("Ctrl+L", lambda: self.sohbet.giris.setFocus())
        kisayol("Ctrl+W", lambda: self.sekmeler.sekme_kapat(self.sekmeler.currentIndex()))
        kisayol("F5", self._proje_tazele)
        kisayol("Escape", self.sohbet.durdur)

    # ------------------------------------------------------------------
    # Panel yonetimi
    # ------------------------------------------------------------------

    def panel_sec(self, anahtar: str) -> None:
        sira = [a for a, _ in RAIL]
        indeks = sira.index(anahtar)

        if self.yan_panel.isVisible() and self.panel_yigin.currentIndex() == indeks:
            self.yan_panel.setVisible(False)
            self.rail_dugmeleri[anahtar].setChecked(False)
            self._rail_ikonlari_boya("")
            return

        for a, dugme in self.rail_dugmeleri.items():
            dugme.setChecked(a == anahtar)
        self._rail_ikonlari_boya(anahtar)
        self.panel_yigin.setCurrentIndex(indeks)
        self.yan_panel.setVisible(True)

        if anahtar == "git":
            self.git_panel.yenile()
        elif anahtar == "geri":
            self.geri_panel.tazele()
        elif anahtar == "ayarlar":
            self.ayar_panel.maliyet_tazele()
            self.bakiyeyi_yenile()
        elif anahtar == "bellek":
            self.bellek_panel.tazele()
        elif anahtar == "oturum":
            self.oturum_panel.tazele(aktif_id=self.sohbet.oturum.id)

    def _oturum_ac(self, oturum_id: str) -> None:
        if self.sohbet.oturumu_yukle(oturum_id):
            self.oturum_panel.tazele(aktif_id=oturum_id)
            self._durum_tazele()

    def _calisma_durumu(self, calisiyor: bool) -> None:
        """Ajan durunca bakiyeyi hemen tazele; harcama ekrana aninda yansisin."""
        if not calisiyor:
            QTimer.singleShot(400, self.bakiyeyi_yenile)

    def yan_paneli_degistir(self) -> None:
        gorunur = self.yan_panel.isVisible()
        self.yan_panel.setVisible(not gorunur)
        sira = [a for a, _ in RAIL]
        if gorunur:
            for dugme in self.rail_dugmeleri.values():
                dugme.setChecked(False)
            self._rail_ikonlari_boya("")
        else:
            aktif = sira[self.panel_yigin.currentIndex()]
            self.rail_dugmeleri[aktif].setChecked(True)
            self._rail_ikonlari_boya(aktif)

    def terminali_degistir(self) -> None:
        gorunur = self.terminal.isVisible()
        self.terminal.setVisible(not gorunur)
        if not gorunur:
            self.terminal.odakla()

    # ------------------------------------------------------------------
    # Proje
    # ------------------------------------------------------------------

    def klasor_sec(self) -> None:
        yol = QFileDialog.getExistingDirectory(
            self, t("Proje klasörünü seç"), self.cfg.project_root or str(Path.home())
        )
        if yol:
            self.projeyi_ac(yol)

    def projeyi_ac(self, yol: str, kaydet: bool = True) -> None:
        yol = str(Path(yol).resolve())
        self.cfg.project_root = yol
        if kaydet:
            self.cfg.remember_project(yol)
            self.cfg.save()
            self.sekmeler.hepsini_kapat(sor=True)

        self.memory.set_project(yol)
        self.checkpoints.project_root = yol
        self.gezgin.yukle(yol)
        self.git_panel.set_cwd(yol)
        self.terminal.set_cwd(yol)
        self.bellek_panel.tazele()
        self.geri_panel.tazele()
        self.oturum_panel.tazele(aktif_id=self.sohbet.oturum.id)
        self.setWindowTitle(f"{Path(yol).name}  ·  {APP_NAME}")
        self._durum_tazele()
        self.durum_yaz(t("Proje açıldı: ") + yol)

    def _proje_tazele(self) -> None:
        self.gezgin.yenile()
        # indeks yerine widget kimligine bakilir: panel sirasi degisince
        # sabit indeks yanlis paneli tazeliyordu
        if self.panel_yigin.currentWidget() is self.git_panel:
            self.git_panel.yenile()

    def dosya_ac(self, yol: str, satir: int | None = None) -> None:
        if self.sekmeler.dosya_ac(yol, satir):
            self.editor_yigin.setCurrentWidget(self.sekmeler)
        else:
            self.durum_yaz(t("Açılamadı (ikili veya çok büyük dosya): ") + Path(yol).name)

    def _editor_durumu(self) -> None:
        if self.sekmeler.count() == 0:
            self.editor_yigin.setCurrentWidget(self.karsilama)
        else:
            self.editor_yigin.setCurrentWidget(self.sekmeler)
        satir, sutun = self.sekmeler.imlec_konumu()
        aktif = self.sekmeler.aktif_yol
        self.durum_imlec.setText(
            f"{t('Sa ')}{satir}{t(', Sü ')}{sutun}" if aktif else ""
        )

    def _ajan_dosyaya_dokundu(self, rel_yol: str) -> None:
        if not self.cfg.project_root:
            return
        tam = Path(self.cfg.project_root) / rel_yol
        self.sekmeler.diskten_tazele(str(tam))
        self.geri_panel.tazele()

    def _geri_alindi(self, mesaj: str) -> None:
        self.durum_yaz(mesaj)
        self._proje_tazele()
        for yol in self.sekmeler.acik_yollar():
            self.sekmeler.diskten_tazele(yol)

    def bellek_panel_tazele(self) -> None:
        self.bellek_panel.tazele()

    # ------------------------------------------------------------------
    # Terminal / git
    # ------------------------------------------------------------------

    def _ajan_komutu(self, komut: str, cikti: str, basarili: bool) -> None:
        """Ajanin calistirdigi komut terminal panelinde de gorunsun."""
        self.terminal.ajan_ciktisi(komut, cikti, basarili)

    def _terminalde_calistir(self, komut: str) -> None:
        self.terminal.setVisible(True)
        self.terminal.calistir(komut)
        QTimer.singleShot(1500, self.git_panel.yenile)

    # ------------------------------------------------------------------
    # Ayarlar
    # ------------------------------------------------------------------

    def _ayarlar_degisti(self) -> None:
        self.sohbet.model_rozetini_tazele()
        self._durum_tazele()
        # anahtar veya gorunurluk degismis olabilir, bakiyeyi hemen sor
        self.bakiyeyi_yenile()

    def _dili_degistir(self, _kod: str) -> None:
        """Dil degisince arayuzu bastan kurmak icin uygulamayi yeniden baslatir."""
        cevap = QMessageBox.question(
            self,
            t("Dil değişikliği"),
            t("Dil değiştirildi. Uygulama şimdi yeniden başlatılsın mı?"),
        )
        if cevap != QMessageBox.StandardButton.Yes:
            return
        self.yeniden_baslat = True
        self.close()

    def _modelleri_cek(self) -> None:
        if not self.cfg.api_key:
            return
        try:
            adlar = DeepSeekClient(self.cfg.api_key, self.cfg.base_url).models()
        except Exception:
            adlar = []
        if adlar:
            self.ayar_panel.modelleri_guncelle(adlar)

    def baglantiyi_test_et(self) -> None:
        anahtar = self.ayar_panel.anahtar.text().strip()
        if anahtar != self.cfg.api_key:
            self.cfg.api_key = anahtar
            self.cfg.save()
        self.durum_yaz(t("Bağlantı test ediliyor") + "...")
        try:
            sonuc = DeepSeekClient(self.cfg.api_key, self.cfg.base_url).test()
        except ApiError as exc:
            QMessageBox.warning(self, t("Bağlantı başarısız"), str(exc))
            self.durum_yaz(t("Bağlantı başarısız."))
            return
        QMessageBox.information(self, "DeepSeek", sonuc)
        self.durum_yaz(sonuc)
        self._modelleri_cek()
        self.bakiyeyi_yenile()

    # ------------------------------------------------------------------
    # Durum serit
    # ------------------------------------------------------------------

    def durum_yaz(self, mesaj: str) -> None:
        self.durum_mesaj.setText(mesaj)
        QTimer.singleShot(9000, lambda: self.durum_mesaj.setText(""))

    def _durum_tazele(self) -> None:
        kok = self.cfg.project_root
        ad = Path(kok).name if kok else t("proje seçilmedi")
        self.durum_proje.setText(ad)
        self.durum_proje.setToolTip(kok or "")
        self.durum_model.setText(self.cfg.model.replace("deepseek-", ""))
        self.durum_maliyet.setText(
            t("oturum ") + usage_mod.para(self.usage.oturum_maliyet) + "  ·  "
            + t("bugün ") + usage_mod.para(self.usage.bugun()["maliyet"])
        )

        # ust serit
        if hasattr(self, "ust_proje"):
            self.ust_proje.setText(kok or t("proje seçilmedi"))
            self.ust_proje.setToolTip(kok or "")
            kip_adi = t("Code") if self.cfg.kip == "code" else t("Chat")
            if self.cfg.kip == "code":
                kip_adi += "  ·  " + t(MODLAR[self.cfg.mode][0])
            self.ust_kip.setText(kip_adi)
            self.ust_oturum_maliyet.setText(
                t("oturum ") + usage_mod.para(self.usage.oturum_maliyet)
            )
            self.bakiye_rozet.setVisible(bool(self.cfg.show_balance))

        if hasattr(self, "ayar_panel"):
            self.ayar_panel.maliyet_tazele()

    # ------------------------------------------------------------------

    def closeEvent(self, event):  # noqa: N802
        if self.sekmeler.kirli_var_mi():
            cevap = QMessageBox.question(
                self, t("Kaydedilmemiş değişiklikler"),
                t("Kaydedilmemiş dosyalar var. Kaydedilsin mi?"),
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if cevap == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if cevap == QMessageBox.StandardButton.Save:
                self.sekmeler.hepsini_kaydet()

        izleyici = getattr(self, "bakiye_izleyici", None)
        if izleyici is not None:
            izleyici.durdur()
            # devam eden bir istek varsa bitmesini bekle (istek zaman asimi 8 sn)
            izleyici.wait(10000)

        self.sohbet.kapaniyor()
        self.terminal.kabugu_kapat()
        self._duzeni_kaydet()
        self.cfg.save()
        super().closeEvent(event)
