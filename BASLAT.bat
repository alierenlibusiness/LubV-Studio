@echo off
chcp 65001 >nul
title LUBV Studio
cd /d "%~dp0"

rem --- Python var mi? ---
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Python bulunamadi. https://www.python.org/downloads/ adresinden kur,
    echo  kurulumda "Add Python to PATH" secenegini isaretle.
    echo.
    pause
    exit /b 1
)

rem --- Gerekli paketler kurulu mu? ---
python -c "import PySide6, requests" >nul 2>&1
if errorlevel 1 (
    echo  Ilk calistirma: gerekli paketler kuruluyor, biraz surebilir...
    python -m pip install --disable-pip-version-check -r requirements.txt
)

start "" pythonw -m lubv_studio
exit /b 0
