from app.db.base import Base
from app.db.session import engine
from seed import seed


def reset_demo() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed()


if __name__ == "__main__":
    reset_demo()
    print("Demo database reset and synthetic data reseeded.")
