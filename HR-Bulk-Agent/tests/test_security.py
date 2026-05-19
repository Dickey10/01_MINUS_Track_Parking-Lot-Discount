import unittest

from app.security import mask_payload


class SecurityTests(unittest.TestCase):
    def test_masks_personal_information(self):
        masked = mask_payload(
            {
                "employee_id": "1001",
                "name": "홍길동",
                "phone": "010-1234-5678",
                "email": "hong@example.com",
                "birth_date": "1991-08-26",
            }
        )

        self.assertEqual(masked["employee_id"], "1001")
        self.assertEqual(masked["name"], "홍**")
        self.assertEqual(masked["phone"], "010****5678")
        self.assertEqual(masked["email"], "ho***@example.com")
        self.assertEqual(masked["birth_date"], "1991-**-**")


if __name__ == "__main__":
    unittest.main()

