"""Dahili terminal (kalici PowerShell oturumu) ve Git paneli."""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
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

    calisma_bitti = Signal()

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
        serit.setFixedHeight(32)
        s_duzen = QHBoxLayout(serit)
        s_duzen.setContentsMargins(12, 0, 8, 0)
        s_duzen.setSpacing(8)

        simge = QLabel()
        simge.setPixmap(ikon("terminal", C["muted"], 14).pixmap(14, 14))
        simge.setFixedSize(14, 14)

        self.baslik = QLabel(t("TERMINAL"))
        self.baslik.setObjectName("SectionLabel")
        self.yol_etiketi = QLabel("")
        self.yol_etiketi.setObjectName("TopPath")

        temizle = QPushButton(t("Temizle"))
        temizle.setProperty("kind", "ghost")
        temizle.setFixedHeight(22)
        temizle.setToolTip(t("Ekrandaki çıktıyı siler"))
        temizle.clicked.connect(self.temizle)

        durdur = QPushButton(t("Yeniden başlat"))
        durdur.setProperty("kind", "ghost")
        durdur.setFixedHeight(22)
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
        self.proc.finished.connect(lambda *_: self.calisma_bitti.emit())
        kabuk = "powershell.exe"
        self.proc.start(
            kabuk,
            ["-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"],
        )
        if self.proc.waitForStarted(4000):
            self._yaz(t("PowerShell oturumu açıldı") + f"  ·  {self.cwd}\n", C["muted"])
            self.calistir("$ProgressPreference='SilentlyContinue'", sessiz=True)
        else:
            self._yaz("PowerShell baslatilamadi.\n", C["red"])

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
            self._yaz("Terminal hazir degil. Once proje klasoru sec.\n", C["red"])
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
    import subprocess

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
    return proc.returncode == 0, ((proc.stdout or "") + (proc.stderr or "")).strip()


class GitPanel(QFrame):
    """Degisiklikleri gor, commit'le, GitHub'a gonder."""

    komut_istendi = Signal(str)   # terminalde calistirilacak komut
    yenile_istendi = Signal()

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
        self.uzak = QLineEdit()
        self.uzak.setPlaceholderText("https://github.com/kullanici/repo.git")
        btn_uzak = QPushButton(t("Uzak depoyu bağla ve gönder"))
        btn_uzak.clicked.connect(self.uzak_bagla)

        duzen.addWidget(baslik)
        duzen.addWidget(self.dal_etiketi)
        duzen.addWidget(self.liste, 1)
        duzen.addWidget(self.mesaj)
        duzen.addLayout(satir1)
        duzen.addLayout(satir2)
        duzen.addSpacing(6)
        duzen.addWidget(uzak_baslik)
        duzen.addWidget(self.uzak)
        duzen.addWidget(btn_uzak)

    # ---------- durum ----------

    def set_cwd(self, yol: str) -> None:
        self.cwd = yol
        self.yenile()

    def yenile(self) -> None:
        self.liste.clear()
        if not self.cwd:
            self.dal_etiketi.setText(t("proje seçilmedi"))
            return

        tamam, dal = git_calistir(self.cwd, "rev-parse", "--abbrev-ref", "HEAD")
        if not tamam:
            self.dal_etiketi.setText(t("bu klasör bir git deposu değil"))
            self.liste.addItem(QListWidgetItem(t("Bu klasörde depo yok. Aşağıdan t('Depo kur') de.")))
            return

        _, uzak = git_calistir(self.cwd, "remote", "get-url", "origin")
        uzak_bilgi = uzak.splitlines()[0] if uzak and "fatal" not in uzak.lower() else t("uzak depo yok")
        self.dal_etiketi.setText(t("dal: ") + dal.strip() + "  ·  " + uzak_bilgi)
        if uzak_bilgi != t("uzak depo yok"):
            self.uzak.setText(uzak_bilgi)

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
        mesaj = self.mesaj.text().strip()
        if not mesaj:
            self.mesaj.setPlaceholderText(t("önce bir commit mesajı yaz"))
            self.mesaj.setFocus()
            return
        guvenli = mesaj.replace('"', "'")
        self.komut_istendi.emit(f'git add -A; git commit -m "{guvenli}"')
        self.mesaj.clear()

    def depo_kur(self) -> None:
        self.komut_istendi.emit(
            'git init; git add -A; git commit -m "ilk commit"'
        )

    def uzak_bagla(self) -> None:
        url = self.uzak.text().strip()
        if not url:
            self.uzak.setFocus()
            return
        self.komut_istendi.emit(
            f'git remote remove origin 2>$null; git remote add origin "{url}"; '
            "git branch -M main; git push -u origin main"
        )
