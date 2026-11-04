from dataclasses import dataclass
from datetime import date

from app.db.base import TaskInstance
from app.services.risk import RiskResult

type TaskMap = dict[str, TaskInstance]
type DependencyMap = dict[str, list[str]]


@dataclass(frozen=True)
class RootCauseResult:
    task_id: str
    chain: tuple[str, ...]


def find_root_cause(
    target: TaskInstance,
    tasks: TaskMap,
    dependencies: DependencyMap,
    projections: dict[str, RiskResult],
) -> RootCauseResult:
    ancestors = _ancestors(target.id, dependencies)
    frontier = [
        task_id
        for task_id in ancestors
        if tasks[task_id].state.value not in {"DONE", "SKIPPED"}
        and all(
            tasks[dependency].state.value in {"DONE", "SKIPPED"}
            for dependency in dependencies[task_id]
        )
    ]
    if not frontier:
        return RootCauseResult(target.id, (target.id,))
    root = max(
        frontier,
        key=lambda task_id: (
            projections[task_id].earliest_finish
            if task_id in projections
            else target.due_date,
            2 if tasks[task_id].state.value == "REJECTED" else 1,
        ),
    )
    return RootCauseResult(root, tuple(_chain(root, target.id, dependencies, projections)))


def _ancestors(task_id: str, dependencies: DependencyMap) -> set[str]:
    found = {task_id}
    pending = [task_id]
    while pending:
        current = pending.pop()
        for dependency in dependencies.get(current, []):
            if dependency not in found:
                found.add(dependency)
                pending.append(dependency)
    return found


def _chain(
    root: str,
    target: str,
    dependencies: DependencyMap,
    projections: dict[str, RiskResult],
) -> list[str]:
    if root == target:
        return [root]
    paths: list[list[str]] = []
    for dependency in dependencies.get(target, []):
        if root in _ancestors(dependency, dependencies):
            paths.append(_chain(root, dependency, dependencies, projections) + [target])
    if not paths:
        return [root, target]
    return max(
        paths,
        key=lambda path: (
            projections[path[-1]].earliest_finish
            if path[-1] in projections
            else date.min
        ),
    )
