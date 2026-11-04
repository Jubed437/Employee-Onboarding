import pytest
from pydantic import ValidationError

from app.domain.api_schemas import HireCreate
from app.llm.service import LLMService


def test_invalid_hire_payload_is_rejected() -> None:
    with pytest.raises(ValidationError):
        HireCreate.model_validate(
            {
                "full_name": "Scenario",
                "email": "person@example.test",
                "job_title": "Engineer",
                "department": "Engineering",
                "join_date": "not-a-date",
                "work_state": "KA",
                "is_experienced": False,
                "is_remote": False,
            }
        )


def test_provider_timeout_falls_back_after_one_retry() -> None:
    calls = 0

    def provider(_: str, __: object) -> object:
        nonlocal calls
        calls += 1
        raise TimeoutError

    result = LLMService(enabled=True, provider=provider).explain_risk(
        {"task_id": "TASK-1", "slack_days": -1}
    )
    assert calls == 2
    assert "TASK-1" in result


def test_provider_output_is_cached() -> None:
    calls = 0

    def provider(_: str, __: object) -> object:
        nonlocal calls
        calls += 1
        return {"explanation": "stable"}

    service = LLMService(enabled=True, provider=provider)
    assert service.explain_risk({"task_id": "TASK-1"}) == "stable"
    assert service.explain_risk({"task_id": "TASK-1"}) == "stable"
    assert calls == 1
