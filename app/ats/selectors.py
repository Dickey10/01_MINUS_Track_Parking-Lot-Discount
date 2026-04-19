# =====================================================================
# ATS (a00992.pweb.kr) DOM 셀렉터 모음
# Playwright Codegen으로 추출한 실제 셀렉터값
# =====================================================================

# --- 로그인 화면 (✅ Codegen으로 확인됨) ---
LOGIN_URL = "/login"
ID_INPUT = {"role": "textbox", "name": "ID"}
PW_INPUT = {"role": "textbox", "name": "PASSWORD"}
SUBMIT_BTN = {"role": "button", "name": "Submit"}

# 로그인 후 팝업 (OK 버튼, 안내 다이얼로그)
POPUP_OK = "OK"                          # page.get_by_text("OK")
POPUP_NOTICE = r"^안내$"                  # regex, filter has_text

# --- 메뉴 이동 (✅ Codegen으로 확인됨) ---
DISCOUNT_MENU = "할인 > 할인등록"         # page.get_by_text(DISCOUNT_MENU)
SEARCH_BTN = {"role": "button", "name": "검색"}

# --- 차량 목록 (⚠️ TODO: 실차 입차 후 Codegen 재실행으로 확인 필요) ---
# 검색 후 나타나는 입차 차량 목록에서 특정 차량번호를 선택하는 셀렉터
# 현재 ArrowDown 키 반복으로만 이동 가능한지, 또는 직접 클릭 가능한지 미확인
CAR_LIST_ROW = "TODO"                    # 차량 목록 행 셀렉터 (예: "tr.car-row")
CAR_NUMBER_CELL = "TODO"                 # 차량번호가 표시되는 셀 셀렉터

# --- 할인 시간 선택 (⚠️ TODO: 실차 입차 후 확인 필요) ---
DISCOUNT_30MIN = "TODO"                  # 30분권 버튼/옵션 셀렉터
DISCOUNT_60MIN = "TODO"                  # 60분권 버튼/옵션 셀렉터

# --- 최종 등록 확인 (⚠️ TODO: 실차 입차 후 확인 필요) ---
CONFIRM_BTN = "TODO"                     # 등록 완료/확인 버튼 셀렉터
SUCCESS_MESSAGE = "TODO"                 # 등록 성공 시 나타나는 텍스트 or 셀렉터
