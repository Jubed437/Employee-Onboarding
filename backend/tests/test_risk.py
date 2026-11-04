from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.clock import SimClock
from app.db.base import Base, TaskInstance, task_dependency
from app.db.base import SimClock as SimClockRow
from app.domain.enums import Role, SimulationMode, TaskState
from app.domain.schemas import PoliciesConfig
from app.services.risk import evaluate_tasks, upsert_risks


def test_risk_engine_detects_upstream_delay_and_critical_gate() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(
            SimClockRow(
                id=1,
                current_time=datetime(2026, 1, 5, 9, tzinfo=UTC),
                mode=SimulationMode.SIM,
            )
        )
        upstream = TaskInstance(
            employee_id="e1", template_key="A", title="A", owner_role=Role.PAYROLL,
            state=TaskState.IN_PROGRESS, due_date=date(2026, 1, 5), duration_days=3,
            started_at=datetime(2026, 1, 5, 9), attempts=1, rework_count=0,
            is_critical=False, is_mandatory=True, is_compliance=False, outcome_tags=[], meta={},
        )
        downstream = TaskInstance(
            employee_id="e1", template_key="B", title="B", owner_role=Role.PAYROLL,
            state=TaskState.NOT_STARTED, due_date=date(2026, 1, 6), duration_days=1,
            attempts=0, rework_count=0, is_critical=True, is_mandatory=True,
            is_compliance=True, outcome_tags=[], meta={},
        )
        session.add_all([upstream, downstream])
        session.commit()
        session.execute(
            task_dependency.insert().values(
                task_id=downstream.id,
                depends_on_task_id=upstream.id,
            )
        )
        session.commit()
        policies = PoliciesConfig(
            slack_buffer_days=1, rework_days=2, owner_overdue_penalty_days=0.5,
            owner_overdue_penalty_cap_days=2, max_recommendations_per_risk=3,
        )
        results = evaluate_tasks(session, "e1", SimClock(session), policies)
        risk = next(item for item in results if item.task_id == downstream.id)
        assert risk.level is not None
        assert risk.level.value == "HIGH"
        assert risk.slack_days < 0
        assert "UPSTREAM_DELAY" in [reason.value for reason in risk.reason_codes]
        stored = upsert_risks(session, "e1", results, SimClock(session))
        assert len(stored) == 2
