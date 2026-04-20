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

# --- 할인 버튼 (✅ HTML 소스 확인됨) ---
# 차량 행 선택 후 #div_dscntcodes 에 <a> 버튼 동적 생성됨
# 버튼 클릭 즉시 fncSave() 자동 호출 → 별도 확인 버튼 없음
# <td id="div_dscntcodes">
DISCOUNT_CODES_DIV = "#div_dscntcodes"
DISCOUNT_BTN = "#div_dscntcodes a"

# ⚠️ TODO: 실차 입차 후 실제 할인권 버튼 텍스트 확인 필요
# (예: "30분", "30분 무료", "30분할인" 등 — 버튼 클릭 후 텍스트 확인)
DISCOUNT_30MIN_TEXT = "30"   # 30분권 버튼 텍스트 부분 일치
DISCOUNT_60MIN_TEXT = "60"   # 60분권 버튼 텍스트 부분 일치

# --- 성공/오류 메시지 (✅ HTML 소스 확인됨) ---
# fncAlertMsg("등록되었습니다.", ...) 호출 결과
SUCCESS_MESSAGE = "등록되었습니다."
NO_RESULT_MESSAGE = "검색 결과가 없습니다"  # 차량 미입차 시
