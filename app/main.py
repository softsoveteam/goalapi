from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.migrate import migrate
from app.routers import auth, dashboard, goals, jobs, recurring, tasks, teams
from app.services.scheduler import start_scheduler

migrate()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(goals.router)
app.include_router(tasks.router)
app.include_router(recurring.router)
app.include_router(jobs.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/health/db")
def health_db():
    from sqlalchemy import inspect
    from app.db.session import engine

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    user_cols = []
    task_cols = []
    if "users" in tables:
        user_cols = [col["name"] for col in inspector.get_columns("users")]
    if "tasks" in tables:
        task_cols = [col["name"] for col in inspector.get_columns("tasks")]
    return {
        "ok": True,
        "tables": tables,
        "users_columns": user_cols,
        "tasks_columns": task_cols,
        "ready": "kind" in user_cols and "tasks" in tables and "otp_codes" in tables and "priority" in task_cols,
    }


start_scheduler()
