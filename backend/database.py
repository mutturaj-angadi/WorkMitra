from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str | None = None):
    target = url or get_settings().database_url
    kwargs = {"check_same_thread": False} if target.startswith("sqlite") else {}
    return create_engine(target, connect_args=kwargs, pool_pre_ping=True)


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def ensure_compat_columns(target_engine=engine):
    """Small additive compatibility migration for local/dev databases."""
    inspector = inspect(target_engine)
    if "quarantined_requests" in inspector.get_table_names():
        names = {
            column["name"] for column in inspector.get_columns("quarantined_requests")
        }
        if "field_errors" not in names:
            with target_engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE quarantined_requests ADD COLUMN field_errors JSON NOT NULL DEFAULT '[]'"
                    )
                )


def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
