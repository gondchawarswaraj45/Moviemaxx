---
name: p2-guardrail-audit
description: Audits prompts for jailbreak attempts, prompt injection, Cypher injection, and unsafe commands.
---

# P2 Guardrail Audit Skill

## Capabilities
- Detects prompt injection (e.g. system prompt leaks, DAN mode, instruction overrides).
- Scans for unauthorized Cypher or database manipulation commands (`DETACH DELETE`, `DROP DATABASE`).
- Returns standardized `GuardrailResult` with risk level and warning messages.
