import httpx
from app.models import Job
from app.cache import make_cache_key, get_cached, set_cached

REMOTIVE_URL = "https://remotive.com/api/remote-jobs"

async def fetch_jobs_from_remotive(search: str = None) -> list[Job]:
    cache_key = make_cache_key("jobs", search=search)
    
    cached = get_cached(cache_key)
    if cached:
        print(f"CACHE HIT: {cache_key}")
        return [Job(**job) for job in cached]
    
    print(f"CACHE MISS: {cache_key}")
    params = {"limit": 20}
    if search:
        params["search"] = search

    async with httpx.AsyncClient() as client:
        response = await client.get(REMOTIVE_URL, params=params)
        response.raise_for_status()
        data = response.json()

    jobs = []
    for item in data["jobs"]:
        job = Job(
            title=item["title"],
            company=item["company_name"],
            location=item["candidate_required_location"] or "Remote",
            salary_min=None,
            salary_max=None,
            description=item["description"][:500],
            url=item["url"]
        )
        jobs.append(job)

    set_cached(cache_key, [job.dict() for job in jobs])
    return jobs