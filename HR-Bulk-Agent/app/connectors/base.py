from abc import ABC, abstractmethod

from app.models import ChangeEvent, ConnectorPreview, ConnectorResult, EmployeePayload, Platform


class HRConnector(ABC):
    platform: Platform
    supports_live_apply: bool = False

    @abstractmethod
    async def validate(self, event_type: ChangeEvent, employee: EmployeePayload) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    async def preview(self, event_type: ChangeEvent, employee: EmployeePayload) -> ConnectorPreview:
        raise NotImplementedError

    @abstractmethod
    async def apply(self, event_type: ChangeEvent, employee: EmployeePayload) -> ConnectorResult:
        raise NotImplementedError

    async def rollback_or_compensate(self, result: ConnectorResult) -> ConnectorResult:
        return ConnectorResult(
            platform=self.platform,
            status="skipped",
            message="자동 롤백 미지원: 플랫폼 관리자 화면에서 수동 확인 필요",
            request_ref=result.request_ref,
        )

