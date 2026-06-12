from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models import SourceCategory

IngestionSource = Literal["manual", "github_actions", "alertmanager", "kubernetes"]


class IncidentEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    source: IngestionSource
    external_id: str
    log_text: str
    source_hint: Optional[SourceCategory] = None
    metadata: dict = Field(default_factory=dict)
    received_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json_bytes(self) -> bytes:
        return self.model_dump_json().encode("utf-8")

    @classmethod
    def from_json_bytes(cls, payload: bytes) -> "IncidentEvent":
        return cls.model_validate_json(payload)


def build_github_external_id(owner: str, repo: str, run_id: int) -> str:
    return f"github:{owner}/{repo}:{run_id}"
