from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.config import load_playbooks, load_policies, load_scoring
from app.core.security import CurrentUser
from app.db.base import AuditLog, EventLog, Notification
from app.domain.api_schemas import AuditResponse, EventResponse, NotificationResponse
from app.domain.enums import Role

CONFIG_ROOT = Path(__file__).parents[4] / "config"
router = APIRouter(tags=["admin"])


@router.get("/config")
def config(
    _: CurrentUser = Depends(require_roles(Role.ADMIN)),
) -> dict[str, object]:
    return {
        "playbooks": load_playbooks(CONFIG_ROOT / "playbooks.yaml").model_dump(),
        "policies": load_policies(CONFIG_ROOT / "policies.yaml").model_dump(),
        "scoring": load_scoring(CONFIG_ROOT / "scoring.yaml").model_dump(),
    }


@router.get("/audit", response_model=list[AuditResponse])
def audit(
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(Role.ADMIN)),
) -> list[AuditLog]:
    return list(session.scalars(select(AuditLog).order_by(AuditLog.ts.desc()).limit(100)))


@router.get("/hires/{hire_id}/events", response_model=list[EventResponse])
def events(
    hire_id: str,
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(Role.ADMIN, Role.HR, Role.MANAGER)),
) -> list[EventLog]:
    return list(
        session.scalars(
            select(EventLog)
            .where(EventLog.employee_id == hire_id)
            .order_by(EventLog.ts.desc())
            .limit(100)
        )
    )


@router.get("/notifications", response_model=list[NotificationResponse])
def notifications(
    hire_id: str | None = None,
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(Role.ADMIN, Role.HR, Role.MANAGER)),
) -> list[Notification]:
    query = select(Notification).order_by(Notification.ts.desc()).limit(100)
    if hire_id:
        query = query.where(Notification.employee_id == hire_id)
    return list(session.scalars(query))
