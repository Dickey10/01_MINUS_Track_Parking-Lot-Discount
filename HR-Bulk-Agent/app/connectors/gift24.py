import httpx

from app.config import settings
from app.models import ChangeEvent, ConnectorPreview, ConnectorResult, EmployeePayload, Platform
from app.security import mask_payload
from app.connectors.base import HRConnector


class Gift24Connector(HRConnector):
    platform = Platform.gift24
    supports_live_apply = True

    def _action(self, event_type: ChangeEvent) -> str:
        if event_type == ChangeEvent.hire:
            return "create"
        if event_type == ChangeEvent.terminate:
            return "deactivate"
        return "update"

    def _payload(self, employee: EmployeePayload) -> dict:
        return {
            "externalId": employee.employee_id,
            "memberName": employee.name,
            "memberPhone": employee.phone,
            "memberRank": employee.rank,
            "birthDate": employee.birth_date,
        }

    async def validate(self, event_type: ChangeEvent, employee: EmployeePayload) -> list[str]:
        errors: list[str] = []
        if event_type in {ChangeEvent.hire, ChangeEvent.promotion} and not employee.rank:
            errors.append("선물24: 직급(memberRank) 값이 필요합니다.")
        if event_type == ChangeEvent.hire and not employee.phone:
            errors.append("선물24: 신규 연동회원 등록에는 전화번호가 필요합니다.")
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
                message="실제 선물24 API 호출은 비활성화되어 있습니다.",
                masked_payload=mask_payload(payload),
            )
        if not settings.gift24_client_id or not settings.gift24_client_secret:
            return ConnectorResult(
                platform=self.platform,
                status="failed",
                message="선물24 client_id/client_secret 설정이 없습니다.",
                masked_payload=mask_payload(payload),
            )
        endpoint = f"{settings.gift24_base_url.rstrip('/')}/birth/external/v1/members"
        headers = {
            "client_id": settings.gift24_client_id,
            "client_secret": settings.gift24_client_secret,
            "Content-Type": "application/json",
        }
        method = "DELETE" if event_type == ChangeEvent.terminate else "POST"
        body = {"externalIdList": [employee.employee_id]} if method == "DELETE" else {"members": [payload]}
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.request(method, endpoint, headers=headers, json=body)
            if response.status_code >= 400:
                return ConnectorResult(
                    platform=self.platform,
                    status="failed",
                    message=f"선물24 API 오류: HTTP {response.status_code}",
                    masked_payload=mask_payload(payload),
                )
            return ConnectorResult(
                platform=self.platform,
                status="success",
                message="선물24 API 반영 완료",
                request_ref=response.headers.get("x-request-id"),
                masked_payload=mask_payload(payload),
            )
        except httpx.HTTPError as exc:
            return ConnectorResult(
                platform=self.platform,
                status="failed",
                message=f"선물24 API 호출 실패: {exc.__class__.__name__}",
                masked_payload=mask_payload(payload),
            )

