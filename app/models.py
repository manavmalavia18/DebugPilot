from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field
from sqlmodel import Field as SQLField, SQLModel

SourceCategory = Literal[
    "kubernetes", "terraform", "github_actions", "docker", "app", "unknown"
]
ConfidenceLevel = Literal["high", "medium", "low"]


class AnalyzeRequest(BaseModel):
    log_text: str = Field(min_length=1)
    source_hint: Optional[SourceCategory] = None
    save: bool = True


class AnalysisResult(BaseModel):
    category: SourceCategory
    symptom: str
    what_failed: str
    root_cause: str
    confidence: ConfidenceLevel
    debug_commands: list[str]
    likely_fix: str
    prevention: list[str]
    similar_incidents: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AnalyzeResponse(AnalysisResult):
    """POST /analyze — diagnosis fields plus cache and timing metadata."""

    cached: bool = False
    duration_ms: float = Field(
        ge=0,
        description="Wall-clock time for this request in milliseconds",
    )


class User(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    github_id: int = SQLField(index=True, unique=True)
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime = SQLField(default_factory=datetime.utcnow)


class UserRead(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None


class SavedIncident(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    user_id: int = SQLField(foreign_key="user.id", index=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    log_text: str
    category: str
    symptom: str
    root_cause: str
    likely_fix: str
    confidence: str
    response_json: str


class SavedIncidentRead(BaseModel):
    id: int
    created_at: datetime
    category: str
    symptom: str
    root_cause: str
    likely_fix: str
    confidence: str
