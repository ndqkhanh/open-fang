"""Entity expansion for papers (v8.2).

Extract authors, affiliations, technique-names, and benchmark-names from
paper content. Each becomes a first-class entity in its own table; papers
link to entities via typed edges (`authored_by`, `affiliated_with`,
`uses_technique`, `evaluates_on`).

Deterministic regex + seeded name lists. No LLM calls.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Seeded technique names — growable via the v6.5 self-research loop.
_SEED_TECHNIQUES: tuple[str, ...] = (
    "ReWOO", "ReAct", "Reflexion", "Voyager", "Plan-and-Solve",
    "Tree of Thoughts", "LATS", "Chain-of-Thought", "Self-Refine",
    "CoT", "ToT", "RAG", "Agentic RAG", "MetaGPT", "AutoGen",
    "Claude", "GPT-4", "GPT-4o", "Gemini", "Llama", "Mistral",
)

# Seeded benchmark names.
_SEED_BENCHMARKS: tuple[str, ...] = (
    "SWE-bench", "SWEBench-Verified", "BFCL", "τ²-Bench", "tau2-Bench",
    "GAIA", "HLE", "MCP-Mark", "Terminal-Bench", "SEC-Bench",
    "OlympiadBench", "AIME24", "AIME25", "HumanEval", "MBPP",
    "MMLU", "ARC-AGI",
)

# Affiliation name hint: words following "@" or "({University|Institute|Corp})"
_AFFIL_RE = re.compile(
    r"\b(University\s+of\s+[\w\-]+|MIT|Stanford|Berkeley|Oxford|Cambridge|"
    r"CMU|Princeton|ETH|Anthropic|OpenAI|Google|DeepMind|Meta|Microsoft|"
    r"Cohere|Nous\s*Research|Hugging\s*Face|Midea)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Entity:
    kind: str  # "author" | "affiliation" | "technique" | "benchmark"
    name: str
    canonical: str


@dataclass(frozen=True)
class EntityEdge:
    src_paper_id: str
    entity_kind: str
    entity_canonical: str
    link_kind: str

    def to_row(self) -> tuple[str, str, str, str]:
        return (self.src_paper_id, self.entity_kind, self.entity_canonical, self.link_kind)


def canonicalize(name: str) -> str:
    """Lowercase, strip non-alphanumeric, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s\-]", "", name)).strip().lower()


def _extract_pattern(content: str, candidates: tuple[str, ...]) -> list[str]:
    """Return candidates that appear as whole-word matches in `content`."""
    found: list[str] = []
    seen: set[str] = set()
    for cand in candidates:
        pattern = re.compile(rf"\b{re.escape(cand)}\b", re.IGNORECASE)
        if pattern.search(content or ""):
            key = canonicalize(cand)
            if key in seen:
                continue
            seen.add(key)
            found.append(cand)
    return found


def extract_techniques(content: str, *, extra: tuple[str, ...] = ()) -> list[Entity]:
    names = _extract_pattern(content, _SEED_TECHNIQUES + extra)
    return [Entity(kind="technique", name=n, canonical=canonicalize(n)) for n in names]


def extract_benchmarks(content: str, *, extra: tuple[str, ...] = ()) -> list[Entity]:
    names = _extract_pattern(content, _SEED_BENCHMARKS + extra)
    return [Entity(kind="benchmark", name=n, canonical=canonicalize(n)) for n in names]


def extract_affiliations(content: str) -> list[Entity]:
    found: list[Entity] = []
    seen: set[str] = set()
    for match in _AFFIL_RE.finditer(content or ""):
        name = match.group(1).strip()
        key = canonicalize(name)
        if key in seen:
            continue
        seen.add(key)
        found.append(Entity(kind="affiliation", name=name, canonical=key))
    return found


def extract_authors(authors_csv: str) -> list[Entity]:
    """Authors come structured on the paper row; we just canonicalize them."""
    if not authors_csv:
        return []
    out: list[Entity] = []
    seen: set[str] = set()
    for raw in authors_csv.split(","):
        name = raw.strip()
        if not name:
            continue
        key = canonicalize(name)
        if key in seen:
            continue
        seen.add(key)
        out.append(Entity(kind="author", name=name, canonical=key))
    return out


def extract_all(
    paper_id: str,
    *,
    content: str,
    authors_csv: str = "",
    extra_techniques: tuple[str, ...] = (),
    extra_benchmarks: tuple[str, ...] = (),
) -> tuple[list[Entity], list[EntityEdge]]:
    entities: list[Entity] = []
    entities.extend(extract_authors(authors_csv))
    entities.extend(extract_affiliations(content))
    entities.extend(extract_techniques(content, extra=extra_techniques))
    entities.extend(extract_benchmarks(content, extra=extra_benchmarks))

    link_map = {
        "author": "authored_by",
        "affiliation": "affiliated_with",
        "technique": "uses_technique",
        "benchmark": "evaluates_on",
    }
    edges = [
        EntityEdge(
            src_paper_id=paper_id,
            entity_kind=e.kind,
            entity_canonical=e.canonical,
            link_kind=link_map[e.kind],
        )
        for e in entities
    ]
    return entities, edges
