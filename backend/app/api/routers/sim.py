
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.clock import SimClock
from app.core.security import CurrentUser
from app.db.base import Employee, EventLog, TaskInstance
from app.db.base import SimClock as SimClockRow
from app.domain.enums import Role, TaskState
from app.services.monitor import evaluate

router = APIRouter(prefix="/sim", tags=["simulation"])


@router.get("/clock")
def get_clock(
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(Role.ADMIN)),
) -> dict[str, str]:
    row = session.get(SimClockRow, 1)
    if row is None:
        raise HTTPException(status_code=404, detail="Simulation clock is not initialized")
    return {"now": SimClock(session).now().isoformat(), "mode": row.mode.value}


@router.post("/clock/advance")
def advance_clock(
    payload: dict[str, int],
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(Role.ADMIN)),
) -> dict[str, str]:
    clock = SimClock(session)
    now = clock.advance(days=payload.get("days", 0), hours=payload.get("hours", 0))
    for employee_id in session.scalars(select(Employee.id)).all():
        evaluate(session, employee_id, clock)
    return {"now": now.isoformat()}


@router.post("/inject")
def inject(
    payload: dict[str, str],
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(Role.ADMIN)),
) -> dict[str, bool]:
    task = session.scalar(
        select(TaskInstance).where(
            TaskInstance.employee_id == payload["hireId"],
            TaskInstance.template_key == payload["taskKey"],
        )
    )
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    kind = payload["kind"]
    if kind == "REJECT":
        task.state = TaskState.REJECTED
        task.meta = {**task.meta, "reason": payload.get("reason", "simulation rejection")}
    elif kind == "DELAY":
        task.duration_days += float(payload.get("days", "5"))
    elif kind == "FAIL_INTEGRATION":
        task.meta = {**task.meta, "integration_failure": payload.get("reason", "injected")}
    else:
        raise HTTPException(status_code=400, detail="Unknown injection kind")
    session.commit()
    row = session.get(SimClockRow, 1)
    if row is not None:
        evaluate(session, task.employee_id, SimClock(session))
    return {"ok": True}


@router.post("/reset")
def reset(
    session: Session = Depends(get_db),
    _: CurrentUser = Depends(require_roles(Role.ADMIN)),
) -> dict[str, bool]:
    for model in (EventLog,):
        session.execute(delete(model))
    for task in session.scalars(select(TaskInstance)).all():
        task.state = TaskState.READY if task.template_key == "HR-01" else TaskState.NOT_STARTED
        task.meta = {}
        task.attempts = 0
        task.rework_count = 0
    session.commit()
    return {"ok": True}
