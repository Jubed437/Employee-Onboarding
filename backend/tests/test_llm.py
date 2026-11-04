from app.llm.redaction import redact
from app.llm.service import LLMService


def test_redaction_masks_sensitive_values() -> None:
    text = "PAN ABCDE1234F, Aadhaar 1234 5678 9012, bank 123456789012 and a@b.test"
    masked = redact(text)
    assert "ABCDE1234F" not in masked
    assert "1234 5678 9012" not in masked
    assert "123456789012" not in masked
    assert "a@b.test" not in masked


def test_disabled_service_uses_validated_deterministic_fallback() -> None:
    service = LLMService(enabled=False)
    first = service.answer_hire_question("What is next?", {"tasks": ["HR-01"]})
    second = service.answer_hire_question("What is next?", {"tasks": ["HR-01"]})
    assert first == second
    assert first.sources == []
    assert "next step" in first.answer


def test_risk_explanation_is_grounded_in_computed_context() -> None:
    result = LLMService(enabled=False).explain_risk(
        {"task_id": "PAY-06", "slack_days": -2}
    )
    assert "PAY-06" in result
    assert "-2" in result


def test_provider_boundary_receives_redacted_input() -> None:
    seen: list[object] = []

    def provider(_: str, payload: object) -> object:
        seen.append(payload)
        return {"fields": {"email": "[EMAIL_REDACTED]"}}

    result = LLMService(enabled=True, provider=provider).extract_document_fields(
        "Contact a@b.test"
    )
    assert result.fields["email"] == "[EMAIL_REDACTED]"
    assert "a@b.test" not in str(seen)
