from datetime import date
import unittest

from app.master import current_pay_grade, promotion_candidate
from app.models import MasterEmployee
from app.security import hash_password, verify_password


class MasterEmployeeTests(unittest.TestCase):
    def test_current_pay_grade_uses_full_service_years(self):
        employee = MasterEmployee(
            employee_id="1001",
            name="홍길동",
            hire_date="2020-06-01",
            initial_pay_grade=3,
            rank="대리",
        )

        self.assertEqual(current_pay_grade(employee, date(2026, 5, 31)), 8)
        self.assertEqual(current_pay_grade(employee, date(2026, 6, 1)), 9)

    def test_promotion_candidate_from_rank_rule(self):
        employee = MasterEmployee(
            employee_id="1001",
            name="홍길동",
            department="영업팀",
            hire_date="2020-01-01",
            initial_pay_grade=3,
            rank="대리",
        )

        candidate = promotion_candidate(employee, date(2026, 1, 1))

        self.assertTrue(candidate.eligible)
        self.assertEqual(candidate.next_rank, "과장")


class AccountSecurityTests(unittest.TestCase):
    def test_password_hash_verification(self):
        password_hash = hash_password("admin123!")

        self.assertTrue(verify_password("admin123!", password_hash))
        self.assertFalse(verify_password("wrong-password", password_hash))


if __name__ == "__main__":
    unittest.main()
