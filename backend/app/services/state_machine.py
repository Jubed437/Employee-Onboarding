from collections.abc import Callable
from copy import deepcopy
from datetime import datetime
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.db.base import (
    AuditLog,
    EventLog,
    TaskInstance,
    new_id,
    task_dependency,
)
from app.domain.enums import Role, TaskState

MonitorCallback = Callable[[str], None]
SYSTEM_ACTOR: Final = "SYSTEM"


class InvalidTransition(ValueError):
    """Raised when a task transition is not permitted."""


def transition_task(
    session: Session,
    task: TaskInstance,
    target: TaskState,
    *,
    actor_id: str,
    actor_role: Role | None,
    clock: Clock,
    reason: str | None = None,
    on_evaluated: MonitorCallback | None = None,
) -> TaskInstance:
    source = task.state
    _validate_transition(
        task,
        target,
        actor_id=actor_id,
        actor_role=actor_role,
        reason=reason,
    )
    before = _task_snapshot(task)
    now = clock.now()
    _apply_transition(task, target, now, reason)
    session.add(
        EventLog(
            id=new_id(),
            ts=now,
            employee_id=task.employee_id,
            task_id=task.id,
            type=f"TASK_{target.value}",
            actor=actor_id,
            payload={"from": source.value, "to": target.value, "reason": reason},
        )
    )
    session.add(
        AuditLog(
            id=new_id(),
            ts=now,
            actor=actor_id,
            action="TASK_TRANSITION",
            entity_type="task_instance",
            entity_id=task.id,
            before=before,
            after=_task_snapshot(task),
            reason=reason,
        )
    )
    _unlock_dependents(session, task, now, actor_id)
    session.commit()
    if on_evaluated is not None:
        on_evaluated(task.employee_id)
    return task


def _validate_transition(
    task: TaskInstance,
    target: TaskState,
    *,
    actor_id: str,
    actor_role: Role | None,
    reason: str | None,
) -> None:
    source = task.state
    if source is TaskState.NOT_STARTED and target is TaskState.READY:
        if actor_id != SYSTEM_ACTOR:
            raise InvalidTransition("only SYSTEM can make a task READY")
        return
    if source is TaskState.READY and target is TaskState.IN_PROGRESS:
        if not _is_owner(task, actor_id, actor_role):
            raise InvalidTransition("only the task owner or assignee can start the task")
        return
    if source is TaskState.IN_PROGRESS and target is TaskState.DONE:
        if actor_id != SYSTEM_ACTOR and not _is_owner(task, actor_id, actor_role):
            raise InvalidTransition("only the task owner or SYSTEM can complete the task")
        return
    if source is TaskState.IN_PROGRESS and target is TaskState.REJECTED:
        if actor_role not in {Role.HR, Role.ADMIN}:
            raise InvalidTransition("only HR or ADMIN can reject a submission")
        if not reason:
            raise InvalidTransition("rejection requires a reason")
        return
    if source is TaskState.REJECTED and target is TaskState.IN_PROGRESS:
        if not _is_owner(task, actor_id, actor_role):
            raise InvalidTransition("only the submitter or assignee can resubmit")
        return
    if source in {TaskState.READY, TaskState.IN_PROGRESS} and target is TaskState.BLOCKED:
        if actor_id != SYSTEM_ACTOR and actor_role is not Role.HR:
            raise InvalidTransition("only SYSTEM or HR can block a task")
        if not reason:
            raise InvalidTransition("blocking requires a reason")
        return
    if source is TaskState.BLOCKED and target in {TaskState.READY, TaskState.IN_PROGRESS}:
        if actor_id != SYSTEM_ACTOR and actor_role is not Role.HR:
            raise InvalidTransition("only SYSTEM or HR can unblock a task")
        return
    if source is TaskState.DONE and target is TaskState.IN_PROGRESS:
        if actor_role not in {Role.HR, Role.ADMIN}:
            raise InvalidTransition("only HR or ADMIN can reopen a task")
        if not reason:
            raise InvalidTransition("reopening requires a reason")
        return
    raise InvalidTransition(f"cannot transition task from {source} to {target}")


def _apply_transition(
    task: TaskInstance,
    target: TaskState,
    now: datetime,
    reason: str | None,
) -> None:
    if target is TaskState.IN_PROGRESS:
        task.attempts += 1
        task.started_at = task.started_at or now
    if target is TaskState.DONE:
        task.completed_at = now
    if target is TaskState.REJECTED:
        task.rework_count += 1
    if target is TaskState.BLOCKED:
        task.meta = {**task.meta, "previous_state": task.state.value}
    if reason is not None:
        task.meta = {**task.meta, "reason": reason}
    task.state = target


def _unlock_dependents(
    session: Session, completed: TaskInstance, now: datetime, actor: str
) -> None:
    dependent_ids: list[str] = list(session.scalars(
        select(task_dependency.c.task_id).where(
            task_dependency.c.depends_on_task_id == completed.id
        )
    ).all())
    for dependent_id in dependent_ids:
        dependent = session.get(TaskInstance, dependent_id)
        if dependent is None or dependent.state is not TaskState.NOT_STARTED:
            continue
        dependency_states = session.execute(
            select(TaskInstance.state)
            .join(
                task_dependency,
                task_dependency.c.depends_on_task_id == TaskInstance.id,
            )
            .where(task_dependency.c.task_id == dependent.id)
        ).scalars()
        if all(state in {TaskState.DONE, TaskState.SKIPPED} for state in dependency_states):
            dependent.state = TaskState.READY
            session.add(
                EventLog(
                    id=new_id(),
                    ts=now,
                    employee_id=dependent.employee_id,
                    task_id=dependent.id,
                    type="TASK_READY",
                    actor=actor,
                    payload={"reason": "dependencies completed"},
                )
            )


def _is_owner(task: TaskInstance, actor_id: str, actor_role: Role | None) -> bool:
    return task.assignee_user_id == actor_id or actor_role is task.owner_role


def _task_snapshot(task: TaskInstance) -> dict[str, object]:
    return {
        "state": task.state.value,
        "attempts": task.attempts,
        "rework_count": task.rework_count,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "meta": deepcopy(task.meta),
    }
