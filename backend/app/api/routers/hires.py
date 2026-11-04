from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_roles
from app.core.clock import RealClock
from app.db.base import Employee, ReadinessSnapshot
from app.domain.api_schemas import HireCreate, HireResponse, ReadinessResponse
from app.domain.enums import EmployeeStatus, Role
from app.services.plan_generator import generate_plan

router = APIRouter(prefix="/hires", tags=["hires"])


@router.get("", response_model=list[HireResponse])
def list_hires(
    session: Session = Depends(get_db),
    _: object = Depends(require_roles(Role.ADMIN, Role.HR, Role.MANAGER)),
) -> list[Employee]:
    return list(session.scalars(select(Employee).order_by(Employee.join_date)))


@router.post("", response_model=HireResponse, status_code=201)
def create_hire(
    request: HireCreate,
    session: Session = Depends(get_db),
    _: object = Depends(require_roles(Role.ADMIN, Role.HR, Role.MANAGER)),
) -> Employee:
    employee = Employee(
        full_name=request.full_name,
        email=request.email,
        profile_key=request.profile_key,
        is_experienced=request.is_experienced,
        is_remote=request.is_remote,
        work_state=request.work_state,
        job_title=request.job_title,
        department=request.department,
        join_date=request.join_date,
        payroll_cutoff_date=request.join_date,
        manager_id=request.manager_id,
        status=EmployeeStatus.ACTIVE,
        created_at=RealClock().now(),
    )
    session.add(employee)
    session.flush()
    generate_plan(session, employee, RealClock())
    return employee


@router.get("/{hire_id}", response_model=HireResponse)
def get_hire(
    hire_id: str,
    session: Session = Depends(get_db),
    _: object = Depends(require_roles(Role.ADMIN, Role.HR, Role.MANAGER)),
) -> Employee:
    employee = session.get(Employee, hire_id)
    if employee is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Hire not found"},
        )
    return employee


@router.get("/{hire_id}/readiness", response_model=ReadinessResponse)
def get_readiness(
    hire_id: str,
    session: Session = Depends(get_db),
    _: object = Depends(require_roles(Role.ADMIN, Role.HR, Role.MANAGER)),
) -> ReadinessSnapshot:
    snapshot = session.scalar(
        select(ReadinessSnapshot)
        .where(ReadinessSnapshot.employee_id == hire_id)
        .order_by(ReadinessSnapshot.ts.desc())
    )
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Readiness snapshot not found"},
        )
    return snapshot


@router.get("/{hire_id}/readiness/history", response_model=list[ReadinessResponse])
def readiness_history(
    hire_id: str,
    session: Session = Depends(get_db),
    _: object = Depends(require_roles(Role.ADMIN, Role.HR, Role.MANAGER)),
) -> list[ReadinessSnapshot]:
    return list(
        session.scalars(
            select(ReadinessSnapshot)
            .where(ReadinessSnapshot.employee_id == hire_id)
            .order_by(ReadinessSnapshot.ts)
        )
    )
