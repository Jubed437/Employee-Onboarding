from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.clock import (
    SimClock,
    add_business_days,
    business_days_between,
    is_business_day,
    load_holidays,
)
from app.db.base import Base
from app.db.base import SimClock as SimClockRow
from app.domain.enums import SimulationMode


def test_business_day_arithmetic_handles_weekends_and_holidays() -> None:
    holidays = {date(2026, 1, 26)}

    assert add_business_days(date(2026, 1, 23), 1, holidays) == date(2026, 1, 27)
    assert add_business_days(date(2026, 1, 27), -1, holidays) == date(2026, 1, 23)
    assert business_days_between(date(2026, 1, 23), date(2026, 1, 27), holidays) == 1
    assert business_days_between(date(2026, 1, 27), date(2026, 1, 23), holidays) == -1


def test_business_day_zero_offset_does_not_move_start() -> None:
    saturday = date(2026, 1, 24)

    assert add_business_days(saturday, 0) == saturday
    assert not is_business_day(saturday)


def test_load_holidays_reads_iso_dates() -> None:
    holidays = load_holidays(Path(__file__).parents[2] / "config" / "holidays_in.yaml")

    assert holidays == frozenset()


def test_sim_clock_reads_writes_and_emits_advance() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    events: list[datetime] = []

    with Session(engine) as session:
        session.add(
            SimClockRow(
                id=1,
                current_time=datetime(2026, 1, 5, 9, tzinfo=UTC),
                mode=SimulationMode.SIM,
            )
        )
        session.commit()
        clock = SimClock(session, on_advanced=events.append)

        assert clock.advance(days=1, hours=2) == datetime(2026, 1, 6, 11, tzinfo=UTC)
        assert clock.set_to(datetime(2026, 1, 7, 9, tzinfo=UTC)) == datetime(
            2026, 1, 7, 9, tzinfo=UTC
        )
        assert events == [
            datetime(2026, 1, 6, 11, tzinfo=UTC),
            datetime(2026, 1, 7, 9, tzinfo=UTC),
        ]


def test_sim_clock_rejects_real_mode_and_naive_time() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            SimClockRow(
                id=1,
                current_time=datetime(2026, 1, 5, 9, tzinfo=UTC),
                mode=SimulationMode.REAL,
            )
        )
        session.commit()
        with pytest.raises(RuntimeError, match="SIM mode"):
            SimClock(session).now()

        row = session.get(SimClockRow, 1)
        assert row is not None
        row.mode = SimulationMode.SIM
        session.commit()
        with pytest.raises(ValueError, match="timezone-aware"):
            SimClock(session).set_to(datetime(2026, 1, 5, 9))
