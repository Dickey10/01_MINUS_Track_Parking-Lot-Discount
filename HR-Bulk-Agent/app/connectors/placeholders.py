from app.connectors.base import HRConnector
from app.models import ChangeEvent, ConnectorPreview, ConnectorResult, EmployeePayload, Platform


class PlaceholderConnector(HRConnector):
    supports_live_apply = False

    def __init__(self, platform: Platform, note: str):
        self.platform = platform
        self.note = note

    async def validate(self, event_type: ChangeEvent, employee: EmployeePayload) -> list[str]:
        return [f"{self.platform.value}: 2차 이후 연동 대상입니다. {self.note}"]

    async def preview(self, event_type: ChangeEvent, employee: EmployeePayload) -> ConnectorPreview:
        return ConnectorPreview(
            platform=self.platform,
            action="unsupported",
            identifier=employee.employee_id,
            warnings=await self.validate(event_type, employee),
        )

    async def apply(self, event_type: ChangeEvent, employee: EmployeePayload) -> ConnectorResult:
        return ConnectorResult(
            platform=self.platform,
            status="skipped",
            message=f"{self.platform.value}는 현재 실제 반영 대상이 아닙니다.",
        )

