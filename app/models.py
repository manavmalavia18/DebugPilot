from pydantic import BaseModel
from typing import Optional

class Job(BaseModel):
    id: int
    title: str
    company: str
    location: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: str
    url: str