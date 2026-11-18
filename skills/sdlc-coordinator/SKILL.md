---
name: sdlc-coordinator
description: Coordinate firmware SDLC roles through versioned artifacts, assignments, handoff checks and return-work requests. Use when running a cross-phase or multi-agent firmware workflow. Does not replace phase engineering or grant execution permission.
---

# Coordinate SDLC work

Read [the project playbook](../../skills.md), HANDOFF.md and the relevant sections of [the phase contract](../../docs/phase-contract.md). Identify the offered scope, pinned inputs, current capability/readiness and next eligible phase.

Assign a role, goal, input revisions, explicit writable outputs, completion evidence and stop/return conditions. Parallelize only disjoint outputs. Keep one conversation responsible for user questions. Use available host delegation only within the authorized task; otherwise execute roles serially and label them honestly.

Verify deliveries against the assignment, then ask the consuming role to inspect the exact offered revisions. Producer completion is not acceptance. Record a blocker or change request when prerequisites or required evidence are missing. Preserve user decisions and source ownership across retries.

For normal Requirement UI operation, use the independent background worker documented in skills.md and docs/background-agent.md. The manual host-agent bridge is a diagnostic fallback. Read only pending requests and respond to the matching project/request; do not simulate the user's first message or automatically apply model proposals. Local model servers and a persistent coordinator are separate runtime capabilities.
