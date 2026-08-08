"""Sohbet balonlari, arac kartlari, onay diyalogu, dosya agaci ve kucuk parcalar."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QFontMetrics, QIcon, QPainter, QPixmap, QTextOption,
)
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QTextBrowser, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from . import render
from .icons import ikon
from .i18n import t
from .theme import C
from .tools import AGAC_GIZLI, ToolCall, insan_boyut, sure_metni


# --------------------------------------------------------------------------
# Kucuk parcalar
# --------------------------------------------------------------------------

class IconButton(QToolButton):
    """Sadece ikonlu, kare, sessiz dugme."""

    def __init__(self, ad: str, ipucu: str = "", boyut: int = 26, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("IconButton")
        self.ad = ad
        self.setFixedSize(QSize(boyut, boyut))
        self.setIconSize(QSize(boyut - 10, boyut - 10))
        self.setIcon(ikon(ad, C["muted"], boyut - 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if ipucu:
            self.setToolTip(ipucu)

    def enterEvent(self, event):  # noqa: N802
        self.setIcon(ikon(self.ad, C["text"], self.iconSize().width()))
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self.setIcon(ikon(self.ad, C["muted"], self.iconSize().width()))
        super().leaveEvent(event)


class Badge(QLabel):
    def __init__(self, metin: str, tone: str = "", parent=None) -> None:
        super().__init__(metin, parent)
        self.setObjectName("Badge")
        if tone:
            self.setProperty("tone", tone)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_tone(self, tone: str) -> None:
        self.setProperty("tone", tone)
        self.style().unpolish(self)
        self.style().polish(self)


class BalanceBadge(QPushButton):
    """Ust seritte duran canli bakiye rozeti.

    Tiklaninca hemen yenilenir. Renk bakiyeye gore degisir: normalde yesil,
    1 birimin altina inince amber, veri alinamiyorsa sonuk gri. Boylece
    "param bitmis mi" sorusu icin hicbir yere girmek gerekmez.
    """

    yenile_istendi = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("BalanceBadge")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self.setIcon(ikon("cuzdan", C["muted"], 13))
        self.setIconSize(QSize(13, 13))
        self.clicked.connect(self.yenile_istendi.emit)
        self.durum_yaz(None)

    def durum_yaz(self, bakiye) -> None:
        if bakiye is None:
            metin, renk, ipucu = "...", C["muted"], t("Bakiye sorgulanıyor")
        elif not bakiye.gecerli:
            metin, renk = "--", C["muted"]
            ipucu = bakiye.mesaj or t("Bakiye alınamadı")
        else:
            metin = bakiye.metin
            renk = C["amber"] if bakiye.dusuk_mu else C["accent_hi"]
            an = time.strftime("%H:%M:%S", time.localtime(bakiye.zaman))
            ipucu = f"{t('Kalan bakiye')}: {bakiye.metin}\n{t('son güncelleme')}: {an}"
            if bakiye.dusuk_mu:
                ipucu += "\n" + t("Bakiye azaldı, yüklemen gerekebilir.")

        self.setText(f"  {metin}")
        self.setIcon(ikon("cuzdan", renk, 13))
        self.setToolTip(ipucu + "\n" + t("Yenilemek için tıkla"))
        self.setStyleSheet(
            f"QPushButton#BalanceBadge{{background:{C['bg2']}; border:1px solid {C['line2']};"
            f"border-radius:7px; padding:2px 9px; color:{renk}; font-size:11.5px;"
            "font-weight:700; min-height:16px;}"
            f"QPushButton#BalanceBadge:hover{{border-color:{renk};}}"
        )


class AutoTextBrowser(QTextBrowser):
    """Icerigi kadar yer kaplayan, kaydirmasiz metin alani."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Message")
        self.setOpenExternalLinks(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().documentLayout().documentSizeChanged.connect(
            lambda _: self._boyu_ayarla()
        )
        self.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)

    def _boyu_ayarla(self) -> None:
        yukseklik = int(self.document().size().height()) + 6
        if abs(self.height() - yukseklik) > 2:
            self.setFixedHeight(max(20, yukseklik))

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self.document().setTextWidth(self.viewport().width())
        self._boyu_ayarla()

    def set_markdown(self, metin: str) -> None:
        self.setHtml(render.markdown_to_html(metin))
        self.document().setTextWidth(self.viewport().width())
        self._boyu_ayarla()


# --------------------------------------------------------------------------
# Sohbet balonlari
# --------------------------------------------------------------------------

class MessageBubble(QFrame):
    """Kullanici veya LUBV mesaji."""

    def __init__(self, rol: str, metin: str = "", parent=None) -> None:
        super().__init__(parent)
        self.rol = rol
        self.ham = metin
        self.setObjectName("UserBubble" if rol == "user" else "AssistantBubble")

        dis = QVBoxLayout(self)
        if rol == "user":
            dis.setContentsMargins(11, 8, 11, 9)
        else:
            dis.setContentsMargins(2, 4, 2, 4)
        dis.setSpacing(4)

        ust = QHBoxLayout()
        ust.setSpacing(6)
        rozet = QLabel(t("SEN") if rol == "user" else "LUBV")
        rozet.setObjectName("RoleName")
        rozet.setStyleSheet(
            f"color:{C['accent_hi'] if rol == 'user' else C['violet']};"
        )
        zaman = QLabel(time.strftime("%H:%M"))
        zaman.setObjectName("TimeStamp")
        ust.addWidget(rozet)
        ust.addWidget(zaman)
        ust.addStretch(1)

        self.govde = AutoTextBrowser()
        self.govde.set_markdown(metin)

        dis.addLayout(ust)
        dis.addWidget(self.govde)

    def append(self, parca: str) -> None:
        self.ham += parca
        self.govde.set_markdown(self.ham)

    def bos_mu(self) -> bool:
        return not self.ham.strip()


class ReasoningBox(QFrame):
    """Modelin dusunme akisi - katlanabilir."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("SystemBubble")
        self.ham = ""
        self.acik = False

        duzen = QVBoxLayout(self)
        duzen.setContentsMargins(10, 8, 10, 8)
        duzen.setSpacing(6)

        self.baslik = QPushButton("  " + t("Düşünüyor"))
        self.baslik.setProperty("kind", "ghost")
        self.baslik.setCursor(Qt.CursorShape.PointingHandCursor)
        self.baslik.setStyleSheet(
            f"text-align:left; color:{C['muted']}; font-size:12px; padding:2px;"
        )
        self.baslik.clicked.connect(self.degistir)

        self.govde = QTextBrowser()
        self.govde.setObjectName("ToolOutput")
        self.govde.setMaximumHeight(180)
        self.govde.setVisible(False)

        duzen.addWidget(self.baslik)
        duzen.addWidget(self.govde)

    def degistir(self) -> None:
        self.acik = not self.acik
        self.govde.setVisible(self.acik)
        self._basligi_yaz()

    def _basligi_yaz(self, bitti: bool = False) -> None:
        ok = "▾" if self.acik else "▸"
        kelime = len(self.ham.split())
        etiket = t("Düşündü") if bitti else t("Düşünüyor")
        self.baslik.setText(f"  {ok}  {etiket}   ({kelime}{t(' kelime')})")

    def append(self, parca: str) -> None:
        self.ham += parca
        self.govde.setHtml(render.plain_to_html(self.ham[-6000:], C["muted"]))
        self.govde.verticalScrollBar().setValue(
            self.govde.verticalScrollBar().maximum()
        )
        self._basligi_yaz()

    def bitir(self) -> None:
        self._basligi_yaz(bitti=True)


class ToolCard(QFrame):
    """Bir arac cagrisinin gorsel karti."""

    def __init__(self, call: ToolCall, parent=None) -> None:
        super().__init__(parent)
        self.call = call
        self.setObjectName("ToolCard")
        self.setProperty("state", "running")
        self.acik = False

        duzen = QVBoxLayout(self)
        duzen.setContentsMargins(12, 9, 12, 9)
        duzen.setSpacing(6)

        ust = QHBoxLayout()
        ust.setSpacing(8)

        self.simge = QLabel()
        self.simge.setFixedSize(QSize(16, 16))
        self.simge.setPixmap(ikon(call.icon, C["text2"], 15).pixmap(15, 15))

        self.baslik = QLabel(t(call.label))
        self.baslik.setObjectName("ToolTitle")

        self.hedef = QLabel()
        self.hedef.setObjectName("ToolTarget")
        # dar panelde uzun yollar rozeti disari itmesin: alan neyse ona sigar
        self.hedef.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.hedef.setMinimumWidth(40)

        self.rozet = Badge(t("çalışıyor"), "amber")

        self.ac_dugme = QToolButton()
        self.ac_dugme.setObjectName("IconButton")
        self.ac_dugme.setFixedSize(QSize(22, 22))
        self.ac_dugme.setIconSize(QSize(13, 13))
        self.ac_dugme.setIcon(ikon("chevron", C["muted"], 13))
        self.ac_dugme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ac_dugme.setToolTip(t("Ayrıntıyı aç/kapa"))
        self.ac_dugme.clicked.connect(self.degistir)

        ust.addWidget(self.simge)
        ust.addWidget(self.baslik)
        ust.addWidget(self.hedef, 1)
        ust.addWidget(self.rozet)
        ust.addWidget(self.ac_dugme)

        self.cikti = QTextBrowser()
        self.cikti.setObjectName("ToolOutput")
        self.cikti.setMaximumHeight(240)
        self.cikti.setVisible(False)

        duzen.addLayout(ust)
        duzen.addWidget(self.cikti)

    def _hedef_metni(self) -> str:
        """Hedefi etiketin gercek genisligine gore kirpar."""
        ham = " ".join((self.call.target or "").split())
        olcum = QFontMetrics(self.hedef.font())
        alan = max(40, self.hedef.width())
        # yol ise sondan, sorgu ise ortadan kirp
        kip = (
            Qt.TextElideMode.ElideLeft
            if self.call.kind in ("read", "write", "edit", "delete", "list")
            else Qt.TextElideMode.ElideRight
        )
        return olcum.elidedText(ham, kip, alan)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self.hedef.setText(self._hedef_metni())

    def degistir(self) -> None:
        self.acik = not self.acik
        self.cikti.setVisible(self.acik)
        self.ac_dugme.setIcon(
            ikon("chevron", C["text2"] if self.acik else C["muted"], 13)
        )

    def tamamla(self, call: ToolCall) -> None:
        self.call = call
        sure = sure_metni(call.duration)

        if call.approved is False:
            durum, tone, etiket = "denied", "", t("reddedildi")
        elif call.ok:
            # Sure rozeti okuma gibi hizli islerde "0.0s" yaziyordu ve is
            # yapilmamis gibi gorunuyordu. Artik ne yapildigi yaziyor.
            durum, tone = "ok", "green"
            etiket = call.ozet or sure
        else:
            durum, tone, etiket = "fail", "red", t("hata")

        self.setProperty("state", durum)
        self.style().unpolish(self)
        self.style().polish(self)
        self.rozet.setText(etiket)
        self.rozet.set_tone(tone)
        self.rozet.setToolTip(f"{t(call.label)}  ·  {sure}")
        self.hedef.setToolTip(self.call.target)
        self.hedef.setText(self._hedef_metni())

        renk = C["text2"] if call.ok else "#FF9C95"
        self.cikti.setHtml(render.plain_to_html((call.output or "")[:8000], renk))
        if not call.ok and not self.acik:
            self.degistir()   # hatayi kullanici acmadan gorsun


# --------------------------------------------------------------------------
# Onay diyalogu
# --------------------------------------------------------------------------

class ApprovalDialog(QDialog):
    """Dosya yazma / silme / komut oncesi kullanici onayi."""

    HEP_ONAYLA = 2

    def __init__(self, call: ToolCall, eski_icerik: str = "", parent=None) -> None:
        super().__init__(parent)
        self.call = call
        self.setWindowTitle(t("LUBV izin istiyor"))
        self.setMinimumSize(760, 520)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        duzen = QVBoxLayout(self)
        duzen.setContentsMargins(20, 18, 20, 18)
        duzen.setSpacing(12)

        basliklar = {
            "write": (t("Dosyanın tamamı değiştirilecek"), C["amber"]),
            "edit": (t("Dosyada değişiklik yapılacak"), C["amber"]),
            "delete": (t("Dosya silinecek"), C["red"]),
            "run": (t("Terminal komutu çalıştırılacak"), C["accent"]),
        }
        metin, renk = basliklar.get(call.kind, (t("İşlem onayı"), C["accent"]))

        baslik = QLabel(metin)
        baslik.setStyleSheet(f"font-size:16px; font-weight:700; color:{renk};")

        hedef = QLabel(call.target)
        hedef.setObjectName("ToolTarget")
        hedef.setStyleSheet(f"font-size:13px; color:{C['text']};")
        hedef.setWordWrap(True)

        govde = QTextBrowser()
        govde.setObjectName("ToolOutput")
        govde.setHtml(self._onizleme(eski_icerik))

        dugmeler = QHBoxLayout()
        dugmeler.setSpacing(8)

        red = QPushButton(t("Reddet"))
        red.setProperty("kind", "danger")
        red.clicked.connect(self.reject)

        hep = QPushButton(t("Bu tür için hep onayla"))
        hep.setProperty("kind", "ghost")
        hep.setToolTip(t("Bu oturumda bir daha sorulmaz (Ayarlar'dan geri alabilirsin)"))
        hep.clicked.connect(lambda: self.done(self.HEP_ONAYLA))

        onay = QPushButton(t("Onayla"))
        onay.setProperty("kind", "primary")
        onay.setDefault(True)
        onay.clicked.connect(self.accept)

        dugmeler.addWidget(red)
        dugmeler.addStretch(1)
        dugmeler.addWidget(hep)
        dugmeler.addWidget(onay)

        duzen.addWidget(baslik)
        duzen.addWidget(hedef)
        duzen.addWidget(govde, 1)
        duzen.addLayout(dugmeler)

    def _onizleme(self, eski: str) -> str:
        call = self.call
        if call.kind == "run":
            return render.plain_to_html(call.target, C["accent_hi"])
        if call.kind == "delete":
            return render.plain_to_html(
                (eski or "(dosya icerigi okunamadi)")[:6000], C["muted"]
            )
        if call.kind == "edit":
            return render.diff_to_html(call.old, call.new, call.target)
        return render.diff_to_html(eski, call.content, call.target)


# --------------------------------------------------------------------------
# Dosya agaci
# --------------------------------------------------------------------------

def _renkli_nokta(renk: str, boyut: int = 8) -> QIcon:
    pix = QPixmap(14, 14)
    pix.fill(Qt.GlobalColor.transparent)
    boyaci = QPainter(pix)
    boyaci.setRenderHint(QPainter.RenderHint.Antialiasing)
    boyaci.setBrush(QColor(renk))
    boyaci.setPen(Qt.PenStyle.NoPen)
    boyaci.drawEllipse(3, 3, boyut, boyut)
    boyaci.end()
    return QIcon(pix)


UZANTI_RENK = {
    ".py": "#4B8BBE", ".js": "#F1E05A", ".ts": "#3178C6", ".tsx": "#3178C6",
    ".jsx": "#F1E05A", ".html": "#E34C26", ".css": "#563D7C", ".json": "#CBCB41",
    ".md": "#7AA2F7", ".java": "#B07219", ".kt": "#A97BFF", ".c": "#555555",
    ".cpp": "#F34B7D", ".cs": "#178600", ".go": "#00ADD8", ".rs": "#DEA584",
    ".rb": "#701516", ".php": "#4F5D95", ".sh": "#89E051", ".bat": "#C1F12E",
    ".ps1": "#012456", ".yml": "#CB171E", ".yaml": "#CB171E", ".xml": "#0060AC",
    ".txt": "#8B95A7", ".sql": "#E38C00", ".vue": "#41B883", ".dart": "#00B4AB",
}


KLASOR_ROL = Qt.ItemDataRole.UserRole + 2      # bu satir bir klasor mu
OK_ALANI = 16                                   # ok isareti icin ayrilan genislik


class FileTree(QTreeWidget):
    """Proje klasoru agaci.

    Klasorlerin solunda VS Code'daki gibi ok isareti cizilir: kapaliyken saga,
    acikken asagi bakar. Qt'nin varsayilan dallanma cizgileri koyu temada zar
    zor gorundugu icin oklar burada elle ciziliyor.
    """

    dosya_secildi = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.kok = ""
        self.setHeaderHidden(True)
        self.setIndentation(OK_ALANI)
        self.setRootIsDecorated(True)
        self.setAnimated(True)
        self.setUniformRowHeights(True)
        self.setExpandsOnDoubleClick(False)
        self.setIconSize(QSize(14, 14))
        self.itemDoubleClicked.connect(self._acildi)
        self.itemClicked.connect(self._tiklandi)
        self.itemExpanded.connect(self._genislet)
        self.itemExpanded.connect(self._klasor_simgesi_tazele)
        self.itemCollapsed.connect(self._klasor_simgesi_tazele)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

    # ---------- ok isaretleri ----------

    @staticmethod
    def klasor_mu(item: QTreeWidgetItem) -> bool:
        return bool(item.data(0, KLASOR_ROL))

    def drawBranches(self, painter, rect, index):  # noqa: N802 (Qt API)
        """Klasorlerin soluna acilma okunu cizer, dosyalarda bos birakir."""
        item = self.itemFromIndex(index)
        if item is None or not self.klasor_mu(item):
            return

        ad = "ok_asagi" if item.isExpanded() else "ok_sag"
        renk = C["text2"] if item.isExpanded() else C["muted"]
        boyut = 10
        simge = ikon(ad, renk, boyut).pixmap(boyut, boyut)
        # ok, satirin kendi girinti seviyesinde durur: her alt klasor bir
        # kademe iceri kayar, hiyerarsi gozle takip edilebilir olur
        x = rect.right() - OK_ALANI + (OK_ALANI - boyut) // 2
        y = rect.top() + (rect.height() - boyut) // 2
        painter.drawPixmap(x, y, simge)

    def _klasor_simgesi_tazele(self, item: QTreeWidgetItem) -> None:
        if self.klasor_mu(item):
            item.setIcon(0, ikon("klasor" if item.isExpanded() else "klasor_kapali",
                                 C["muted"], 14))

    def yukle(self, kok: str) -> None:
        self.kok = kok
        self.clear()
        if not kok or not Path(kok).is_dir():
            return
        self._klasor_doldur(Path(kok), self.invisibleRootItem())

    def yenile(self) -> None:
        acik = self._acik_yollar()
        self.yukle(self.kok)
        self._acik_yollari_geri_yukle(acik)

    def _acik_yollar(self) -> set[str]:
        acik: set[str] = set()

        def gez(item: QTreeWidgetItem) -> None:
            for i in range(item.childCount()):
                cocuk = item.child(i)
                if cocuk.isExpanded():
                    acik.add(cocuk.data(0, Qt.ItemDataRole.UserRole) or "")
                    gez(cocuk)

        gez(self.invisibleRootItem())
        return acik

    def _acik_yollari_geri_yukle(self, acik: set[str]) -> None:
        def gez(item: QTreeWidgetItem) -> None:
            for i in range(item.childCount()):
                cocuk = item.child(i)
                yol = cocuk.data(0, Qt.ItemDataRole.UserRole)
                if yol in acik:
                    cocuk.setExpanded(True)
                    gez(cocuk)

        gez(self.invisibleRootItem())

    def _klasor_doldur(self, klasor: Path, ebeveyn) -> None:
        try:
            girdiler = sorted(
                (p for p in klasor.iterdir() if p.name not in AGAC_GIZLI),
                key=lambda p: (p.is_file(), p.name.lower()),
            )
        except Exception:
            return

        for yol in girdiler:
            item = QTreeWidgetItem(ebeveyn)
            item.setData(0, Qt.ItemDataRole.UserRole, str(yol))
            item.setText(0, yol.name)
            if yol.is_dir():
                item.setData(0, KLASOR_ROL, True)
                item.setIcon(0, ikon("klasor_kapali", C["muted"], 14))
                item.setToolTip(0, str(yol))
                item.setChildIndicatorPolicy(
                    QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                )
                item.setData(0, Qt.ItemDataRole.UserRole + 1, False)  # yuklenmedi
            else:
                item.setData(0, KLASOR_ROL, False)
                renk = UZANTI_RENK.get(yol.suffix.lower(), C["line2"])
                item.setIcon(0, _renkli_nokta(renk))
                item.setChildIndicatorPolicy(
                    QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
                )
                try:
                    item.setToolTip(0, f"{yol}  ·  {insan_boyut(yol.stat().st_size)}")
                except Exception:
                    item.setToolTip(0, str(yol))

    def _genislet(self, item: QTreeWidgetItem) -> None:
        yuklendi = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if yuklendi:
            return
        yol = item.data(0, Qt.ItemDataRole.UserRole)
        item.takeChildren()
        if yol:
            self._klasor_doldur(Path(yol), item)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, True)
        if item.childCount() == 0:
            # bos klasorde ok isareti kalmasin, yanlis beklenti yaratiyor
            item.setChildIndicatorPolicy(
                QTreeWidgetItem.ChildIndicatorPolicy.DontShowIndicator
            )

    def _tiklandi(self, item: QTreeWidgetItem, _sutun: int) -> None:
        """Klasorde tek tik acar/kapatir; VS Code'da da boyle calisir.

        Cift tikin ikinci tiki da buraya dusuyor ve klasoru hemen geri
        kapatiyordu. Cift tik araligindaki ikinci tik yok sayilir.
        """
        if not self.klasor_mu(item):
            return
        simdi = time.monotonic()
        aralik = QApplication.doubleClickInterval() / 1000.0
        onceki = getattr(self, "_son_tik", None)
        if onceki and onceki[0] is item and simdi - onceki[1] < aralik:
            return
        self._son_tik = (item, simdi)
        item.setExpanded(not item.isExpanded())

    def _acildi(self, item: QTreeWidgetItem, _sutun: int) -> None:
        yol = item.data(0, Qt.ItemDataRole.UserRole)
        if not yol:
            return
        if self.klasor_mu(item):
            return  # cift tik klasorde tek tikla ayni islemi tekrarlamasin
        self.dosya_secildi.emit(yol)

    def secili_yol(self) -> str:
        item = self.currentItem()
        return item.data(0, Qt.ItemDataRole.UserRole) if item else ""
