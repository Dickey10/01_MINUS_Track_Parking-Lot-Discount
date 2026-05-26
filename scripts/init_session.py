"""
최초 1회 실행 — ATS 수동 로그인 후 storage_state.json 생성.
Docker 실행 전에 로컬에서 먼저 실행하세요.

사용법:
    python scripts/init_session.py
"""

import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


SESSION_PATH = Path("data/storage_state.json")


async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        print("브라우저가 열렸습니다. ATS에 직접 로그인하세요.")
        print("로그인 완료 후 이 터미널에서 Enter를 누르세요.")
        await page.goto("https://a00992.pweb.kr/login")

        input("로그인 완료 후 Enter >>>")

        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(SESSION_PATH))
        print(f"세션 저장 완료: {SESSION_PATH}")

        await context.close()
        await browser.close()


asyncio.run(main())
