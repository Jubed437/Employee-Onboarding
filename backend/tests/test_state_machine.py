from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.clock import SimClock
from app.db.base import Base, EventLog, TaskInstance, task_dependency
from app.db.base import SimClock as SimClockRow
from app.domain.enums import Role, SimulationMode, TaskState
from app.services.state_machine import InvalidTransition, transition_task


def _setup() -> tuple[Session, SimClock, TaskInstance, TaskInstance]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    session.add(
        SimClockRow(
            id=1,
            current_time=datetime(2026, 1, 5, 9, tzinfo=UTC),
            mode=SimulationMode.SIM,
        )
    )
    first = TaskInstance(
        employee_id="employee-1",
        template_key="A",
        title="First",
        owner_role=Role.NEW_HIRE,
        state=TaskState.READY,
        due_date=date(2026, 1, 10),
        duration_days=1,
        attempts=0,
        rework_count=0,
        is_critical=False,
        is_mandatory=True,
        is_compliance=False,
        outcome_tags=[],
        meta={},
    )
    second = TaskInstance(
        employee_id="employee-1",
        template_key="B",
        title="Second",
        owner_role=Role.PAYROLL,
        state=TaskState.NOT_STARTED,
        due_date=date(2026, 1, 10),
        duration_days=1,
        attempts=0,
        rework_count=0,
        is_critical=False,
        is_mandatory=True,
        is_compliance=False,
        outcome_tags=[],
        meta={},
    )
    session.add_all([first, second])
    session.flush()
    session.execute(
        task_dependency.insert().values(task_id=second.id, depends_on_task_id=first.id)
    )
    session.commit()
    return session, SimClock(session), first, second


def test_allowed_transition_writes_audit_event_and_unlocks_dependent() -> None:
    session, clock, first, second = _setup()
    evaluated: list[str] = []

    transition_task(
        session,
        first,
        TaskState.IN_PROGRESS,
        actor_id="new-hire-1",
        actor_role=Role.NEW_HIRE,
        clock=clock,
        on_evaluated=evaluated.append,
    )
    transition_task(
        session,
        first,
        TaskState.DONE,
        actor_id="new-hire-1",
        actor_role=Role.NEW_HIRE,
        clock=clock,
        on_evaluated=evaluated.append,
    )

    assert first.completed_at == datetime(2026, 1, 5, 9)
    assert second.state is TaskState.READY
    assert len(session.scalars(select(EventLog)).all()) == 3
    assert evaluated == ["employee-1", "employee-1"]


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (TaskState.NOT_STARTED, TaskState.DONE),
        (TaskState.READY, TaskState.DONE),
        (TaskState.DONE, TaskState.READY),
        (TaskState.REJECTED, TaskState.DONE),
    ],
)
def test_invalid_transitions_are_rejected(source: TaskState, target: TaskState) -> None:
    session, clock, first, _ = _setup()
    first.state = source

    with pytest.raises(InvalidTransition):
        transition_task(
            session,
            first,
            target,
            actor_id="new-hire-1",
            actor_role=Role.NEW_HIRE,
            clock=clock,
        )


def test_rejection_requires_reason_and_records_rework() -> None:
    session, clock, first, _ = _setup()
    first.state = TaskState.IN_PROGRESS

    with pytest.raises(InvalidTransition, match="reason"):
        transition_task(
            session,
            first,
            TaskState.REJECTED,
            actor_id="hr-1",
            actor_role=Role.HR,
            clock=clock,
        )

    transition_task(
        session,
        first,
        TaskState.REJECTED,
        actor_id="hr-1",
        actor_role=Role.HR,
        clock=clock,
        reason="Bank proof is unreadable",
    )
    assert first.rework_count == 1
    assert first.meta["reason"] == "Bank proof is unreadable"
