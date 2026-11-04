from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.clock import SimClock
from app.db.base import Base, Employee, User
from app.db.base import SimClock as SimClockRow
from app.db.session import DATABASE_URL
from app.domain.enums import EmployeeStatus, Role, SimulationMode
from app.services.monitor import evaluate
from app.services.plan_generator import generate_plan


def seed() -> None:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        now = datetime(2026, 10, 26, 9, tzinfo=UTC)
        clock_row = session.get(SimClockRow, 1)
        if clock_row is None:
            session.add(
                SimClockRow(id=1, current_time=now, mode=SimulationMode.SIM)
            )
            session.commit()
        else:
            clock_row.current_time = now
            clock_row.mode = SimulationMode.SIM
            session.commit()
        manager = session.get(User, "manager-1")
        if manager is None:
            manager = User(
                id="manager-1",
                display_name="Rohan Iyer",
                role=Role.MANAGER,
                team_id="engineering",
            )
            session.add(manager)
        personas = [
            ("hr-1", "Meera Shah", Role.HR, "people"),
            ("payroll-1", "Karthik Rao", Role.PAYROLL, "payroll"),
            ("it-1", "Divya Menon", Role.IT, "it"),
            ("benefits-1", "Asha Verma", Role.BENEFITS, "benefits"),
            ("admin-1", "Demo Admin", Role.ADMIN, "platform"),
        ]
        for user_id, name, role, team in personas:
            if session.get(User, user_id) is None:
                session.add(
                    User(id=user_id, display_name=name, role=role, team_id=team)
                )
        session.commit()
        hires = [
            (
                "priya-1", "Priya Nair", "priya@example.test", True, True,
                "Karnataka", date(2026, 11, 16),
            ),
            (
                "arjun-1", "Arjun Mehta", "arjun@example.test", False, False,
                "Maharashtra", date(2026, 11, 23),
            ),
            (
                "sana-1", "Sana Khan", "sana@example.test", True, False,
                "Tamil Nadu", date(2026, 11, 18),
            ),
        ]
        for employee_id, name, email, experienced, remote, state, join_date in hires:
            employee = session.get(Employee, employee_id)
            if employee is None:
                employee = Employee(
                    id=employee_id,
                    full_name=name,
                    email=email,
                    profile_key="india_full_time",
                    is_experienced=experienced,
                    is_remote=remote,
                    work_state=state,
                    job_title="Software Engineer",
                    department="Engineering",
                    join_date=join_date,
                    payroll_cutoff_date=join_date,
                    manager_id=manager.id,
                    status=EmployeeStatus.ACTIVE,
                    created_at=now,
                )
                session.add(employee)
                session.flush()
                generate_plan(session, employee, SimClock(session))
        session.commit()
        for employee_id, *_ in hires:
            evaluate(session, employee_id, SimClock(session))


if __name__ == "__main__":
    seed()
