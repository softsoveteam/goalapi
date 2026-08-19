from sqlalchemy import MetaData, inspect, text

from app.db import models  # noqa: F401
from app.db.seed import seed_defaults
from app.db.session import Base, SessionLocal, engine

EXTRA_COLUMNS = {
    "tasks": {
        "priority": "priority VARCHAR(20) DEFAULT 'normal'",
        "reminded_at": "reminded_at TIMESTAMP",
        "warned_at": "warned_at TIMESTAMP",
        "recurring_rule_id": "recurring_rule_id INTEGER",
        "is_archived": "is_archived BOOLEAN DEFAULT FALSE",
        "archive_reason": "archive_reason TEXT DEFAULT ''",
        "archived_at": "archived_at TIMESTAMP",
        "archived_by": "archived_by INTEGER",
    },
    "goals": {
        "priority": "priority VARCHAR(20) DEFAULT 'normal'",
        "sort_order": "sort_order INTEGER DEFAULT 0",
    },
    "goal_items": {
        "parent_id": "parent_id INTEGER",
    },
}


def _priority_from_rank(index: int) -> str:
    if index < 5:
        return "urgent"
    if index < 10:
        return "high"
    if index < 20:
        return "normal"
    return "low"


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    added_sort = False
    with engine.begin() as conn:
        for table, columns in EXTRA_COLUMNS.items():
            if table not in tables:
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text("ALTER TABLE {0} ADD COLUMN {1}".format(table, ddl)))
                    print("Added {0}.{1}".format(table, name))
                    if table == "goals" and name == "sort_order":
                        added_sort = True
        if added_sort:
            rows = conn.execute(text("SELECT id FROM goals ORDER BY id")).fetchall()
            for index, row in enumerate(rows):
                conn.execute(
                    text("UPDATE goals SET sort_order = :s, priority = :p WHERE id = :id"),
                    {"s": index, "p": _priority_from_rank(index), "id": row[0]},
                )


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


if __name__ == "__main__":
    migrate()
