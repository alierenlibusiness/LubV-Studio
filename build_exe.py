"""LUBV Studio'yu tek dosyalik bir .exe haline getirir.

Kullanim:
    python build_exe.py

Sonuc:  dist\\LUBV Studio.exe   (cift tiklayip calistirilir, Python gerekmez)
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
AD = "LUBV Studio"
IKON = KOK / "lubv_studio" / "lubv.ico"


def calistir(*komut: str) -> None:
    print(">", " ".join(komut))
    sonuc = subprocess.run(komut)
    if sonuc.returncode != 0:
        sys.exit(f"Komut basarisiz: {' '.join(komut)}")


def main() -> None:
    print(f"== {AD} derleniyor ==\n")

    # 1) gerekli paketler
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        calistir(sys.executable, "-m", "pip", "install", "pyinstaller")
    calistir(sys.executable, "-m", "pip", "install", "-q", "-r", str(KOK / "requirements.txt"))

    # 2) eski ciktilari temizle
    for klasor in ("build", "dist"):
        hedef = KOK / klasor
        if hedef.exists():
            shutil.rmtree(hedef, ignore_errors=True)
    for spec in KOK.glob("*.spec"):
        spec.unlink(missing_ok=True)

    # 3) derle
    argumanlar = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",              # tek exe
        "--windowed",             # konsol penceresi acilmasin
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
    if IKON.exists():
        argumanlar += ["--icon", str(IKON), "--add-data", f"{IKON};lubv_studio"]
    argumanlar.append(str(KOK / "run_app.py"))

    calistir(*argumanlar)

    exe = KOK / "dist" / f"{AD}.exe"
    if exe.exists():
        mb = exe.stat().st_size / 1024 / 1024
        print(f"\nHAZIR:  {exe}   ({mb:.0f} MB)")
        print("Bu dosyayi istedigin yere tasiyabilirsin, Python gerektirmez.")
    else:
        sys.exit("exe olusturulamadi.")


if __name__ == "__main__":
    main()
