---
name: peer-review
description: "Produce a structured critique of a finished research report."
origin: curated
---

## Overview

The end-of-pipeline pass that yields a peer-review-style critique of a
finished `Report`. Used by the CriticAgent and by v2's Diagnostician to
surface weaknesses that feed back into the evolving arena loop.

## When to Activate

Activate when:
- A report has passed verification but the user requests a meta-review.
- The Diagnostician is building a failure-trace bundle for the arena loop.
- A report's faithfulness ratio is close to the 0.90 floor — margin runs
  benefit from an external critique pass.

Do NOT activate for:
- Individual claim verification (use `claim-localization` + verifier tiers).
- Citation-graph checks (use `citation-extraction` + edge extractor).

## Concepts

- **Review axes**: novelty, method soundness, claim-evidence binding,
  external validity, threats to validity, missed related work.
- **Structured critique** — JSON-shaped output with one entry per axis:
  `{axis, rating, rationale, cited_span}`.
- **Constructive bias** — a good review offers a specific remediation, not
  just a complaint.

## Code Examples

```python
critique = peer_review.critique(report)
# critique is a list of {axis, rating, rationale, cited_span} records.
```

## Anti-Patterns

- Free-form prose without axis labels — hard to aggregate across reports.
- Rating without a cited span — costs the Diagnostician a second pass.
- Recommending generic improvements ("be more rigorous"); specify a
  concrete missing paper or missing numerical check.

## Best Practices

- Cap critiques at 6 axes per report; more is noise.
- Feed critiques back into `~/.openfang/skills/learned/` when the same
  failure pattern recurs across reports — this is the seed of the evolving
  arena skill library.
- Always include one *positive* axis; it's a signal that helps the
  Diagnostician distinguish patterns worth keeping from patterns to fix.
