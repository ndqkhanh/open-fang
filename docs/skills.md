---
title: OpenFang — Skills (evolution over existing 5 skills)
description: EvoSkill-style failure-driven evolution layered over OpenFang's existing skill library.
---

# OpenFang — Skills (evolution over existing skills)

OpenFang ships 5 hand-authored skills (citation-extraction, claim-localization,
counter-example-generation, peer-review, reproduction-script). This integration
adds **failure-driven evolution** over them via the 5-tier verifier's
rejection events.

## Corner of the design space

| Axis | Value |
|---|---|
| Feedback signal | 5-tier verifier (lexical → mutation → LLM-judge → executable → cross-channel) |
| Skill artifact | Folder + scripts (matches existing skills/ layout) |
| Parameter access | Frozen weights (RL pipeline optional via Atropos export) |
| Reference paper | [EvoSkill](../../../docs/168-evoskill-coding-agent-skill-discovery.md) |

## Adapter

`openfang.skills_adapter` provides `OpenFangFailureExtractor` that reads
verifier-rejection events from any of the 5 tiers and proposes evolution
candidates against the existing skill set.

## Bright-lines

- `BL-OPENFANG-SKILL-LITERATURE-DRIFT` — feed-week-tagged skills auto-decay
  after N weeks unless renewed.

## Existing skills (auto-tagged `T2-AUTO-EXTRACTED` until reviewed)

- citation-extraction
- claim-localization
- counter-example-generation
- peer-review
- reproduction-script
