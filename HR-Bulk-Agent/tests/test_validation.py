import unittest

from app.models import ChangeEvent, ChangeRequestCreate, EmployeePayload
from app.validation import validate_change_request


class ValidationTests(unittest.TestCase):
    def test_hire_requires_core_fields(self):
        request = ChangeRequestCreate(
            event_type=ChangeEvent.hire,
            employee=EmployeePayload(employee_id="1001", name="홍길동"),
        )

        errors = validate_change_request(request)

        self.assertIn("hire: 필수값 누락 - company", errors)
        self.assertIn("hire: 필수값 누락 - hire_date", errors)

    def test_termination_date_cannot_precede_hire_date(self):
        request = ChangeRequestCreate(
            event_type=ChangeEvent.terminate,
            employee=EmployeePayload(
                employee_id="1001",
                name="홍길동",
                hire_date="2026-05-10",
                termination_date="2026-05-01",
            ),
        )

        errors = validate_change_request(request)

        self.assertIn("퇴사일은 입사일보다 빠를 수 없습니다.", errors)


if __name__ == "__main__":
    unittest.main()

