from calendar import monthrange
from datetime import date
from pathlib import Path
from typing import Final

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.core.clock import Clock, add_business_days, is_business_day, load_holidays
from app.core.config import load_profile
from app.db.base import (
    AuditLog,
    Employee,
    EventLog,
    TaskInstance,
    new_id,
    task_dependency,
)
from app.domain.enums import TaskState
from app.domain.schemas import ProfileConfig, TaskConfig

DEFAULT_CONFIG_ROOT: Final = Path(__file__).parents[3] / "config"


class PlanGenerationError(ValueError):
    """Raised when an employee plan cannot be generated."""


def calculate_payroll_cutoff(
    join_date: date,
    cutoff_day: int,
    holidays: set[date] | frozenset[date],
) -> date:
    year, month = join_date.year, join_date.month
    if join_date.day > cutoff_day:
        month += 1
        if month == 13:
            year, month = year + 1, 1
    cutoff = date(year, month, min(cutoff_day, monthrange(year, month)[1]))
    while not is_business_day(cutoff, holidays):
        cutoff = add_business_days(cutoff, -1, holidays)
    return cutoff


def generate_plan(
    session: Session,
    employee: Employee,
    clock: Clock,
    *,
    config_root: Path = DEFAULT_CONFIG_ROOT,
    holidays: set[date] | frozenset[date] | None = None,
) -> list[TaskInstance]:
    existing = session.scalars(
        select(TaskInstance).where(TaskInstance.employee_id == employee.id)
    ).all()
    if existing:
        return list(existing)

    profile = load_profile(config_root / "profiles" / f"{employee.profile_key}.yaml")
    holiday_set = holidays if holidays is not None else load_holidays(
        config_root / f"{profile.defaults.business_calendar}.yaml"
    )
    payroll_cutoff = calculate_payroll_cutoff(
        employee.join_date, profile.defaults.payroll_cutoff_day, holiday_set
    )
    employee.payroll_cutoff_date = payroll_cutoff

    selected_tasks, removed_tasks = _apply_variants(profile, employee)
    _validate_selected_dependencies(selected_tasks)
    task_rows = _build_tasks(
        employee, selected_tasks, removed_tasks, payroll_cutoff, holiday_set
    )
    session.add_all(task_rows)
    session.flush()

    task_ids = {task.template_key: task.id for task in task_rows}
    for template_key, task_config in selected_tasks.items():
        for dependency in task_config.depends_on:
            session.execute(
                insert(task_dependency).values(
                    task_id=task_ids[template_key],
                    depends_on_task_id=task_ids[dependency],
                )
            )

    now = clock.now()
    session.add(
        EventLog(
            id=new_id(),
            ts=now,
            employee_id=employee.id,
            type="PLAN_GENERATED",
            actor="SYSTEM",
            payload={"profile_key": employee.profile_key, "task_count": len(task_rows)},
        )
    )
    session.add(
        AuditLog(
            id=new_id(),
            ts=now,
            actor="SYSTEM",
            action="PLAN_GENERATED",
            entity_type="employee",
            entity_id=employee.id,
            before={},
            after={"task_count": len(task_rows), "profile_key": employee.profile_key},
            reason="Initial onboarding plan generation",
        )
    )
    session.commit()
    return task_rows


def _apply_variants(
    profile: ProfileConfig, employee: Employee
) -> tuple[dict[str, TaskConfig], set[str]]:
    selected = dict(profile.tasks)
    removed: set[str] = set()
    variant_names = [
        "experienced" if employee.is_experienced else "fresher",
        "remote" if employee.is_remote else "office",
    ]
    for variant_name in variant_names:
        variant = profile.variants.get(variant_name)
        if variant is None:
            continue
        for task_id in variant.remove_tasks:
            if task_id in selected:
                removed.add(task_id)
        for task_id, override in variant.override.items():
            if task_id in selected and override.duration_days is not None:
                selected[task_id] = selected[task_id].model_copy(
                    update={"duration_days": override.duration_days}
                )
    return selected, removed


def _validate_selected_dependencies(tasks: dict[str, TaskConfig]) -> None:
    for task_id, task in tasks.items():
        missing = set(task.depends_on) - set(tasks)
        if missing:
            raise PlanGenerationError(
                f"{task_id} depends on removed or unknown tasks: {sorted(missing)}"
            )


def _build_tasks(
    employee: Employee,
    configs: dict[str, TaskConfig],
    removed_tasks: set[str],
    payroll_cutoff: date,
    holidays: set[date] | frozenset[date],
) -> list[TaskInstance]:
    ready_keys = {
        key
        for key, config in configs.items()
        if key not in removed_tasks
        and all(dependency in removed_tasks for dependency in config.depends_on)
    }
    rows: list[TaskInstance] = []
    for template_key, config in configs.items():
        anchor = (
            employee.join_date
            if config.deadline.relative_to == "join_date"
            else payroll_cutoff
        )
        due_date = add_business_days(anchor, config.deadline.offset_days, holidays)
        rows.append(
            TaskInstance(
                id=new_id(),
                employee_id=employee.id,
                template_key=template_key,
                title=config.title,
                owner_role=config.owner_role,
                state=(
                    TaskState.SKIPPED
                    if template_key in removed_tasks
                    else TaskState.READY
                    if template_key in ready_keys
                    else TaskState.NOT_STARTED
                ),
                due_date=due_date,
                duration_days=config.duration_days,
                attempts=0,
                rework_count=0,
                is_critical=config.flags.critical,
                is_mandatory=config.flags.mandatory,
                is_compliance=config.flags.compliance,
                external_sla_days=config.external_sla_days,
                outcome_tags=config.outcome_tags,
                meta={},
            )
        )
    return rows
