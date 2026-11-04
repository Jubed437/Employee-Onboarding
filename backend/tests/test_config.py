from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import ConfigLoadError, load_profile
from app.domain.enums import Role
from app.domain.schemas import (
    DeadlineConfig,
    ProfileConfig,
    ProfileDefaults,
    TaskConfig,
    TaskFlags,
)

CONFIG_ROOT = Path(__file__).parents[2] / "config"


def test_india_profile_loads_with_all_catalog_tasks() -> None:
    profile = load_profile(CONFIG_ROOT / "profiles" / "india_full_time.yaml")

    assert profile.profile == "india_full_time"
    assert len(profile.tasks) == 27
    assert profile.tasks["PAY-06"].deadline.relative_to == "payroll_cutoff"


def test_us_stub_profile_loads_without_code_changes() -> None:
    profile = load_profile(CONFIG_ROOT / "profiles" / "us_full_time.yaml")

    assert profile.profile == "us_full_time"
    assert set(profile.tasks) == {"HR-01"}


def test_missing_dependency_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown task IDs"):
        ProfileConfig(
            profile="test_profile",
            display_name="Test",
            defaults=ProfileDefaults(payroll_cutoff_day=20, business_calendar="test"),
            tasks={
                "A": TaskConfig(
                    title="A",
                    owner_role=Role.HR,
                    depends_on=["MISSING"],
                    duration_days=1,
                    deadline=DeadlineConfig(relative_to="join_date", offset_days=0),
                    flags=TaskFlags(),
                )
            },
        )


def test_dependency_cycle_is_rejected() -> None:
    with pytest.raises(ValidationError, match="dependency cycle"):
        ProfileConfig(
            profile="test_profile",
            display_name="Test",
            defaults=ProfileDefaults(payroll_cutoff_day=20, business_calendar="test"),
            tasks={
                "A": TaskConfig(
                    title="A",
                    owner_role=Role.HR,
                    depends_on=["B"],
                    duration_days=1,
                    deadline=DeadlineConfig(relative_to="join_date", offset_days=0),
                ),
                "B": TaskConfig(
                    title="B",
                    owner_role=Role.HR,
                    depends_on=["A"],
                    duration_days=1,
                    deadline=DeadlineConfig(relative_to="join_date", offset_days=0),
                ),
            },
        )


def test_invalid_yaml_path_has_clear_error() -> None:
    with pytest.raises(ConfigLoadError, match="Invalid configuration"):
        load_profile(CONFIG_ROOT / "profiles" / "does_not_exist.yaml")
