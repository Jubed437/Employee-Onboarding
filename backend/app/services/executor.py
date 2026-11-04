from collections.abc import Iterable
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import Clock, add_business_days
from app.db.base import (
    Approval,
    AuditLog,
    Employee,
    EventLog,
    Recommendation,
    Risk,
    TaskInstance,
    User,
    new_id,
)
from app.domain.enums import ApprovalDecision, RecommendationStatus, Role, Tier


class ApprovalError(ValueError):
    """Raised when a recommendation lacks a required valid approval."""


class ExecutionError(ValueError):
    """Raised when a recommendation cannot be executed."""


def record_approval(
    session: Session,
    recommendation: Recommendation,
    *,
    approver: object,
    decision: ApprovalDecision,
    clock: Clock,
    comment: str | None = None,
) -> Approval:
    role = getattr(approver, "role", None)
    if not _can_approve(recommendation.tier, role):
        raise ApprovalError("user is not authorized to approve this recommendation")
    approval = Approval(
        id=new_id(),
        recommendation_id=recommendation.id,
        approver_user_id=getattr(approver, "id"),
        decision=decision,
        comment=comment,
        ts=clock.now(),
    )
    session.add(approval)
    if decision is ApprovalDecision.REJECTED:
        recommendation.status = RecommendationStatus.REJECTED
    elif recommendation.status is RecommendationStatus.PROPOSED:
        recommendation.status = RecommendationStatus.APPROVED
    session.commit()
    return approval


def execute_recommendation(
    session: Session,
    recommendation: Recommendation,
    *,
    actor_id: str,
    actor_role: Role,
    clock: Clock,
    holidays: Iterable[date] = (),
) -> Recommendation:
    if recommendation.status is RecommendationStatus.EXECUTED:
        return recommendation
    if (
        recommendation.status is not RecommendationStatus.APPROVED
        and recommendation.tier is not Tier.AUTO
    ):
        raise ApprovalError("recommendation requires approval before execution")
    if recommendation.tier is not Tier.AUTO:
        _require_approvals(session, recommendation)
    before = _snapshot(recommendation)
    try:
        risk = session.get(Risk, recommendation.risk_id)
        if risk is None:
            raise ExecutionError("risk not found")
        root = session.get(TaskInstance, risk.root_cause_task_id or risk.task_id)
        if root is None:
            raise ExecutionError("root cause task not found")
        _apply_effect(session, recommendation, root, clock)
        recommendation.status = RecommendationStatus.EXECUTED
        session.add(EventLog(
            id=new_id(), ts=clock.now(), employee_id=risk.employee_id,
            task_id=root.id, type="RECOMMENDATION_EXECUTED", actor=actor_id,
            payload={
                "recommendation_id": recommendation.id,
                "playbook_id": recommendation.playbook_id,
            },
        ))
        session.add(AuditLog(
            id=new_id(), ts=clock.now(), actor=actor_id, action="RECOMMENDATION_EXECUTED",
            entity_type="recommendation", entity_id=recommendation.id,
            before=before, after=_snapshot(recommendation), reason=recommendation.rationale,
        ))
        session.commit()
        return recommendation
    except Exception:
        recommendation.status = RecommendationStatus.FAILED
        session.commit()
        raise


def _apply_effect(
    session: Session,
    recommendation: Recommendation,
    root: TaskInstance,
    clock: Clock,
) -> None:
    params = recommendation.params
    if "reduce_remaining_days" in params:
        root.duration_days = max(0.5, root.duration_days - float(params["reduce_remaining_days"]))
    if "change_owner" in params:
        root.owner_role = Role(str(params["change_owner"]))
        root.assignee_user_id = None
    if params.get("halve_external_sla"):
        root.external_sla_days = (root.external_sla_days or 0) / 2
    if "extend_due_days" in params:
        target = root
        if params.get("target_task"):
            target = session.scalar(select(TaskInstance).where(
                TaskInstance.employee_id == root.employee_id,
                TaskInstance.template_key == params["target_task"],
            )) or root
        target.due_date = add_business_days(target.due_date, int(params["extend_due_days"]))
    if "shift_join_date_days" in params:
        employee = session.get(Employee, root.employee_id)
        if employee is not None:
            employee.join_date = add_business_days(
                employee.join_date, int(params["shift_join_date_days"])
            )


def _require_approvals(session: Session, recommendation: Recommendation) -> None:
    approvals = session.scalars(select(Approval).where(
        Approval.recommendation_id == recommendation.id,
        Approval.decision == ApprovalDecision.APPROVED,
    )).all()
    roles = {
        getattr(session.get(User, approval.approver_user_id), "role", None)
        for approval in approvals
    }
    if recommendation.tier is Tier.MANAGER_APPROVAL and not (
        Role.MANAGER in roles or Role.ADMIN in roles
    ):
        raise ApprovalError("manager approval is required")
    if recommendation.tier is Tier.MANAGER_AND_HR_APPROVAL and not (
        (Role.MANAGER in roles or Role.ADMIN in roles) and Role.HR in roles
    ):
        raise ApprovalError("manager and HR approvals are required")


def _can_approve(tier: Tier, role: Role | None) -> bool:
    return role is Role.ADMIN or (
        tier is Tier.MANAGER_APPROVAL and role is Role.MANAGER
    ) or (
        tier is Tier.MANAGER_AND_HR_APPROVAL and role in {Role.MANAGER, Role.HR}
    )


def _snapshot(recommendation: Recommendation) -> dict[str, object]:
    return {
        "status": recommendation.status.value,
        "params": dict(recommendation.params),
    }
