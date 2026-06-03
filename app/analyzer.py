import json
from pathlib import Path

from app.ai import analyze_with_claude
from app.models import AnalysisResult, SourceCategory

INCIDENTS_DIR = Path(__file__).parent / "incidents"

KEYWORD_MAP: dict[str, list[str]] = {
    "redis-localhost-k8s.md": [
        "redis",
        "6379",
        "connection refused",
        "localhost",
        "crashloopbackoff",
    ],
    "image-pull-backoff.md": [
        "imagepullbackoff",
        "errimagepull",
        "failed to pull image",
        "manifest unknown",
    ],
    "ingress-503.md": [
        "503",
        "service unavailable",
        "ingress",
        "upstream",
    ],
    "terraform-state-lock.md": [
        "terraform",
        "state lock",
        "force-unlock",
        "acquiring the state lock",
    ],
    "github-actions-kubeconfig.md": [
        "github actions",
        "workflow",
        "kubeconfig",
        "unauthorized",
        "logged in to the server",
        "eks update-kubeconfig",
    ],
    "cert-manager-tls.md": [
        "cert-manager",
        "certificate",
        "letsencrypt",
        "tls",
        "x509",
        "challenge",
    ],
}

SOURCE_PATTERNS: list[tuple[SourceCategory, list[str]]] = [
    ("kubernetes", ["kubectl", "pod", "deployment", "crashloop", "namespace", "kube-"]),
    ("terraform", ["terraform", "provider.", "module.", "resource \""]),
    ("github_actions", ["github actions", "workflow", "runs-on:", "##[error]"]),
    ("docker", ["docker", "container", "dockerfile"]),
]


def _score_incident(filename: str, log_text: str) -> int:
    keywords = KEYWORD_MAP.get(filename, [])
    haystack = log_text.lower()
    return sum(1 for keyword in keywords if keyword in haystack)


def find_relevant_incidents(log_text: str, limit: int = 3) -> list[tuple[str, str]]:
    scored: list[tuple[int, str, str]] = []
    for path in INCIDENTS_DIR.glob("*.md"):
        score = _score_incident(path.name, log_text)
        if score > 0:
            scored.append((score, path.stem, path.read_text()))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [(name, content) for _, name, content in scored[:limit]]


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


def analyze_log(log_text: str, source_hint: SourceCategory | None = None) -> AnalysisResult:
    relevant = find_relevant_incidents(log_text)
    category = detect_source(log_text, source_hint)
    context_blocks = "\n\n---\n\n".join(
        f"Known incident: {name}\n{content}" for name, content in relevant
    )

    raw = analyze_with_claude(
        log_text=log_text.strip(),
        category=category,
        incident_context=context_blocks or "No closely matching saved incidents.",
    )

    result = AnalysisResult(**raw)
    result.similar_incidents = [name for name, _ in relevant]
    if result.category == "unknown" and category != "unknown":
        result.category = category
    return result


def result_to_json(result: AnalysisResult) -> str:
    return json.dumps(result.model_dump())
