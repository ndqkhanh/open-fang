---
name: counter-example-generation
description: "Given a claim and evidence, produce a plausible counter-claim the LLM judge should reject."
origin: curated
---

## Overview

Used by the mutation-robust verifier tier (W3 in v2-plan.md) to test whether
the LLM judge actually reads the evidence. For a supported claim, produce
3-5 plausible mutations (swap numbers, flip signs, change units, reverse
quantifiers). The judge must flag all mutants as `not_supported` while
keeping the original `supported`.

## When to Activate

Activate when:
- A claim has passed the lexical-overlap pre-filter and is about to be LLM-
  judged.
- The claim contains numeric, quantitative, or comparative content.

Do NOT activate for:
- Obviously qualitative claims with no number or comparison.
- Claims the lexical filter has already rejected.

## Concepts

- **Mutation** — a minimally-changed version of the claim that should
  logically flip the verdict.
- **Distinguishable** — a good mutation set is one the judge can
  distinguish; if the judge passes mutants too, the signal is degraded.
- **Mutation classes**: digit-swap, sign-flip, unit-swap, quantifier-reverse.

## Code Examples

```python
mutants = counter_example_skill.mutate(
    claim="ReWOO reduces token usage fivefold relative to ReAct.",
    classes=["digit-swap", "sign-flip", "quantifier-reverse"],
)
# Expected: 'tenfold', 'increases', 'never reduces' etc.
```

## Anti-Patterns

- Mutating to something trivially unrelated ("the sky is blue") — too easy
  to reject; produces no signal.
- Mutating claims where the evidence itself is ambiguous; apply to
  high-confidence claims only.

## Best Practices

- Generate 3-5 mutants per claim; fewer weakens signal, more wastes tokens.
- Always include one near-miss mutant (single-word change) to stress-test.
- Record which mutant class fooled the judge — feeds back into the
  red-team corpus (W4).
