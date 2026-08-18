from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, MetaData

from app.core.config import settings
from app.db import models  # noqa: F401
from app.db.seed import seed_defaults
from app.db.session import Base, SessionLocal, engine
from app.routers import auth, dashboard, goals, tasks, teams

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

Base.metadata.create_all(bind=engine)
with SessionLocal() as db:
    seed_defaults(db)

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
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"ok": True}
