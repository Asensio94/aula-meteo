# Daily run of Aula Meteo (for the Windows Task Scheduler or by hand); publishes to GitHub Pages.
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File run_daily.ps1 [--reuse-text]
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\python.exe" -m aulameteo.daily --publish @args
exit $LASTEXITCODE
