import asyncio
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from app.models import RegisterRequest, RegisterResponse
from app.ats.registrar import ATSRegistrar
from app.config import settings

app = FastAPI(title="하츠 주차 할인권 자동화 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://dickey10.github.io"],  # GitHub Pages 도메인으로 변경 필요
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# ATS 동시 접근 방지 (ATS는 한 번에 하나만 처리)
_ats_lock = asyncio.Lock()
registrar = ATSRegistrar()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/register", response_model=RegisterResponse)
async def register(
    req: RegisterRequest,
    x_api_key: str = Header(default=""),
):
    if settings.api_key and x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")

    async with _ats_lock:
        result = await registrar.run(req)

    return result
