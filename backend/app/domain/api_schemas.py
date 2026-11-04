from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import Role, TaskState


class Persona(BaseModel):
    id: str
    display_name: str
    role: Role
    team_id: str


class LoginRequest(BaseModel):
    user_id: str


class LoginResponse(BaseModel):
    token: str
    user: Persona


class HireCreate(BaseModel):
    full_name: str
    email: str
    job_title: str
    department: str
    join_date: date
    work_state: str
    is_experienced: bool
    is_remote: bool
    manager_id: str | None = None
    profile_key: str = "india_full_time"


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    template_key: str
    title: str
    state: TaskState
    due_date: date
    owner_role: Role
    assignee_user_id: str | None = None
    duration_days: float
    is_critical: bool
    is_mandatory: bool
    is_compliance: bool
    outcome_tags: list[str]
    meta: dict[str, object]


class PlanResponse(BaseModel):
    tasks: list[TaskResponse]
    edges: list[dict[str, str]]


class RiskResponse(BaseModel):
    id: str
    task_id: str
    level: str
    reason_codes: list[str]
    predicted_breach_date: date
    slack_days: float
    root_cause_task_id: str | None
    impact: dict[str, object]
    status: str


class RecommendationResponse(BaseModel):
    id: str
    risk_id: str
    playbook_id: str
    action_type: str
    tier: str
    simulated_outcome: dict[str, object]
    rank: int
    rationale: str
    status: str


class ApprovalRequest(BaseModel):
    comment: str | None = None


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ts: datetime
    employee_id: str
    task_id: str | None
    type: str
    actor: str
    payload: dict[str, object]


class AuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ts: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    before: dict[str, object]
    after: dict[str, object]
    reason: str | None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ts: datetime
    employee_id: str
    to_role_or_user: str
    subject: str
    body: str
    related_task_id: str | None
    status: str


class HireResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str
    join_date: date
    profile_key: str


class ReadinessResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    employee_id: str
    ts: datetime
    score: int
    band: str
    breakdown: dict[str, float]
    drivers: list[str]


class TransitionRequest(BaseModel):
    to: TaskState
    reason: str | None = None
