"""
ATS 주차 할인권 자동 등록 클래스.

확인된 흐름:
  1. 로그인 (storage_state 재사용, 만료 시 재로그인)
  2. /discount/registration 직접 이동
  3. 차량번호 입력 → 검색
  4. dhtmlXGrid JS로 해당 행 선택 (XgridMst.selectRow)
  5. #div_dscntcodes 에 동적 생성된 할인 버튼 클릭 → fncSave() 자동 호출
  6. "등록되었습니다." 모달 확인
"""

import re
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

        # 할인등록 페이지 직접 이동 (✅ URL 확인됨)
        await page.goto(f"{settings.ats_url}{sel.DISCOUNT_URL}")
        await page.wait_for_load_state("networkidle")

        # 차량번호 입력 후 검색 (✅ HTML 확인됨)
        await page.locator(sel.CAR_SEARCH_INPUT).fill(req.car_number)
        await page.locator(sel.SEARCH_BUTTON).click()
        await page.wait_for_load_state("networkidle")

        # 검색 결과 없음 확인 (차량 미입차)
        try:
            await page.get_by_text(sel.NO_RESULT_MESSAGE).wait_for(timeout=3000)
            await page.get_by_role("button", name="OK").click()
            return RegisterResponse(
                success=False,
                message=f"차량 미입차: {req.car_number}",
                car_number=req.car_number,
                discount_type=req.discount_type,
            )
        except Exception:
            pass  # 검색 결과 있음, 계속 진행

        # dhtmlXGrid에서 차량번호 행 선택 (✅ JS 전역변수: dataSetMst, XgridMst)
        # 행 값의 모든 필드를 순회하여 차량번호 포함 여부로 찾음
        row_index = await page.evaluate(
            """(carNo) => {
                try {
                    var normalized = carNo.replace(/\\s/g, '');
                    for (var i = 0; i < dataSetMst.length; i++) {
                        var row = dataSetMst[i];
                        for (var key in row) {
                            if (String(row[key]).replace(/\\s/g, '').includes(normalized)) {
                                XgridMst.selectRow(i, true);
                                return i;
                            }
                        }
                    }
                } catch(e) {}
                return -1;
            }""",
            req.car_number,
        )

        if row_index == -1:
            return RegisterResponse(
                success=False,
                message=f"그리드에서 차량 미발견: {req.car_number}",
                car_number=req.car_number,
                discount_type=req.discount_type,
            )

        # 행 선택 후 #div_dscntcodes 에 할인 버튼 동적 생성될 때까지 대기
        # ⚠️ time 속성값이 분 단위(30/60)인지 실차 확인 필요
        discount_sel = (
            sel.DISCOUNT_30MIN_SEL if req.discount_type == "30"
            else sel.DISCOUNT_60MIN_SEL
        )
        await page.locator(discount_sel).wait_for(timeout=5000)

        # 버튼 클릭 → fncSetDscntType() → fncSave() 자동 호출 (확인 버튼 없음)
        await page.locator(discount_sel).click()

        # 성공 모달 대기 (fncAlertMsg → jQuery UI dialog)
        await page.get_by_text(sel.SUCCESS_MESSAGE).wait_for(timeout=10000)
        await page.get_by_role("button", name="OK").click()

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
