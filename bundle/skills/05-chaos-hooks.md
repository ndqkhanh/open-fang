---
name: chaos-hooks
description: Periodically perturb the system to verify robustness.
---
# Chaos Hooks

Every 1000 papers, the chaos hook injects a perturbation:

- Drop a random specialist for 24h (cohort robustness test).
- Corrupt a random tier output (verifier robustness test).
- Replay a 6-month-old query against the current corpus
  (longitudinal stability test).

Failures from chaos hooks become first-class issues, not bugs to
silence. Each chaos failure emits a `chaos.{kind}.failed` event the
curator must triage.
