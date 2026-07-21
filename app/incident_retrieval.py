import hashlib
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
INCIDENT_DISPLAY_LIMIT = int(os.getenv("INCIDENT_DISPLAY_LIMIT", "2"))
MIN_KEYWORD_OVERLAP = int(os.getenv("INCIDENT_KEYWORD_MIN_OVERLAP", "4"))

# Soft ranking boosts — prefer incidents the user confirmed or marked helpful.
RESOLUTION_BOOST = float(os.getenv("INCIDENT_RESOLUTION_BOOST", "0.05"))
FEEDBACK_UP_BOOST = float(os.getenv("INCIDENT_FEEDBACK_UP_BOOST", "0.03"))

# In-process memo for incident embeddings (id + content hash → vector).
_EMBED_CACHE_MAX = int(os.getenv("INCIDENT_EMBED_CACHE_MAX", "200"))
_incident_embed_cache: dict[tuple[int, str], list[float]] = {}


@dataclass(frozen=True)
class IncidentHistoryMatch:
    incident_id: int
    content: str
    score: float
    method: str  # "semantic" | "keyword"
    symptom: str = ""


def clear_incident_embed_cache() -> None:
    _incident_embed_cache.clear()


def _incident_content(row: SavedIncident) -> str:
    log_excerpt = row.log_text[:1500].strip()
    parts = [
        f"Category: {row.category}",
        f"Symptom: {row.symptom}",
        f"Root cause: {row.root_cause}",
        f"Likely fix: {row.likely_fix}",
    ]
    if row.resolution:
        parts.append(f"Confirmed resolution: {row.resolution}")
    parts.extend(
        [
            f"Confidence: {row.confidence}",
            f"Log excerpt:\n{log_excerpt}",
        ]
    )
    return "\n".join(parts)


def _incident_embed_text(row: SavedIncident) -> str:
    resolution = f"\nConfirmed resolution: {row.resolution}" if row.resolution else ""
    return (
        f"{row.log_text[:LOG_EMBED_MAX_CHARS]}\n"
        f"Symptom: {row.symptom}\n"
        f"Root cause: {row.root_cause}\n"
        f"Fix: {row.likely_fix}{resolution}"
    )


def _cached_incident_embed(row: SavedIncident) -> list[float]:
    """Embed incident text with a small process-local cache."""
    text = _incident_embed_text(row)
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    cache_key = (row.id or 0, content_hash)
    cached = _incident_embed_cache.get(cache_key)
    if cached is not None:
        return cached

    vector = _embed_text(text)
    if row.id is not None and vector:
        if len(_incident_embed_cache) >= _EMBED_CACHE_MAX:
            # Drop an arbitrary oldest-ish entry (dict preserves insertion order).
            _incident_embed_cache.pop(next(iter(_incident_embed_cache)))
        _incident_embed_cache[cache_key] = vector
    return vector


def _quality_boost(row: SavedIncident) -> float:
    boost = 0.0
    if row.resolution and row.resolution.strip():
        boost += RESOLUTION_BOOST
    if row.feedback == 1:
        boost += FEEDBACK_UP_BOOST
    return boost


def _apply_quality_boost(score: float, row: SavedIncident) -> float:
    return min(1.0, round(score + _quality_boost(row), 3))


def _token_set(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9][a-z0-9._/-]{2,}", text.lower())}


def _incident_search_corpus(row: SavedIncident) -> str:
    parts = [row.log_text, row.symptom, row.root_cause, row.likely_fix]
    if row.resolution:
        parts.append(row.resolution)
    return "\n".join(part for part in parts if part)


def _keyword_incident_matches(
    log_text: str,
    rows: list[SavedIncident],
    limit: int,
) -> list[IncidentHistoryMatch]:
    haystack = _token_set(log_text)
    if not haystack:
        return []

    scored: list[tuple[float, SavedIncident]] = []
    raw_overlaps: list[tuple[int, SavedIncident]] = []
    for row in rows:
        overlap = len(haystack & _token_set(_incident_search_corpus(row)))
        if overlap >= MIN_KEYWORD_OVERLAP:
            raw_overlaps.append((overlap, row))

    if not raw_overlaps:
        return []

    top_overlap = max(value for value, _ in raw_overlaps)
    for overlap, row in raw_overlaps:
        base = min(1.0, overlap / max(top_overlap, 1))
        scored.append((_apply_quality_boost(base, row), row))

    # Tie-break on quality boost so confirmed/helpful incidents win when scores cap at 1.0.
    scored.sort(key=lambda item: (item[0], _quality_boost(item[1])), reverse=True)
    return [
        IncidentHistoryMatch(
            incident_id=row.id,
            content=_incident_content(row),
            score=score,
            method="keyword",
            symptom=row.symptom,
        )
        for score, row in scored[:limit]
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

    scored: list[tuple[float, SavedIncident]] = []
    for row in rows:
        if row.id is None:
            continue
        raw_score = _cosine_similarity(log_vector, _cached_incident_embed(row))
        score = _apply_quality_boost(raw_score, row)
        if score >= RETRIEVAL_MIN_SCORE:
            scored.append((score, row))

    scored.sort(key=lambda item: (item[0], _quality_boost(item[1])), reverse=True)
    return [
        IncidentHistoryMatch(
            incident_id=row.id,
            content=_incident_content(row),
            score=score,
            method="semantic",
            symptom=row.symptom,
        )
        for score, row in scored[:limit]
        if row.id is not None
    ]


def dedupe_incident_history_matches(
    matches: list[IncidentHistoryMatch],
    limit: int = INCIDENT_DISPLAY_LIMIT,
) -> list[IncidentHistoryMatch]:
    seen: set[str] = set()
    deduped: list[IncidentHistoryMatch] = []
    for match in matches:
        key = match.symptom.strip().lower()[:120] if match.symptom else str(match.incident_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(match)
        if len(deduped) >= limit:
            break
    return deduped


def incidents_for_llm_context(matches: list[IncidentHistoryMatch]) -> list[IncidentHistoryMatch]:
    if not matches:
        return []
    strong = [match for match in matches if match.score >= RETRIEVAL_CONTEXT_MIN_SCORE]
    if strong:
        return dedupe_incident_history_matches(strong)
    if matches[0].method == "keyword":
        return dedupe_incident_history_matches(matches[:1])
    return []


def incidents_for_ui_display(matches: list[IncidentHistoryMatch]) -> list[IncidentHistoryMatch]:
    """Chips shown in the UI — prefer injected context, else best similar match."""
    context = incidents_for_llm_context(matches)
    if context:
        return context
    return dedupe_incident_history_matches(matches)


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
    rows = [row for row in rows if row.feedback != -1]
    if not rows:
        return []

    keyword_matches = _keyword_incident_matches(log_text, rows, limit)

    if semantic_rag_enabled():
        try:
            semantic_matches = _semantic_incident_matches(log_text, rows, limit)
            if incidents_for_llm_context(semantic_matches):
                return semantic_matches
        except Exception:
            pass

    return keyword_matches


def format_incident_history_context(matches: list[IncidentHistoryMatch]) -> str:
    context_matches = incidents_for_llm_context(matches)
    if not context_matches:
        return ""

    return "\n\n---\n\n".join(
        f"Past incident #{match.incident_id} (match {int(match.score * 100)}%):\n{match.content}"
        for match in context_matches
    )
