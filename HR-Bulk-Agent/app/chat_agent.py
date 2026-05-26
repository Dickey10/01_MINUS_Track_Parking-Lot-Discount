import re
from datetime import datetime

from app.models import (
    ChangeEvent,
    ChangeRequestCreate,
    ChatAnalyzeRequest,
    ChatAnalyzeResponse,
    ChatDraftItem,
    EmployeePayload,
    Platform,
)
from app.validation import REQUIRED_BY_EVENT, validate_change_request


EVENT_KEYWORDS: list[tuple[ChangeEvent, tuple[str, ...]]] = [
    (ChangeEvent.hire, ("입사", "신입", "신규", "등록")),
    (ChangeEvent.terminate, ("퇴사", "퇴직", "퇴사자")),
    (ChangeEvent.leave_start, ("휴직", "휴직자")),
    (ChangeEvent.leave_end, ("복직", "복직자")),
    (ChangeEvent.promotion, ("승진", "진급", "승급")),
    (ChangeEvent.department_transfer, ("부서변경", "이동", "전보", "전입", "조직개편")),
    (ChangeEvent.org_change, ("조직개편", "조직 변경")),
]

RANK_WORDS = ("사원", "주임", "대리", "과장", "차장", "부장", "팀장", "실장", "상무", "전무", "이사")
COMPANY_WORDS = ("하츠", "벽산", "샐러리파이")


def split_items(message: str) -> list[str]:
    lines = [line.strip(" -\t") for line in message.splitlines() if line.strip(" -\t")]
    if len(lines) > 1:
        items: list[str] = []
        for line in lines:
            items.extend(split_items(line))
        return items
    if len(re.findall(r"사번\s*[A-Za-z0-9_-]+", message)) > 1:
        segments = re.split(r"(?=사번\s*[A-Za-z0-9_-]+)", message)
        return [segment.strip(" ,，") for segment in segments if segment.strip(" ,，")]
    parts = [part.strip() for part in re.split(r"[;•]", message) if part.strip()]
    return parts or [message.strip()]


def infer_event_type(text: str, fallback: ChangeEvent | None = None) -> ChangeEvent:
    for event_type, keywords in EVENT_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return event_type
    return fallback or ChangeEvent.hire


def find_date(text: str) -> str | None:
    match = re.search(r"(20\d{2})[-./년 ]\s*(\d{1,2})[-./월 ]\s*(\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    match = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if not match:
        return None
    month, day = match.groups()
    year = str(datetime.now().year)
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def find_phone(text: str) -> str | None:
    match = re.search(r"01[016789][-\s]?\d{3,4}[-\s]?\d{4}", text)
    return re.sub(r"\D", "", match.group(0)) if match else None


def find_email(text: str) -> str | None:
    match = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else None


def find_employee_id(text: str) -> str | None:
    match = re.search(r"(?:사번|ID|id|No\.?)\s*[:：]?\s*([A-Za-z0-9_-]{3,})", text)
    if match:
        return match.group(1)
    return None


def find_name(text: str) -> str | None:
    match = re.search(r"(?:이름|성명)\s*[:：]?\s*([가-힣]{2,5})", text)
    if match:
        return match.group(1)
    employee_id_match = re.search(r"(?:사번|ID|id|No\.?)\s*[:：]?\s*([A-Za-z0-9_-]{3,})", text)
    search_text = text[employee_id_match.end():] if employee_id_match else text
    tokens = re.findall(r"\b[가-힣]{2,5}\b", search_text)
    excluded = set(RANK_WORDS) | set(COMPANY_WORDS) | {
        "입사",
        "입사자",
        "퇴사",
        "퇴사자",
        "휴직",
        "휴직자",
        "복직",
        "복직자",
        "승진",
        "승진자",
        "진급",
        "진급자",
        "조직개편",
        "부서변경",
        "회사",
        "회사는",
        "사번",
    }
    for token in tokens:
        if (
            token not in excluded
            and not token.endswith(("팀", "부", "실", "센터", "본부", "해줘", "처리", "등록", "는"))
        ):
            return token
    return None


def find_rank(text: str) -> str | None:
    for rank in RANK_WORDS:
        if rank in text:
            return rank
    return None


def find_department(text: str) -> str | None:
    match = re.search(r"([가-힣A-Za-z0-9]+(?:팀|부|실|센터|본부))", text)
    return match.group(1) if match else None


def find_company(text: str) -> str | None:
    for company in COMPANY_WORDS:
        if company in text:
            return company
    return None


def missing_questions(event_type: ChangeEvent, employee: EmployeePayload) -> tuple[list[str], list[str]]:
    data = employee.model_dump()
    missing = [field for field in sorted(REQUIRED_BY_EVENT[event_type]) if not data.get(field)]
    if employee.employee_id.startswith("TEMP-") and "employee_id" in REQUIRED_BY_EVENT[event_type]:
        missing.append("employee_id")
    if employee.name == "미확인" and "name" in REQUIRED_BY_EVENT[event_type]:
        missing.append("name")
    missing = sorted(set(missing))
    labels = {
        "employee_id": "사번",
        "name": "이름",
        "hire_date": "입사일",
        "termination_date": "퇴사일",
        "leave_start_date": "휴직 시작일",
        "leave_end_date": "복직일",
        "department": "부서",
        "rank": "직급",
        "company": "회사/법인",
    }
    questions = [f"{labels.get(field, field)} 정보를 알려주세요." for field in missing]
    return missing, questions


def parse_item(
    text: str,
    row_number: int,
    default_event: ChangeEvent,
    platforms: list[Platform],
    default_company: str | None,
    default_date: str | None,
) -> ChatDraftItem:
    event_type = infer_event_type(text, default_event)
    date = find_date(text) or default_date
    employee = EmployeePayload(
        employee_id=find_employee_id(text) or f"TEMP-{row_number:03d}",
        name=find_name(text) or "미확인",
        company=find_company(text) or default_company,
        department=find_department(text),
        rank=find_rank(text),
        email=find_email(text),
        phone=find_phone(text),
        hire_date=date if event_type == ChangeEvent.hire else None,
        termination_date=date if event_type == ChangeEvent.terminate else None,
        leave_start_date=date if event_type == ChangeEvent.leave_start else None,
        leave_end_date=date if event_type == ChangeEvent.leave_end else None,
    )
    change_request = ChangeRequestCreate(
        event_type=event_type,
        employee=employee,
        target_platforms=platforms,
        requested_by="chat-agent",
        memo=text,
    )
    validation_errors = validate_change_request(change_request)
    missing, questions = missing_questions(event_type, employee)
    confidence = 0.85
    if employee.employee_id.startswith("TEMP-"):
        confidence -= 0.25
    if employee.name == "미확인":
        confidence -= 0.25
    confidence -= min(len(missing) * 0.08, 0.32)
    if validation_errors:
        questions.extend(validation_errors)
    return ChatDraftItem(
        row_number=row_number,
        confidence=max(0.1, round(confidence, 2)),
        source_text=text,
        change_request=change_request,
        missing_fields=missing,
        followup_questions=questions,
    )


async def analyze_chat(request: ChatAnalyzeRequest) -> ChatAnalyzeResponse:
    default_event = infer_event_type(request.message)
    default_company = find_company(request.message)
    default_date = find_date(request.message)
    items = []
    raw_items = split_items(request.message)
    for item in raw_items:
        has_person_signal = bool(find_employee_id(item) or find_name(item))
        if len(raw_items) > 1 and not has_person_signal:
            continue
        items.append(item)
    items = items or raw_items
    drafts = [
        parse_item(
            text=item,
            row_number=index,
            default_event=default_event,
            platforms=request.default_platforms,
            default_company=default_company,
            default_date=default_date,
        )
        for index, item in enumerate(items, start=1)
    ]
    valid_count = sum(1 for draft in drafts if not draft.missing_fields)
    strategy = [
        "여러 직원/여러 팀 변경은 줄 단위로 쪼개 초안을 만들고, 누락값만 역질문합니다.",
        "연말 조직개편/연초 승진은 Excel 붙여넣기 또는 줄바꿈 목록을 그대로 입력하면 직원별 작업 큐로 분리합니다.",
        "실행은 기존과 동일하게 미리보기와 승인 단계를 거치며, 담당자 PC 로컬 DB에 감사 로그를 남깁니다.",
    ]
    global_questions: list[str] = []
    if len(drafts) > 1:
        global_questions.append("대상 플랫폼이 모든 직원에게 동일한지 확인해주세요. 기본값은 선물24와 워크드입니다.")
    if valid_count < len(drafts):
        global_questions.append("누락값이 있는 항목은 승인 요청 생성 전에 세부 정보를 보완해야 합니다.")
    return ChatAnalyzeResponse(
        mode="local_rules",
        summary=f"{len(drafts)}건의 변경 후보를 추출했고, 이 중 {valid_count}건은 필수값이 채워졌습니다.",
        strategy=strategy,
        drafts=drafts,
        global_questions=global_questions,
    )
