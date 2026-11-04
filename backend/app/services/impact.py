from dataclasses import dataclass
from datetime import date

from app.db.base import TaskInstance
from app.services.risk import RiskResult
from app.services.root_cause import DependencyMap, TaskMap


@dataclass(frozen=True)
class ImpactItem:
    task_id: str
    title: str
    due_date: date
    projected_finish: date
    breaches: bool
    outcome_tags: tuple[str, ...]


@dataclass(frozen=True)
class ImpactResult:
    items: tuple[ImpactItem, ...]
    outcome_tags: tuple[str, ...]
    has_critical_task: bool


def calculate_impact(
    root_task_id: str,
    tasks: TaskMap,
    dependencies: DependencyMap,
    projections: dict[str, RiskResult],
) -> ImpactResult:
    descendants = _descendants(root_task_id, dependencies)
    items = tuple(
        _item(tasks[task_id], projections[task_id])
        for task_id in descendants
        if task_id in projections
    )
    tags = sorted({tag for item in items for tag in item.outcome_tags})
    return ImpactResult(
        items=items,
        outcome_tags=tuple(tags),
        has_critical_task=any(tasks[item.task_id].is_critical for item in items),
    )


def _descendants(root: str, dependencies: DependencyMap) -> list[str]:
    children: dict[str, list[str]] = {}
    for task_id, dependency_ids in dependencies.items():
        for dependency_id in dependency_ids:
            children.setdefault(dependency_id, []).append(task_id)
    result: list[str] = []
    pending = [root]
    while pending:
        current = pending.pop(0)
        if current not in result:
            result.append(current)
            pending.extend(children.get(current, []))
    return result


def _item(task: TaskInstance, projection: RiskResult) -> ImpactItem:
    return ImpactItem(
        task_id=task.id,
        title=task.title,
        due_date=task.due_date,
        projected_finish=projection.earliest_finish,
        breaches=projection.slack_days < 0,
        outcome_tags=tuple(task.outcome_tags),
    )
