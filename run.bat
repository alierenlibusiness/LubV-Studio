@echo off
chcp 65001 >nul
title LUBV Studio
cd /d "%~dp0"

rem --- is Python available? ---
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  Python was not found. Install it from https://www.python.org/downloads/
    echo  and tick "Add Python to PATH" during setup.
    echo.
    pause
    exit /b 1
)

rem --- are the dependencies installed? ---
python -c "import PySide6, requests" >nul 2>&1
if errorlevel 1 (
    echo  First run: installing dependencies, this may take a minute...
    python -m pip install --disable-pip-version-check -r requirements.txt
)

start "" pythonw -m lubv_studio
exit /b 0
