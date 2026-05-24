from app.celery_app import celery_app
from app.services import fetch_jobs_from_remotive
from app.database import get_session
from app.models import Job
import asyncio

@celery_app.task(bind=True)
def fetch_jobs_task(self, search: str = None):
    self.update_state(state="STARTED", meta={"search": search})
    
    jobs = asyncio.run(fetch_jobs_from_remotive(search))
    
    session = next(get_session())
    try:
        for job in jobs:
            session.add(job)
        session.commit()
    finally:
        session.close()
    
    return {"status": "completed", "jobs_fetched": len(jobs)}