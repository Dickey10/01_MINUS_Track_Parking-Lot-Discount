import httpx

from app.config import settings
from app.models import ChangeEvent, ConnectorPreview, ConnectorResult, EmployeePayload, Platform
from app.security import mask_payload
from app.connectors.base import HRConnector


class WorkdConnector(HRConnector):
    platform = Platform.workd
    supports_live_apply = True

    def _action(self, event_type: ChangeEvent) -> str:
        if event_type == ChangeEvent.hire:
            return "create"
        if event_type == ChangeEvent.terminate:
            return "deactivate"
        return "update"

    def _payload(self, employee: EmployeePayload) -> dict:
        return {
            "employeeNo": employee.employee_id,
            "name": employee.name,
            "company": employee.company,
            "department": employee.department,
            "rank": employee.rank,
            "title": employee.title,
            "email": str(employee.email) if employee.email else None,
            "phone": employee.phone,
            "status": employee.employment_status,
            "hireDate": employee.hire_date,
            "terminationDate": employee.termination_date,
        }

    async def validate(self, event_type: ChangeEvent, employee: EmployeePayload) -> list[str]:
        errors: list[str] = []
        if event_type == ChangeEvent.hire and not employee.email:
            errors.append("워크드: 신규 직원 생성에는 이메일이 필요합니다.")
        if not employee.company:
            errors.append("워크드: 회사/법인(company) 값이 필요합니다.")
        return errors

    async def preview(self, event_type: ChangeEvent, employee: EmployeePayload) -> ConnectorPreview:
        warnings = await self.validate(event_type, employee)
        return ConnectorPreview(
            platform=self.platform,
            action=self._action(event_type),
            identifier=employee.employee_id,
            after=mask_payload(self._payload(employee)),
            warnings=warnings,
        )

    async def apply(self, event_type: ChangeEvent, employee: EmployeePayload) -> ConnectorResult:
        payload = self._payload(employee)
        if not settings.allow_live_connectors:
            return ConnectorResult(
                platform=self.platform,
                status="dry_run",
                message="실제 워크드 API 호출은 비활성화되어 있습니다.",
                masked_payload=mask_payload(payload),
            )
        if not settings.workd_base_url or not settings.workd_api_key:
            return ConnectorResult(
                platform=self.platform,
                status="failed",
                message="워크드 base URL/API key 설정이 없습니다.",
                masked_payload=mask_payload(payload),
            )
        action = self._action(event_type)
        endpoint = f"{settings.workd_base_url.rstrip('/')}/employees/{employee.employee_id}"
        method = "POST" if action == "create" else "PATCH"
        if action == "deactivate":
            payload["status"] = "inactive"
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.request(
                    method,
                    endpoint,
                    headers={"Authorization": f"Bearer {settings.workd_api_key}"},
                    json=payload,
                )
            if response.status_code >= 400:
                return ConnectorResult(
                    platform=self.platform,
                    status="failed",
                    message=f"워크드 API 오류: HTTP {response.status_code}",
                    masked_payload=mask_payload(payload),
                )
            return ConnectorResult(
                platform=self.platform,
                status="success",
                message="워크드 API 반영 완료",
                request_ref=response.headers.get("x-request-id"),
                masked_payload=mask_payload(payload),
            )
        except httpx.HTTPError as exc:
            return ConnectorResult(
                platform=self.platform,
                status="failed",
                message=f"워크드 API 호출 실패: {exc.__class__.__name__}",
                masked_payload=mask_payload(payload),
            )

