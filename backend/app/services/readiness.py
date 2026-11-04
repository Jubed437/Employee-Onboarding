from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock
from app.db.base import Employee, ReadinessSnapshot, TaskInstance, new_id
from app.domain.enums import TaskState
from app.domain.schemas import ScoringConfig
from app.services.risk import RiskResult


@dataclass(frozen=True)
class ReadinessResult:
    score: int
    band: str
    breakdown: dict[str, float]
    drivers: tuple[str, ...]


def calculate_readiness(
    session: Session,
    employee_id: str,
    clock: Clock,
    scoring: ScoringConfig,
    risk_results: list[RiskResult],
    *,
    slack_buffer_days: float,
) -> ReadinessResult:
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise ValueError(f"employee {employee_id!r} not found")
    tasks = session.scalars(
        select(TaskInstance).where(TaskInstance.employee_id == employee_id)
    ).all()
    projections = {result.task_id: result for result in risk_results}
    now = clock.now().date()
    mandatory_pre_join = [
        task for task in tasks if task.is_mandatory and task.due_date <= employee.join_date
    ]
    critical = _ratio(
        sum(task.state is TaskState.DONE for task in mandatory_pre_join),
        len(mandatory_pre_join),
    )
    open_critical = [
        task for task in tasks
        if task.is_critical and task.state not in {TaskState.DONE, TaskState.SKIPPED}
    ]
    slack = _ratio(
        sum(
            projections[task.id].slack_days >= slack_buffer_days
            for task in open_critical
            if task.id in projections
        ),
        len(open_critical),
    )
    compliance = [task for task in tasks if task.is_compliance]
    compliance_good = sum(
        task.state in {TaskState.DONE, TaskState.SKIPPED}
        or (
            task.id in projections
            and projections[task.id].slack_days >= slack_buffer_days
        )
        for task in compliance
    )
    compliance_score = _ratio(compliance_good, len(compliance))
    due_tasks = [task for task in tasks if task.due_date <= now]
    overdue = sum(
        task.state not in {TaskState.DONE, TaskState.SKIPPED}
        and task.due_date < now
        for task in due_tasks
    )
    timeliness = 1 - overdue / len(due_tasks) if due_tasks else 1.0
    breakdown = {
        "critical": critical,
        "slack": slack,
        "compliance": compliance_score,
        "timeliness": timeliness,
    }
    score = round(
        100
        * sum(scoring.weights[name] * value for name, value in breakdown.items())
    )
    band = (
        "READY"
        if score >= scoring.bands["ready_min"]
        else "WATCH"
        if score >= scoring.bands["watch_min"]
        else "AT_RISK"
    )
    return ReadinessResult(
        score=score,
        band=band,
        breakdown=breakdown,
        drivers=_drivers(tasks, projections, breakdown, slack_buffer_days),
    )


def save_snapshot(
    session: Session,
    employee_id: str,
    clock: Clock,
    result: ReadinessResult,
) -> ReadinessSnapshot:
    snapshot = ReadinessSnapshot(
        id=new_id(),
        employee_id=employee_id,
        ts=clock.now(),
        score=result.score,
        band=result.band,
        breakdown=result.breakdown,
        drivers=list(result.drivers),
    )
    session.add(snapshot)
    session.commit()
    return snapshot


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 1.0


def _drivers(
    tasks: Sequence[TaskInstance],
    projections: dict[str, RiskResult],
    breakdown: dict[str, float],
    slack_buffer_days: float,
) -> tuple[str, ...]:
    drivers: list[str] = []
    for task in tasks:
        projection = projections.get(task.id)
        if task.state is TaskState.REJECTED:
            drivers.append(f"{task.template_key} rejected affects critical and slack readiness")
        elif projection is not None and projection.slack_days < slack_buffer_days:
            drivers.append(
                f"{task.template_key} has {projection.slack_days:g} days of slack"
            )
    if breakdown["critical"] < 1:
        drivers.append(f"critical completion is {breakdown['critical']:.2f}")
    if breakdown["compliance"] < 1:
        drivers.append(f"compliance readiness is {breakdown['compliance']:.2f}")
    return tuple(dict.fromkeys(drivers))
