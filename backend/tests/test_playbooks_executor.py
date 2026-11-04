from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.clock import SimClock
from app.db.base import (
    Base,
    Employee,
    Recommendation,
    Risk,
    TaskInstance,
    User,
)
from app.db.base import (
    SimClock as SimClockRow,
)
from app.domain.enums import (
    ActionType,
    ApprovalDecision,
    EmployeeStatus,
    RecommendationStatus,
    RiskLevel,
    RiskStatus,
    Role,
    SimulationMode,
    TaskState,
    Tier,
)
from app.domain.schemas import (
    PlaybookConditions,
    PlaybookConfig,
    PlaybookEffect,
    PlaybooksConfig,
    PoliciesConfig,
)
from app.services.executor import execute_recommendation, record_approval
from app.services.impact import ImpactResult
from app.services.recommender import recommend_for_risk


def _task(owner: Role = Role.NEW_HIRE) -> TaskInstance:
    return TaskInstance(
        employee_id="employee-1",
        template_key="DOC-01",
        title="Identity documents",
        owner_role=owner,
        state=TaskState.REJECTED,
        due_date=date(2026, 1, 10),
        duration_days=2,
        attempts=1,
        rework_count=1,
        is_critical=False,
        is_mandatory=True,
        is_compliance=False,
        outcome_tags=[],
        meta={},
    )


def _clock(session: Session) -> SimClock:
    session.add(
        SimClockRow(
            id=1,
            current_time=datetime(2026, 1, 5, 9, tzinfo=UTC),
            mode=SimulationMode.SIM,
        )
    )
    session.commit()
    return SimClock(session)


def test_recommender_is_idempotent_and_auto_executor_changes_task() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        clock = _clock(session)
        task = _task()
        session.add(task)
        session.commit()
        risk = Risk(
            employee_id=task.employee_id,
            task_id=task.id,
            level=RiskLevel.HIGH,
            reason_codes=[],
            predicted_breach_date=date(2026, 1, 8),
            slack_days=-1,
            status=RiskStatus.OPEN,
            first_seen_at=clock.now(),
        )
        session.add(risk)
        session.commit()
        playbooks = PlaybooksConfig(
            playbooks=[
                PlaybookConfig(
                    id="PB-REMIND",
                    action_type=ActionType.SEND_REMINDER,
                    tier=Tier.AUTO,
                    applies_when=PlaybookConditions(
                        owner_role=[Role.NEW_HIRE],
                        task_states=[TaskState.REJECTED],
                    ),
                    effect=PlaybookEffect(reduce_remaining_days=1),
                )
            ]
        )
        policies = PoliciesConfig(
            slack_buffer_days=1,
            rework_days=2,
            owner_overdue_penalty_days=0.5,
            owner_overdue_penalty_cap_days=2,
            max_recommendations_per_risk=3,
        )
        impact = ImpactResult((), (), False)
        recommendations = recommend_for_risk(
            session,
            risk,
            task,
            impact,
            playbooks=playbooks,
            policies=policies,
            clock=clock,
        )
        duplicate = recommend_for_risk(
            session,
            risk,
            task,
            impact,
            playbooks=playbooks,
            policies=policies,
            clock=clock,
        )
        assert len(recommendations) == 1
        assert duplicate[0].id == recommendations[0].id
        execute_recommendation(
            session,
            recommendations[0],
            actor_id="SYSTEM",
            actor_role=Role.ADMIN,
            clock=clock,
        )
        assert recommendations[0].status is RecommendationStatus.EXECUTED
        assert task.duration_days == 1


def test_manager_approval_is_required_before_execution() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        clock = _clock(session)
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
            created_at=clock.now(),
        )
        manager = User(
            id="manager-1",
            display_name="Synthetic Manager",
            role=Role.MANAGER,
            team_id="team-1",
        )
        task = _task(Role.HR)
        session.add_all([employee, manager, task])
        session.commit()
        risk = Risk(
            employee_id=employee.id,
            task_id=task.id,
            level=RiskLevel.HIGH,
            reason_codes=[],
            predicted_breach_date=date(2026, 1, 8),
            slack_days=-1,
            status=RiskStatus.OPEN,
            first_seen_at=clock.now(),
        )
        session.add(risk)
        session.commit()
        recommendation = Recommendation(
            risk_id=risk.id,
            playbook_id="PB-EXPEDITE",
            action_type="EXPEDITE_EXTERNAL",
            tier=Tier.MANAGER_APPROVAL,
            params={},
            simulated_outcome={},
            rank=1,
            rationale="test",
            status=RecommendationStatus.PROPOSED,
            idempotency_key="approval-test",
            created_at=clock.now(),
        )
        session.add(recommendation)
        session.commit()
        record_approval(
            session,
            recommendation,
            approver=manager,
            decision=ApprovalDecision.APPROVED,
            clock=clock,
        )
        execute_recommendation(
            session,
            recommendation,
            actor_id=manager.id,
            actor_role=Role.MANAGER,
            clock=clock,
        )
        assert recommendation.status is RecommendationStatus.EXECUTED
