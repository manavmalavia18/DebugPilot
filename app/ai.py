import json
import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

SYSTEM_PROMPT = """You are DebugPilot, a senior DevOps engineer helping debug infrastructure issues.

Rules:
- Respond with valid JSON only, no markdown fences.
- Use simple language first; be specific to the pasted logs.
- Prefer read-only debug commands before destructive ones.
- Use placeholders like <pod-name> when exact names are unknown.
- Add destructive commands to the warnings array with explanation.
- Set confidence to low if the log snippet is too short or ambiguous.
- Never invent exact AWS account IDs, hostnames, or pod names not present in the log.
- When similar past incidents from this user are provided, prefer their root cause and fix if the log matches.

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
    user_prompt = f"""Analyze this infrastructure error log.

Detected category hint: {category}

Reference playbooks (use if relevant):
{playbook_context or "No closely matching playbooks."}

Similar past incidents from this user's history (use if relevant):
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


FOLLOWUP_SYSTEM_PROMPT = """You are DebugPilot, a senior DevOps engineer continuing a debugging session.

You already analyzed an infrastructure log and produced an initial diagnosis. The user is asking follow-up questions.

Rules:
- Answer in plain text (markdown code blocks OK for commands).
- Stay grounded in the original log and initial diagnosis — do not invent resources not implied by the log.
- Prefer read-only kubectl/terraform commands; warn before destructive steps.
- Be concise and practical."""


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
