import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

INCIDENTS_DIR = Path(__file__).parent / "incidents"
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.35"))
RETRIEVAL_CONTEXT_MIN_SCORE = float(os.getenv("RETRIEVAL_CONTEXT_MIN_SCORE", "0.70"))
LOG_EMBED_MAX_CHARS = int(os.getenv("LOG_EMBED_MAX_CHARS", "4000"))

KEYWORD_MAP: dict[str, list[str]] = {
    "redis-localhost-k8s.md": [
        "redis",
        "6379",
        "connection refused",
        "localhost",
        "crashloopbackoff",
        "cache",
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
    "external-dns-stale-cname.md": [
        "external-dns",
        "cname",
        "dns",
        "cloudflare",
        "stale",
    ],
}


@dataclass(frozen=True)
class PlaybookMatch:
    name: str
    content: str
    score: float
    method: str  # "semantic" | "keyword"


def semantic_rag_enabled() -> bool:
    return os.getenv("SEMANTIC_RAG_DISABLED", "").lower() not in ("1", "true", "yes")


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


@lru_cache(maxsize=1)
def _embedding_model():
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=EMBEDDING_MODEL)


def _embed_text(text: str) -> list[float]:
    model = _embedding_model()
    chunks = list(model.embed([text]))
    if not chunks:
        return []
    return chunks[0].tolist()


@lru_cache(maxsize=1)
def _playbook_vectors() -> tuple[tuple[str, str, tuple[float, ...]], ...]:
    rows: list[tuple[str, str, tuple[float, ...]]] = []
    for path in sorted(INCIDENTS_DIR.glob("*.md")):
        content = path.read_text()
        vector = tuple(_embed_text(content))
        rows.append((path.stem, content, vector))
    return tuple(rows)


def warmup_playbook_index() -> None:
    """Pre-load embedding model and playbook vectors (e.g. Docker build or app startup)."""
    if not semantic_rag_enabled():
        return
    _playbook_vectors()


def _keyword_matches(log_text: str, limit: int) -> list[PlaybookMatch]:
    haystack = log_text.lower()
    scored: list[tuple[int, str, str]] = []
    for path in INCIDENTS_DIR.glob("*.md"):
        keywords = KEYWORD_MAP.get(path.name, [])
        score = sum(1 for keyword in keywords if keyword in haystack)
        if score > 0:
            scored.append((score, path.stem, path.read_text()))
    scored.sort(key=lambda item: item[0], reverse=True)
    if not scored:
        return []
    top_score = scored[0][0]
    return [
        PlaybookMatch(
            name=name,
            content=content,
            score=round(min(1.0, value / max(top_score, 1)), 3),
            method="keyword",
        )
        for value, name, content in scored[:limit]
    ]


def _semantic_matches(log_text: str, limit: int) -> list[PlaybookMatch]:
    log_vector = _embed_text(log_text[:LOG_EMBED_MAX_CHARS])
    if not log_vector:
        return []

    scored: list[PlaybookMatch] = []
    for name, content, vector in _playbook_vectors():
        score = _cosine_similarity(log_vector, list(vector))
        if score >= RETRIEVAL_MIN_SCORE:
            scored.append(
                PlaybookMatch(name=name, content=content, score=round(score, 3), method="semantic")
            )

    scored.sort(key=lambda item: item.score, reverse=True)
    if scored:
        return scored[:limit]

    best_name, best_content, best_vector = max(
        _playbook_vectors(),
        key=lambda row: _cosine_similarity(log_vector, list(row[2])),
    )
    best_score = round(_cosine_similarity(log_vector, list(best_vector)), 3)
    if best_score >= RETRIEVAL_MIN_SCORE * 0.75:
        return [
            PlaybookMatch(
                name=best_name,
                content=best_content,
                score=best_score,
                method="semantic",
            )
        ]
    return []


def playbooks_for_llm_context(matches: list[PlaybookMatch]) -> list[PlaybookMatch]:
    """Only strong semantic matches are injected into the Claude prompt."""
    if not matches:
        return []
    strong = [match for match in matches if match.score >= RETRIEVAL_CONTEXT_MIN_SCORE]
    if strong:
        return strong
    if matches[0].method == "keyword":
        return matches
    return []


def find_relevant_playbooks(log_text: str, limit: int = 3) -> list[PlaybookMatch]:
    if not log_text.strip():
        return []

    if semantic_rag_enabled():
        try:
            matches = _semantic_matches(log_text, limit)
            if matches:
                return matches
        except Exception:
            pass

    return _keyword_matches(log_text, limit)
