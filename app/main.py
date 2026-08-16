from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.seed import seed_defaults
from app.db.session import Base, SessionLocal, engine
from app.routers import auth, dashboard, goals, projects, roles, tasks, teams, users

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
app.include_router(roles.router)
app.include_router(users.router)
app.include_router(teams.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(goals.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"ok": True}
