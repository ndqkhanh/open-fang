# FANG.md — OpenFang persona partition

> Never-compacted, size-capped (16KB), version-controlled. Loaded every session.
> This seed is generic; the user should edit it to reflect their actual research identity.

## Domains of interest

- AI Agents and Agentic AI
- Harness Engineering (agent loops, subagents, skills, hooks, permissions, MCP)
- Verifier/evaluator loops and LLM-as-Judge
- Agentic RAG and citation-grounded synthesis
- Self-evolving agents and skill libraries

## Evidence bar

- Arxiv preprints accepted.
- Peer-reviewed preferred for empirical claims with effect sizes.
- Benchmark numbers require cross-channel confirmation (abstract ∧ body ∧ table).
- Blog posts and vendor announcements are signal, not evidence.

## Citation style

- Inline author-year plus arxiv id, e.g. `(Zhu et al., 2026; arxiv:2604.11548)`.
- Every claim carries structured `evidence_ids`, not prose.
- Fabricated citations are a release-blocker, not a warning.

## Output format defaults

- Length: 1200–1800 words unless the brief overrides.
- Structure: TL;DR → Method → Evidence → Trade-offs → Open questions.
- Show `faithfulness_ratio` and `verified_claims / total_claims` in the footer.

## Known-read papers

- *(Empty seed. OpenFang maintains this list automatically via `kb.promote`.)*

## Venues and preferences

- Preferred: NeurIPS, ICML, ICLR, COLM, ACL, EMNLP, arxiv cs.AI / cs.CL / cs.LG.
- Cautious: vendor technical reports, non-archival workshops.
- Blocked: none (mark with rationale if added).
