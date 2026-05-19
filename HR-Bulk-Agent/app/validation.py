from app.models import ChangeEvent, ChangeRequestCreate


REQUIRED_BY_EVENT: dict[ChangeEvent, set[str]] = {
    ChangeEvent.hire: {"employee_id", "name", "hire_date", "department", "rank", "company"},
    ChangeEvent.terminate: {"employee_id", "name", "termination_date"},
    ChangeEvent.leave_start: {"employee_id", "name", "leave_start_date"},
    ChangeEvent.leave_end: {"employee_id", "name", "leave_end_date"},
    ChangeEvent.promotion: {"employee_id", "name", "rank"},
    ChangeEvent.department_transfer: {"employee_id", "name", "department"},
    ChangeEvent.org_change: {"employee_id", "name", "department"},
}


def validate_change_request(request: ChangeRequestCreate) -> list[str]:
    employee = request.employee.model_dump()
    errors: list[str] = []
    for field in sorted(REQUIRED_BY_EVENT[request.event_type]):
        if not employee.get(field):
            errors.append(f"{request.event_type.value}: 필수값 누락 - {field}")
    if request.event_type == ChangeEvent.hire and request.employee.termination_date:
        errors.append("입사 처리에는 termination_date를 입력하지 않습니다.")
    if request.event_type == ChangeEvent.terminate and request.employee.hire_date and request.employee.termination_date:
        if request.employee.termination_date < request.employee.hire_date:
            errors.append("퇴사일은 입사일보다 빠를 수 없습니다.")
    if request.event_type in {ChangeEvent.leave_start, ChangeEvent.leave_end}:
        if request.employee.termination_date:
            errors.append("퇴사자는 휴직/복직 처리 대상에서 제외해야 합니다.")
    return errors

