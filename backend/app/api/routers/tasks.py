from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.clock import RealClock
from app.core.security import CurrentUser
from app.db.base import Employee, TaskInstance, task_dependency
from app.domain.api_schemas import PlanResponse, TaskResponse, TransitionRequest
from app.domain.enums import Role, TaskState
from app.services.state_machine import InvalidTransition, transition_task

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/mine", response_model=list[TaskResponse])
def my_tasks(
    state: str | None = Query(default=None),
    session: Session = Depends(get_db),
    user: CurrentUser = Depends(current_user),
) -> list[TaskInstance]:
    query = select(TaskInstance)
    if user.role is Role.NEW_HIRE:
        employee = session.scalar(
            select(Employee).where(Employee.email == f"{user.id}@example.test")
        )
        if employee is None:
            return []
        query = query.where(TaskInstance.employee_id == employee.id)
    else:
        query = query.where(TaskInstance.owner_role == user.role)
    if state:
        try:
            query = query.where(TaskInstance.state == TaskState(state))
        except ValueError as error:
            raise HTTPException(status_code=400, detail="Invalid task state") from error
    return list(session.scalars(query.order_by(TaskInstance.due_date)))


@router.get("/plans/{hire_id}", response_model=PlanResponse)
def plan(
    hire_id: str,
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(current_user),
) -> PlanResponse:
    tasks = list(
        session.scalars(
            select(TaskInstance)
            .where(TaskInstance.employee_id == hire_id)
            .order_by(TaskInstance.due_date, TaskInstance.template_key)
        )
    )
    if not tasks:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Plan not found"},
        )
    task_ids = {task.id for task in tasks}
    edges = [
        {"from": dependency_id, "to": task_id}
        for task_id, dependency_id in session.execute(select(task_dependency)).all()
        if task_id in task_ids and dependency_id in task_ids
    ]
    return PlanResponse(
        tasks=[TaskResponse.model_validate(task) for task in tasks],
        edges=edges,
    )


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
