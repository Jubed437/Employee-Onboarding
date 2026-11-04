from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock, add_business_days, business_days_between
from app.db.base import Risk, TaskInstance, new_id, task_dependency
from app.domain.enums import ReasonCode, RiskLevel, RiskStatus, TaskState
from app.domain.schemas import PoliciesConfig


@dataclass(frozen=True)
class RiskResult:
    task_id: str
    earliest_finish: date
    slack_days: float
    level: RiskLevel | None
    reason_codes: tuple[ReasonCode, ...]


def evaluate_tasks(
    session: Session,
    employee_id: str,
    clock: Clock,
    policies: PoliciesConfig,
    *,
    holidays: set[date] | frozenset[date] = frozenset(),
) -> list[RiskResult]:
    tasks = session.scalars(
        select(TaskInstance).where(TaskInstance.employee_id == employee_id)
    ).all()
    by_id = {task.id: task for task in tasks}
    dependencies = _dependencies(session, by_id)
    now = clock.now()
    results: list[RiskResult] = []
    finishes: dict[str, date] = {}
    for task in _topological_order(tasks, dependencies):
        if task.state in {TaskState.DONE, TaskState.SKIPPED}:
            finishes[task.id] = task.completed_at.date() if task.completed_at else task.due_date
            continue
        start = max(
            [now.date()]
            + [
                finishes[dependency]
                for dependency in dependencies[task.id]
                if dependency in finishes
            ]
        )
        remaining = _remaining_days(task, now, holidays)
        owner_penalty = _owner_penalty(task, tasks, now.date(), policies)
        if owner_penalty:
            remaining += owner_penalty
        sla = task.external_sla_days if task.external_sla_days and not task.started_at else 0
        if sla:
            remaining += sla
        finish = add_business_days(start, _business_day_count(remaining), holidays)
        slack = business_days_between(finish, task.due_date, holidays)
        reasons = _reasons(task, dependencies, by_id, finishes, owner_penalty, sla, now.date())
        level = (
            RiskLevel.HIGH
            if slack < 0 or task.due_date < now.date()
            else RiskLevel.MEDIUM
            if slack < policies.slack_buffer_days
            else None
        )
        finishes[task.id] = finish
        results.append(RiskResult(task.id, finish, float(slack), level, tuple(reasons)))
    return results


def upsert_risks(
    session: Session,
    employee_id: str,
    results: list[RiskResult],
    clock: Clock,
) -> list[Risk]:
    now = clock.now()
    risks: list[Risk] = []
    for result in results:
        existing: Risk | None = session.scalar(
            select(Risk).where(
                Risk.employee_id == employee_id,
                Risk.task_id == result.task_id,
                Risk.status == RiskStatus.OPEN,
            )
        )
        if result.level is None:
            if existing is not None:
                existing.status = RiskStatus.RESOLVED
                existing.resolved_at = now
            continue
        if existing is None:
            existing = Risk(
                id=new_id(),
                employee_id=employee_id,
                task_id=result.task_id,
                first_seen_at=now,
                status=RiskStatus.OPEN,
            )
            session.add(existing)
        existing.level = result.level
        existing.reason_codes = [reason.value for reason in result.reason_codes]
        existing.predicted_breach_date = result.earliest_finish
        existing.slack_days = result.slack_days
        risks.append(existing)
    session.commit()
    return risks


def _dependencies(session: Session, tasks: dict[str, TaskInstance]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {task_id: [] for task_id in tasks}
    for task_id, dependency_id in session.execute(select(task_dependency)).all():
        if task_id in tasks and dependency_id in tasks:
            result[task_id].append(dependency_id)
    return result


def _topological_order(
    tasks: Sequence[TaskInstance], dependencies: dict[str, list[str]]
) -> list[TaskInstance]:
    ordered: list[TaskInstance] = []
    remaining = {task.id: task for task in tasks}
    while remaining:
        ready = [
            task
            for task in remaining.values()
            if all(dep not in remaining for dep in dependencies[task.id])
        ]
        if not ready:
            raise ValueError("task dependency cycle detected")
        for task in ready:
            ordered.append(task)
            del remaining[task.id]
    return ordered


def _remaining_days(
    task: TaskInstance, now: datetime, holidays: set[date] | frozenset[date]
) -> float:
    if task.state is TaskState.IN_PROGRESS and task.started_at:
        elapsed = business_days_between(task.started_at.date(), now.date(), holidays)
        return max(0.5, task.duration_days - elapsed)
    return task.duration_days + (2 if task.state is TaskState.REJECTED else 0)


def _owner_penalty(
    task: TaskInstance,
    tasks: Sequence[TaskInstance],
    today: date,
    policies: PoliciesConfig,
) -> float:
    overdue = sum(
        other.owner_role == task.owner_role
        and other.state not in {TaskState.DONE, TaskState.SKIPPED}
        and other.due_date < today
        for other in tasks
    )
    return min(
        policies.owner_overdue_penalty_days * overdue,
        policies.owner_overdue_penalty_cap_days,
    )


def _reasons(
    task: TaskInstance,
    dependencies: dict[str, list[str]],
    by_id: dict[str, TaskInstance],
    finishes: dict[str, date],
    owner_penalty: float,
    sla: float,
    today: date,
) -> list[ReasonCode]:
    reasons: list[ReasonCode] = []
    if task.due_date < today:
        reasons.append(ReasonCode.OVERDUE)
    if any(finishes[dependency] > by_id[task.id].due_date for dependency in dependencies[task.id]):
        reasons.append(ReasonCode.UPSTREAM_DELAY)
    if any(by_id[dependency].state is TaskState.REJECTED for dependency in dependencies[task.id]):
        reasons.append(ReasonCode.REJECTED_ANCESTOR)
    if owner_penalty:
        reasons.append(ReasonCode.OWNER_OVERLOAD)
    if sla:
        reasons.append(ReasonCode.EXTERNAL_SLA)
    if task.is_critical:
        reasons.append(ReasonCode.CRITICAL_GATE)
    return reasons


def _business_day_count(days: float) -> int:
    return max(1, int(days + 0.999999))
