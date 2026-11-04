from datetime import UTC, date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.clock import SimClock
from app.db.base import Base, Employee, EventLog, task_dependency
from app.db.base import SimClock as SimClockRow
from app.domain.enums import EmployeeStatus, SimulationMode, TaskState
from app.services.plan_generator import calculate_payroll_cutoff, generate_plan


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _employee(*, experienced: bool, remote: bool, join_date: date) -> Employee:
    return Employee(
        full_name="Synthetic Employee",
        email=f"{experienced}-{remote}@example.test",
        profile_key="india_full_time",
        is_experienced=experienced,
        is_remote=remote,
        work_state="Karnataka",
        job_title="Engineer",
        department="Engineering",
        join_date=join_date,
        payroll_cutoff_date=join_date,
        status=EmployeeStatus.ACTIVE,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_payroll_cutoff_rolls_to_next_month() -> None:
    assert calculate_payroll_cutoff(date(2026, 1, 25), 20, set()) == date(2026, 2, 20)
    assert calculate_payroll_cutoff(date(2026, 1, 10), 20, set()) == date(2026, 1, 20)


def test_fresher_office_plan_marks_experienced_tasks_skipped() -> None:
    with _session() as session:
        employee = _employee(experienced=False, remote=False, join_date=date(2026, 1, 12))
        session.add(employee)
        session.commit()
        session.add(
            SimClockRow(
                id=1,
                current_time=datetime(2026, 1, 1, tzinfo=UTC),
                mode=SimulationMode.SIM,
            )
        )
        session.commit()
        clock = SimClock(session)

        tasks = generate_plan(session, employee, clock)
        by_key = {task.template_key: task for task in tasks}

        assert by_key["HR-06"].state is TaskState.SKIPPED
        assert by_key["PAY-05"].state is TaskState.SKIPPED
        assert by_key["HR-01"].state is TaskState.READY
        assert session.scalars(select(EventLog)).one().type == "PLAN_GENERATED"
        assert len(generate_plan(session, employee, clock)) == len(tasks)


def test_remote_plan_marks_building_access_skipped_and_overrides_laptop() -> None:
    with _session() as session:
        employee = _employee(experienced=True, remote=True, join_date=date(2026, 1, 12))
        session.add(employee)
        session.commit()
        session.add(
            SimClockRow(
                id=1,
                current_time=datetime(2026, 1, 1, tzinfo=UTC),
                mode=SimulationMode.SIM,
            )
        )
        session.commit()

        tasks = generate_plan(session, employee, SimClock(session))
        by_key = {task.template_key: task for task in tasks}

        assert by_key["IT-04"].state is TaskState.SKIPPED
        assert by_key["IT-01"].duration_days == 7
        assert session.execute(select(task_dependency)).all()
