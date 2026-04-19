"""
로컬 Smoke Test — FastAPI 서버 실행 중일 때 사용.

사용법:
    uvicorn app.main:app --reload   # 터미널1
    python scripts/test_register.py # 터미널2
"""

import requests

BASE_URL = "http://localhost:8000"
API_KEY = "여기에_API_KEY_입력"  # .env의 API_KEY 값


def test_health():
    r = requests.get(f"{BASE_URL}/health")
    print("Health:", r.json())


def test_register():
    payload = {
        "car_number": "12가3456",   # ⚠️ 실제 입차 차량번호로 변경
        "discount_type": "60",
        "dept": "영업전략팀",
        "requester": "홍길동",
        "reason": "업무 방문",
    }
    headers = {"x-api-key": API_KEY}
    r = requests.post(f"{BASE_URL}/register", json=payload, headers=headers)
    print("Register:", r.status_code, r.json())


if __name__ == "__main__":
    test_health()
    test_register()
