import unittest

from app.chat_agent import analyze_chat
from app.models import ChatAnalyzeRequest


class ChatAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_bulk_promotion_lines_are_split(self):
        result = await analyze_chat(
            ChatAnalyzeRequest(
                message="사번 1001 홍길동 영업팀 과장 승진\n사번 1002 김하나 개발팀 차장 승진"
            )
        )

        self.assertEqual(len(result.drafts), 2)
        self.assertEqual(result.drafts[0].change_request.event_type.value, "promotion")
        self.assertEqual(result.drafts[0].change_request.employee.employee_id, "1001")

    async def test_missing_details_generate_followup_questions(self):
        result = await analyze_chat(ChatAnalyzeRequest(message="박민수 입사 처리해줘"))

        questions = " ".join(result.drafts[0].followup_questions)

        self.assertIn("사번 정보를 알려주세요.", questions)
        self.assertIn("입사일 정보를 알려주세요.", questions)

    async def test_global_company_and_date_apply_to_employee_lines(self):
        result = await analyze_chat(
            ChatAnalyzeRequest(
                message="6월 1일 입사자 등록해줘. 회사는 하츠.\n사번 260601 홍길동 영업팀 대리"
            )
        )

        employee = result.drafts[0].change_request.employee

        self.assertEqual(len(result.drafts), 1)
        self.assertEqual(employee.company, "하츠")
        self.assertEqual(employee.hire_date, "2026-06-01")

    async def test_multiple_employee_ids_in_one_line_are_split(self):
        result = await analyze_chat(
            ChatAnalyzeRequest(message="사번 1001 박민수 영업팀 과장 승진, 사번 1002 이서연 개발팀 차장 승진")
        )

        self.assertEqual(len(result.drafts), 2)
        self.assertEqual(result.drafts[1].change_request.employee.employee_id, "1002")


if __name__ == "__main__":
    unittest.main()
