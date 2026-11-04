from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.db.base import SimClock as SimClockRow
from app.domain.enums import SimulationMode

ClockEventCallback = Callable[[datetime], None]


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""

    def advance(self, *, days: int = 0, hours: int = 0) -> datetime:
        raise RuntimeError("clock advancement is only available in SIM mode")

    def set_to(self, value: datetime) -> datetime:
        raise RuntimeError("setting the clock is only available in SIM mode")


class RealClock(Clock):
    def now(self) -> datetime:
        return datetime.now(UTC)


class SimClock(Clock):
    def __init__(
        self,
        session: Session,
        *,
        on_advanced: ClockEventCallback | None = None,
    ) -> None:
        self._session = session
        self._on_advanced = on_advanced

    def now(self) -> datetime:
        row = self._get_row()
        return _as_utc(row.current_time, assume_naive_utc=True)

    def advance(self, *, days: int = 0, hours: int = 0) -> datetime:
        row = self._get_row()
        row.current_time = _as_utc(row.current_time, assume_naive_utc=True) + timedelta(
            days=days, hours=hours
        )
        self._session.commit()
        current_time = _as_utc(row.current_time, assume_naive_utc=True)
        self._emit_advanced(current_time)
        return current_time

    def set_to(self, value: datetime) -> datetime:
        row = self._get_row()
        row.current_time = _as_utc(value)
        self._session.commit()
        current_time = _as_utc(row.current_time, assume_naive_utc=True)
        self._emit_advanced(current_time)
        return current_time

    def _get_row(self) -> SimClockRow:
        row = self._session.get(SimClockRow, 1)
        if row is None:
            raise RuntimeError("sim_clock row is not initialized")
        if row.mode is not SimulationMode.SIM:
            raise RuntimeError("sim_clock must be in SIM mode")
        return row

    def _emit_advanced(self, current_time: datetime) -> None:
        if self._on_advanced is not None:
            self._on_advanced(current_time)


def load_holidays(path: Path) -> frozenset[date]:
    try:
        with path.open(encoding="utf-8") as holiday_file:
            raw = yaml.safe_load(holiday_file) or {}
    except (OSError, yaml.YAMLError) as error:
        raise ValueError(f"Invalid holiday configuration in {path}: {error}") from error

    holidays = raw.get("holidays", [])
    if not isinstance(holidays, list):
        raise ValueError(f"Invalid holiday configuration in {path}: holidays must be a list")
    try:
        return frozenset(date.fromisoformat(str(value)) for value in holidays)
    except ValueError as error:
        raise ValueError(f"Invalid holiday date in {path}: {error}") from error


def is_business_day(day: date, holidays: Iterable[date] = ()) -> bool:
    return day.weekday() < 5 and day not in holidays


def add_business_days(
    start: date,
    days: int,
    holidays: Iterable[date] = (),
) -> date:
    holiday_set = frozenset(holidays)
    current = start
    step = 1 if days >= 0 else -1
    remaining = abs(days)
    while remaining:
        current += timedelta(days=step)
        if is_business_day(current, holiday_set):
            remaining -= 1
    return current


def business_days_between(
    start: date,
    end: date,
    holidays: Iterable[date] = (),
) -> int:
    if start == end:
        return 0
    step = 1 if end > start else -1
    current = start
    distance = 0
    holiday_set = frozenset(holidays)
    while current != end:
        current += timedelta(days=step)
        if is_business_day(current, holiday_set):
            distance += step
    return distance


def _as_utc(value: datetime, *, assume_naive_utc: bool = False) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        if assume_naive_utc:
            return value.replace(tzinfo=UTC)
        raise ValueError("clock timestamps must be timezone-aware")
    return value.astimezone(UTC)
