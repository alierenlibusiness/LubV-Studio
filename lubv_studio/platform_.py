"""Isletim sistemi farklari tek yerde toplanir.

Uygulama Windows ve macOS'ta ayni sekilde calisir (Linux da calisir, sadece
daha az test edilmistir). Kabuk, yazi tipi ve ikon bicimi gibi platforma gore
degisen ne varsa buradan sorulur; baska hicbir modul sys.platform'a bakmaz.
"""

from __future__ import annotations

import sys

WINDOWS = sys.platform.startswith("win")
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")


def isletim_sistemi() -> str:
    """Modele gonderilen okunabilir ad."""
    if WINDOWS:
        return "Windows"
    if MACOS:
        return "macOS"
    if LINUX:
        return "Linux"
    return sys.platform


def kabuk() -> tuple[str, list[str], str]:
    """Terminal panelinin acacagi kabuk: (program, argumanlar, gorunen ad).

    Hepsi komutlari stdin'den okuyacak sekilde baslatilir; boylece tek bir
    surec acik kalir ve calisma dizini komutlar arasinda korunur.
    """
    if WINDOWS:
        return (
            "powershell.exe",
            ["-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"],
            "PowerShell",
        )
    if MACOS:
        return ("/bin/zsh", [], "zsh")
    return ("/bin/bash", [], "bash")


def kabuk_adi() -> str:
    return kabuk()[2]


def ui_yazi_tipleri() -> list[str]:
    """Arayuz yazi tipi adaylari, ilk bulunan kullanilir."""
    if WINDOWS:
        return ["Segoe UI", "Tahoma"]
    if MACOS:
        return ["SF Pro Text", "Helvetica Neue", "Helvetica"]
    return ["Inter", "Cantarell", "DejaVu Sans"]


def kod_yazi_tipleri() -> list[str]:
    """Kod ve terminal icin sabit genislikli yazi tipi adaylari."""
    if WINDOWS:
        return ["Cascadia Mono", "Consolas", "Courier New"]
    if MACOS:
        return ["SF Mono", "Menlo", "Monaco", "Courier New"]
    return ["JetBrains Mono", "DejaVu Sans Mono", "monospace"]


def ikon_dosyasi() -> str:
    """Pencere ikonu icin dosya adi. macOS .icns ister, Windows .ico."""
    return "lubv.icns" if MACOS else "lubv.ico"


def gorev_cubugu_ikonu_gerekli() -> bool:
    """macOS'ta ikon .app paketinden gelir, kod icinden atamaya gerek yok."""
    return not MACOS


def kod_yazi_tipi(boyut: int = 12):
    """Sistemde bulunan ilk sabit genislikli yazi tipini QFont olarak verir."""
    from PySide6.QtGui import QFont, QFontInfo

    for ad in kod_yazi_tipleri():
        font = QFont(ad)
        if QFontInfo(font).fixedPitch() or QFontInfo(font).family().lower() == ad.lower():
            font.setStyleHint(QFont.StyleHint.Monospace)
            font.setPointSize(boyut)
            return font
    font = QFont()
    font.setStyleHint(QFont.StyleHint.Monospace)
    font.setFamily(font.defaultFamily())
    font.setPointSize(boyut)
    return font
