import unittest

from app.connectors.gift24 import Gift24Connector
from app.connectors.workd import WorkdConnector
from app.models import ChangeEvent, EmployeePayload


class ConnectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_gift24_defaults_to_dry_run(self):
        connector = Gift24Connector()
        result = await connector.apply(
            ChangeEvent.hire,
            EmployeePayload(
                employee_id="1001",
                name="홍길동",
                company="하츠",
                rank="대리",
                phone="01012345678",
            ),
        )

        self.assertEqual(result.status, "dry_run")
        self.assertNotIn("01012345678", str(result.masked_payload))

    async def test_workd_validates_email_for_hire(self):
        connector = WorkdConnector()
        errors = await connector.validate(
            ChangeEvent.hire,
            EmployeePayload(employee_id="1001", name="홍길동", company="하츠"),
        )

        self.assertIn("워크드: 신규 직원 생성에는 이메일이 필요합니다.", errors)


if __name__ == "__main__":
    unittest.main()

