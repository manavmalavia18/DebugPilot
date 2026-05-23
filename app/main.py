from fastapi import FastAPI, Depends
from app.services import fetch_jobs_from_remotive
from sqlmodel import Session, select
from app.models import Job, JobRead
from app.database import create_db_and_tables, get_session
from typing import List

app = FastAPI(
    title="JobRadar",
    description="AI-powered job intelligence system",
    version="0.1.0"
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

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