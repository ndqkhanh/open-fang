# 08 — ClaimVerifier

## Purpose

Multi-tier gate that turns every claim in a report into either
`verified=True` or `verified=False` with a `verification_note` explaining
the rejection. Sets `report.faithfulness_ratio = verified / total`.

## Tiers

Run in order; later tiers only execute when earlier ones don't reject.

### Tier 1 — Lexical (free, always on)

- Every `evidence_id` must resolve.
- Claim text must share ≥1 non-stopword token (length > 3) with the cited
  evidence content.
- Rejection here short-circuits the LLM judge — so the dominant cost is the
  LLM only when something actually looks plausible.

### Tier 2 — LLM judge (optional)

Contract (strict JSON from the LLM):
```json
{"verdict": "supported" | "not_supported", "span": "<short quoted span>"}
```

Non-JSON replies fall back to phrase-matching (case-insensitive `"supported"`
without `"not_supported"`). See [llm_judge.py](../../src/open_fang/verify/llm_judge.py).

### Tier 3 — Cross-channel metadata (not a gate)

Sets `claim.cross_channel_confirmed = True` when ≥2 distinct evidence
channels (`abstract` / `body` / `table` / `figure-caption`) back the claim.
Displayed in the report but doesn't block the verified flag.

## Optional post-pass — CriticAgent

`verify/critic.py` rephrases each verified claim as a question, asks the LLM
to answer using only cited evidence, and downgrades on disagreement. No-op
without an LLM; recomputes `faithfulness_ratio` when it downgrades anything.

## Release floors (plan.md §6, §9)

- Per-brief faithfulness ≥ 0.90
- Aggregate faithfulness ≥ 0.90 across the 20-brief eval corpus
- Per-brief `Pass@5` ≥ 0.70
- Aggregate `Pass^5` ≥ 0.70

Enforced by [tests/evaluation/test_eval_corpus.py](../../tests/evaluation/test_eval_corpus.py).

## Tests

- [tests/unit/test_verify_claim.py](../../tests/unit/test_verify_claim.py)
- [tests/unit/test_llm_judge.py](../../tests/unit/test_llm_judge.py)
- [tests/unit/test_verifier_with_llm_judge.py](../../tests/unit/test_verifier_with_llm_judge.py)
- [tests/unit/test_critic.py](../../tests/unit/test_critic.py)
- [tests/integration/test_pipeline_fabricated.py](../../tests/integration/test_pipeline_fabricated.py)
