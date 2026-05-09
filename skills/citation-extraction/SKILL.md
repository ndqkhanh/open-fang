---
name: citation-extraction
description: "Extract the reference list from a paper's body text as structured citations."
origin: curated
---

## Overview

Given a paper's body text (or a bibliography/references section), return a
list of structured citations: `{authors, year, title, venue, arxiv_id}`.
Feeds the citation-graph edge extractor (v2 W2 workstream).

## When to Activate

Activate when:
- A paper has just been promoted to the KB and its outgoing citation edges
  must be populated.
- A user asks "what does this paper cite?" or "which referenced works are
  already in the KB?".

Do NOT activate for in-body inline citations of the form `(Xu et al., 2023)`
— those need a separate inline-citation-resolver skill (future).

## Concepts

- **Reference** — a single bibliography entry.
- **Identifier preference** — arxiv id > DOI > venue+year+title match.
- **BibTeX-aware** — when BibTeX is available, trust its field parse over
  free-text regex.

## Code Examples

```python
skill = registry.get("citation-extraction")
# The planner lists this skill when a 'resolve.citation' DAG node is queued.
```

## Anti-Patterns

- Inventing arxiv ids when none are present; return empty identifier fields.
- Splitting a single reference on commas inside author names.
- Treating footnotes as references.

## Best Practices

- Preserve the source span (character offset in the body) for provenance.
- Emit arxiv id in canonical form (strip `v1`/`v2` version suffixes) so the
  KB's `upsert_paper` dedupes correctly.
- Flag references with ambiguous identifiers for human review rather than
  silently dropping them.
