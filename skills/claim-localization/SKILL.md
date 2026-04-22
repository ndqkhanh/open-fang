---
name: claim-localization
description: "Find the exact sentence in evidence that supports a specific claim."
origin: curated
---

## Overview

Given a claim and one or more evidence snippets, return the single sentence
(or short span) from the evidence that most directly supports the claim.
Used by `ClaimVerifier` and `CriticAgent` to anchor verification in a
quotable span.

## When to Activate

Activate when:
- A claim must be verified against a cited evidence chunk.
- The synthesis writer has produced a claim and needs a span-level citation.
- A reader asks "where exactly does the paper say this?".

Do NOT activate for multi-sentence synthesis or abstract summarization.

## Concepts

- **Span** — a contiguous character range, not a paraphrase.
- **Anchor** — the shortest span that entails the claim.
- **Negative cases** — if no sentence entails the claim, return empty span
  rather than a near-match. Over-matching erodes the verifier signal.

## Code Examples

```python
from open_fang.skills import SkillRegistry

registry = SkillRegistry.from_loader(SkillLoader())
skill = registry.get("claim-localization")
# Pass skill.when_to_activate + skill.overview into the LLM judge prompt.
```

## Anti-Patterns

- Returning a full paragraph when one sentence suffices.
- Paraphrasing the evidence to match the claim's wording.
- Falling back to lexical overlap when the claim is not actually supported.

## Best Practices

- Prefer short spans; verifier downstream tests can quote them.
- Always include the sentence boundary characters so the span is quotable
  verbatim.
- Return empty when nothing matches; the verifier prefers a known unknown
  over a fabricated anchor.
