import json

from prometheus_client import Counter

from app.ai import analyze_with_claude
from app.cache import (
    cache_key,
    get_cached_analysis,
    history_fingerprint,
    set_cached_analysis,
)
from app.models import AnalysisResult, PlaybookMatch, SourceCategory
from app.retrieval import find_relevant_playbooks, playbooks_for_llm_context

analysis_cache_hits = Counter(
    "debugpilot_analysis_cache_hits_total",
    "Analysis responses served from Redis cache",
)
analysis_cache_misses = Counter(
    "debugpilot_analysis_cache_misses_total",
    "Analysis responses that invoked Claude",
)

SOURCE_PATTERNS: list[tuple[SourceCategory, list[str]]] = [
    ("kubernetes", ["kubectl", "pod", "deployment", "crashloop", "namespace", "kube-"]),
    ("terraform", ["terraform", "provider.", "module.", "resource \""]),
    (
        "github_actions",
        [
            "github actions",
            "workflow",
            "runs-on:",
            "##[error]",
            "pytest",
            "test session starts",
            "failed [",
            "::test_",
        ],
    ),
    ("docker", ["docker", "container", "dockerfile"]),
]


def detect_source(log_text: str, source_hint: SourceCategory | None) -> SourceCategory:
    if source_hint and source_hint != "unknown":
        return source_hint

    haystack = log_text.lower()
    best_category: SourceCategory = "unknown"
    best_score = 0
    for category, patterns in SOURCE_PATTERNS:
        score = sum(1 for pattern in patterns if pattern in haystack)
        if score > best_score:
            best_score = score
            best_category = category

    if best_category != "unknown":
        return best_category

    if "crashloop" in haystack or "pod" in haystack:
        return "kubernetes"
    if "pytest" in haystack or "traceback" in haystack or "assert " in haystack:
        return "app"
    return "app"


def analyze_log(
    log_text: str,
    source_hint: SourceCategory | None = None,
    *,
    user_id: int | None = None,
    incident_history_context: str = "",
) -> tuple[AnalysisResult, bool]:
    # Include history in the cache key so a new confirmed fix / similar past
    # incident cannot serve a stale Claude answer for the same log text.
    key = cache_key(
        log_text,
        source_hint,
        user_id=user_id,
        history_fingerprint=history_fingerprint(incident_history_context),
    )
    cached_payload = get_cached_analysis(key)
    if cached_payload is not None:
        analysis_cache_hits.inc()
        return AnalysisResult(**cached_payload), True

    matches = find_relevant_playbooks(log_text)
    context_matches = playbooks_for_llm_context(matches)
    category = detect_source(log_text, source_hint)
    playbook_context = "\n\n---\n\n".join(
        f"Playbook: {match.name}\n{match.content}" for match in context_matches
    )

    raw = analyze_with_claude(
        log_text=log_text.strip(),
        category=category,
        playbook_context=playbook_context,
        incident_history_context=incident_history_context,
    )

    result = AnalysisResult(**raw)
    result.similar_incidents = [match.name for match in matches]
    result.playbook_matches = [
        PlaybookMatch(name=match.name, score=match.score, method=match.method)
        for match in matches
    ]
    if result.category == "unknown" and category != "unknown":
        result.category = category

    set_cached_analysis(key, result.model_dump())
    analysis_cache_misses.inc()
    return result, False


def result_to_json(result: AnalysisResult) -> str:
    return json.dumps(result.model_dump())
