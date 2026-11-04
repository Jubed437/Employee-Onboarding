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
