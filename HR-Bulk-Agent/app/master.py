from datetime import date, datetime
from typing import Any

from app.models import MasterEmployee, PromotionCandidate


PROMOTION_RULES: dict[str, tuple[str, int]] = {
    "사원": ("주임", 3),
    "주임": ("대리", 5),
    "대리": ("과장", 8),
    "과장": ("차장", 12),
    "차장": ("부장", 16),
}


def parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()


def years_of_service(hire_date: str, today: date | None = None) -> int:
    today = today or date.today()
    hired = parse_date(hire_date)
    years = today.year - hired.year
    if (today.month, today.day) < (hired.month, hired.day):
        years -= 1
    return max(0, years)


def current_pay_grade(employee: MasterEmployee, today: date | None = None) -> int:
    return employee.initial_pay_grade + years_of_service(employee.hire_date, today)


def promotion_candidate(employee: MasterEmployee, today: date | None = None) -> PromotionCandidate:
    service_years = years_of_service(employee.hire_date, today)
    current_grade = employee.initial_pay_grade + service_years
    next_rank, required_grade = PROMOTION_RULES.get(employee.rank or "", (None, 999))
    eligible = next_rank is not None and current_grade >= required_grade and employee.status == "active"
    reason = "진급 검토 대상" if eligible else "호봉/직급/재직상태 기준 미충족"
    if next_rank is None:
        reason = "현재 직급에 대한 진급 규칙 없음"
    if employee.status != "active":
        reason = "재직 상태가 active가 아님"
    return PromotionCandidate(
        employee_id=employee.employee_id,
        name=employee.name,
        department=employee.department,
        rank=employee.rank,
        hire_date=employee.hire_date,
        years_of_service=service_years,
        initial_pay_grade=employee.initial_pay_grade,
        current_pay_grade=current_grade,
        next_rank=next_rank,
        required_pay_grade=required_grade,
        eligible=eligible,
        reason=reason,
    )


def mask_master_employee(data: dict[str, Any]) -> dict[str, Any]:
    masked = dict(data)
    if masked.get("phone"):
        value = "".join(ch for ch in str(masked["phone"]) if ch.isdigit())
        masked["phone"] = f"{value[:3]}****{value[-4:]}" if len(value) >= 7 else "***"
    if masked.get("email") and "@" in str(masked["email"]):
        local, domain = str(masked["email"]).split("@", 1)
        masked["email"] = f"{local[:2]}***@{domain}"
    if masked.get("birth_date"):
        masked["birth_date"] = str(masked["birth_date"])[:4] + "-**-**"
    return masked
