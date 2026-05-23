from sqlmodel import SQLModel, Field
from typing import Optional

class JobBase(SQLModel):
    title: str
    company: str
    location: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    description: str
    url: str

class Job(JobBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

class JobRead(JobBase):
    id: int