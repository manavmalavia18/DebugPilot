import hashlib
import hmac
import logging
import os
from datetime import datetime, timezone

import httpx

from app.events.producer import publish_incident_event
from app.events.schema import IncidentEvent, build_github_external_id
logger = logging.getLogger(__name__)

_MAX_LOG_CHARS = 8000


def _webhook_secret() -> str:
    return os.getenv("GITHUB_WEBHOOK_SECRET", "").strip()


def _api_token() -> str:
    return os.getenv("GITHUB_WEBHOOK_TOKEN", "").strip()


def webhook_configured() -> bool:
    return bool(_webhook_secret() and _api_token())


def verify_github_signature(payload: bytes, signature_header: str | None) -> bool:
    secret = _webhook_secret()
    if not secret or not signature_header:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def _github_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _fetch_failed_job_logs(client: httpx.Client, owner: str, repo: str, run_id: int) -> str:
    jobs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
    jobs_resp = client.get(jobs_url, headers=_github_headers(), timeout=30)
    jobs_resp.raise_for_status()
    jobs = jobs_resp.json().get("jobs", [])
    failed_jobs = [job for job in jobs if job.get("conclusion") == "failure"]
    if not failed_jobs:
        failed_jobs = jobs[:1]

    chunks: list[str] = []
    for job in failed_jobs:
        job_id = job.get("id")
        if not job_id:
            continue
        logs_url = f"https://api.github.com/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
        logs_resp = client.get(logs_url, headers=_github_headers(), timeout=60)
        if logs_resp.status_code == 404:
            continue
        logs_resp.raise_for_status()
        name = job.get("name", "job")
        chunks.append(f"=== Job: {name} ===\n{logs_resp.text}")

    if not chunks:
        return f"Workflow run {run_id} failed but job logs were unavailable."

    combined = "\n\n".join(chunks)
    return combined[:_MAX_LOG_CHARS]


def build_incident_from_workflow_run(payload: dict) -> IncidentEvent | None:
    if payload.get("action") != "completed":
        return None

    run = payload.get("workflow_run") or {}
    if run.get("conclusion") != "failure":
        return None

    repo = payload.get("repository") or {}
    owner = (repo.get("owner") or {}).get("login", "")
    repo_name = repo.get("name", "")
    run_id = run.get("id")
    if not owner or not repo_name or not run_id:
        return None

    with httpx.Client(follow_redirects=True) as client:
        log_text = _fetch_failed_job_logs(client, owner, repo_name, run_id)

    actor_obj = run.get("actor") or {}
    actor = actor_obj.get("login")
    actor_github_id = actor_obj.get("id")
    metadata = {
        "repo": f"{owner}/{repo_name}",
        "commit": (run.get("head_commit") or {}).get("id"),
        "actor": actor,
        "actor_github_id": actor_github_id,
        "workflow_name": run.get("name"),
        "run_url": run.get("html_url"),
        "run_id": run_id,
        "event": run.get("event"),
        "branch": run.get("head_branch"),
    }

    return IncidentEvent(
        source="github_actions",
        external_id=build_github_external_id(owner, repo_name, run_id),
        log_text=log_text,
        source_hint="github_actions",
        metadata=metadata,
        received_at=datetime.now(timezone.utc),
    )


def handle_workflow_run_webhook(payload: dict) -> tuple[int, str]:
    if not webhook_configured():
        return 503, "GitHub webhook is not configured"

    event = build_incident_from_workflow_run(payload)
    if event is None:
        return 200, "ignored"

    published = publish_incident_event(event)
    if not published:
        return 503, "Kafka producer is not configured"

    logger.info("Queued GitHub workflow failure %s", event.external_id)
    return 202, "accepted"
