"""
Google Sheets 이력 기록.
서비스 계정 JSON을 data/gsheet_creds.json 에 저장 후 사용.
"""

from datetime import datetime
from app.config import settings


async def append_history(req, result) -> None:
    if not settings.gsheet_id:
        return

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(
            settings.gsheet_creds_path, scopes=scopes
        )
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(settings.gsheet_id)
        ws = sh.sheet1

        ws.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            req.car_number,
            f"{req.discount_type}분",
            req.dept,
            req.requester,
            req.reason,
            "성공" if result.success else "실패",
        ])
    except Exception as e:
        # Sheets 기록 실패가 메인 흐름을 막지 않도록 예외만 출력
        print(f"[gsheets] 기록 실패: {e}")
