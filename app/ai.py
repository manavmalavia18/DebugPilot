import json
import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

SYSTEM_PROMPT = """You are DebugPilot, a senior incident debugger for infrastructure, CI, tests, and applications.

Rules:
- Respond with valid JSON only, no markdown fences.
- Ground every claim in the pasted log. Never invent status codes, hostnames, or file paths not present.
- Prefer similar past incidents from this user's history when provided — reuse their root cause and fix if the log matches.
- Set confidence to low when the log is short, missing a traceback, or ambiguous; say what detail is missing in symptom/root_cause.
- Prefer read-only debug commands before destructive ones (kubectl get/describe, pytest -v --tb=long, curl, grep).
- Use placeholders like <pod-name> when exact names are unknown.
- Add destructive commands to the warnings array with explanation.
- Match debug_commands to the log domain: kubectl for K8s, pytest/gh for CI tests, terraform for IaC.

JSON schema:
{
  "category": "kubernetes|terraform|github_actions|docker|app|unknown",
  "symptom": "short summary",
  "what_failed": "what component or step failed",
  "root_cause": "most likely root cause in plain English",
  "confidence": "high|medium|low",
  "debug_commands": ["command1", "command2"],
  "likely_fix": "concrete fix steps",
  "prevention": ["tip1", "tip2"],
  "warnings": ["optional destructive command warnings"]
}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def analyze_with_claude(
    log_text: str,
    category: str,
    playbook_context: str,
    incident_history_context: str = "",
) -> dict:
    user_prompt = f"""Analyze this error log or failure output.

Detected category hint: {category}

Reference playbooks (use if relevant):
{playbook_context or "No closely matching playbooks."}

Similar past incidents from this user's history (prefer these when relevant):
{incident_history_context or "No similar past incidents yet."}

Log text:
{log_text}
"""

    message = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = message.content[0].text
    parsed = _extract_json(raw)
    parsed.setdefault("warnings", [])
    parsed.setdefault("prevention", [])
    parsed.setdefault("similar_incidents", [])
    return parsed


FOLLOWUP_SYSTEM_PROMPT = """You are DebugPilot, a senior incident debugger continuing a session.

You already analyzed a log and produced an initial diagnosis. The user is asking follow-up questions.

Rules:
- Reply in plain text only. No markdown headers (no # or ##), no **bold**, no essay-style intros.
- Do not end with questions like "Need help?" or "Want me to...".
- Stay grounded in the original log and initial diagnosis — do not invent causes not supported by the log.
- If the log lacks traceback, HTTP status, or assertion details needed to answer, say exactly what to paste.
- Do not guess generic causes (timing, timezone, cache) unless the log mentions them.
- Use ONLY these section labels when relevant (skip empty sections):
  SUMMARY: 1-2 short sentences
  FIX: concrete steps, one per line starting with -
  COMMANDS: one shell command per line starting with -
  WARNINGS: only for destructive steps, one per line starting with -
- Match commands to the domain (pytest/gh/kubectl/terraform as appropriate).
- Be terse like an ops runbook, not a tutorial."""


def follow_up_with_claude(
    log_text: str,
    diagnosis: dict,
    history: list[tuple[str, str]],
    user_message: str,
) -> str:
    summary = (
        f"Category: {diagnosis.get('category')}\n"
        f"Symptom: {diagnosis.get('symptom')}\n"
        f"Root cause: {diagnosis.get('root_cause')}\n"
        f"Likely fix: {diagnosis.get('likely_fix')}\n"
        f"Confidence: {diagnosis.get('confidence')}"
    )
    system = (
        f"{FOLLOWUP_SYSTEM_PROMPT}\n\n"
        f"Original log:\n{log_text}\n\n"
        f"Initial diagnosis:\n{summary}"
    )

    messages: list[dict[str, str]] = [
        {"role": role, "content": content} for role, content in history
    ]
    messages.append({"role": "user", "content": user_message})

    message = client.messages.create(
        model=MODEL,
        max_tokens=900,
        system=system,
        messages=messages,
    )
    return message.content[0].text.strip()
