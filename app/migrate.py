from sqlalchemy import MetaData, inspect, text

from app.db import models  # noqa: F401
from app.db.seed import seed_defaults
from app.db.session import Base, SessionLocal, engine

TASK_COLUMNS = {
    "priority": "priority VARCHAR(20) DEFAULT 'normal'",
    "reminded_at": "reminded_at TIMESTAMP",
    "warned_at": "warned_at TIMESTAMP",
    "recurring_rule_id": "recurring_rule_id INTEGER",
}


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "tasks" not in tables:
        return
    existing = {col["name"] for col in inspector.get_columns("tasks")}
    with engine.begin() as conn:
        for name, ddl in TASK_COLUMNS.items():
            if name not in existing:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN {0}".format(ddl)))
                print("Added tasks.{0}".format(name))


def migrate() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    legacy = bool({"roles", "projects", "team_members", "teams"} & tables)
    kind_missing = False
    if "users" in tables:
        cols = {col["name"] for col in inspector.get_columns("users")}
        kind_missing = "kind" not in cols
    if legacy or kind_missing:
        reflected = MetaData()
        reflected.reflect(bind=engine)
        reflected.drop_all(bind=engine)
        print("Dropped legacy tables")
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    with SessionLocal() as db:
        seed_defaults(db)
    print("Tables ready: {0}".format(", ".join(sorted(Base.metadata.tables))))
    print("Owner: admin@softsove.com")
    print("Manager: manager@softsove.com")


if __name__ == "__main__":
    migrate()
