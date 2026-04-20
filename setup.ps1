$Host.UI.RawUI.WindowTitle = "MINUS Track Setup"
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Clear-Host
Write-Host "============================================"
Write-Host "  MINUS Track Parking Discount Auto Setup"
Write-Host "============================================"
Write-Host ""

# Step 1: Check Python
Write-Host "[1/6] Checking Python..."
try {
    $pyver = python --version 2>&1
    Write-Host "  OK: $pyver"
} catch {
    Write-Host "  ERROR: Python not found. Install from python.org first."
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 2: ATS credentials
Write-Host ""
Write-Host "[2/6] Enter ATS login credentials (https://a00992.pweb.kr)"
Write-Host ""
$atsId = Read-Host "  ATS ID"
$atsPw = Read-Host "  ATS Password"

if (-not $atsId -or -not $atsPw) {
    Write-Host "  ERROR: ID or password is empty. Please run again."
    Read-Host "Press Enter to exit"
    exit 1
}

# Step 3: Create .env file
Write-Host ""
Write-Host "[3/6] Creating .env file..."
$envContent = "ATS_ID=$atsId`r`nATS_PW=$atsPw`r`nATS_URL=https://a00992.pweb.kr`r`nSESSION_PATH=data/storage_state.json`r`nSCREENSHOT_DIR=data/screenshots`r`nAPI_KEY=minus-parking-2024`r`nGSHEET_ID=`r`nGSHEET_CREDS_PATH=data/gsheet_creds.json`r`nSMTP_HOST=smtp.gmail.com`r`nSMTP_PORT=587`r`nSMTP_USER=`r`nSMTP_PASSWORD=`r`nALERT_EMAIL=`r`nCLOUDFLARE_TUNNEL_TOKEN=`r`n"
[System.IO.File]::WriteAllText("$PWD\.env", $envContent, [System.Text.Encoding]::UTF8)
Write-Host "  OK: .env created"

# Step 4: Create folders
Write-Host ""
Write-Host "[4/6] Creating data folders..."
New-Item -ItemType Directory -Force -Path "data" | Out-Null
New-Item -ItemType Directory -Force -Path "data\screenshots" | Out-Null
Write-Host "  OK: folders created"

# Step 5: Install packages
Write-Host ""
Write-Host "[5/6] Installing Python packages (this may take 2-3 minutes)..."
python -m pip install -r requirements.txt --quiet
python -m playwright install chromium
Write-Host "  OK: packages installed"

# Step 6: ATS login session
Write-Host ""
Write-Host "[6/6] ATS Login Session"
Write-Host ""
Write-Host "  IMPORTANT:"
Write-Host "  1. A Chrome browser will open automatically"
Write-Host "  2. Log in to ATS in that browser"
Write-Host "  3. After login, come back here and press Enter"
Write-Host ""
Read-Host "  Press Enter to open the browser"

python scripts/init_session.py

Write-Host ""
Write-Host "============================================"
Write-Host "  Setup Complete!"
Write-Host "============================================"
Write-Host ""
Write-Host "  To start the server, run this command:"
Write-Host ""
Write-Host "    python -m uvicorn app.main:app --reload"
Write-Host ""
Read-Host "Press Enter to exit"
