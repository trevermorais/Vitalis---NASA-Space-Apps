"""SQLite engine + request-scoped session (same pattern as home_pharmacy)."""
from typing import Generator
from sqlmodel import Session, SQLModel, create_engine
from core.config import settings

engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    from core import models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
