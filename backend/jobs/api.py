from fastapi import APIRouter
from jobs.core import list_jobs

router = APIRouter()

@router.get("/jobs")
def list_jobs_route():
    """
    Return all jobs, including pending, processing, done, failed.
    """
    jobs = list_jobs()
    return {"jobs": [job.dict() for job in jobs.values()]}