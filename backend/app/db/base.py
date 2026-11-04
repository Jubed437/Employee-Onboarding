from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import (
    ActionType,
    ApprovalDecision,
    EmployeeStatus,
    NotificationChannel,
    RecommendationStatus,
    RiskLevel,
    RiskStatus,
    Role,
    SimulationMode,
    TaskState,
    Tier,
)


def new_id() -> str:
    return str(uuid4())


def enum_type(enum_class: type[Any]) -> SqlEnum:
    return SqlEnum(
        enum_class,
        native_enum=False,
        values_callable=lambda enum: [member.value for member in enum],
    )


class Base(DeclarativeBase):
    type_annotation_map = {
        dict[str, Any]: JSON,
        list[str]: JSON,
    }


class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    profile_key: Mapped[str] = mapped_column(String(100))
    is_experienced: Mapped[bool]
    is_remote: Mapped[bool]
    work_state: Mapped[str] = mapped_column(String(100))
    job_title: Mapped[str] = mapped_column(String(200))
    department: Mapped[str] = mapped_column(String(100))
    join_date: Mapped[date] = mapped_column(Date)
    payroll_cutoff_date: Mapped[date] = mapped_column(Date)
    manager_id: Mapped[str | None] = mapped_column(
        ForeignKey("user.id", use_alter=True, name="fk_employee_manager"),
        nullable=True,
    )
    status: Mapped[EmployeeStatus] = mapped_column(enum_type(EmployeeStatus))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    tasks: Mapped[list["TaskInstance"]] = relationship(back_populates="employee")


class User(Base):
    __tablename__ = "user"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(enum_type(Role))
    team_id: Mapped[str] = mapped_column(String(100))
    employee_id: Mapped[str | None] = mapped_column(
        ForeignKey("employee.id"), nullable=True, unique=True
    )


class TaskInstance(Base):
    __tablename__ = "task_instance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employee.id"), index=True)
    template_key: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(300))
    owner_role: Mapped[Role] = mapped_column(enum_type(Role))
    assignee_user_id: Mapped[str | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    state: Mapped[TaskState] = mapped_column(enum_type(TaskState))
    due_date: Mapped[date] = mapped_column(Date)
    duration_days: Mapped[float] = mapped_column(Float)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    rework_count: Mapped[int] = mapped_column(Integer, default=0)
    is_critical: Mapped[bool] = mapped_column(default=False)
    is_mandatory: Mapped[bool] = mapped_column(default=False)
    is_compliance: Mapped[bool] = mapped_column(default=False)
    external_sla_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    outcome_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    meta: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    employee: Mapped[Employee] = relationship(back_populates="tasks")


task_dependency = Table(
    "task_dependency",
    Base.metadata,
    Column("task_id", String(36), ForeignKey("task_instance.id"), primary_key=True),
    Column(
        "depends_on_task_id",
        String(36),
        ForeignKey("task_instance.id"),
        primary_key=True,
    ),
)


class EventLog(Base):
    __tablename__ = "event_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    employee_id: Mapped[str] = mapped_column(ForeignKey("employee.id"), index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("task_instance.id"), nullable=True)
    type: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Risk(Base):
    __tablename__ = "risk"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employee.id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("task_instance.id"))
    level: Mapped[RiskLevel] = mapped_column(enum_type(RiskLevel))
    reason_codes: Mapped[list[str]] = mapped_column(JSON, default=list)
    predicted_breach_date: Mapped[date] = mapped_column(Date)
    slack_days: Mapped[float] = mapped_column(Float)
    root_cause_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("task_instance.id"), nullable=True
    )
    impact: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[RiskStatus] = mapped_column(enum_type(RiskStatus))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Recommendation(Base):
    __tablename__ = "recommendation"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    risk_id: Mapped[str] = mapped_column(ForeignKey("risk.id"), index=True)
    playbook_id: Mapped[str] = mapped_column(String(100))
    action_type: Mapped[ActionType] = mapped_column(enum_type(ActionType))
    tier: Mapped[Tier] = mapped_column(enum_type(Tier))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    simulated_outcome: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    rank: Mapped[int] = mapped_column(Integer)
    rationale: Mapped[str] = mapped_column(Text)
    status: Mapped[RecommendationStatus] = mapped_column(enum_type(RecommendationStatus))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Approval(Base):
    __tablename__ = "approval"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    recommendation_id: Mapped[str] = mapped_column(ForeignKey("recommendation.id"), index=True)
    approver_user_id: Mapped[str] = mapped_column(ForeignKey("user.id"))
    decision: Mapped[ApprovalDecision] = mapped_column(enum_type(ApprovalDecision))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReadinessSnapshot(Base):
    __tablename__ = "readiness_snapshot"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employee.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    score: Mapped[int] = mapped_column(Integer)
    band: Mapped[str] = mapped_column(String(50))
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    drivers: Mapped[list[str]] = mapped_column(JSON, default=list)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(100))
    entity_id: Mapped[str] = mapped_column(String(36))
    before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    employee_id: Mapped[str] = mapped_column(ForeignKey("employee.id"), index=True)
    to_role_or_user: Mapped[str] = mapped_column(String(100))
    channel: Mapped[NotificationChannel] = mapped_column(enum_type(NotificationChannel))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    related_task_id: Mapped[str | None] = mapped_column(
        ForeignKey("task_instance.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50))


class SimClock(Base):
    __tablename__ = "sim_clock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    current_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    mode: Mapped[SimulationMode] = mapped_column(enum_type(SimulationMode))


class Document(Base):
    __tablename__ = "document"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employee.id"), index=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("task_instance.id"))
    kind: Mapped[str] = mapped_column(String(100))
    filename: Mapped[str] = mapped_column(String(300))
    masked_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    extracted_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    verification_status: Mapped[str] = mapped_column(String(50))
