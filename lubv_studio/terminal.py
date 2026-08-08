"""Dahili terminal (kalici PowerShell oturumu) ve Git paneli."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout,
)

from .icons import ikon
from .i18n import t
from .theme import C

_ANSI_RE = re.compile(r"\x1B\[[0-9;?]*[ -/]*[@-~]")


def _mono(size: int = 12) -> QFont:
    font = QFont("Cascadia Mono")
    if not font.exactMatch():
        font = QFont("Consolas")
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setPointSize(size)
    return font


class Terminal(QFrame):
    """Proje klasorunde acilan, durumunu koruyan PowerShell oturumu."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("TerminalPanel")
        self.cwd = ""
        self.proc: QProcess | None = None
        self.gecmis: list[str] = []
        self.gecmis_index = -1

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

        temizle = QPushButton(t("Temizle"))
        temizle.setProperty("kind", "ghost")
        temizle.setProperty("size", "compact")
        temizle.setToolTip(t("Ekrandaki çıktıyı siler"))
        temizle.clicked.connect(self.temizle)

        durdur = QPushButton(t("Yeniden başlat"))
        durdur.setProperty("kind", "ghost")
        durdur.setProperty("size", "compact")
        durdur.setToolTip(t("Çalışan komutu keser ve kabuğu yeniden başlatır"))
        durdur.clicked.connect(self.yeniden_baslat)

        s_duzen.addWidget(simge)
        s_duzen.addWidget(self.baslik)
        s_duzen.addWidget(self.yol_etiketi, 1)
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
        self.cwd = yol or ""
        self.yol_etiketi.setText(self.cwd)
        self.yeniden_baslat()

    def yeniden_baslat(self) -> None:
        self._kabugu_kapat()
        if not self.cwd or not Path(self.cwd).is_dir():
            return
        self.proc = QProcess(self)
        self.proc.setWorkingDirectory(self.cwd)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._oku)
        kabuk = "powershell.exe"
        self.proc.start(
            kabuk,
            ["-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"],
        )
        if self.proc.waitForStarted(4000):
            self._yaz(t("PowerShell oturumu açıldı") + f"  ·  {self.cwd}\n", C["muted"])
            self.calistir("$ProgressPreference='SilentlyContinue'", sessiz=True)
        else:
            self._yaz(t("PowerShell başlatılamadı.") + "\n", C["red"])

    def _kabugu_kapat(self) -> None:
        if self.proc is not None:
            try:
                self.proc.kill()
                self.proc.waitForFinished(1500)
            except Exception:
                pass
            self.proc = None

    def closeEvent(self, event):  # noqa: N802
        self._kabugu_kapat()
        super().closeEvent(event)

    # ---------- calistirma ----------

    def calistir(self, komut: str, sessiz: bool = False) -> None:
        if not komut.strip():
            return
        if self.proc is None or self.proc.state() != QProcess.ProcessState.Running:
            self.yeniden_baslat()
        if self.proc is None:
            self._yaz(t("Terminal hazır değil. Önce proje klasörü seç.") + "\n", C["red"])
            return
        if not sessiz:
            self._yaz(f"\n❯ {komut}\n", C["accent_hi"])
            self.gecmis.append(komut)
            self.gecmis_index = len(self.gecmis)
        self.proc.write((komut + "\n").encode("utf-8"))

    def _gonder(self) -> None:
        komut = self.giris.text()
        self.giris.clear()
        if komut.strip().lower() in ("cls", "clear"):
            self.temizle()
            return
        self.calistir(komut)

    def _oku(self) -> None:
        if self.proc is None:
            return
        ham = bytes(self.proc.readAllStandardOutput())
        metin = ham.decode("utf-8", errors="replace")
        metin = _ANSI_RE.sub("", metin)
        if metin.strip():
            self._yaz(metin, C["text2"])

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
        self.komut_istendi.emit(f'git add -A; git commit -m "{guvenli}"')
        self.mesaj.clear()

    def depo_kur(self) -> None:
        if not self.kimligi_saglat():
            return
        self.komut_istendi.emit(
            'git init; git add -A; git commit -m "Initial commit"'
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

    def _ilk_commit_komutu(self) -> str:
        """Depo yoksa kurar, hic commit yoksa bir tane atar. Varsa hicbir sey yapmaz.

        Commit var mi kontrolu cikis koduyla yapilir: bos depoda
        `git rev-parse HEAD` stdout'a "HEAD" yazdigi icin ciktiya bakmak yanlis
        sonuc verir ve ilk commit hic atilmaz.
        """
        return (
            "if (-not (Test-Path .git)) { git init | Out-Null }; "
            "git rev-parse --verify -q HEAD > $null 2>&1; "
            'if ($LASTEXITCODE -ne 0) { git add -A; git commit -m "Initial commit" | Out-Null }; '
        )

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

        self.komut_istendi.emit(
            self._ilk_commit_komutu()
            + "git remote remove origin 2>$null; "
            + f'git remote add origin "{adres}"; '
            + "git branch -M main; git push -u origin main"
        )

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

        self.komut_istendi.emit(
            self._ilk_commit_komutu()
            + "git branch -M main; "
            + f'gh repo create "{ad}" {bayrak} --source=. --remote=origin --push'
        )
        self.uzak.setText(f"{kullanici}/{ad}")
