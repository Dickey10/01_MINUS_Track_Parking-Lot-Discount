# =====================================================
# MINUS Track 주차 할인권 자동화 - 설치 스크립트
# 사용법: 이 파일에서 마우스 우클릭 → PowerShell로 실행
# =====================================================

$Host.UI.RawUI.WindowTitle = "MINUS Track 설치"
$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host ""
    Write-Host ">>> $msg" -ForegroundColor Cyan
}

function Write-OK($msg) {
    Write-Host "    [OK] $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
    Write-Host "    [오류] $msg" -ForegroundColor Red
}

Clear-Host
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  MINUS Track 주차 할인권 자동화 설치" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# -------------------------------------------
# 1단계: Python 설치 확인
# -------------------------------------------
Write-Step "Python 설치 확인 중..."
try {
    $pyver = python --version 2>&1
    Write-OK "Python 확인됨: $pyver"
} catch {
    Write-Fail "Python이 설치되어 있지 않습니다."
    Write-Host "    python.org 에서 Python 설치 후 다시 실행하세요." -ForegroundColor Yellow
    Read-Host "Enter를 눌러 종료"
    exit 1
}

# -------------------------------------------
# 2단계: ATS 계정 정보 입력
# -------------------------------------------
Write-Step "ATS 로그인 정보 입력"
Write-Host "    (ATS: https://a00992.pweb.kr 에서 사용하는 계정입니다)" -ForegroundColor Gray
Write-Host ""
$atsId = Read-Host "    ATS 아이디를 입력하세요"
$atsPw = Read-Host "    ATS 비밀번호를 입력하세요"

if (-not $atsId -or -not $atsPw) {
    Write-Fail "아이디 또는 비밀번호가 비어있습니다. 다시 실행해주세요."
    Read-Host "Enter를 눌러 종료"
    exit 1
}

# -------------------------------------------
# 3단계: .env 파일 자동 생성
# -------------------------------------------
Write-Step ".env 파일 생성 중..."
$envContent = @"
ATS_ID=$atsId
ATS_PW=$atsPw
ATS_URL=https://a00992.pweb.kr
SESSION_PATH=data/storage_state.json
SCREENSHOT_DIR=data/screenshots
API_KEY=minus-parking-2024
GSHEET_ID=
GSHEET_CREDS_PATH=data/gsheet_creds.json
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
ALERT_EMAIL=
CLOUDFLARE_TUNNEL_TOKEN=
"@
$envContent | Set-Content -Encoding UTF8 ".env"
Write-OK ".env 파일 생성 완료"

# -------------------------------------------
# 4단계: 필요 폴더 생성
# -------------------------------------------
Write-Step "폴더 생성 중..."
New-Item -ItemType Directory -Force -Path "data" | Out-Null
New-Item -ItemType Directory -Force -Path "data\screenshots" | Out-Null
Write-OK "data 폴더 생성 완료"

# -------------------------------------------
# 5단계: Python 패키지 설치
# -------------------------------------------
Write-Step "필요한 Python 패키지 설치 중... (1~3분 소요)"
python -m pip install -r requirements.txt --quiet
Write-OK "패키지 설치 완료"

# -------------------------------------------
# 6단계: Playwright 브라우저 설치
# -------------------------------------------
Write-Step "자동화용 브라우저 설치 중... (1~2분 소요)"
python -m playwright install chromium
Write-OK "브라우저 설치 완료"

# -------------------------------------------
# 7단계: ATS 로그인 세션 저장
# -------------------------------------------
Write-Step "ATS 로그인 세션 저장"
Write-Host ""
Write-Host "    ★ 지금부터 중요합니다 ★" -ForegroundColor Yellow
Write-Host "    1. 잠시 후 크롬 브라우저가 자동으로 열립니다" -ForegroundColor Yellow
Write-Host "    2. 열린 브라우저에서 ATS에 직접 로그인해주세요" -ForegroundColor Yellow
Write-Host "    3. 로그인 완료 후 이 창으로 돌아와서 Enter를 누르세요" -ForegroundColor Yellow
Write-Host ""
Read-Host "    준비되면 Enter를 눌러 브라우저를 여세요"

python scripts/init_session.py

# -------------------------------------------
# 완료
# -------------------------------------------
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  설치 완료!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  서버 실행 방법:" -ForegroundColor White
Write-Host "  PowerShell에서 아래 명령어 입력:" -ForegroundColor White
Write-Host ""
Write-Host "    python -m uvicorn app.main:app --reload" -ForegroundColor Yellow
Write-Host ""
Write-Host "  서버가 실행되면 http://127.0.0.1:8000/health 에서 확인 가능" -ForegroundColor Gray
Write-Host ""
Read-Host "Enter를 눌러 종료"
