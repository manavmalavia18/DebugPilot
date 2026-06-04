import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sqlmodel import Session, select

from app.analyzer import analyze_log
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
    SavedIncident,
    SavedIncidentRead,
    User,
    UserRead,
)

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
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
    return {"status": "ok", "service": "debugpilot", "auth_enabled": auth_enabled()}


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


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(
    request: AnalyzeRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    started = time.perf_counter()
    try:
        result, cached = analyze_log(request.log_text, request.source_hint)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {exc}") from exc

    duration_ms = round((time.perf_counter() - started) * 1000, 1)

    if request.save:
        saved = SavedIncident(
            user_id=user.id,
            log_text=request.log_text[:8000],
            category=result.category,
            symptom=result.symptom,
            root_cause=result.root_cause,
            likely_fix=result.likely_fix,
            confidence=result.confidence,
            response_json=json.dumps(result.model_dump()),
        )
        session.add(saved)
        session.commit()

    return AnalyzeResponse(
        **result.model_dump(),
        cached=cached,
        duration_ms=duration_ms,
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
            )
        ):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(FRONTEND_DIST / "index.html")
