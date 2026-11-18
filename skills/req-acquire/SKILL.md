---
name: req-acquire
description: Acquire firmware requirements through user stories and acceptance criteria using the local requirement workspace or its artifacts, assess them against an imported capability snapshot, and prepare a versioned handoff for Design. Use for requirement interviews, refining firmware user stories, resolving feasibility gaps, or preparing Requirement to Design artifacts. Does not generate or flash firmware.
---

# Acquire firmware requirements

Read [skills.md](../../skills.md) for multi-agent ownership and assignment rules. For an interactive test requested through the UI, receive the user's real first message there; do not replace it with a chat interview or a synthetic example. Background agent / CLI is the normal interactive path: an independent worker executes this role with supplied context and sends proposals through reqstudio.bridge. Do not call a local HTTP LLM endpoint from that path. Host-agent mode remains an explicitly manual diagnostic fallback.

Use the project's [requirement UI guide](../../docs/req-ui.md) for launching the local workspace and the [phase contract](../../docs/phase-contract.md) for phase boundaries. Read the pinned capability snapshot before assessing support; see [snapshot maintenance](../../docs/capabilities/README.md) when freshness is uncertain.

Preserve the user's intent. Acquire actor, desired behavior, benefit, acceptance criteria, test intent, constraints and unanswered questions. Record uncertainty rather than inventing limits, pins or supported features. Candidate recipes are feasibility references; detailed architecture and recipe configuration belong to Design.

Decompose by independently valuable, testable user goals. Selecting a story provides focus; it does not require appending every new goal to that story. For example, scan-and-save, setting time, clearing records and viewing a summary can be separate stories, while CSV fields and duplicate handling belong to scan-and-save criteria. Avoid splitting stories by drivers, recipes or implementation tasks. Reuse an existing story for the same goal; preserve its revision and criterion IDs. When splitting an oversized story, propose a narrowed update and new stories for the other goals, retaining confirmed criteria and routing open questions to their responsible goal. Explain the grouping and leave the proposals unapplied. Prior unapplied proposals are suggestions, not confirmed user answers.

Treat model responses as proposals. Never overwrite a manually edited story implicitly. Keep stable story/criterion IDs, increment revisions and preserve source-turn references where available. A changed target, constraint or capability snapshot requires renewed review/feasibility assessment.

Use the UI's explicit draft-acceptance and review actions. Mark supported only with a valid target-matching capability reference and rationale. Distinguish recipe support, imported evidence and current readiness. A prepared recipe or a PASS on only selected tests does not establish firmware acceptance.

Offer a baseline only when the user has reviewed the stories, each criterion has test intent, the offered scope has no blocking questions/feasibility gaps, and the pinned snapshot is not known to be stale. Provider source unavailable means freshness is unverified and Design must check it; do not label it current.

Export the ZIP plus JSON/Markdown through the app. Validate the ZIP with `python scripts/validate_handoff.py <bundle.zip>`. The result is offered to Design with consumer acceptance pending. No hardware operation or publication is authorized by this handoff.
