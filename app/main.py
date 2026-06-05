import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sqlmodel import Session, select

from app.ai import follow_up_with_claude
from app.analyzer import analyze_log
from app.incident_retrieval import (
    find_similar_saved_incidents,
    format_incident_history_context,
    incidents_for_llm_context,
)
from app.auth import (
    OAUTH_STATE_COOKIE,
    build_github_login_redirect,
    clear_session_cookie,
    create_session_token,
    exchange_github_code,
    set_session_cookie,
    upsert_user_from_github,
    verify_oauth_state,
)
from app.auth_settings import auth_enabled
from app.database import create_db_and_tables, get_session
from app.deps import get_current_user
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisResult,
    ChatMessageRead,
    ChatRequest,
    ChatResponse,
    IncidentChatMessage,
    IncidentHistoryMatchRead,
    LogUpload,
    SavedIncident,
    SavedIncidentRead,
    UploadResponse,
    User,
    UserRead,
)
from app.storage import (
    build_storage_key,
    decode_log_bytes,
    get_object_bytes,
    put_object,
    storage_backend,
    validate_upload,
)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    from app.retrieval import warmup_playbook_index

    warmup_playbook_index()
    yield


app = FastAPI(
    title="DebugPilot",
    description="AI-powered DevOps incident debugger",
    version="0.1.0",
    lifespan=lifespan,
)
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "service": "debugpilot",
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
        "ui": "http://localhost:5173",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "debugpilot",
        "auth_enabled": auth_enabled(),
        "uploads_backend": storage_backend(),
    }


@app.get("/auth/config")
def auth_config():
    return {
        "auth_enabled": auth_enabled(),
        "login_url": "/auth/github/login" if auth_enabled() else None,
    }


@app.get("/auth/me", response_model=UserRead)
def auth_me(user: User = Depends(get_current_user)):
    return UserRead(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
    )


@app.get("/auth/github/login")
def auth_github_login():
    response = RedirectResponse(url="", status_code=302)
    response.headers["Location"] = build_github_login_redirect(response)
    return response


@app.get("/auth/github/callback")
def auth_github_callback(
    request: Request,
    code: str = "",
    state: str = "",
    session: Session = Depends(get_session),
):
    if not code:
        return RedirectResponse(url="/?auth_error=missing_code", status_code=302)
    verify_oauth_state(request, state)
    profile = exchange_github_code(code)
    user = upsert_user_from_github(session, profile)
    token = create_session_token(user.id)
    response = RedirectResponse(url="/", status_code=302)
    set_session_cookie(response, token)
    response.delete_cookie(OAUTH_STATE_COOKIE)
    return response


@app.post("/auth/logout")
def auth_logout():
    response = Response(status_code=204)
    clear_session_cookie(response)
    return response


def _load_upload_log_text(session: Session, user: User, upload_id: int) -> tuple[str, LogUpload]:
    row = session.get(LogUpload, upload_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Upload not found")
    try:
        raw = get_object_bytes(row.storage_key)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to read upload: {exc}") from exc
    text = decode_log_bytes(raw)
    if not text:
        raise HTTPException(status_code=400, detail="Upload file has no readable log text")
    return text, row


@app.post("/uploads", response_model=UploadResponse)
async def upload_log_file(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    data = await file.read()
    filename = file.filename or "upload.log"
    try:
        validate_upload(filename, len(data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    log_text = decode_log_bytes(data)
    if not log_text:
        raise HTTPException(status_code=400, detail="File has no readable log text")

    storage_key = build_storage_key(user.id, filename)
    try:
        put_object(storage_key, data, file.content_type or "text/plain")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Upload storage failed: {exc}") from exc

    record = LogUpload(
        user_id=user.id,
        filename=filename,
        storage_key=storage_key,
        size_bytes=len(data),
        content_type=file.content_type or "text/plain",
    )
    session.add(record)
    session.commit()
    session.refresh(record)

    return UploadResponse(
        id=record.id,
        filename=record.filename,
        size_bytes=record.size_bytes,
        storage_backend=storage_backend(),
        log_text=log_text[:8000],
    )


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: AnalyzeRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    upload_row: LogUpload | None = None
    log_text = request.resolved_log_text()

    if request.upload_id:
        log_text, upload_row = _load_upload_log_text(session, user, request.upload_id)

    if not log_text:
        raise HTTPException(status_code=400, detail="log_text or upload_id is required")

    history_matches = find_similar_saved_incidents(session, user.id, log_text)
    context_matches = incidents_for_llm_context(history_matches)
    history_context = format_incident_history_context(history_matches)

    try:
        result, cached = analyze_log(
            log_text,
            request.source_hint,
            user_id=user.id,
            incident_history_context=history_context,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {exc}") from exc

    duration_ms = round((time.perf_counter() - started) * 1000, 1)

    incident_id: int | None = None
    if request.save:
        saved = SavedIncident(
            user_id=user.id,
            upload_id=upload_row.id if upload_row else request.upload_id,
            source_filename=upload_row.filename if upload_row else None,
            log_text=log_text[:8000],
            category=result.category,
            symptom=result.symptom,
            root_cause=result.root_cause,
            likely_fix=result.likely_fix,
            confidence=result.confidence,
            response_json=json.dumps(result.model_dump()),
        )
        session.add(saved)
        session.commit()
        session.refresh(saved)
        incident_id = saved.id

    return AnalyzeResponse(
        **result.model_dump(),
        cached=cached,
        duration_ms=duration_ms,
        incident_id=incident_id,
        incident_history_matches=[
            IncidentHistoryMatchRead(
                incident_id=match.incident_id,
                score=match.score,
                method=match.method,
                symptom=match.symptom,
            )
            for match in context_matches
        ],
    )


@app.get("/incidents", response_model=List[SavedIncidentRead])
def list_incidents(
    limit: int = 20,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    query = (
        select(SavedIncident)
        .where(SavedIncident.user_id == user.id)
        .order_by(SavedIncident.created_at.desc())
        .limit(limit)
    )
    rows = session.exec(query).all()
    return [
        SavedIncidentRead(
            id=row.id,
            created_at=row.created_at,
            category=row.category,
            symptom=row.symptom,
            root_cause=row.root_cause,
            likely_fix=row.likely_fix,
            confidence=row.confidence,
            source_filename=row.source_filename,
        )
        for row in rows
    ]


@app.get("/incidents/{incident_id}", response_model=AnalysisResult)
def get_incident(
    incident_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    row = session.get(SavedIncident, incident_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Incident not found")
    return AnalysisResult(**json.loads(row.response_json))


def _get_user_incident(
    session: Session, user: User, incident_id: int
) -> SavedIncident:
    row = session.get(SavedIncident, incident_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Incident not found")
    return row


@app.get("/incidents/{incident_id}/messages", response_model=List[ChatMessageRead])
def list_incident_messages(
    incident_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    _get_user_incident(session, user, incident_id)
    query = (
        select(IncidentChatMessage)
        .where(IncidentChatMessage.incident_id == incident_id)
        .order_by(IncidentChatMessage.created_at.asc())
    )
    rows = session.exec(query).all()
    return [
        ChatMessageRead(
            id=row.id,
            role=row.role,
            content=row.content,
            created_at=row.created_at,
        )
        for row in rows
    ]


@app.post("/incidents/{incident_id}/chat", response_model=ChatResponse)
def incident_chat(
    incident_id: int,
    request: ChatRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    incident = _get_user_incident(session, user, incident_id)
    prior_rows = session.exec(
        select(IncidentChatMessage)
        .where(IncidentChatMessage.incident_id == incident_id)
        .order_by(IncidentChatMessage.created_at.asc())
    ).all()
    history = [(row.role, row.content) for row in prior_rows]
    diagnosis = json.loads(incident.response_json)

    try:
        reply = follow_up_with_claude(
            log_text=incident.log_text,
            diagnosis=diagnosis,
            history=history,
            user_message=request.message.strip(),
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Chat failed: {exc}") from exc

    user_row = IncidentChatMessage(
        incident_id=incident_id,
        user_id=user.id,
        role="user",
        content=request.message.strip(),
    )
    assistant_row = IncidentChatMessage(
        incident_id=incident_id,
        user_id=user.id,
        role="assistant",
        content=reply,
    )
    session.add(user_row)
    session.add(assistant_row)
    session.commit()
    session.refresh(assistant_row)

    return ChatResponse(
        reply=reply,
        message=ChatMessageRead(
            id=assistant_row.id,
            role="assistant",
            content=assistant_row.content,
            created_at=assistant_row.created_at,
        ),
    )


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith(
            (
                "analyze",
                "incidents",
                "health",
                "metrics",
                "docs",
                "openapi.json",
                "redoc",
                "auth",
                "uploads",
            )
        ):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(FRONTEND_DIST / "index.html")
