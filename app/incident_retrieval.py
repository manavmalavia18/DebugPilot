import os
import re
from dataclasses import dataclass

from sqlmodel import Session, select

from app.models import SavedIncident
from app.retrieval import (
    LOG_EMBED_MAX_CHARS,
    RETRIEVAL_CONTEXT_MIN_SCORE,
    RETRIEVAL_MIN_SCORE,
    _cosine_similarity,
    _embed_text,
    semantic_rag_enabled,
)

INCIDENT_HISTORY_LIMIT = int(os.getenv("INCIDENT_HISTORY_LIMIT", "50"))
INCIDENT_RETRIEVAL_LIMIT = int(os.getenv("INCIDENT_RETRIEVAL_LIMIT", "3"))
MIN_KEYWORD_OVERLAP = int(os.getenv("INCIDENT_KEYWORD_MIN_OVERLAP", "4"))


@dataclass(frozen=True)
class IncidentHistoryMatch:
    incident_id: int
    content: str
    score: float
    method: str  # "semantic" | "keyword"


def _incident_content(row: SavedIncident) -> str:
    log_excerpt = row.log_text[:1500].strip()
    return (
        f"Category: {row.category}\n"
        f"Symptom: {row.symptom}\n"
        f"Root cause: {row.root_cause}\n"
        f"Likely fix: {row.likely_fix}\n"
        f"Confidence: {row.confidence}\n"
        f"Log excerpt:\n{log_excerpt}"
    )


def _incident_embed_text(row: SavedIncident) -> str:
    return (
        f"{row.log_text[:LOG_EMBED_MAX_CHARS]}\n"
        f"Symptom: {row.symptom}\n"
        f"Root cause: {row.root_cause}\n"
        f"Fix: {row.likely_fix}"
    )


def _token_set(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9][a-z0-9._/-]{2,}", text.lower())}


def _keyword_incident_matches(
    log_text: str,
    rows: list[SavedIncident],
    limit: int,
) -> list[IncidentHistoryMatch]:
    haystack = _token_set(log_text)
    if not haystack:
        return []

    scored: list[tuple[int, SavedIncident]] = []
    for row in rows:
        overlap = len(haystack & _token_set(row.log_text))
        if overlap >= MIN_KEYWORD_OVERLAP:
            scored.append((overlap, row))

    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return []

    top_score = scored[0][0]
    return [
        IncidentHistoryMatch(
            incident_id=row.id,
            content=_incident_content(row),
            score=round(min(1.0, value / max(top_score, 1)), 3),
            method="keyword",
        )
        for value, row in scored[:limit]
        if row.id is not None
    ]


def _semantic_incident_matches(
    log_text: str,
    rows: list[SavedIncident],
    limit: int,
) -> list[IncidentHistoryMatch]:
    log_vector = _embed_text(log_text[:LOG_EMBED_MAX_CHARS])
    if not log_vector:
        return []

    scored: list[IncidentHistoryMatch] = []
    for row in rows:
        if row.id is None:
            continue
        score = _cosine_similarity(log_vector, _embed_text(_incident_embed_text(row)))
        if score >= RETRIEVAL_MIN_SCORE:
            scored.append(
                IncidentHistoryMatch(
                    incident_id=row.id,
                    content=_incident_content(row),
                    score=round(score, 3),
                    method="semantic",
                )
            )

    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit]


def incidents_for_llm_context(matches: list[IncidentHistoryMatch]) -> list[IncidentHistoryMatch]:
    if not matches:
        return []
    strong = [match for match in matches if match.score >= RETRIEVAL_CONTEXT_MIN_SCORE]
    if strong:
        return strong
    if matches[0].method == "keyword":
        return matches[:1]
    return []


def find_similar_saved_incidents(
    session: Session,
    user_id: int,
    log_text: str,
    limit: int = INCIDENT_RETRIEVAL_LIMIT,
) -> list[IncidentHistoryMatch]:
    if not log_text.strip():
        return []

    rows = session.exec(
        select(SavedIncident)
        .where(SavedIncident.user_id == user_id)
        .order_by(SavedIncident.created_at.desc())
        .limit(INCIDENT_HISTORY_LIMIT)
    ).all()
    if not rows:
        return []

    if semantic_rag_enabled():
        try:
            matches = _semantic_incident_matches(log_text, rows, limit)
            if matches:
                return matches
        except Exception:
            pass

    return _keyword_incident_matches(log_text, rows, limit)


def format_incident_history_context(matches: list[IncidentHistoryMatch]) -> str:
    context_matches = incidents_for_llm_context(matches)
    if not context_matches:
        return ""

    return "\n\n---\n\n".join(
        f"Past incident #{match.incident_id} (match {int(match.score * 100)}%):\n{match.content}"
        for match in context_matches
    )
