import json
import os
from pathlib import Path
from playwright.async_api import Page


SESSION_PATH = Path("data/storage_state.json")


def session_exists() -> bool:
    return SESSION_PATH.exists() and SESSION_PATH.stat().st_size > 0


async def save_session(context) -> None:
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=str(SESSION_PATH))


async def is_session_valid(page: Page, base_url: str) -> bool:
    """현재 페이지가 로그인 화면으로 리다이렉트됐는지 확인."""
    await page.goto(f"{base_url}/discount/registration")
    await page.wait_for_load_state("networkidle")
    return "login" not in page.url
