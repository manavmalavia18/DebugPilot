import json
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sqlmodel import Session, select

from app.analyzer import analyze_log
from app.database import create_db_and_tables, get_session
from app.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisResult,
    SavedIncident,
    SavedIncidentRead,
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
    return {"status": "ok", "service": "debugpilot"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, session: Session = Depends(get_session)):
    started = time.perf_counter()
    try:
        result, cached = analyze_log(request.log_text, request.source_hint)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Analysis failed: {exc}") from exc

    duration_ms = round((time.perf_counter() - started) * 1000, 1)

    if request.save:
        saved = SavedIncident(
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
):
    query = select(SavedIncident).order_by(SavedIncident.created_at.desc()).limit(limit)
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
def get_incident(incident_id: int, session: Session = Depends(get_session)):
    row = session.get(SavedIncident, incident_id)
    if not row:
        raise HTTPException(status_code=404, detail="Incident not found")
    return AnalysisResult(**json.loads(row.response_json))


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend(full_path: str):
        if full_path.startswith(
            ("analyze", "incidents", "health", "metrics", "docs", "openapi.json", "redoc")
        ):
            raise HTTPException(status_code=404, detail="Not found")
        return FileResponse(FRONTEND_DIST / "index.html")
