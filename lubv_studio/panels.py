"""Sol yan paneller: Dosyalar, Bellek, Beyin (sistem prompt), Geri Al, Ayarlar.

Hepsi ayni iskelet uzerine kurulu: ust seritte baslik ve ikon butonlar,
altta govde. Boylece panel degistirdiginde hicbir sey yerinden oynamaz.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSlider, QSpinBox, QVBoxLayout, QWidget,
)

from . import usage as usage_mod
from .config import DEFAULT_SYSTEM_PROMPT, MODEL_NOTLARI, MODELS
from .memory import GLOBAL, PROJECT
from .i18n import DILLER, t
from .theme import C
from .widgets import IconButton

BASLIK_YUKSEK = 34
KENAR = 10


def _bolum(metin: str) -> QLabel:
    etiket = QLabel(metin.upper())
    etiket.setObjectName("SectionLabel")
    return etiket


def _ipucu(metin: str) -> QLabel:
    etiket = QLabel(metin)
    etiket.setObjectName("PanelHint")
    etiket.setWordWrap(True)
    return etiket


class PanelBase(QFrame):
    """Ust seritli panel iskeleti."""

    def __init__(self, baslik: str, parent=None) -> None:
        super().__init__(parent)
        dis = QVBoxLayout(self)
        dis.setContentsMargins(0, 0, 0, 0)
        dis.setSpacing(0)

        self.serit = QFrame()
        self.serit.setObjectName("PanelHeader")
        self.serit.setFixedHeight(BASLIK_YUKSEK)
        self.serit_duzen = QHBoxLayout(self.serit)
        self.serit_duzen.setContentsMargins(KENAR, 0, 4, 0)
        self.serit_duzen.setSpacing(2)

        self.baslik = QLabel(baslik.upper())
        self.baslik.setObjectName("PanelTitle")
        self.serit_duzen.addWidget(self.baslik)
        self.serit_duzen.addStretch(1)

        govde = QWidget()
        govde.setObjectName("PanelBody")
        self.duzen = QVBoxLayout(govde)
        self.duzen.setContentsMargins(KENAR, 8, KENAR, 8)
        self.duzen.setSpacing(7)

        dis.addWidget(self.serit)
        dis.addWidget(govde, 1)

    def serit_dugmesi(self, ad: str, ipucu: str, islev) -> IconButton:
        dugme = IconButton(ad, ipucu, boyut=24)
        dugme.clicked.connect(islev)
        self.serit_duzen.addWidget(dugme)
        return dugme


# --------------------------------------------------------------------------
# Dosyalar
# --------------------------------------------------------------------------

class ExplorerPanel(PanelBase):
    dosya_ac = Signal(str)
    klasor_degistir = Signal()
    baglama_ekle = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(t("Dosyalar"), parent)
        from .widgets import FileTree

        self.serit_dugmesi("yenile", t("Ağacı yenile"), self.yenile)
        self.serit_dugmesi("klasor", t("Başka proje klasörü aç"), self.klasor_degistir.emit)

        self.arama = QLineEdit()
        self.arama.setPlaceholderText(t("dosya adı filtrele"))
        self.arama.setClearButtonEnabled(True)
        self.arama.textChanged.connect(self._filtrele)

        self.agac = FileTree()
        self.agac.dosya_secildi.connect(self.dosya_ac.emit)
        self.agac.currentItemChanged.connect(self._secim_degisti)

        self.ekle_dugme = QPushButton(t("Seçili dosyayı sohbete ekle"))
        self.ekle_dugme.setEnabled(False)
        self.ekle_dugme.clicked.connect(self._baglama_ekle)

        self.duzen.setContentsMargins(KENAR, 8, KENAR, 8)
        self.duzen.addWidget(self.arama)
        self.duzen.addWidget(self.agac, 1)
        self.duzen.addWidget(self.ekle_dugme)

    def yukle(self, kok: str) -> None:
        self.agac.yukle(kok)
        self.baslik.setText((Path(kok).name if kok else t("Dosyalar")).upper())
        self.baslik.setToolTip(kok or "")

    def yenile(self) -> None:
        self.agac.yenile()

    def _secim_degisti(self, *_) -> None:
        yol = self.agac.secili_yol()
        self.ekle_dugme.setEnabled(bool(yol) and Path(yol).is_file())

    def _filtrele(self, metin: str) -> None:
        metin = metin.lower().strip()

        def gez(item) -> bool:
            gorunur = False
            for i in range(item.childCount()):
                cocuk = item.child(i)
                cocuk_gorunur = gez(cocuk)
                kendi = metin in cocuk.text(0).lower()
                cocuk.setHidden(not (kendi or cocuk_gorunur) if metin else False)
                gorunur = gorunur or kendi or cocuk_gorunur
            return gorunur

        gez(self.agac.invisibleRootItem())

    def _baglama_ekle(self) -> None:
        yol = self.agac.secili_yol()
        if yol and Path(yol).is_file():
            self.baglama_ekle.emit(yol)


# --------------------------------------------------------------------------
# Bellek
# --------------------------------------------------------------------------

class MemoryPanel(PanelBase):
    degisti = Signal()

    def __init__(self, store, parent=None) -> None:
        super().__init__(t("Bellek"), parent)
        self.store = store
        self.serit_dugmesi("yenile", t("Listeyi yenile"), self.tazele)

        self.duzen.addWidget(
            _ipucu(t(
                "LUBV'nin sohbetler arası hatırladıkları. Buradaki her not "
                "istek başına sistem prompt'una eklenir."
            ))
        )

        self.liste = QListWidget()
        self.liste.setWordWrap(True)

        giris = QHBoxLayout()
        giris.setSpacing(5)
        self.kutu = QLineEdit()
        self.kutu.setPlaceholderText(t("yeni not, Enter ile ekle"))
        self.kutu.returnPressed.connect(self.ekle)
        self.kapsam = QComboBox()
        self.kapsam.addItem(t("Bu proje"), PROJECT)
        self.kapsam.addItem(t("Her yerde"), GLOBAL)
        self.kapsam.setFixedWidth(96)
        giris.addWidget(self.kutu, 1)
        giris.addWidget(self.kapsam)

        dugmeler = QHBoxLayout()
        dugmeler.setSpacing(5)
        sil = QPushButton(t("Seçiliyi sil"))
        sil.setProperty("kind", "danger")
        sil.clicked.connect(self.sil)
        temizle = QPushButton(t("Projeyi boşalt"))
        temizle.setProperty("kind", "ghost")
        temizle.clicked.connect(self.bosalt)
        dugmeler.addWidget(sil, 1)
        dugmeler.addWidget(temizle, 1)

        self.duzen.addWidget(self.liste, 1)
        self.duzen.addLayout(giris)
        self.duzen.addLayout(dugmeler)
        self.tazele()

    def tazele(self) -> None:
        self.liste.clear()
        for kayit in self.store.all():
            etiket = t("genel") if kayit.scope == GLOBAL else t("proje")
            item = QListWidgetItem(f"{kayit.text}\n{etiket}  ·  {kayit.created_label}")
            item.setData(Qt.ItemDataRole.UserRole, kayit.id)
            self.liste.addItem(item)
        if self.liste.count() == 0:
            bos = QListWidgetItem(t("Henüz not yok."))
            bos.setFlags(Qt.ItemFlag.NoItemFlags)
            self.liste.addItem(bos)

    def ekle(self) -> None:
        metin = self.kutu.text().strip()
        if not metin:
            return
        self.store.add(metin, self.kapsam.currentData())
        self.kutu.clear()
        self.tazele()
        self.degisti.emit()

    def sil(self) -> None:
        item = self.liste.currentItem()
        if item is None:
            return
        kimlik = item.data(Qt.ItemDataRole.UserRole)
        if kimlik:
            self.store.delete(kimlik)
            self.tazele()
            self.degisti.emit()

    def bosalt(self) -> None:
        onay = QMessageBox.question(
            self, t("Bellek"), t("Bu projeye ait tüm notlar silinsin mi?")
        )
        if onay == QMessageBox.StandardButton.Yes:
            self.store.clear(PROJECT)
            self.tazele()
            self.degisti.emit()


# --------------------------------------------------------------------------
# Beyin (sistem prompt)
# --------------------------------------------------------------------------

class BrainPanel(PanelBase):
    kaydedildi = Signal(str)

    def __init__(self, cfg, parent=None) -> None:
        super().__init__(t("Beyin"), parent)
        self.cfg = cfg

        self.duzen.addWidget(
            _ipucu(t(
                "LUBV'nin sistem prompt'u. Kendi talimatlarını buraya yapıştır ve "
                "Kaydet'e bas, kalıcı olur. Araç protokolü sona otomatik eklenir."
            ))
        )

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("PromptEdit")
        self.editor.setPlainText(cfg.system_prompt)
        self.editor.textChanged.connect(self._sayac_guncelle)

        self.sayac = _ipucu("")

        dugmeler = QHBoxLayout()
        dugmeler.setSpacing(5)
        kaydet = QPushButton(t("Kaydet"))
        kaydet.setProperty("kind", "primary")
        kaydet.clicked.connect(self.kaydet)
        varsayilan = QPushButton(t("Sıfırla"))
        varsayilan.setProperty("kind", "ghost")
        varsayilan.clicked.connect(self.varsayilana_don)
        dugmeler.addWidget(kaydet, 2)
        dugmeler.addWidget(varsayilan, 1)

        self.duzen.addWidget(self.editor, 1)
        self.duzen.addWidget(self.sayac)
        self.duzen.addLayout(dugmeler)
        self._sayac_guncelle()

    def _sayac_guncelle(self) -> None:
        metin = self.editor.toPlainText()
        self.sayac.setText(
            f"{len(metin)}" + t(" karakter  ·  ~") + f"{len(metin) // 3} token  ·  "
            + f"{len(metin.splitlines())}" + t(" satır")
        )

    def kaydet(self) -> None:
        self.cfg.system_prompt = self.editor.toPlainText()
        self.cfg.save()
        self.kaydedildi.emit(t("Beyin kaydedildi, bir sonraki mesajdan itibaren geçerli."))

    def varsayilana_don(self) -> None:
        self.editor.setPlainText(DEFAULT_SYSTEM_PROMPT)


# --------------------------------------------------------------------------
# Geri al
# --------------------------------------------------------------------------

class CheckpointPanel(PanelBase):
    geri_alindi = Signal(str)

    def __init__(self, store, cfg, parent=None) -> None:
        super().__init__(t("Geri al"), parent)
        self.store = store
        self.cfg = cfg
        self.serit_dugmesi("yenile", t("Listeyi yenile"), self.tazele)

        self.duzen.addWidget(
            _ipucu(t(
                "LUBV'nin değiştirdiği her dosyanın önceki hali burada. "
                "Bir satıra çift tıkla, o değişiklik geri alınsın."
            ))
        )

        self.liste = QListWidget()
        self.liste.itemDoubleClicked.connect(self._geri_al)

        geri = QPushButton(t("Seçiliyi geri al"))
        geri.setProperty("kind", "primary")
        geri.clicked.connect(lambda: self._geri_al(self.liste.currentItem()))

        self.duzen.addWidget(self.liste, 1)
        self.duzen.addWidget(geri)
        self.tazele()

    def tazele(self) -> None:
        self.liste.clear()
        kayitlar = self.store.for_project(self.cfg.project_root)
        if not kayitlar:
            bos = QListWidgetItem(t("Henüz bir değişiklik yok."))
            bos.setFlags(Qt.ItemFlag.NoItemFlags)
            self.liste.addItem(bos)
            return
        for nokta in kayitlar[:120]:
            durum = t("geri alındı") if nokta.reverted else t(nokta.action_label)
            item = QListWidgetItem(f"{nokta.rel_path}\n{nokta.time_label}  ·  {durum}")
            item.setData(Qt.ItemDataRole.UserRole, nokta.id)
            if nokta.reverted:
                item.setForeground(Qt.GlobalColor.gray)
            self.liste.addItem(item)

    def _geri_al(self, item: QListWidgetItem | None) -> None:
        if item is None:
            return
        kimlik = item.data(Qt.ItemDataRole.UserRole)
        if not kimlik:
            return
        tamam, mesaj = self.store.revert(kimlik)
        self.tazele()
        self.geri_alindi.emit(mesaj if tamam else t("Geri alınamadı: ") + mesaj)


# --------------------------------------------------------------------------
# Ayarlar
# --------------------------------------------------------------------------

class SettingsPanel(QFrame):
    degisti = Signal()
    bildirim = Signal(str)
    baglanti_test = Signal()
    dil_degisti = Signal(str)

    def __init__(self, cfg, usage_store, parent=None) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.usage = usage_store

        dis = QVBoxLayout(self)
        dis.setContentsMargins(0, 0, 0, 0)
        dis.setSpacing(0)

        serit = QFrame()
        serit.setObjectName("PanelHeader")
        serit.setFixedHeight(BASLIK_YUKSEK)
        sd = QHBoxLayout(serit)
        sd.setContentsMargins(KENAR, 0, 4, 0)
        baslik = QLabel(t("AYARLAR"))
        baslik.setObjectName("PanelTitle")
        sd.addWidget(baslik)
        sd.addStretch(1)

        kaydirma = QScrollArea()
        kaydirma.setWidgetResizable(True)
        kaydirma.setStyleSheet(f"QScrollArea{{background:{C['bg1']};}}")
        govde = QWidget()
        govde.setObjectName("PanelBody")
        kaydirma.setWidget(govde)

        d = QVBoxLayout(govde)
        d.setContentsMargins(KENAR, 10, KENAR, 14)
        d.setSpacing(7)

        # ---- Dil ----
        d.addWidget(_bolum(t("Arayüz dili")))
        self.dil_kutu = QComboBox()
        for kod, ad in DILLER.items():
            self.dil_kutu.addItem(ad, kod)
        idx = self.dil_kutu.findData(cfg.language)
        self.dil_kutu.setCurrentIndex(max(0, idx))
        self.dil_kutu.currentIndexChanged.connect(self._dil_degisti)
        d.addWidget(self.dil_kutu)

        # ---- API ----
        d.addSpacing(4)
        d.addWidget(_bolum(t("DeepSeek API")))
        anahtar_satir = QHBoxLayout()
        anahtar_satir.setSpacing(5)
        self.anahtar = QLineEdit(cfg.api_key)
        self.anahtar.setEchoMode(QLineEdit.EchoMode.Password)
        self.anahtar.setPlaceholderText("sk-...")
        self.anahtar.editingFinished.connect(self._anahtar_kaydet)
        self.goster = QPushButton(t("Göster"))
        self.goster.setProperty("kind", "ghost")
        self.goster.setFixedWidth(70)
        self.goster.setCheckable(True)
        self.goster.toggled.connect(self._anahtar_gorunurluk)
        anahtar_satir.addWidget(self.anahtar, 1)
        anahtar_satir.addWidget(self.goster)
        d.addLayout(anahtar_satir)

        test = QPushButton(t("Bağlantıyı test et ve bakiyeyi göster"))
        test.clicked.connect(self.baglanti_test.emit)
        d.addWidget(test)

        # ---- Model ----
        d.addSpacing(4)
        d.addWidget(_bolum(t("Model")))
        self.model_kutu = QComboBox()
        self._modelleri_doldur([m[0] for m in MODELS])
        self.model_kutu.currentIndexChanged.connect(self._model_degisti)
        d.addWidget(self.model_kutu)
        self.model_not = _ipucu(t(MODEL_NOTLARI.get(cfg.model, "")))
        d.addWidget(self.model_not)

        self.dusunme = QCheckBox(t("Düşünme modu"))
        self.dusunme.setToolTip(t("Daha isabetli cevap, biraz daha yavaş ve pahalı"))
        self.dusunme.setChecked(cfg.thinking)
        self.dusunme.toggled.connect(lambda v: self._ayarla("thinking", v))
        d.addWidget(self.dusunme)

        self.dusunme_goster = QCheckBox(t("Düşünme akışını sohbette göster"))
        self.dusunme_goster.setChecked(cfg.show_reasoning)
        self.dusunme_goster.toggled.connect(lambda v: self._ayarla("show_reasoning", v))
        d.addWidget(self.dusunme_goster)

        sic_satir = QHBoxLayout()
        self.sic_etiket = QLabel(t("Sıcaklık  ") + f"{cfg.temperature:.2f}")
        self.sic_etiket.setStyleSheet(f"color:{C['text2']}; font-size:12.5px;")
        self.sicaklik = QSlider(Qt.Orientation.Horizontal)
        self.sicaklik.setRange(0, 150)
        self.sicaklik.setValue(int(cfg.temperature * 100))
        self.sicaklik.valueChanged.connect(self._sicaklik)
        sic_satir.addWidget(self.sic_etiket, 1)
        sic_satir.addWidget(self.sicaklik, 1)
        d.addLayout(sic_satir)

        d.addLayout(self._sayi_satiri(
            t("Maks. yanıt token"), 1024, 131072, cfg.max_tokens, 1024, "max_tokens"
        ))
        d.addLayout(self._sayi_satiri(
            t("Maks. ajan adımı"), 1, 40, cfg.max_iterations, 1, "max_iterations"
        ))
        d.addWidget(_ipucu(t("Bir istek için LUBV'nin arka arkaya kaç adım atabileceği.")))

        # ---- İzinler ----
        d.addSpacing(4)
        d.addWidget(_bolum(t("İzinler")))
        self.oto_yaz = QCheckBox(t("Dosya yazmayı sorma"))
        self.oto_yaz.setChecked(cfg.auto_approve_write)
        self.oto_yaz.toggled.connect(lambda v: self._ayarla("auto_approve_write", v))
        self.oto_sil = QCheckBox(t("Dosya silmeyi sorma"))
        self.oto_sil.setChecked(cfg.auto_approve_delete)
        self.oto_sil.toggled.connect(lambda v: self._ayarla("auto_approve_delete", v))
        self.oto_komut = QCheckBox(t("Komut çalıştırmayı sorma"))
        self.oto_komut.setChecked(cfg.auto_approve_command)
        self.oto_komut.toggled.connect(lambda v: self._ayarla("auto_approve_command", v))
        self.bellek_kullan = QCheckBox(t("Kalıcı belleği kullan"))
        self.bellek_kullan.setChecked(cfg.use_memory)
        self.bellek_kullan.toggled.connect(lambda v: self._ayarla("use_memory", v))
        for kutu in (self.oto_yaz, self.oto_sil, self.oto_komut, self.bellek_kullan):
            d.addWidget(kutu)

        d.addLayout(self._sayi_satiri(
            t("Komut zaman aşımı (sn)"), 10, 900, cfg.command_timeout, 10, "command_timeout"
        ))

        # ---- Harcama ----
        d.addSpacing(4)
        d.addWidget(_bolum(t("Harcama")))
        self.maliyet_kutu = QLabel()
        self.maliyet_kutu.setWordWrap(True)
        self.maliyet_kutu.setTextFormat(Qt.TextFormat.RichText)
        self.maliyet_kutu.setStyleSheet(
            f"background:{C['bg2']}; border:1px solid {C['line']}; "
            "border-radius:10px; padding:10px;"
        )
        d.addWidget(self.maliyet_kutu)

        sifirla = QPushButton(t("Oturum sayacını sıfırla"))
        sifirla.setProperty("kind", "ghost")
        sifirla.clicked.connect(self._oturum_sifirla)
        d.addWidget(sifirla)

        d.addStretch(1)

        dis.addWidget(serit)
        dis.addWidget(kaydirma, 1)
        self.maliyet_tazele()

    # ---------- yardimcilar ----------

    def _sayi_satiri(self, etiket, alt, ust, deger, adim, alan) -> QHBoxLayout:
        satir = QHBoxLayout()
        yazi = QLabel(etiket)
        yazi.setStyleSheet(f"color:{C['text2']}; font-size:12.5px;")
        kutu = QSpinBox()
        kutu.setRange(alt, ust)
        kutu.setSingleStep(adim)
        kutu.setValue(deger)
        kutu.setFixedWidth(88)
        kutu.valueChanged.connect(lambda v, a=alan: self._ayarla(a, v))
        satir.addWidget(yazi, 1)
        satir.addWidget(kutu)
        return satir

    def _dil_degisti(self) -> None:
        kod = self.dil_kutu.currentData()
        if kod and kod != self.cfg.language:
            self.cfg.language = kod
            self.cfg.save()
            self.dil_degisti.emit(kod)

    def _anahtar_gorunurluk(self, acik: bool) -> None:
        self.anahtar.setEchoMode(
            QLineEdit.EchoMode.Normal if acik else QLineEdit.EchoMode.Password
        )
        self.goster.setText("Gizle" if acik else t("Göster"))

    def _modelleri_doldur(self, adlar: list[str]) -> None:
        self.model_kutu.blockSignals(True)
        self.model_kutu.clear()
        etiketler = dict(MODELS)
        for ad in adlar:
            self.model_kutu.addItem(t(etiketler.get(ad, ad)), ad)
        if self.cfg.model not in adlar:
            self.model_kutu.addItem(self.cfg.model, self.cfg.model)
        idx = self.model_kutu.findData(self.cfg.model)
        self.model_kutu.setCurrentIndex(max(0, idx))
        self.model_kutu.blockSignals(False)

    def modelleri_guncelle(self, adlar: list[str]) -> None:
        if adlar:
            self._modelleri_doldur(adlar)

    def _ayarla(self, alan: str, deger) -> None:
        setattr(self.cfg, alan, deger)
        self.cfg.save()
        self.degisti.emit()

    def _anahtar_kaydet(self) -> None:
        yeni = self.anahtar.text().strip()
        if yeni != self.cfg.api_key:
            self._ayarla("api_key", yeni)
            self.bildirim.emit(t("API anahtarı kaydedildi."))

    def _model_degisti(self) -> None:
        ad = self.model_kutu.currentData()
        if ad:
            self._ayarla("model", ad)
            self.model_not.setText(t(MODEL_NOTLARI.get(ad, "")))

    def _sicaklik(self, deger: int) -> None:
        self.sic_etiket.setText(t("Sıcaklık  ") + f"{deger / 100:.2f}")
        self._ayarla("temperature", deger / 100)

    def _oturum_sifirla(self) -> None:
        self.usage.sifirla_oturum()
        self.maliyet_tazele()
        self.degisti.emit()

    def maliyet_tazele(self) -> None:
        bugun = self.usage.bugun()
        toplam = self.usage.toplam
        para = usage_mod.para
        token_kisa = usage_mod.token_kisa

        def blok(ad: str, tutar: float, token: int, istek: int, buyuk: bool = False) -> str:
            renk = C["accent_hi"] if buyuk else C["text2"]
            boyut = "18px" if buyuk else "13px"
            return (
                f"<div style='color:{C['muted']}; font-size:11px;'>{ad}</div>"
                f"<div style='color:{renk}; font-size:{boyut}; font-weight:700;'>"
                f"{para(tutar)}"
                f"<span style='color:{C['muted']}; font-size:11px; font-weight:400;'>"
                f"   {token_kisa(token)}{t(' token, ')}{istek}{t(' istek')}"
                "</span></div>"
            )

        parcalar = [
            blok(t("BU OTURUM"), self.usage.oturum_maliyet, self.usage.oturum_token,
                 len(self.usage.oturum), buyuk=True),
            "<div style='height:8px'></div>",
            blok(t("BUGÜN"), bugun["maliyet"], bugun["girdi"] + bugun["cikti"], bugun["istek"]),
            "<div style='height:8px'></div>",
            blok(t("TOPLAM"), toplam["maliyet"], toplam["girdi"] + toplam["cikti"],
                 toplam["istek"]),
        ]
        son = self.usage.son_gunler(5)
        if len(son) > 1:
            parcalar.append(
                f"<div style='height:8px'></div>"
                f"<div style='color:{C['muted']}; font-size:11px;'>" + t("SON GÜNLER") + "</div>"
            )
            for gun, veri in son:
                parcalar.append(
                    f"<div style='color:{C['muted']}; font-size:11.5px;'>"
                    f"{gun}   {para(veri['maliyet'])}</div>"
                )
        self.maliyet_kutu.setText("".join(parcalar))
