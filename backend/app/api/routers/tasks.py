from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.clock import RealClock
from app.core.security import CurrentUser
from app.db.base import TaskInstance
from app.domain.api_schemas import TaskResponse, TransitionRequest
from app.services.state_machine import InvalidTransition, transition_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/{task_id}/transition", response_model=TaskResponse)
def transition(
    task_id: str,
    request: TransitionRequest,
    session: Session = Depends(get_db),
    user: CurrentUser = Depends(current_user),
) -> TaskInstance:
    task = session.get(TaskInstance, task_id)
    if task is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Task not found"},
        )
    try:
        return transition_task(
            session,
            task,
            request.to,
            actor_id=user.id,
            actor_role=user.role,
            clock=RealClock(),
            reason=request.reason,
        )
    except InvalidTransition as error:
        raise HTTPException(
            status_code=409,
            detail={"code": "INVALID_TRANSITION", "message": str(error)},
        ) from error
