# install.ps1 — one-shot setup for ORF-5 on Windows (PowerShell / Windows Terminal).
# If script execution is blocked, run once:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Say([string]$msg) { Write-Host "[orf5] $msg" -ForegroundColor Cyan }

try {
    $null = Get-Command python -ErrorAction Stop
} catch {
    Say "Python not found. Install it from python.org, or: winget install Python.Python.3.12"
    exit 1
}
Say ("Using " + (python --version 2>&1))

if (-not (Test-Path .venv)) {
    Say "Creating virtual environment ..."
    python -m venv .venv
}
& "$PSScriptRoot\.venv\Scripts\Activate.ps1"

Say "Upgrading pip ..."
python -m pip install --quiet --upgrade pip

Say "Installing dependencies ..."
pip install --quiet -r requirements.txt

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Say "Created .env - add your tokens before using the Telegram bot / PUBG module."
}

Write-Host ""
Say "Done. Quick start:"
Write-Host "    .venv\Scripts\activate"
Write-Host "    python main.py username octocat"
Write-Host ""
Say "Happy hacking."
