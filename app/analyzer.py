import json

from prometheus_client import Counter

from app.ai import analyze_with_claude
from app.cache import cache_key, get_cached_analysis, set_cached_analysis
from app.models import AnalysisResult, PlaybookMatch, SourceCategory
from app.retrieval import find_relevant_playbooks

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
    ("github_actions", ["github actions", "workflow", "runs-on:", "##[error]"]),
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
    return "app"


def analyze_log(log_text: str, source_hint: SourceCategory | None = None) -> tuple[AnalysisResult, bool]:
    key = cache_key(log_text, source_hint)
    cached_payload = get_cached_analysis(key)
    if cached_payload is not None:
        analysis_cache_hits.inc()
        return AnalysisResult(**cached_payload), True

    matches = find_relevant_playbooks(log_text)
    category = detect_source(log_text, source_hint)
    context_blocks = "\n\n---\n\n".join(
        f"Known incident: {match.name}\n{match.content}" for match in matches
    )

    raw = analyze_with_claude(
        log_text=log_text.strip(),
        category=category,
        incident_context=context_blocks or "No closely matching saved incidents.",
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
