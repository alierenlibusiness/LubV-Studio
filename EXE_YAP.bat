@echo off
chcp 65001 >nul
title LUBV Studio - EXE olusturucu
cd /d "%~dp0"
python build_exe.py
echo.
pause
