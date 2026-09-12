@echo off
rem install.bat - one-shot setup for ORF-5 on Windows (cmd / Windows Terminal).
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [orf5] Python not found. Install it from python.org, or: winget install Python.Python.3.12
    exit /b 1
)

echo [orf5] Using:
python --version

if not exist .venv (
    echo [orf5] Creating virtual environment ...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [orf5] Upgrading pip ...
python -m pip install --quiet --upgrade pip

echo [orf5] Installing dependencies ...
pip install --quiet -r requirements.txt

if not exist .env (
    copy .env.example .env >nul
    echo [orf5] Created .env - add your tokens before using the Telegram bot / PUBG module.
)

echo.
echo [orf5] Done. Quick start:
echo     .venv\Scripts\activate
echo     python main.py username octocat
echo.
echo [orf5] Happy hacking.
endlocal
