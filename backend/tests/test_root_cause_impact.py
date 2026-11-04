from datetime import date

from app.db.base import TaskInstance
from app.domain.enums import Role, TaskState
from app.services.impact import calculate_impact
from app.services.risk import RiskResult
from app.services.root_cause import find_root_cause


def _task(
    key: str,
    *,
    state: TaskState = TaskState.NOT_STARTED,
    critical: bool = False,
    tags: list[str] | None = None,
) -> TaskInstance:
    return TaskInstance(
        id=key,
        employee_id="employee-1",
        template_key=key,
        title=key,
        owner_role=Role.PAYROLL,
        state=state,
        due_date=date(2026, 1, 10),
        duration_days=1,
        attempts=0,
        rework_count=0,
        is_critical=critical,
        is_mandatory=True,
        is_compliance=False,
        outcome_tags=tags or [],
        meta={},
    )


def _projection(task_id: str, finish_day: int, slack: float = -1) -> RiskResult:
    return RiskResult(task_id, date(2026, 1, finish_day), slack, None, ())


def test_root_cause_prefers_rejected_frontier_on_tie_and_returns_chain() -> None:
    tasks = {
        "A": _task("A", state=TaskState.REJECTED),
        "B": _task("B", state=TaskState.BLOCKED),
        "C": _task("C", critical=True),
    }
    dependencies = {"A": [], "B": [], "C": ["A", "B"]}
    projections = {"A": _projection("A", 8), "B": _projection("B", 8), "C": _projection("C", 12)}

    result = find_root_cause(tasks["C"], tasks, dependencies, projections)

    assert result.task_id == "A"
    assert result.chain == ("A", "C")


def test_impact_traverses_descendants_and_collects_tags() -> None:
    tasks = {
        "A": _task("A", tags=["PAYROLL_SETUP_DELAYED"]),
        "B": _task("B", critical=True, tags=["FIRST_SALARY_AT_RISK"]),
        "C": _task("C"),
    }
    dependencies = {"A": [], "B": ["A"], "C": ["B"]}
    projections = {
        "A": _projection("A", 8),
        "B": _projection("B", 12),
        "C": _projection("C", 11, 1),
    }

    result = calculate_impact("A", tasks, dependencies, projections)

    assert [item.task_id for item in result.items] == ["A", "B", "C"]
    assert result.outcome_tags == ("FIRST_SALARY_AT_RISK", "PAYROLL_SETUP_DELAYED")
    assert result.has_critical_task is True
    assert result.items[1].breaches is True
