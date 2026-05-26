# =====================================================================
# ATS (a00992.pweb.kr) DOM 셀렉터 모음
# ✅ = HTML 소스 분석으로 확인됨
# ⚠️ = 실차 입차 후 확인 필요
# =====================================================================

# --- 로그인 화면 (✅ Codegen 확인됨) ---
LOGIN_URL = "/login"
DISCOUNT_URL = "/discount/registration"  # ✅ 직접 접근 URL

# --- 차량번호 검색 (✅ HTML 소스 확인됨) ---
# <input type="text" id="schCarNo" ...>
CAR_SEARCH_INPUT = "#schCarNo"

# <input type="button" class="btnS1_1 btn" value="검색" ...>
SEARCH_BUTTON = "input.btnS1_1"

# --- 차량 목록 그리드 (✅ HTML 소스 확인됨) ---
# dhtmlXGrid → JS 전역변수 dataSetMst / XgridMst 로 직접 제어
# <div id="gridMst" ...>
CAR_GRID = "#gridMst"

# --- 할인 버튼 (✅ JS 소스 분석 확인됨) ---
# 차량 행 선택 후 /discount/registration/getForDiscount API 응답의
# listDiscountType[] 배열로 fncGetDscntBtn()이 동적 생성
# 버튼 구조: <a name="btnDscntType" time="{discount_value}" price="{discount_price}">
# 버튼 클릭 즉시 fncSetDscntType() → fncSave() 자동 호출 → 별도 확인 버튼 없음
DISCOUNT_CODES_DIV = "#div_dscntcodes"

# ✅ attribute 기반 셀렉터 (텍스트보다 안정적)
# ⚠️ time 속성값이 분 단위(30/60)인지 실차 확인 필요 — discount_value 기준
DISCOUNT_30MIN_SEL = '#div_dscntcodes a[name="btnDscntType"][time="30"]'
DISCOUNT_60MIN_SEL = '#div_dscntcodes a[name="btnDscntType"][time="60"]'

# 실차 확인용 JS (버튼 생성 후 DevTools 콘솔 실행):
# Array.from(document.querySelectorAll('#div_dscntcodes a[name="btnDscntType"]'))
#   .map(a=>({id:a.id,text:a.textContent.trim(),time:a.getAttribute('time'),price:a.getAttribute('price')}))

# --- 성공/오류 메시지 (✅ HTML 소스 확인됨) ---
# fncAlertMsg("등록되었습니다.", ...) 호출 결과
SUCCESS_MESSAGE = "등록되었습니다."
NO_RESULT_MESSAGE = "검색 결과가 없습니다"  # 차량 미입차 시
