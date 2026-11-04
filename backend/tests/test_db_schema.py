from sqlalchemy import create_engine, inspect

from app.db.base import Base


def test_metadata_contains_all_prd_tables() -> None:
    expected = {
        "employee",
        "user",
        "task_instance",
        "task_dependency",
        "event_log",
        "risk",
        "recommendation",
        "approval",
        "readiness_snapshot",
        "audit_log",
        "notification",
        "sim_clock",
        "document",
    }

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    assert set(inspect(engine).get_table_names()) == expected


def test_task_dependency_has_composite_primary_key() -> None:
    primary_key = Base.metadata.tables["task_dependency"].primary_key

    assert {column.name for column in primary_key.columns} == {
        "task_id",
        "depends_on_task_id",
    }
