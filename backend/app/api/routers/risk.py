from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_db
from app.core.clock import RealClock
from app.core.security import CurrentUser
from app.db.base import Recommendation, Risk, User
from app.domain.api_schemas import (
    ApprovalRequest,
    RecommendationResponse,
    RiskResponse,
)
from app.domain.enums import ApprovalDecision, RecommendationStatus
from app.services.executor import ApprovalError, record_approval

router = APIRouter(tags=["risks", "approvals"])


@router.get("/hires/{hire_id}/risks", response_model=list[RiskResponse])
def risks(
    hire_id: str,
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(current_user),
) -> list[Risk]:
    return list(
        session.scalars(
            select(Risk)
            .where(Risk.employee_id == hire_id, Risk.status == "OPEN")
            .order_by(Risk.level.desc(), Risk.slack_days)
        )
    )


@router.get("/recommendations", response_model=list[RecommendationResponse])
def recommendations(
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(current_user),
) -> list[Recommendation]:
    return list(
        session.scalars(
            select(Recommendation).where(
                Recommendation.status == RecommendationStatus.PROPOSED
            )
        )
    )


def _decide(
    recommendation_id: str,
    decision: ApprovalDecision,
    request: ApprovalRequest,
    session: Session,
    user: CurrentUser,
) -> Recommendation:
    recommendation = session.get(Recommendation, recommendation_id)
    if recommendation is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    approver = session.get(User, user.id)
    if approver is None:
        approver = User(
            id=user.id,
            display_name=user.id,
            role=user.role,
            team_id=user.team_id,
        )
        session.add(approver)
        session.flush()
    try:
        record_approval(
            session,
            recommendation,
            approver=approver,
            decision=decision,
            clock=RealClock(),
            comment=request.comment,
        )
    except ApprovalError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    return recommendation


@router.post(
    "/recommendations/{recommendation_id}/approve",
    response_model=RecommendationResponse,
)
def approve(
    recommendation_id: str,
    request: ApprovalRequest,
    session: Session = Depends(get_db),
    user: CurrentUser = Depends(current_user),
) -> Recommendation:
    return _decide(
        recommendation_id, ApprovalDecision.APPROVED, request, session, user
    )


@router.post(
    "/recommendations/{recommendation_id}/reject",
    response_model=RecommendationResponse,
)
def reject(
    recommendation_id: str,
    request: ApprovalRequest,
    session: Session = Depends(get_db),
    user: CurrentUser = Depends(current_user),
) -> Recommendation:
    return _decide(
        recommendation_id, ApprovalDecision.REJECTED, request, session, user
    )
