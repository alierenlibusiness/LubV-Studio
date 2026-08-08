"""Dahili terminal (kalici kabuk oturumu) ve Git paneli.

Kabuk platforma gore secilir: Windows'ta PowerShell, macOS'ta zsh,
Linux'ta bash. Bkz. platform_.kabuk().
"""

from __future__ import annotations

import re
import subprocess
import time
import uuid
from pathlib import Path

from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from . import platform_
from .icons import ikon
from .i18n import t
from .theme import C

_ANSI_RE = re.compile(r"\x1B\[[0-9;?]*[ -/]*[@-~]")


def _mono(size: int = 12) -> QFont:
    return platform_.kod_yazi_tipi(size)


class Terminal(QFrame):
    """Proje klasorunde acilan, durumunu koruyan kabuk oturumu.

    Kabuk stdin'den beslendigi icin normalde "komut bitti mi, cikis kodu ne,
    hangi klasordeyiz" bilinemez. Her komuttan sonra gizli bir bitis satiri
    gonderilir; ciktida o satir gorununce durum serit guncellenir ve satir
    ekrandan ayiklanir. Kullanici sadece kendi komutunun ciktisini gorur.
    """

    calisma_degisti = Signal(bool)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TerminalPanel")
        self.cwd = ""
        self.proc: QProcess | None = None
        self.gecmis: list[str] = []
        self.gecmis_index = -1
        self.calisiyor = False
        self._tampon = ""
        self._isaret = f"__LUBV_{uuid.uuid4().hex[:10]}__"
        self._isaret_re = re.compile(
            re.escape(self._isaret) + r" (-?\d+) ?(.*)"
        )
        self._baslangic = time.monotonic()

        duzen = QVBoxLayout(self)
        duzen.setContentsMargins(0, 0, 0, 0)
        duzen.setSpacing(0)

        # ust seritte baslik ve butonlar
        serit = QFrame()
        serit.setObjectName("TopBar")
        serit.setFixedHeight(34)
        s_duzen = QHBoxLayout(serit)
        s_duzen.setContentsMargins(12, 0, 8, 0)
        s_duzen.setSpacing(6)
        s_duzen.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        simge = QLabel()
        simge.setPixmap(ikon("terminal", C["muted"], 14).pixmap(14, 14))
        simge.setFixedSize(14, 14)

        self.baslik = QLabel(t("TERMINAL"))
        self.baslik.setObjectName("SectionLabel")
        self.yol_etiketi = QLabel("")
        self.yol_etiketi.setObjectName("TopPath")

        self.durum_rozet = QLabel("")
        self.durum_rozet.setObjectName("Badge")
        self.durum_rozet.setVisible(False)

        temizle = QPushButton(t("Temizle"))
        temizle.setProperty("kind", "ghost")
        temizle.setProperty("size", "compact")
        temizle.setToolTip(t("Ekrandaki çıktıyı siler"))
        temizle.clicked.connect(self.temizle)

        self.kes_dugme = QPushButton(t("Durdur"))
        self.kes_dugme.setProperty("kind", "danger")
        self.kes_dugme.setProperty("size", "compact")
        self.kes_dugme.setToolTip(t("Çalışan komutu keser"))
        self.kes_dugme.clicked.connect(self.komutu_kes)
        self.kes_dugme.setVisible(False)

        durdur = QPushButton(t("Yeniden başlat"))
        durdur.setProperty("kind", "ghost")
        durdur.setProperty("size", "compact")
        durdur.setToolTip(t("Çalışan komutu keser ve kabuğu yeniden başlatır"))
        durdur.clicked.connect(self.yeniden_baslat)

        s_duzen.addWidget(simge)
        s_duzen.addWidget(self.baslik)
        s_duzen.addWidget(self.yol_etiketi, 1)
        s_duzen.addWidget(self.durum_rozet)
        s_duzen.addWidget(self.kes_dugme)
        s_duzen.addWidget(temizle)
        s_duzen.addWidget(durdur)

        # cikti
        self.cikti = QPlainTextEdit()
        self.cikti.setReadOnly(True)
        self.cikti.setFont(_mono())
        self.cikti.setStyleSheet(
            f"QPlainTextEdit{{background:{C['kod']}; border:none; "
            f"padding:8px 12px; color:{C['text2']};}}"
        )
        self.cikti.setMaximumBlockCount(5000)

        # giris
        giris_kutu = QFrame()
        g_duzen = QHBoxLayout(giris_kutu)
        g_duzen.setContentsMargins(12, 6, 12, 8)
        g_duzen.setSpacing(8)
        isaret = QLabel("❯")
        isaret.setStyleSheet(f"color:{C['green']}; font-weight:800; font-size:14px;")
        self.giris = QLineEdit()
        self.giris.setPlaceholderText(t("komut yaz ve Enter'a bas, örnek: git status"))
        self.giris.setFont(_mono())
        self.giris.returnPressed.connect(self._gonder)
        self.giris.installEventFilter(self)
        g_duzen.addWidget(isaret)
        g_duzen.addWidget(self.giris)

        duzen.addWidget(serit)
        duzen.addWidget(self.cikti, 1)
        duzen.addWidget(giris_kutu)

    # ---------- kabuk yonetimi ----------

    def set_cwd(self, yol: str) -> None:
        yeni = yol or ""
        if yeni == self.cwd and self.hazir_mi():
            return   # ayni klasor icin kabugu bosuna yeniden baslatma
        self.cwd = yeni
        self.yol_etiketi.setText(self.cwd)
        self.yeniden_baslat()

    def hazir_mi(self) -> bool:
        return (
            self.proc is not None
            and self.proc.state() == QProcess.ProcessState.Running
        )

    def yeniden_baslat(self) -> None:
        self.kabugu_kapat()
        self._durum_ayarla(False)
        self._tampon = ""
        if not self.cwd or not Path(self.cwd).is_dir():
            self.yol_etiketi.setText(t("proje seçilmedi"))
            return

        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(self.cwd)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._oku)
        self.proc.finished.connect(self._kabuk_bitti)
        self.proc.errorOccurred.connect(self._kabuk_hatasi)

        ortam = QProcessEnvironment.systemEnvironment()
        ortam.insert("PYTHONIOENCODING", "utf-8")
        ortam.insert("PYTHONUNBUFFERED", "1")
        ortam.insert("GIT_PAGER", "cat")
        ortam.insert("PAGER", "cat")
        ortam.insert("TERM", "dumb")
        self.proc.setProcessEnvironment(ortam)

        program, argumanlar, ad = platform_.kabuk()
        self.proc.start(program, argumanlar)
        if not self.proc.waitForStarted(6000):
            self._yaz(t("Kabuk başlatılamadı.") + f" ({program})\n", C["red"])
            self.proc = None
            return

        self._yaz(f"{ad} {t('oturumu açıldı')}  ·  {self.cwd}\n", C["muted"])
        # ciktiyi bozan varsayilanlar (ilerleme cubugu, renk kacislari, kod
        # sayfasi) daha ilk komuttan once kapatilir
        for hazirlik in platform_.kabuk_hazirlik_komutlari():
            self._ham_yaz(hazirlik)

    def kabugu_kapat(self) -> None:
        if self.proc is None:
            return
        try:
            self.proc.readyReadStandardOutput.disconnect()
            self.proc.finished.disconnect()
            self.proc.errorOccurred.disconnect()
        except Exception:
            pass
        try:
            self.proc.kill()
            self.proc.waitForFinished(1500)
        except Exception:
            pass
        self.proc = None

    def _kabuk_bitti(self, kod: int, _durum) -> None:
        self._durum_ayarla(False)
        self._yaz(f"\n{t('Kabuk kapandı')} ({kod}). {t('Yeniden başlat.')}\n", C["muted"])

    def _kabuk_hatasi(self, _hata) -> None:
        self._durum_ayarla(False)

    def closeEvent(self, event):  # noqa: N802
        self.kabugu_kapat()
        super().closeEvent(event)

    # ---------- calistirma ----------

    def _ham_yaz(self, satir: str) -> None:
        """Kabuga ekranda gorunmeden bir satir gonderir."""
        if self.hazir_mi():
            self.proc.write((satir + "\n").encode("utf-8"))

    def calistir(self, komut: str, sessiz: bool = False) -> None:
        if not komut.strip():
            return
        if not self.hazir_mi():
            self.yeniden_baslat()
        if not self.hazir_mi():
            self._yaz(t("Terminal hazır değil. Önce proje klasörü seç.") + "\n", C["red"])
            return

        if not sessiz:
            self._yaz(f"\n❯ {komut}\n", C["accent_hi"])
            if not self.gecmis or self.gecmis[-1] != komut:
                self.gecmis.append(komut)
            self.gecmis_index = len(self.gecmis)
            self._durum_ayarla(True)
            self._baslangic = time.monotonic()

        self.proc.write((komut + "\n").encode("utf-8"))
        if not sessiz:
            # bitis isareti: cikis kodu ve guncel klasor buradan ogrenilir
            self._ham_yaz(platform_.bitis_isareti_komutu(self._isaret))

    def komutu_kes(self) -> None:
        """Calisan komutu keser. Kabuk stdin ile beslendigi icin tek guvenilir
        yol sureci kapatip yeniden acmaktir; klasor korunur."""
        if not self.calisiyor:
            return
        self._yaz("\n" + t("komut kesildi") + "\n", C["red"])
        self.yeniden_baslat()   # self.cwd korunur, kabuk ayni klasorde acilir

    def _gonder(self) -> None:
        komut = self.giris.text()
        self.giris.clear()
        if komut.strip().lower() in ("cls", "clear"):
            self.temizle()
            return
        self.calistir(komut)

    def _durum_ayarla(self, calisiyor: bool) -> None:
        self.calisiyor = calisiyor
        self.kes_dugme.setVisible(calisiyor)
        self.durum_rozet.setVisible(calisiyor)
        if calisiyor:
            self.durum_rozet.setText(t("çalışıyor"))
            self.durum_rozet.setProperty("tone", "amber")
        self.durum_rozet.style().unpolish(self.durum_rozet)
        self.durum_rozet.style().polish(self.durum_rozet)
        self.calisma_degisti.emit(calisiyor)

    def _oku(self) -> None:
        if self.proc is None:
            return
        ham = bytes(self.proc.readAllStandardOutput())
        if not ham:
            return
        self._tampon += ham.decode("utf-8", errors="replace")

        # bitis isareti tam satir olarak gelmis olabilir; satir satir isle
        while "\n" in self._tampon:
            satir, self._tampon = self._tampon.split("\n", 1)
            self._satir_isle(satir)

        # Satir sonu gelmemis kalan parca (ornegin ilerleme yazisi) beklerken
        # ekranda gorunmezse kullanici uygulama dondu saniyor. Ancak isaretin
        # yarisi gelmis olabilir; onu basip tamponu bosaltmak isaretin geri
        # kalanini eslesmez hale getirir ve "calisiyor" rozeti sonsuza kadar
        # asili kalirdi. Isaretin baslangici olabilecek parca bekletilir.
        if self._tampon and not self._isaret_baslangici_olabilir(self._tampon):
            temiz = _ANSI_RE.sub("", self._tampon)
            if temiz.strip():
                self._yaz(temiz, C["text2"])
                self._tampon = ""

    def _isaret_baslangici_olabilir(self, tampon: str) -> bool:
        """Tampon isareti iceriyor ya da isaretin bir onekiyle bitiyor mu?"""
        if self._isaret in tampon:
            return True
        en_fazla = min(len(tampon), len(self._isaret) - 1)
        return any(
            tampon.endswith(self._isaret[:uzunluk])
            for uzunluk in range(en_fazla, 0, -1)
        )

    def _satir_isle(self, satir: str) -> None:
        temiz = _ANSI_RE.sub("", satir).replace("\r", "")
        es = self._isaret_re.search(temiz)
        if es is None:
            if temiz.strip() or self.cikti.blockCount() > 1:
                self._yaz(temiz + "\n", C["text2"])
            return

        # bitis isareti: kullaniciya gosterilmez, durum seride yansir
        kod = es.group(1)
        klasor = (es.group(2) or "").strip()
        if klasor and Path(klasor).is_dir():
            self.cwd = klasor
            self.yol_etiketi.setText(klasor)

        gecen = time.monotonic() - self._baslangic
        renk = C["muted"] if kod == "0" else C["red"]
        self._yaz(
            f"{t('bitti')}  ·  {t('çıkış')} {kod}  ·  {gecen:.2f}s\n", renk
        )
        self._durum_ayarla(False)

    def _yaz(self, metin: str, renk: str) -> None:
        imlec = self.cikti.textCursor()
        imlec.movePosition(QTextCursor.MoveOperation.End)
        bicim = imlec.charFormat()
        bicim.setForeground(QColor(renk))
        imlec.setCharFormat(bicim)
        imlec.insertText(metin)
        self.cikti.setTextCursor(imlec)
        self.cikti.ensureCursorVisible()

    def ajan_ciktisi(self, komut: str, cikti: str, basarili: bool) -> None:
        """LUBV bir komut calistirdiginda burada da gorunsun.

        Ajan kendi kabugunda calisir; buraya yazmasak kullanici ne yapildigini
        sadece sohbet kartinda gorurdu. Her sey tek yerde toplansin diye
        komut ve ciktisi terminale de dusulur.
        """
        self._yaz(f"\n[LUBV] ❯ {komut}\n", C["violet"])
        kirpik = cikti if len(cikti) <= 4000 else cikti[:4000] + "\n... (kirpildi)"
        self._yaz(kirpik.rstrip() + "\n", C["text2"] if basarili else C["red"])

    def temizle(self) -> None:
        self.cikti.clear()

    def odakla(self) -> None:
        self.giris.setFocus()

    # ---------- klavye gecmisi ----------

    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self.giris and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                if self.gecmis:
                    self.gecmis_index = max(0, self.gecmis_index - 1)
                    self.giris.setText(self.gecmis[self.gecmis_index])
                return True
            if event.key() == Qt.Key.Key_Down:
                if self.gecmis:
                    self.gecmis_index = min(len(self.gecmis), self.gecmis_index + 1)
                    self.giris.setText(
                        self.gecmis[self.gecmis_index]
                        if self.gecmis_index < len(self.gecmis) else ""
                    )
                return True
        return super().eventFilter(obj, event)


# --------------------------------------------------------------------------
# Git
# --------------------------------------------------------------------------

def git_calistir(cwd: str, *args: str, timeout: int = 30) -> tuple[bool, str]:
    """Tek seferlik git komutu (panel icin, ciktiyi programa alir)."""
    if not cwd:
        return False, t("Proje klasörü yok.")
    try:
        proc = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=platform_.GIZLI_PENCERE,
        )
    except FileNotFoundError:
        return False, t("Git bulunamadı. https://git-scm.com adresinden kur.")
    except Exception as exc:
        return False, str(exc)
    # Sadece sondaki bosluklar atilir: `status --porcelain` ciktisinda ilk iki
    # sutun durum kodudur ve bastaki bosluk anlamlidir, strip() onu yiyip
    # dosya adinin ilk harfini kirpiyordu.
    return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or "")).rstrip()


class GitPanel(QFrame):
    """Degisiklikleri gor, commit'le, GitHub'a gonder."""

    komut_istendi = Signal(str)   # terminalde calistirilacak komut

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.cwd = ""
        duzen = QVBoxLayout(self)
        duzen.setContentsMargins(14, 12, 14, 12)
        duzen.setSpacing(10)

        baslik = QLabel(t("KAYNAK KONTROL"))
        baslik.setObjectName("SectionLabel")

        self.dal_etiketi = QLabel(t("depo yok"))
        self.dal_etiketi.setObjectName("PanelHint")

        self.liste = QListWidget()
        self.liste.setMinimumHeight(120)
        self.liste.itemDoubleClicked.connect(self._fark_goster)

        self.mesaj = QLineEdit()
        self.mesaj.setPlaceholderText(t("commit mesajı"))
        self.mesaj.returnPressed.connect(self.commit_et)

        satir1 = QHBoxLayout()
        satir1.setSpacing(6)
        self.btn_commit = QPushButton(t("Commit"))
        self.btn_commit.setProperty("kind", "primary")
        self.btn_commit.clicked.connect(self.commit_et)
        self.btn_push = QPushButton(t("Push"))
        self.btn_push.clicked.connect(lambda: self.komut_istendi.emit("git push"))
        self.btn_pull = QPushButton(t("Pull"))
        self.btn_pull.clicked.connect(lambda: self.komut_istendi.emit("git pull --rebase"))
        satir1.addWidget(self.btn_commit, 2)
        satir1.addWidget(self.btn_push, 1)
        satir1.addWidget(self.btn_pull, 1)

        satir2 = QHBoxLayout()
        satir2.setSpacing(6)
        btn_yenile = QPushButton(t("Yenile"))
        btn_yenile.setProperty("kind", "ghost")
        btn_yenile.clicked.connect(self.yenile)
        btn_log = QPushButton(t("Geçmiş"))
        btn_log.setProperty("kind", "ghost")
        btn_log.clicked.connect(
            lambda: self.komut_istendi.emit("git log --oneline --graph -20")
        )
        btn_init = QPushButton(t("Depo kur"))
        btn_init.setProperty("kind", "ghost")
        btn_init.setToolTip(t("git init ve ilk commit"))
        btn_init.clicked.connect(self.depo_kur)
        satir2.addWidget(btn_yenile)
        satir2.addWidget(btn_log)
        satir2.addWidget(btn_init)

        uzak_baslik = QLabel(t("GITHUB"))
        uzak_baslik.setObjectName("SectionLabel")

        self.hesap_etiketi = QLabel("")
        self.hesap_etiketi.setObjectName("PanelHint")
        self.hesap_etiketi.setWordWrap(True)

        self.uzak = QLineEdit()
        self.uzak.setPlaceholderText("kullanici/repo")
        self.uzak.setToolTip(
            "kullanici/repo  ·  https://github.com/kullanici/repo  ·  git@github.com:..."
        )
        self.uzak.returnPressed.connect(self.uzak_bagla)

        satir3 = QHBoxLayout()
        satir3.setSpacing(6)
        self.btn_yeni_repo = QPushButton(t("GitHub'da repo aç"))
        self.btn_yeni_repo.setToolTip(t("Yeni bir depo oluşturur ve projeyi gönderir"))
        self.btn_yeni_repo.clicked.connect(self.github_repo_olustur)
        btn_uzak = QPushButton(t("Bağla ve gönder"))
        btn_uzak.setProperty("kind", "primary")
        btn_uzak.setToolTip(t("Var olan bir depoya bağlanır ve projeyi gönderir"))
        btn_uzak.clicked.connect(self.uzak_bagla)
        satir3.addWidget(self.btn_yeni_repo, 1)
        satir3.addWidget(btn_uzak, 1)

        duzen.addWidget(baslik)
        duzen.addWidget(self.dal_etiketi)
        duzen.addWidget(self.liste, 1)
        duzen.addWidget(self.mesaj)
        duzen.addLayout(satir1)
        duzen.addLayout(satir2)
        duzen.addSpacing(6)
        duzen.addWidget(uzak_baslik)
        duzen.addWidget(self.hesap_etiketi)
        duzen.addWidget(self.uzak)
        duzen.addLayout(satir3)

    # ---------- durum ----------

    def set_cwd(self, yol: str) -> None:
        self.cwd = yol
        self.yenile()
        self.hesabi_tazele()

    def yenile(self) -> None:
        self.liste.clear()
        if not self.cwd:
            self.dal_etiketi.setText(t("proje seçilmedi"))
            return

        tamam, dal = git_calistir(self.cwd, "rev-parse", "--abbrev-ref", "HEAD")
        if not tamam:
            self.dal_etiketi.setText(t("bu klasör bir git deposu değil"))
            self.liste.addItem(QListWidgetItem(t("Bu klasörde git deposu yok.")))
            return

        _, uzak = git_calistir(self.cwd, "remote", "get-url", "origin")
        uzak_bilgi = uzak.splitlines()[0] if uzak and "fatal" not in uzak.lower() else t("uzak depo yok")
        self.dal_etiketi.setText(t("dal: ") + dal.strip() + "  ·  " + uzak_bilgi)
        if uzak_bilgi != t("uzak depo yok"):
            self.uzak.setText(uzak_bilgi)
            self.uzak.setCursorPosition(0)   # uzun adreste bas gorunsun

        tamam, durum = git_calistir(self.cwd, "status", "--porcelain")
        if not durum.strip():
            self.liste.addItem(QListWidgetItem(t("Değişiklik yok, her şey temiz")))
            return
        for satir in durum.splitlines():
            kod = satir[:2].strip() or "?"
            ad = satir[3:].strip()
            simge = {"M": "~", "A": "+", "D": "-", "??": "+", "R": "→"}.get(kod, kod)
            item = QListWidgetItem(f"{simge}  {ad}")
            renk = {
                "M": C["amber"], "A": C["green"], "??": C["green"],
                "D": C["red"], "R": C["accent"],
            }.get(kod, C["text2"])
            item.setForeground(QColor(renk))
            item.setData(Qt.ItemDataRole.UserRole, ad)
            self.liste.addItem(item)

    def _fark_goster(self, item: QListWidgetItem) -> None:
        ad = item.data(Qt.ItemDataRole.UserRole)
        if ad:
            self.komut_istendi.emit(f'git diff -- "{ad}"')

    # ---------- eylemler ----------

    def commit_et(self) -> None:
        if not self.kimligi_saglat():
            return
        mesaj = self.mesaj.text().strip()
        if not mesaj:
            self.mesaj.setPlaceholderText(t("önce bir commit mesajı yaz"))
            self.mesaj.setFocus()
            return
        guvenli = mesaj.replace('"', "'")
        self._komutlari_gonder(["git add -A", f'git commit -m "{guvenli}"'])
        self.mesaj.clear()

    def depo_kur(self) -> None:
        if not self.kimligi_saglat():
            return
        self._komutlari_gonder(
            ["git init", "git add -A", 'git commit -m "Initial commit"']
        )

    # ---------- git kimligi ----------

    def _kimlik_var_mi(self) -> bool:
        ad = git_calistir(self.cwd, "config", "user.name")[1].strip()
        posta = git_calistir(self.cwd, "config", "user.email")[1].strip()
        return bool(ad and posta)

    def kimligi_saglat(self) -> bool:
        """Commit atabilmek icin git kimligi sart. Yoksa bir kez sorup kaydeder."""
        if self._kimlik_var_mi():
            return True

        # GitHub CLI girisliyse oradan on doldur
        varsayilan_ad, varsayilan_posta = "", ""
        _, kullanici = self._gh_durumu()
        if kullanici:
            varsayilan_ad = kullanici
            varsayilan_posta = f"{kullanici}@users.noreply.github.com"

        ad, tamam = QInputDialog.getText(
            self, t("Git kimliği"),
            t("Commit'lerde görünecek isim:"), text=varsayilan_ad,
        )
        if not tamam or not ad.strip():
            return False
        posta, tamam = QInputDialog.getText(
            self, t("Git kimliği"),
            t("Commit'lerde görünecek e-posta:"), text=varsayilan_posta,
        )
        if not tamam or not posta.strip():
            return False

        for anahtar, deger in (("user.name", ad.strip()), ("user.email", posta.strip())):
            git_calistir(self.cwd, "config", "--global", anahtar, deger)

        if not self._kimlik_var_mi():
            QMessageBox.warning(
                self, t("Git kimliği"), t("Kimlik kaydedilemedi, terminalden dene.")
            )
            return False
        return True

    # ---------- GitHub ----------

    def _gh_durumu(self) -> tuple[bool, str]:
        """GitHub CLI kurulu ve giris yapilmis mi? (kurulu_mu, kullanici_adi)"""
        try:
            proc = subprocess.run(
                ["gh", "auth", "status"], capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=10,
                creationflags=platform_.GIZLI_PENCERE,
            )
        except FileNotFoundError:
            return False, ""
        except Exception:
            return False, ""
        cikti = (proc.stdout or "") + (proc.stderr or "")
        es = re.search(r"account\s+(\S+)", cikti) or re.search(r"as\s+(\S+)", cikti)
        return True, (es.group(1) if es and proc.returncode == 0 else "")

    def hesabi_tazele(self) -> None:
        kurulu, kullanici = self._gh_durumu()
        if not kurulu:
            self.hesap_etiketi.setText(t("GitHub CLI kurulu değil, repo adresini elle yapıştır"))
            self.btn_yeni_repo.setEnabled(True)
        elif kullanici:
            self.hesap_etiketi.setText(t("GitHub hesabı: ") + kullanici)
            self.btn_yeni_repo.setEnabled(True)
        else:
            self.hesap_etiketi.setText(t("GitHub CLI kurulu ama giriş yapılmamış"))
            self.btn_yeni_repo.setEnabled(True)

    @staticmethod
    def github_adresi(metin: str) -> str:
        """kullanici/repo, github.com/... veya tam URL girdisini tek bicime cevirir."""
        ham = (metin or "").strip().strip('"').strip("'").rstrip("/")
        if not ham:
            return ""
        if ham.startswith("git@") or ham.startswith("ssh://"):
            return ham
        if ham.startswith("http://"):
            ham = "https://" + ham[len("http://"):]
        if ham.startswith("https://"):
            return ham
        if ham.startswith("github.com/") or ham.startswith("www.github.com/"):
            return "https://" + ham.removeprefix("www.")
        if re.fullmatch(r"[\w.-]+/[\w.-]+", ham):
            return f"https://github.com/{ham}"
        return ""

    def _ilk_commit_komutu(self) -> list[str]:
        """Depo yoksa kurar, hic commit yoksa bir tane atar. Varsa hicbir sey yapmaz.

        Commit var mi kontrolu cikis koduyla yapilir: bos depoda
        `git rev-parse HEAD` stdout'a "HEAD" yazdigi icin ciktiya bakmak yanlis
        sonuc verir ve ilk commit hic atilmaz.
        """
        komutlar: list[str] = []
        if not (Path(self.cwd) / ".git").is_dir():
            komutlar.append("git init")
        if not self._commit_var_mi():
            komutlar += ["git add -A", 'git commit -m "Initial commit"']
        return komutlar

    def _commit_var_mi(self) -> bool:
        """Depoda en az bir commit var mi?

        Cikis koduna bakilir: bos depoda `git rev-parse HEAD` stdout'a "HEAD"
        yazdigi icin ciktiya bakmak yanlis sonuc verir.
        """
        return git_calistir(self.cwd, "rev-parse", "--verify", "HEAD")[0]

    def _uzak_var_mi(self) -> bool:
        return git_calistir(self.cwd, "remote", "get-url", "origin")[0]

    def _komutlari_gonder(self, komutlar: list[str]) -> None:
        """Komutlari sirayla terminale yollar; kullanici hepsini ve ciktisini gorur."""
        for komut in komutlar:
            self.komut_istendi.emit(komut)

    def uzak_bagla(self) -> None:
        if not self.kimligi_saglat():
            return
        adres = self.github_adresi(self.uzak.text())
        if not adres:
            QMessageBox.warning(
                self, t("GITHUB"),
                t("Geçerli bir depo adresi yaz. Örnek: kullanici/repo"),
            )
            self.uzak.setFocus()
            return

        # Kabuk sozdizimi kullanilmaz (PowerShell / zsh / bash hepsinde ayni
        # calissin diye): kosullar Python tarafinda cozulur, terminale sadece
        # duz git komutlari gider.
        komutlar = self._ilk_commit_komutu()
        komutlar.append(
            f'git remote set-url origin "{adres}"' if self._uzak_var_mi()
            else f'git remote add origin "{adres}"'
        )
        komutlar += ["git branch -M main", "git push -u origin main"]
        self._komutlari_gonder(komutlar)

    def github_repo_olustur(self) -> None:
        if not self.cwd or not self.kimligi_saglat():
            return
        kurulu, kullanici = self._gh_durumu()

        if not kurulu:
            cevap = QMessageBox.question(
                self, t("GITHUB"),
                t(
                    "Uygulama içinden repo açmak için GitHub CLI gerekiyor "
                    "(cli.github.com). Şimdi tarayıcıda yeni repo sayfasını "
                    "açayım mı? Sonra adresi yukarıdaki kutuya yapıştır."
                ),
            )
            if cevap == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl("https://github.com/new"))
            return

        if not kullanici:
            cevap = QMessageBox.question(
                self, t("GITHUB"),
                t("GitHub CLI kurulu ama giriş yapılmamış. Giriş başlatılsın mı?"),
            )
            if cevap == QMessageBox.StandardButton.Yes:
                self.komut_istendi.emit("gh auth login --web --git-protocol https")
            return

        varsayilan = Path(self.cwd).name
        ad, tamam = QInputDialog.getText(
            self, t("GitHub'da repo aç"), t("Depo adı:"), text=varsayilan
        )
        if not tamam or not ad.strip():
            return
        ad = re.sub(r"[^\w.-]+", "-", ad.strip())

        gorunurluk = QMessageBox.question(
            self, t("GitHub'da repo aç"),
            t("Depo herkese açık (public) olsun mu? Hayır dersen özel (private) olur."),
        )
        bayrak = "--public" if gorunurluk == QMessageBox.StandardButton.Yes else "--private"

        komutlar = self._ilk_commit_komutu()
        komutlar += [
            "git branch -M main",
            f'gh repo create "{ad}" {bayrak} --source=. --remote=origin --push',
        ]
        self._komutlari_gonder(komutlar)
        self.uzak.setText(f"{kullanici}/{ad}")
        self.uzak.setCursorPosition(0)
