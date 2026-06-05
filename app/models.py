from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator
from sqlmodel import Field as SQLField, SQLModel

SourceCategory = Literal[
    "kubernetes", "terraform", "github_actions", "docker", "app", "unknown"
]
ConfidenceLevel = Literal["high", "medium", "low"]


class AnalyzeRequest(BaseModel):
    log_text: str = Field(default="", max_length=8000)
    source_hint: Optional[SourceCategory] = None
    save: bool = True
    upload_id: Optional[int] = None

    def resolved_log_text(self) -> str:
        return self.log_text.strip()

    @model_validator(mode="after")
    def require_log_or_upload(self):
        if not self.upload_id and not self.log_text.strip():
            raise ValueError("log_text or upload_id is required")
        return self


class PlaybookMatch(BaseModel):
    name: str
    score: float = Field(ge=0, le=1)
    method: Literal["semantic", "keyword"] = "semantic"


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
    playbook_matches: list[PlaybookMatch] = Field(default_factory=list)
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


class LogUpload(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    user_id: int = SQLField(foreign_key="user.id", index=True)
    created_at: datetime = SQLField(default_factory=datetime.utcnow)
    filename: str
    storage_key: str
    size_bytes: int
    content_type: str = "text/plain"


class UploadResponse(BaseModel):
    id: int
    filename: str
    size_bytes: int
    storage_backend: str
    log_text: str


class SavedIncident(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    user_id: int = SQLField(foreign_key="user.id", index=True)
    upload_id: Optional[int] = SQLField(default=None, foreign_key="logupload.id")
    source_filename: Optional[str] = None
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
    source_filename: Optional[str] = None
