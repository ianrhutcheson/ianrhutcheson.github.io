from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings
from .models.db import Base


def get_engine():
    return create_engine(settings.database_url, pool_pre_ping=True)


def init_db() -> Session:
    """Create tables and return a session factory."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


SessionLocal = init_db()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# FastAPI dependency

def get_db() -> Generator[Session, None, None]:
    with session_scope() as session:
        yield session
