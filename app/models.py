from pydantic import BaseModel
from typing import Literal


class RegisterRequest(BaseModel):
    car_number: str          # 예: "12가3456"
    discount_type: Literal["30", "60"]  # 30분권 or 60분권
    dept: str = ""           # 부서명 (이력 기록용)
    requester: str = ""      # 신청자 이름
    reason: str = ""         # 방문 사유


class RegisterResponse(BaseModel):
    success: bool
    message: str
    car_number: str
    discount_type: str
    screenshot_path: str = ""
