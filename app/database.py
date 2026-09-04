"""SQLAlchemy engine & session."""
from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False,
)

# Enable SQLite foreign keys
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_ensure_columns() -> None:
    """Lightweight additive migrations for Phase-1 user fields (sqlite)."""
    if not settings.database_url.startswith("sqlite"):
        return
    alters = [
        ("sys_users", "position_id", "ALTER TABLE sys_users ADD COLUMN position_id INTEGER REFERENCES positions(id)"),
        ("sys_users", "phone", "ALTER TABLE sys_users ADD COLUMN phone VARCHAR(64)"),
        ("sys_users", "email", "ALTER TABLE sys_users ADD COLUMN email VARCHAR(128)"),
        ("sys_users", "last_login_at", "ALTER TABLE sys_users ADD COLUMN last_login_at DATETIME"),
    ]
    with engine.begin() as conn:
        for table, col, ddl in alters:
            rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
            names = {r[1] for r in rows}
            if col not in names:
                conn.execute(text(ddl))
                print(f"Schema migrate: added {table}.{col}")


def init_db() -> None:
    """Create all tables (MVP; switch to Alembic for production)."""
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _sqlite_ensure_columns()
