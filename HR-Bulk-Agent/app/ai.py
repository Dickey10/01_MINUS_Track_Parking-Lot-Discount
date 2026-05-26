from app.config import settings
from app.models import AIAssistRequest
from app.security import mask_payload
from app.validation import REQUIRED_BY_EVENT, validate_change_request
from app.models import ChangeRequestCreate


def local_assist(request: AIAssistRequest) -> dict:
    change = ChangeRequestCreate(event_type=request.event_type, employee=request.employee)
    missing = [
        field
        for field in sorted(REQUIRED_BY_EVENT[request.event_type])
        if not getattr(request.employee, field)
    ]
    errors = validate_change_request(change)
    return {
        "mode": "local_rules",
        "masked_employee": mask_payload(request.employee.model_dump()),
        "missing_fields": missing,
        "validation_errors": errors,
        "recommendation": "누락 필드를 보완한 뒤 미리보기에서 플랫폼별 반영 값을 확인하세요.",
    }


async def assist(request: AIAssistRequest) -> dict:
    if not settings.openai_api_key:
        return local_assist(request)
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        safe_payload = mask_payload(request.employee.model_dump())
        response = await client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": "You help HR staff validate masked employee change requests. Do not ask for resident registration numbers, bank accounts, or secrets.",
                },
                {
                    "role": "user",
                    "content": f"event_type={request.event_type.value}, employee={safe_payload}, question={request.question or ''}",
                },
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "hr_assist",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "missing_fields": {"type": "array", "items": {"type": "string"}},
                            "risk_notes": {"type": "array", "items": {"type": "string"}},
                            "recommendation": {"type": "string"},
                        },
                        "required": ["missing_fields", "risk_notes", "recommendation"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            },
        )
        return {"mode": "openai_masked", "masked_employee": safe_payload, "assistant": response.output_text}
    except Exception as exc:
        fallback = local_assist(request)
        fallback["mode"] = "local_rules_openai_failed"
        fallback["openai_error"] = exc.__class__.__name__
        return fallback

