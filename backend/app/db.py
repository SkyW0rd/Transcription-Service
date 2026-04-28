from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_parent_dir() -> None:
    url = make_url(settings.database_url)
    if url.drivername != "sqlite":
        return
    if not url.database:
        return
    Path(url.database).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir()

engine = create_engine(settings.database_url, future=True, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
