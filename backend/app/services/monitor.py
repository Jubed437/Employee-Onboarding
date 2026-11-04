from collections import defaultdict
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock, load_holidays
from app.core.config import load_playbooks, load_policies, load_scoring
from app.db.base import Employee, TaskInstance
from app.services.impact import calculate_impact
from app.services.readiness import calculate_readiness, save_snapshot
from app.services.recommender import recommend_for_risk
from app.services.risk import evaluate_tasks, upsert_risks
from app.services.root_cause import find_root_cause

DEFAULT_CONFIG_ROOT = Path(__file__).parents[3] / "config"
Subscriber = Callable[[dict[str, object]], None]
_subscribers: list[Subscriber] = []


def subscribe(callback: Subscriber) -> Callable[[], None]:
    _subscribers.append(callback)

    def unsubscribe() -> None:
        if callback in _subscribers:
            _subscribers.remove(callback)

    return unsubscribe


def publish(event: dict[str, object]) -> None:
    for callback in tuple(_subscribers):
        callback(event)


def evaluate(
    session: Session,
    employee_id: str,
    clock: Clock,
    *,
    config_root: Path = DEFAULT_CONFIG_ROOT,
) -> None:
    employee = session.get(Employee, employee_id)
    if employee is None:
        raise ValueError(f"employee {employee_id!r} not found")
    policies = load_policies(config_root / "policies.yaml")
    scoring = load_scoring(config_root / "scoring.yaml")
    playbooks = load_playbooks(config_root / "playbooks.yaml")
    holidays = load_holidays(config_root / "holidays_in.yaml")
    results = evaluate_tasks(
        session, employee_id, clock, policies, holidays=holidays
    )
    stored = upsert_risks(session, employee_id, results, clock)
    tasks = session.scalars(
        select(TaskInstance).where(TaskInstance.employee_id == employee_id)
    ).all()
    by_id = {task.id: task for task in tasks}
    projections = {result.task_id: result for result in results}
    dependencies = _dependencies(session, by_id)
    for risk in stored:
        target = by_id[risk.task_id]
        root = find_root_cause(target, by_id, dependencies, projections)
        impact = calculate_impact(root.task_id, by_id, dependencies, projections)
        risk.root_cause_task_id = root.task_id
        risk.impact = {
            "chain": list(root.chain),
            "outcome_tags": list(impact.outcome_tags),
            "has_critical_task": impact.has_critical_task,
        }
        recommendations = recommend_for_risk(
            session,
            risk,
            by_id[root.task_id],
            impact,
            playbooks=playbooks,
            policies=policies,
            clock=clock,
        )
        for recommendation in recommendations:
            if recommendation.tier.value == "AUTO":
                from app.domain.enums import Role
                from app.services.executor import execute_recommendation

                execute_recommendation(
                    session,
                    recommendation,
                    actor_id="SYSTEM",
                    actor_role=Role.ADMIN,
                    clock=clock,
                )
                publish(
                    {
                        "type": "recommendation.executed",
                        "hireId": employee_id,
                        "ts": clock.now().isoformat(),
                        "data": {"recommendationId": recommendation.id},
                    }
                )
    session.commit()
    readiness = calculate_readiness(
        session,
        employee_id,
        clock,
        scoring,
        results,
        slack_buffer_days=policies.slack_buffer_days,
    )
    save_snapshot(session, employee_id, clock, readiness)
    publish(
        {
            "type": "readiness.updated",
            "hireId": employee_id,
            "ts": clock.now().isoformat(),
            "data": {"score": readiness.score, "band": readiness.band},
        }
    )


def _dependencies(
    session: Session, tasks: dict[str, TaskInstance]
) -> dict[str, list[str]]:
    from app.db.base import task_dependency

    result: dict[str, list[str]] = defaultdict(list)
    for task_id, dependency_id in session.execute(select(task_dependency)).all():
        if task_id in tasks and dependency_id in tasks:
            result[task_id].append(dependency_id)
    return result
