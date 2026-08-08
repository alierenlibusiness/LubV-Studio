@echo off
chcp 65001 >nul
title LUBV Studio - executable builder
cd /d "%~dp0"
python build_exe.py
echo.
pause
