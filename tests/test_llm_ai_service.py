import unittest

from services.llm_ai_service import LLMAIService
from utils.exceptions import AIConnectionError


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


class _FakeChatCompletions:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content
        self.error = error

    def create(self, **kwargs):  # noqa: ANN003
        if self.error:
            raise self.error
        return _FakeResponse(self.content or "{}")


class _FakeClient:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self.chat = type(
            "FakeChat",
            (),
            {"completions": _FakeChatCompletions(content=content, error=error)},
        )()


class LLMServiceTestCase(unittest.TestCase):
    def test_analyze_application_json_success(self) -> None:
        content = (
            '{"conclusion":"可提交","risk_level":"LOW","issues":["无"],'
            '"suggestions":["保持现有内容"],"summary":"ok"}'
        )
        service = LLMAIService(client=_FakeClient(content=content))
        result = service.analyze_application({"student_name": "A"})
        self.assertEqual(result["risk_level"], "LOW")
        self.assertTrue(isinstance(result["issues"], list))

    def test_summarize_feedback_fallback_text(self) -> None:
        content = "反馈类型：专业不匹配；建议动作：改专业后重申。"
        service = LLMAIService(client=_FakeClient(content=content))
        result = service.summarize_feedback(content)
        self.assertEqual(result["parse_mode"], "fallback_text")
        self.assertIn("summary", result)

    def test_suggest_next_action_with_quota(self) -> None:
        content = (
            '{"operation_explanations":["当前状态允许学校处理"],'
            '"recommended_next_action":"SCHOOL_RESERVE",'
            '"reasoning":["名额充足"],"alternatives":["SCHOOL_FEEDBACK"],"summary":"ok"}'
        )
        service = LLMAIService(client=_FakeClient(content=content))
        result = service.suggest_next_action(
            application_data={"status": "SCHOOL_PENDING"},
            role_code="ANU_OFFICER",
            quota_info={"university_left_quota": 2},
        )
        self.assertEqual(result["recommended_next_action"], "SCHOOL_RESERVE")

    def test_api_unavailable_error(self) -> None:
        service = LLMAIService(client=_FakeClient(error=RuntimeError("connection refused")))
        with self.assertRaises(AIConnectionError):
            service.analyze_application({"student_name": "A"})

    def test_illegal_status_explanation_output(self) -> None:
        content = (
            '{"operation_explanations":["状态为CLOSED，不能继续占位"],'
            '"recommended_next_action":"NO_ACTION",'
            '"reasoning":["流程已关闭"],"alternatives":["查看历史"],"summary":"done"}'
        )
        service = LLMAIService(client=_FakeClient(content=content))
        result = service.suggest_next_action(
            application_data={"status": "CLOSED"},
            role_code="AGENT_A",
            quota_info={"university_left_quota": 0},
        )
        self.assertIn("CLOSED", result["operation_explanations"][0])


if __name__ == "__main__":
    unittest.main()
