---
name: reproduction-script
description: "Convert a quantitative claim into a Python assertion that would check it against structured evidence."
origin: curated
---

## Overview

Produces `Vcode`-shape assertions (per arxiv:2604.18292) for executable
verification. Given a claim like "ReWOO reduces tokens fivefold" and
structured evidence like `{rewoo_tokens: 120, react_tokens: 600}`, emit a
Python assertion that checks the relationship.

## When to Activate

Activate when:
- A claim has quantitative content: percentages, counts, ratios, thresholds,
  units.
- Structured evidence is available (LaTeX tables, benchmark numbers in
  abstracts, named counts).

Do NOT activate for:
- Purely qualitative claims.
- Claims without identifiable structured evidence to check against.

## Concepts

- **Assertion script** — a small Python expression that raises on mismatch.
- **Sandboxed execution** — runs in a subprocess with no network, 2s
  timeout, memory cap; see W3 executable-verifier design.
- **Tolerance** — quantitative claims often carry implicit tolerance ("~5×"
  means 4×–6×). The assertion should encode this.

## Code Examples

```python
# Input claim:    "ReWOO reduces tokens ~fivefold relative to ReAct."
# Input evidence: {"rewoo_tokens": 120, "react_tokens": 600}
# Output script:
assert 4.0 <= (evidence['react_tokens'] / evidence['rewoo_tokens']) <= 6.0, \
    "ratio mismatch"
```

## Anti-Patterns

- Asserting exact equality when the claim carries implicit tolerance.
- Generating scripts that call `os.system` or touch the filesystem — the
  sandbox will reject them but the assertion itself should be data-only.
- Over-fitting the assertion to one evidence record; generalize over the set.

## Best Practices

- Keep the assertion one or two lines; longer scripts are harder to audit.
- Always include an error message so the verifier can log *why* a claim was
  rejected.
- When the claim is ambiguous, produce an assertion that tests the weakest
  reasonable interpretation — the verifier should fail closed.
