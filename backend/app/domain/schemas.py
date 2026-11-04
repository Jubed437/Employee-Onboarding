from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import ActionType, Role, TaskState, Tier

RelativeTo = Literal["join_date", "payroll_cutoff"]
PositiveDays = Annotated[float, Field(ge=0)]


class DeadlineConfig(BaseModel):
    relative_to: RelativeTo
    offset_days: int


class TaskFlags(BaseModel):
    critical: bool = False
    mandatory: bool = False
    compliance: bool = False


class TaskConfig(BaseModel):
    title: str = Field(min_length=1)
    owner_role: Role
    depends_on: list[str] = Field(default_factory=list)
    duration_days: PositiveDays
    deadline: DeadlineConfig
    external_sla_days: PositiveDays | None = None
    flags: TaskFlags = Field(default_factory=TaskFlags)
    outcome_tags: list[str] = Field(default_factory=list)


class TaskOverride(BaseModel):
    duration_days: PositiveDays | None = None


class VariantConfig(BaseModel):
    add_tasks: list[str] = Field(default_factory=list)
    remove_tasks: list[str] = Field(default_factory=list)
    override: dict[str, TaskOverride] = Field(default_factory=dict)


class ProfileDefaults(BaseModel):
    payroll_cutoff_day: int = Field(ge=1, le=31)
    business_calendar: str = Field(min_length=1)


class ProfileConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str = Field(pattern=r"^[a-z0-9_]+$")
    display_name: str = Field(min_length=1)
    defaults: ProfileDefaults
    variants: dict[str, VariantConfig] = Field(default_factory=dict)
    tasks: dict[str, TaskConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_references(self) -> "ProfileConfig":
        task_ids = set(self.tasks)
        for task_id, task in self.tasks.items():
            unknown_dependencies = set(task.depends_on) - task_ids
            if unknown_dependencies:
                raise ValueError(
                    f"{task_id} depends on unknown task IDs: {sorted(unknown_dependencies)}"
                )
        for variant_name, variant in self.variants.items():
            referenced = set(variant.add_tasks) | set(variant.remove_tasks) | set(variant.override)
            unknown_tasks = referenced - task_ids
            if unknown_tasks:
                raise ValueError(
                    f"variant {variant_name!r} references unknown task IDs: {sorted(unknown_tasks)}"
                )
        _ensure_acyclic(self.tasks)
        return self


class PlaybookConditions(BaseModel):
    owner_role: list[Role] = Field(default_factory=list)
    task_states: list[TaskState] = Field(default_factory=list)
    outcome_tags: list[str] = Field(default_factory=list)


class PlaybookEffect(BaseModel):
    reduce_remaining_days: PositiveDays | None = None
    extend_due_days: PositiveDays | None = None
    change_owner: Role | None = None
    halve_external_sla: bool = False
    shift_join_date_days: int | None = None
    target_task: str | None = None

    @model_validator(mode="after")
    def has_one_effect(self) -> "PlaybookEffect":
        if not any(
            (
                self.reduce_remaining_days is not None,
                self.extend_due_days is not None,
                self.change_owner is not None,
                self.halve_external_sla,
                self.shift_join_date_days is not None,
            )
        ):
            raise ValueError("a playbook effect must define at least one effect")
        return self


class PlaybookConfig(BaseModel):
    id: str = Field(pattern=r"^[A-Z0-9-]+$")
    action_type: ActionType
    tier: Tier
    applies_when: PlaybookConditions = Field(default_factory=PlaybookConditions)
    effect: PlaybookEffect


class PlaybooksConfig(BaseModel):
    playbooks: list[PlaybookConfig]


class ScoringConfig(BaseModel):
    weights: dict[str, float]
    bands: dict[str, int]

    @model_validator(mode="after")
    def validate_weights_and_bands(self) -> "ScoringConfig":
        required = {"critical", "slack", "compliance", "timeliness"}
        if set(self.weights) != required:
            raise ValueError(f"weights must contain exactly {sorted(required)}")
        if any(weight < 0 for weight in self.weights.values()):
            raise ValueError("weights cannot be negative")
        if abs(sum(self.weights.values()) - 1) > 1e-9:
            raise ValueError("weights must sum to 1")
        if not 0 <= self.bands["watch_min"] <= self.bands["ready_min"] <= 100:
            raise ValueError("score bands must be ordered between 0 and 100")
        return self


class PoliciesConfig(BaseModel):
    slack_buffer_days: PositiveDays
    rework_days: PositiveDays
    owner_overdue_penalty_days: PositiveDays
    owner_overdue_penalty_cap_days: PositiveDays
    max_recommendations_per_risk: int = Field(ge=1)


def _ensure_acyclic(tasks: dict[str, TaskConfig]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError(f"task dependency cycle detected at {task_id}")
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in tasks[task_id].depends_on:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in tasks:
        visit(task_id)
