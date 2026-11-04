import importlib.util
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base, Employee, ReadinessSnapshot
from app.db.base import SimClock as SimClockRow

SEED_PATH = Path(__file__).parents[2] / "backend" / "seed.py"
spec = importlib.util.spec_from_file_location("seed_script", SEED_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("Could not load seed script")
seed_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seed_module)


def test_seed_creates_initial_readiness_snapshots(tmp_path, monkeypatch) -> None:
    database = tmp_path / "seed.db"
    engine = create_engine(f"sqlite:///{database}", connect_args={"check_same_thread": False})
    monkeypatch.setattr("app.db.session.engine", engine)
    monkeypatch.setattr(seed_module, "DATABASE_URL", f"sqlite:///{database}")
    Base.metadata.create_all(engine)

    seed_module.seed()

    with Session(engine) as session:
        assert session.scalar(select(SimClockRow)) is not None
        assert len(session.scalars(select(Employee)).all()) == 3
        assert len(session.scalars(select(ReadinessSnapshot)).all()) == 3
