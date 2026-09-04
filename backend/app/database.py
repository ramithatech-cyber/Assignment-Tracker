"""Engine + session plumbing.

SQLite locally, Postgres in production -- switched purely by DATABASE_URL, so
no application code changes between the two.
"""

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

_connect_args = {}
if settings.database_url.startswith("sqlite"):
    # FastAPI serves requests on a threadpool; SQLite objects would otherwise
    # refuse to cross threads.
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args=_connect_args,
    pool_pre_ping=True,
)


def _add_missing_sqlite_columns() -> None:
    """Add columns that exist on the models but not yet in an existing SQLite file.

    `create_all` creates missing *tables* but never alters existing ones, so a
    dev database made before a column was added would break on the next query.
    This keeps local data intact without pulling in Alembic; production
    (Postgres) should use real migrations.
    """
    from sqlalchemy import inspect, text

    if not settings.database_url.startswith("sqlite"):
        return

    additions = {
        "users": {"enrolled_on": "DATE"},
    }

    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table, columns in additions.items():
            if table not in existing_tables:
                continue
            present = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl_type in columns.items():
                if name not in present:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}"))


def create_db_and_tables() -> None:
    # Import for the side effect of registering the tables on SQLModel.metadata.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _add_missing_sqlite_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
