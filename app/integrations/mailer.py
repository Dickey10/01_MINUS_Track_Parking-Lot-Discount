"""
SMTP 실패 알림 메일.
Gmail 앱 비밀번호 방식 사용.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from pathlib import Path
from app.config import settings


async def send_failure_alert(req, error_msg: str, screenshot_path: str) -> None:
    if not settings.smtp_user or not settings.alert_email:
        return

    try:
        msg = MIMEMultipart()
        msg["Subject"] = f"[주차할인 실패] 차량번호: {req.car_number}"
        msg["From"] = settings.smtp_user
        msg["To"] = settings.alert_email

        body = (
            f"차량번호: {req.car_number}\n"
            f"할인 유형: {req.discount_type}분권\n"
            f"부서: {req.dept}\n"
            f"신청자: {req.requester}\n"
            f"오류: {error_msg}\n\n"
            "스크린샷을 첨부합니다."
        )
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if screenshot_path and Path(screenshot_path).exists():
            with open(screenshot_path, "rb") as f:
                img = MIMEImage(f.read(), name=Path(screenshot_path).name)
                msg.attach(img)

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)

    except Exception as e:
        print(f"[mailer] 메일 발송 실패: {e}")
