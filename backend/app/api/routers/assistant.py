from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.security import CurrentUser
from app.db.base import Employee, TaskInstance
from app.llm.service import get_llm_service

router = APIRouter(tags=["assistant"])


class AssistantRequest(BaseModel):
    question: str


@router.post("/hires/{hire_id}/assistant")
def assistant(
    hire_id: str,
    request: AssistantRequest,
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(current_user),
) -> dict[str, object]:
    if session.get(Employee, hire_id) is None:
        raise HTTPException(status_code=404, detail="Hire not found")
    tasks = session.scalars(
        select(TaskInstance).where(TaskInstance.employee_id == hire_id)
    ).all()
    result = get_llm_service().answer_hire_question(
        request.question,
        {"tasks": [{"id": task.template_key, "state": task.state.value} for task in tasks]},
    )
    return result.model_dump()
