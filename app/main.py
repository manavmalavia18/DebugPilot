from fastapi import FastAPI
from app.models import Job
from typing import List

app = FastAPI(
    title="JobRadar",
    description="AI-powered job intelligence system",
    version="0.1.0"
)

FAKE_JOBS = [
    Job(
        id=1,
        title="Backend Engineer",
        company="Stripe",
        location="Remote",
        salary_min=120000,
        salary_max=160000,
        description="Build payment infrastructure at scale.",
        url="https://stripe.com/jobs/1"
    ),
    Job(
        id=2,
        title="DevOps Engineer",
        company="Cloudflare",
        location="London",
        salary_min=90000,
        salary_max=130000,
        description="Manage Kubernetes clusters and CI/CD pipelines.",
        url="https://cloudflare.com/jobs/2"
    ),
]

@app.get("/")
def root():
    return {"message": "JobRadar is alive"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/jobs", response_model=List[Job])
def get_jobs():
    return FAKE_JOBS