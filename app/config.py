from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ATS 로그인 정보
    ats_id: str
    ats_pw: str
    ats_url: str = "https://a00992.pweb.kr"

    # 세션 저장 경로
    session_path: str = "data/storage_state.json"
    screenshot_dir: str = "data/screenshots"

    # Google Sheets (선택)
    gsheet_id: str = ""
    gsheet_creds_path: str = "data/gsheet_creds.json"

    # SMTP 이메일 알림 (선택)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email: str = ""        # 실패 알림 수신 이메일

    # API 보안
    api_key: str = ""            # GitHub Pages → FastAPI 호출 시 검증

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
