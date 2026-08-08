"""LUBV Studio'yu tek parca calistirilabilir dosya haline getirir.

Kullanim:
    python build_exe.py       (Windows'ta build.bat, macOS'ta ./build.sh)

Sonuc:
    Windows :  dist/LUBV Studio.exe   (cift tiklanir, Python gerekmez)
    macOS   :  dist/LUBV Studio.app   (Uygulamalar'a surukle)
    Linux   :  dist/LUBV Studio       (calistirilabilir dosya)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
AD = "LUBV Studio"
PAKET = KOK / "lubv_studio"

WINDOWS = sys.platform.startswith("win")
MACOS = sys.platform == "darwin"


def calistir(*komut: str) -> None:
    print(">", " ".join(komut))
    sonuc = subprocess.run(komut)
    if sonuc.returncode != 0:
        sys.exit(f"Command failed: {' '.join(komut)}")


def ikonlari_hazirla() -> Path | None:
    """png/ico/icns uretir ve platformun istedigi dosyayi dondurur."""
    try:
        from PySide6.QtWidgets import QApplication

        from lubv_studio.icons import ikon_dosyalari_uret

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        uygulama = QApplication.instance() or QApplication([])
        ikon_dosyalari_uret(PAKET)
        del uygulama
    except Exception as exc:
        print(f"  (ikonlar uretilemedi: {exc})")

    hedef = PAKET / ("lubv.icns" if MACOS else "lubv.ico")
    return hedef if hedef.exists() else None


def main() -> None:
    print(f"== Building {AD} ==\n")

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        calistir(sys.executable, "-m", "pip", "install", "pyinstaller")
    calistir(sys.executable, "-m", "pip", "install", "-q", "-r", str(KOK / "requirements.txt"))

    for klasor in ("build", "dist"):
        shutil.rmtree(KOK / klasor, ignore_errors=True)
    for spec in KOK.glob("*.spec"):
        spec.unlink(missing_ok=True)

    ikon = ikonlari_hazirla()

    argumanlar = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile" if not MACOS else "--onedir",   # macOS .app paketi ister
        "--windowed",
        "--name", AD,
        "--collect-all", "ddgs",
        "--hidden-import", "lubv_studio",
        "--exclude-module", "tkinter",
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtCharts",
        "--exclude-module", "PySide6.QtDataVisualization",
    ]
    if ikon is not None:
        # add-data ayraci platforma gore degisir: Windows ';', digerleri ':'
        argumanlar += ["--icon", str(ikon),
                       "--add-data", f"{ikon}{os.pathsep}lubv_studio"]
    if MACOS:
        argumanlar += ["--osx-bundle-identifier", "com.lubv.studio"]
    argumanlar.append(str(KOK / "run_app.py"))

    calistir(*argumanlar)

    if MACOS:
        cikti = KOK / "dist" / f"{AD}.app"
    elif WINDOWS:
        cikti = KOK / "dist" / f"{AD}.exe"
    else:
        cikti = KOK / "dist" / AD

    if cikti.exists():
        if cikti.is_dir():
            mb = sum(f.stat().st_size for f in cikti.rglob("*") if f.is_file()) / 1024 / 1024
        else:
            mb = cikti.stat().st_size / 1024 / 1024
        print(f"\nDONE:  {cikti}   ({mb:.0f} MB)")
        print("Self-contained: move it anywhere, no Python required.")
    else:
        sys.exit("Executable was not produced.")


if __name__ == "__main__":
    main()
