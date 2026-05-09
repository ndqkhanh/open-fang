---
name: verifier-5tier
description: Five-tier verifier (parse / cite / ground / reproduce / meta).
---
# Five-Tier Verifier

Each claim flows through five tiers:

1. **Parse** — structural validity. Cheap. Filters malformed inputs.
2. **Cite** — every cited source supports the cited quote. Catches
   citation hallucination.
3. **Ground** — the claim survives a re-derivation from primary
   evidence (raw data, prior theorem, etc.).
4. **Reproduce** — for experimental claims, run against the public
   artifact (code, dataset).
5. **Meta** — the claim is consistent with related work in the
   corpus (no silent contradiction with cited prior).

A claim's verification level is the *highest tier it passed* — so
"tier 3 verified" means parse, cite, ground all green; reproduce
not attempted or failed.

**Telemetry:** emits `openfang.tier{N}.{pass|fail}` per (claim, tier).
