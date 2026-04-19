"""
ATS 주차 할인권 자동 등록 클래스.

확인된 흐름:
  1. 로그인 (storage_state 재사용, 만료 시 재로그인)
  2. 할인 > 할인등록 메뉴 이동
  3. 검색 버튼 클릭 → 입차 차량 목록 표시
  4. 차량번호로 해당 행 선택         ← ⚠️ TODO
  5. 30분권 / 60분권 선택            ← ⚠️ TODO
  6. 등록 확인                        ← ⚠️ TODO
"""

import re
import os
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page, BrowserContext

from app.models import RegisterRequest, RegisterResponse
from app.config import settings
from app.ats import selectors as sel
from app.ats.session import session_exists, save_session, is_session_valid
from app.integrations.gsheets import append_history
from app.integrations.mailer import send_failure_alert


class ATSRegistrar:

    async def run(self, req: RegisterRequest) -> RegisterResponse:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)

            # storage_state 재사용 (세션 유지)
            ctx_kwargs = {}
            if session_exists():
                ctx_kwargs["storage_state"] = str(
                    Path(settings.session_path)
                )

            context = await browser.new_context(**ctx_kwargs)
            page = await context.new_page()

            try:
                # 세션 유효성 확인 → 만료 시 재로그인
                if not await is_session_valid(page, settings.ats_url):
                    await self._login(page, context)

                result = await self._register(page, req)

                # 성공 시 이력 기록
                await append_history(req, result)
                return result

            except Exception as e:
                screenshot_path = await self._take_screenshot(
                    page, f"error_{req.car_number}"
                )
                await send_failure_alert(req, str(e), screenshot_path)
                return RegisterResponse(
                    success=False,
                    message=f"오류 발생: {e}",
                    car_number=req.car_number,
                    discount_type=req.discount_type,
                    screenshot_path=screenshot_path,
                )
            finally:
                await context.close()
                await browser.close()

    async def _login(self, page: Page, context: BrowserContext) -> None:
        """ATS 로그인 후 세션 저장."""
        await page.goto(f"{settings.ats_url}/login")
        await page.wait_for_load_state("networkidle")

        # 로그인 폼 입력 (✅ Codegen 확인됨)
        await page.get_by_role("listitem").nth(1).click()
        await page.get_by_role("textbox", name="ID").fill(settings.ats_id)
        await page.get_by_role("textbox", name="ID").press("Enter")
        await page.get_by_role("textbox", name="PASSWORD").click()
        await page.get_by_role("textbox", name="PASSWORD").fill(settings.ats_pw)
        await page.get_by_role("button", name="Submit").click()
        await page.wait_for_load_state("networkidle")

        # 로그인 후 팝업 처리 (OK / 안내 다이얼로그)
        await self._dismiss_popups(page)

        await save_session(context)

    async def _dismiss_popups(self, page: Page) -> None:
        """로그인 후 나타나는 OK / 안내 팝업 닫기 (✅ Codegen 확인됨)."""
        try:
            ok_btn = page.get_by_text("OK").first
            if await ok_btn.is_visible(timeout=3000):
                await ok_btn.click()
        except Exception:
            pass

        try:
            notice = page.locator("div").filter(
                has_text=re.compile(r"^안내$")
            ).first
            if await notice.is_visible(timeout=2000):
                await notice.click()
        except Exception:
            pass

    async def _register(
        self, page: Page, req: RegisterRequest
    ) -> RegisterResponse:
        """할인 등록 메인 로직."""

        # 할인등록 메뉴 이동 (✅ Codegen 확인됨)
        await page.get_by_text(sel.DISCOUNT_MENU).click()
        await page.wait_for_load_state("networkidle")

        # 검색 버튼 클릭 → 입차 차량 목록 (✅ Codegen 확인됨)
        await page.get_by_role("button", name="검색").click()
        await page.wait_for_load_state("networkidle")

        # ⚠️ TODO: 차량번호로 목록에서 해당 차량 행 찾아서 클릭
        # 현재는 ArrowDown 반복으로만 이동 가능한지 미확인
        # 실차 테스트 후 아래 코드 완성 필요
        #
        # 예상 구현:
        # row = page.locator(sel.CAR_LIST_ROW).filter(has_text=req.car_number)
        # await row.click()
        raise NotImplementedError(
            "⚠️ 차량 선택 셀렉터 미확인 — 실차 입차 후 Codegen 재실행 필요"
        )

        # ⚠️ TODO: 30분권 / 60분권 선택
        # if req.discount_type == "30":
        #     await page.locator(sel.DISCOUNT_30MIN).click()
        # else:
        #     await page.locator(sel.DISCOUNT_60MIN).click()

        # ⚠️ TODO: 최종 등록 확인 버튼 클릭
        # await page.locator(sel.CONFIRM_BTN).click()
        # await page.wait_for_selector(sel.SUCCESS_MESSAGE)

        screenshot_path = await self._take_screenshot(
            page, f"success_{req.car_number}"
        )
        return RegisterResponse(
            success=True,
            message="할인권 등록 완료",
            car_number=req.car_number,
            discount_type=req.discount_type,
            screenshot_path=screenshot_path,
        )

    async def _take_screenshot(self, page: Page, name: str) -> str:
        """스크린샷 저장 후 경로 반환."""
        dir_ = Path(settings.screenshot_dir)
        dir_.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = str(dir_ / f"{ts}_{name}.png")
        await page.screenshot(path=path)
        return path
