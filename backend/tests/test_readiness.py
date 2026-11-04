from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.clock import SimClock
from app.db.base import Base, Employee, ReadinessSnapshot, TaskInstance
from app.db.base import SimClock as SimClockRow
from app.domain.enums import EmployeeStatus, Role, SimulationMode, TaskState
from app.domain.schemas import ScoringConfig
from app.services.readiness import calculate_readiness, save_snapshot
from app.services.risk import RiskResult


def test_readiness_calculates_formula_breakdown_band_and_snapshot() -> None:
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
        employee = Employee(
            id="employee-1",
            full_name="Synthetic Hire",
            email="hire@example.test",
            profile_key="india_full_time",
            is_experienced=False,
            is_remote=False,
            work_state="KA",
            job_title="Engineer",
            department="IT",
            join_date=date(2026, 1, 10),
            payroll_cutoff_date=date(2026, 1, 10),
            status=EmployeeStatus.ACTIVE,
            created_at=datetime(2026, 1, 5, 9, tzinfo=UTC),
        )
        done = _task("PAY-01", TaskState.DONE, mandatory=True, compliance=True)
        critical = _task("IT-01", TaskState.IN_PROGRESS, critical=True, compliance=True)
        late = _task("BGV-01", TaskState.REJECTED, mandatory=True)
        session.add_all([employee, done, critical, late])
        session.commit()
        scoring = ScoringConfig(
            weights={"critical": 0.4, "slack": 0.25, "compliance": 0.2, "timeliness": 0.15},
            bands={"ready_min": 85, "watch_min": 60},
        )
        results = [
            RiskResult(done.id, date(2026, 1, 5), 2, None, ()),
            RiskResult(critical.id, date(2026, 1, 8), 0, None, ()),
            RiskResult(late.id, date(2026, 1, 12), -2, None, ()),
        ]
        clock = SimClock(session)
        result = calculate_readiness(
            session,
            employee.id,
            clock,
            scoring,
            results,
            slack_buffer_days=1,
        )
        assert result.score == 45
        assert result.band == "AT_RISK"
        assert result.breakdown == {
            "critical": 0.5,
            "slack": 0.0,
            "compliance": 0.5,
            "timeliness": 1.0,
        }
        assert any("BGV-01 rejected" in driver for driver in result.drivers)
        snapshot = save_snapshot(session, employee.id, clock, result)
        assert snapshot.score == 45
        assert session.query(ReadinessSnapshot).count() == 1


def _task(
    key: str,
    state: TaskState,
    *,
    mandatory: bool = False,
    critical: bool = False,
    compliance: bool = False,
) -> TaskInstance:
    return TaskInstance(
        employee_id="employee-1",
        template_key=key,
        title=key,
        owner_role=Role.HR,
        state=state,
        due_date=date(2026, 1, 10),
        duration_days=1,
        attempts=0,
        rework_count=0,
        is_critical=critical,
        is_mandatory=mandatory,
        is_compliance=compliance,
        outcome_tags=[],
        meta={},
    )
