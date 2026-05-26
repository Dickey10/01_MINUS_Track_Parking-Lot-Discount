$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if (Test-Path ".\.venv\Scripts\python.exe") {
  .\.venv\Scripts\python.exe run.py
} else {
  python run.py
}
