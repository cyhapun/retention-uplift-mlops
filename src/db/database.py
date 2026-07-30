import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

DEFAULT_DATABASE_URL = "sqlite:///:memory:"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


class Base(DeclarativeBase):
    pass


def create_database_engine(database_url: str = DATABASE_URL):
    connect_args = {}
    engine_options = {}

    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if database_url in {"sqlite:///:memory:", "sqlite://"}:
            engine_options["poolclass"] = StaticPool

    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args=connect_args,
        **engine_options,
    )


engine = create_database_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db_session() -> Generator[Session, None, None]:
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


def init_database() -> None:
    # Import models here so SQLAlchemy registers them before create_all().
    from src.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
