"""Giris noktasi: uygulamayi baslatir."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QFont, QFontInfo, QIcon
from PySide6.QtWidgets import QApplication

from .config import APP_NAME, Config
from . import platform_
from .i18n import ayarla as dili_ayarla
from .icons import uygulama_ikonu
from .main_window import MainWindow
from .theme import palette


def _eski_surumden_tasi(cfg: Config) -> None:
    """Ilk acilista eski lubv_client.py icindeki anahtari ve klasoru devralir."""
    if cfg.api_key and cfg.project_root:
        return

    kok = Path(__file__).resolve().parent.parent
    adaylar = [
        kok / "eski" / "lubv_client.py",
        kok / "lubv_client.py",
        kok / "lubv_studio" / "lubv_client.py",
    ]
    for aday in adaylar:
        if not aday.exists():
            continue
        try:
            metin = aday.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        if not cfg.api_key:
            es = re.search(r'API_KEY\s*=\s*["\'](sk-[A-Za-z0-9]+)["\']', metin)
            if es:
                cfg.api_key = es.group(1)
        if not cfg.project_root:
            es = re.search(r'PROJECT_ROOT\s*=\s*r?["\'](.+?)["\']', metin)
            if es and Path(es.group(1)).is_dir():
                cfg.project_root = es.group(1)
        break
    cfg.save()


def _paketli() -> bool:
    """PyInstaller ile tek dosya exe olarak mi calisiyoruz?"""
    return getattr(sys, "frozen", False)


def _kaynak(ad: str) -> Path:
    """PyInstaller ile paketlendiginde de dogru yolu bulur."""
    temel = getattr(sys, "_MEIPASS", None)
    if temel:
        aday = Path(temel) / "lubv_studio" / ad
        if aday.exists():
            return aday
        return Path(temel) / ad
    return Path(__file__).resolve().parent / ad


def main() -> int:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True)

    uygulama = QApplication(sys.argv)
    uygulama.setApplicationName(APP_NAME)
    uygulama.setOrganizationName("LUBV")
    uygulama.setStyle("Fusion")
    uygulama.setPalette(palette())   # Fusion'in beyaz varsayilanlarini kapatir

    simge_yolu = _kaynak(platform_.ikon_dosyasi())
    if simge_yolu.exists():
        uygulama.setWindowIcon(QIcon(str(simge_yolu)))
    else:
        uygulama.setWindowIcon(QIcon(uygulama_ikonu(256)))

    yazi = QFont()
    for aday in platform_.ui_yazi_tipleri():
        deneme = QFont(aday)
        if QFontInfo(deneme).family().lower() == aday.lower():
            yazi = deneme
            break
    yazi.setPointSize(13 if platform_.MACOS else 10)
    yazi.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    uygulama.setFont(yazi)

    cfg = Config.load()
    _eski_surumden_tasi(cfg)

    if len(sys.argv) > 1 and Path(sys.argv[1]).is_dir():
        cfg.project_root = str(Path(sys.argv[1]).resolve())

    dili_ayarla(cfg.language)

    pencere = MainWindow(cfg)
    pencere.show()
    sonuc = uygulama.exec()

    # dil degistiyse uygulamayi ayni argumanlarla tekrar ac
    if getattr(pencere, "yeniden_baslat", False):
        QProcess.startDetached(sys.executable, sys.argv[1:] if _paketli() else sys.argv)
    return sonuc


if __name__ == "__main__":
    sys.exit(main())
