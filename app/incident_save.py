import json

from sqlmodel import Session, select

from app.analyzer import analyze_log
from app.events.schema import IncidentEvent
from app.incident_retrieval import (
    find_similar_saved_incidents,
    format_incident_history_context,
)
from app.models import SavedIncident


def find_existing_incident(
    session: Session, user_id: int, external_id: str
) -> SavedIncident | None:
    return session.exec(
        select(SavedIncident).where(
            SavedIncident.user_id == user_id,
            SavedIncident.external_id == external_id,
        )
    ).first()


def save_analyzed_incident(
    session: Session,
    *,
    user_id: int,
    log_text: str,
    source_hint,
    ingestion_source: str,
    external_id: str | None = None,
    event_metadata: dict | None = None,
    upload_id: int | None = None,
    source_filename: str | None = None,
) -> SavedIncident:
    history_matches = find_similar_saved_incidents(session, user_id, log_text)
    history_context = format_incident_history_context(history_matches)
    result, _cached = analyze_log(
        log_text,
        source_hint,
        user_id=user_id,
        incident_history_context=history_context,
    )
    saved = SavedIncident(
        user_id=user_id,
        upload_id=upload_id,
        source_filename=source_filename,
        log_text=log_text[:8000],
        category=result.category,
        symptom=result.symptom,
        root_cause=result.root_cause,
        likely_fix=result.likely_fix,
        confidence=result.confidence,
        response_json=json.dumps(result.model_dump()),
        ingestion_source=ingestion_source,
        external_id=external_id,
        event_metadata_json=json.dumps(event_metadata or {}),
    )
    session.add(saved)
    session.commit()
    session.refresh(saved)
    return saved


def process_incident_event(session: Session, event: IncidentEvent, user_id: int) -> SavedIncident | None:
    if event.external_id:
        existing = find_existing_incident(session, user_id, event.external_id)
        if existing:
            return existing

    return save_analyzed_incident(
        session,
        user_id=user_id,
        log_text=event.log_text,
        source_hint=event.source_hint,
        ingestion_source=event.source,
        external_id=event.external_id,
        event_metadata=event.metadata,
        source_filename=event.metadata.get("workflow_name"),
    )
