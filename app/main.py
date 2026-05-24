from fastapi import FastAPI, Depends
from app.services import fetch_jobs_from_remotive
from sqlmodel import Session, select
from app.models import Job, JobRead
from app.database import create_db_and_tables, get_session
from typing import List
from app.ai import score_job, generate_cover_letter
from contextlib import asynccontextmanager
from pydantic import BaseModel
from dotenv import load_dotenv
from app.celery_app import celery_app
from app.tasks import fetch_jobs_task
import os
from anthropic import Anthropic
import time
from app.logging_config import logger

start_time = time.time()
load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))



@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(
    title="JobRadar",
    description="AI-powered job intelligence system",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/")
def root():
    return {"message": "JobRadar is alive"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/jobs", response_model=List[JobRead])
def get_jobs(
    title: str = None,
    location: str = None,
    session: Session = Depends(get_session)
):
    query = select(Job)
    if title:
        query = query.where(Job.title.contains(title))
    if location:
        query = query.where(Job.location.contains(location))
    return session.exec(query).all()

@app.post("/jobs", response_model=JobRead)
def create_job(job: Job, session: Session = Depends(get_session)):
    session.add(job)
    session.commit()
    session.refresh(job)
    return job

@app.get("/jobs/fetch", response_model=List[JobRead])
async def fetch_and_store_jobs(
    search: str = None,
    session: Session = Depends(get_session)
):
    jobs = await fetch_jobs_from_remotive(search)
    for job in jobs:
        session.add(job)
    session.commit()
    return jobs

class CVMatchRequest(BaseModel):
    cv_text: str
    limit: int = 10

class CoverLetterRequest(BaseModel):
    cv_text: str

@app.post("/match")
def match_jobs(request: CVMatchRequest, session: Session = Depends(get_session)):
    query = select(Job).limit(request.limit)
    jobs = session.exec(query).all()
    
    results = []
    for job in jobs:
        score = score_job(
            cv_text=request.cv_text,
            job_title=job.title,
            job_description=job.description
        )
        results.append({
            "job": job,
            "score": score["score"],
            "reason": score["reason"],
            "missing": score["missing"]
        })
    
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

@app.post("/cover-letter/{job_id}")
def cover_letter(
    job_id: int,
    request: CoverLetterRequest,
    session: Session = Depends(get_session)
):
    job = session.get(Job, job_id)
    if not job:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Job not found")
    
    letter = generate_cover_letter(
        cv_text=request.cv_text,
        job_title=job.title,
        company=job.company,
        job_description=job.description
    )
    return {"cover_letter": letter, "job": job}


@app.post("/jobs/fetch-async")
def fetch_jobs_async(search: str = None):
    task = fetch_jobs_task.delay(search=search)
    return {
        "task_id": task.id,
        "status": "queued",
        "message": f"Fetching jobs in background. Poll /tasks/{task.id} for status"
    }

@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    task = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.status,
        "result": task.result if task.ready() else None
    }



@app.get("/metrics")
def metrics(session: Session = Depends(get_session)):
    jobs = session.exec(select(Job)).all()
    uptime = round(time.time() - start_time, 2)
    logger.info("metrics endpoint hit")
    return {
        "uptime_seconds": uptime,
        "total_jobs": len(jobs),
        "status": "healthy"
    }