"""Isletim sistemi farklari tek yerde toplanir.

Uygulama Windows ve macOS'ta ayni sekilde calisir (Linux da calisir, sadece
daha az test edilmistir). Kabuk, yazi tipi ve ikon bicimi gibi platforma gore
degisen ne varsa buradan sorulur; baska hicbir modul sys.platform'a bakmaz.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

WINDOWS = sys.platform.startswith("win")
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")

# Windows'ta yeni surec acilirken konsol penceresi parlamasin (paketli exe'de
# her komutta siyah pencere aciliyordu).
GIZLI_PENCERE = getattr(subprocess, "CREATE_NO_WINDOW", 0) if WINDOWS else 0


def isletim_sistemi() -> str:
    """Modele gonderilen okunabilir ad."""
    if WINDOWS:
        return "Windows"
    if MACOS:
        return "macOS"
    if LINUX:
        return "Linux"
    return sys.platform


def _windows_kabugu() -> tuple[str, str]:
    """PowerShell 7 kuruluysa onu, degilse Windows PowerShell'i secer."""
    pwsh = shutil.which("pwsh") or shutil.which("pwsh.exe")
    if pwsh:
        return pwsh, "PowerShell 7"
    return shutil.which("powershell") or "powershell.exe", "PowerShell"


def _posix_kabugu() -> tuple[str, str]:
    """Kullanicinin kendi kabugu varsa o, yoksa platformun varsayilani."""
    tercih = (os.environ.get("SHELL") or "").strip()
    if tercih and Path(tercih).exists():
        return tercih, tercih.rsplit("/", 1)[-1]
    if MACOS:
        return "/bin/zsh", "zsh"
    return shutil.which("bash") or "/bin/bash", "bash"


def kabuk() -> tuple[str, list[str], str]:
    """Terminal panelinin acacagi kabuk: (program, argumanlar, gorunen ad).

    Hepsi komutlari stdin'den okuyacak sekilde baslatilir; boylece tek bir
    surec acik kalir ve calisma dizini komutlar arasinda korunur.
    """
    if WINDOWS:
        program, ad = _windows_kabugu()
        return (
            program,
            ["-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "-"],
            ad,
        )
    # stdin bir boru oldugu icin -i (etkilesimli) kullanilmaz: is denetimi
    # uyarilari ciktiyi kirletiyor. Kabuk komutlari boruyu okuyarak calistirir.
    program, ad = _posix_kabugu()
    return (program, ["-s"], ad)


def kabuk_adi() -> str:
    return kabuk()[2]


def komut_argumanlari(komut: str) -> list[str]:
    """Tek seferlik bir komutu kullanicinin kabugunda calistiracak arguman listesi.

    Ajanin komutlari da terminal panelindeki kabukla ayni sozdizimini kullansin
    diye burada uretilir. Onceden shell=True ile cmd.exe kullaniliyordu ve model
    PowerShell sozdizimi yazdiginda komut sessizce patliyordu.

    Tek istisna: Windows PowerShell 5.1 `&&` ve `||` zincirlerini ayristiramaz
    ("cd app && npm install" gibi cok yaygin bir kalip). PowerShell 7 yoksa ve
    komutta boyle bir zincir varsa komut cmd.exe'ye verilir.
    """
    if WINDOWS:
        program, ad = _windows_kabugu()
        if ad == "PowerShell" and ("&&" in komut or "||" in komut):
            comspec = os.environ.get("COMSPEC") or "cmd.exe"
            return [comspec, "/d", "/s", "/c", komut]
        hazirlik = (
            "$ProgressPreference='SilentlyContinue'; "
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; "
        )
        return [
            program, "-NoLogo", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command", hazirlik + komut,
        ]
    program, _ = _posix_kabugu()
    return [program, "-lc", komut]


def kabuk_hazirlik_komutlari() -> list[str]:
    """Kabuk acilir acilmaz calistirilan, ciktiyi duzelten komutlar."""
    if WINDOWS:
        komutlar = [
            "$ProgressPreference='SilentlyContinue'",
            "[Console]::OutputEncoding=[System.Text.Encoding]::UTF8",
            "$OutputEncoding=[System.Text.Encoding]::UTF8",
            "$env:GIT_PAGER='cat'",
        ]
        if shutil.which("pwsh"):
            # PowerShell 7 ciktiya ANSI renk kacislari basiyor, duz metne cevir
            komutlar.append("$PSStyle.OutputRendering='PlainText'")
        return komutlar
    return ["export LANG=${LANG:-en_US.UTF-8}", "export PAGER=cat", "export GIT_PAGER=cat"]


def bitis_isareti_komutu(isaret: str) -> str:
    """Komut bitisini ve guncel klasoru bildiren tek satirlik kabuk ifadesi.

    Terminal panelinin "komut bitti mi, cikis kodu ne, hangi klasordeyiz"
    sorularini cevaplamasi icin her komuttan sonra gonderilir.
    """
    if WINDOWS:
        return (
            "$__lubv_ok=$?; $__lubv_rc=$LASTEXITCODE; "
            "Write-Output (\"" + isaret + " {0} {1}\" -f "
            "$(if ($__lubv_ok) {0} elseif ($__lubv_rc) {$__lubv_rc} else {1}), "
            "$(Get-Location).Path)"
        )
    return f'printf "{isaret} %s %s\\n" "$?" "$PWD"'


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
