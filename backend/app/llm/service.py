import hashlib
import json
import os
from collections.abc import Callable, Mapping
from typing import TypeVar

from pydantic import BaseModel

from app.llm.redaction import redact
from app.llm.schemas import ExtractedFields, HireAnswer, Message, RiskExplanation

ModelT = TypeVar("ModelT", bound=BaseModel)


class LLMService:
    def __init__(
        self,
        *,
        enabled: bool | None = None,
        provider: Callable[[str, object], object] | None = None,
    ) -> None:
        self.enabled = (
            enabled
            if enabled is not None
            else os.getenv("LLM_ENABLED", "false").lower() == "true"
        )
        self._provider = provider
        self._cache: dict[str, object] = {}

    def extract_document_fields(self, doc_text: str) -> ExtractedFields:
        return self._run(
            "extract",
            {"text": redact(doc_text)},
            ExtractedFields,
            ExtractedFields(),
        )

    def explain_risk(self, context: Mapping[str, object]) -> str:
        result = self._run(
            "risk",
            context,
            RiskExplanation,
            RiskExplanation(explanation=_risk_template(context)),
        )
        return result.explanation

    def draft_message(self, kind: str, context: Mapping[str, object]) -> Message:
        return self._run(
            "message",
            {"kind": kind, "context": context},
            Message,
            Message(
                subject=f"Onboarding update: {kind}",
                body="Please review the next onboarding action in the workspace.",
            ),
        )

    def justify_recommendations(
        self, options: list[Mapping[str, object]], context: Mapping[str, object]
    ) -> list[str]:
        return [
            f"{option.get('playbook_id', 'Action')} is ranked from computed schedule impact."
            for option in options
        ]

    def answer_hire_question(
        self, question: str, hire_context: Mapping[str, object]
    ) -> HireAnswer:
        tasks = hire_context.get("tasks", [])
        answer = (
            "The next step is the earliest unfinished task in the dependency plan."
            if tasks
            else "No onboarding tasks are currently available."
        )
        return self._run(
            "answer",
            {"question": redact(question), "context": hire_context},
            HireAnswer,
            HireAnswer(answer=answer, sources=[]),
        )

    def _run(
        self,
        operation: str,
        payload: object,
        output: type[ModelT],
        fallback: ModelT,
    ) -> ModelT:
        key = hashlib.sha256(
            json.dumps(
                {"operation": operation, "payload": payload},
                sort_keys=True,
                default=str,
            ).encode()
        ).hexdigest()
        cached = self._cache.get(key)
        if cached is not None:
            return output.model_validate(cached)
        if not self.enabled:
            return fallback
        result: ModelT = fallback
        if self._provider is not None:
            for _ in range(2):
                try:
                    result = output.model_validate(self._provider(operation, payload))
                    break
                except (TimeoutError, ValueError, TypeError):
                    continue
        self._cache[key] = result.model_dump()  # type: ignore[attr-defined]
        return result


def get_llm_service() -> LLMService:
    return LLMService()


def _risk_template(context: Mapping[str, object]) -> str:
    task_id = context.get("task_id", "the task")
    slack = context.get("slack_days", "computed")
    return f"{task_id} is at risk based on its deterministic projection of {slack} days of slack."
