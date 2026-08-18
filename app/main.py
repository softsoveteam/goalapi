from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.migrate import migrate
from app.routers import auth, dashboard, goals, tasks, teams

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
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"ok": True}
