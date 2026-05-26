from app.connectors.base import HRConnector
from app.connectors.gift24 import Gift24Connector
from app.connectors.placeholders import PlaceholderConnector
from app.connectors.workd import WorkdConnector
from app.models import Platform


def connector_registry() -> dict[Platform, HRConnector]:
    return {
        Platform.gift24: Gift24Connector(),
        Platform.workd: WorkdConnector(),
        Platform.shiftee: PlaceholderConnector(Platform.shiftee, "Open API 신청 및 토큰 발급 후 활성화합니다."),
        Platform.erp: PlaceholderConnector(Platform.erp, "구형 ERP-IU는 1차 범위에서 write 제외입니다."),
        Platform.amaranth: PlaceholderConnector(Platform.amaranth, "그룹웨어/Amaranth10 API 정책 확인 후 활성화합니다."),
        Platform.inhr: PlaceholderConnector(Platform.inhr, "자인원 IN HR 연동 문서 확보 후 활성화합니다."),
    }

