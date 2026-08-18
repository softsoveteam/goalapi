from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.services import jobs

router = APIRouter(prefix="/internal/jobs", tags=["jobs"])


@router.post("/run")
def run_job(job: str = Query(...), token: str = Query(...)):
    if not settings.job_secret or token != settings.job_secret:
        raise HTTPException(status_code=403, detail="Invalid job token")
    if job == "reminders":
        return jobs.run_reminders()
    if job == "digest":
        return jobs.run_digest()
    if job == "recurring":
        return jobs.run_recurring()
    if job == "care":
        return jobs.run_care()
    raise HTTPException(status_code=400, detail="Unknown job")
