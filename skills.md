# Multi-agent firmware SDLC playbook

Use this project playbook for agent-guided Capability preflight -> Requirement -> Design -> Code gen -> Test. Read HANDOFF.md for the current implementation and docs/phase-contract.md for shared semantics. The root skills.md is a routing/coordination document; executable agent instructions use the standard skills/<name>/SKILL.md layout.

## Roles and owned artifacts

| Role / skill | Inputs | Owned output | Completion gate |
| --- | --- | --- | --- |
| Coordinator / sdlc-coordinator | User scope, run state, artifact references | Task assignments, handoff decisions and next-action records | Consumer has inspected exact offered revisions, or an explicit blocker/return request exists |
| Requirement / req-acquire | User conversation, pinned capabilities | Stories, criteria/test intent, constraints, requirement proposals/baseline | User review and completeness checks; offered to Design, not automatically accepted |
| Design / design-contract | Offered requirement package and capabilities | Architecture/interfaces, recipe/configuration mapping, design decisions | Every offered criterion is covered; generation and regeneration plan is actionable |
| Code gen / codegen-dispatch | Accepted design and source baseline | Provider operation plan, generated/custom code, candidate manifest | Actual build/check evidence for the identified candidate; no claim of behavior acceptance |
| Test / test-evidence | Requirement/design revisions, candidate and test plan | Test specifications, result/evidence records and findings | Applicable required checks pass for the matching candidate, or acceptance stays blocked |

Use roles serially until distinct agents are useful. Role labels do not prove independent review. Agent-guided Design/Code gen/Test procedures are available as skills; automated phase controllers and firmware execution adapters remain future work. No local LLM server is implied by the existence of a skill.

## Assignment and delivery contract

Each assignment records task ID, role, goal, exact input references/revisions, allowed writable outputs, prerequisites, checks, stop conditions and return target. Each delivery records task ID, producer, output revisions, evidence references, findings, state and next action. Use the artifact IDs from the phase contract; do not copy an entire chat as the handoff.

Coordinator owns dispatch; producer owns its artifact; consumer records acceptance separately. Do not edit upstream artifacts to resolve a downstream finding. Return a change request naming the affected criterion/interface/revision.

## Concurrent work

- One writer owns each artifact. Parallel tasks must have disjoint writable outputs and pinned inputs.
- Agents offer proposals against base revisions. Re-read current revisions before applying; stale updates return for reconciliation.
- Shared draft state goes through reqstudio.contracts.save_project, with its existing lock and revision checks. Never edit state.json directly or remove a live lock to bypass contention.
- Only the designated execution role controls a bench/console at a time, using provider locks and gates. Other roles consume evidence.
- A changed requirement, target, constraint, recipe or snapshot triggers impact review before affected work continues. Preserve historical bundles/results.
- Collect user questions through one acquisition/coordinator conversation; avoid several agents interviewing the user simultaneously.

Delegation uses capabilities actually available in the host and the user's authorized scope. These instructions do not authorize new external messages, tool installation, milestone activation, flashing or publication.

## Interactive Requirement operation

Use Background agent / CLI for normal interactive work. The local worker consumes only background-routed requests, runs authenticated Codex CLI with the project playbook/req-acquire contract, and publishes structured proposals through the bridge. The UI polls the saved state and refreshes automatically; no chat notification is required.

The worker is independent of this chat and remains active until stopped. Only one worker owns a data directory. A request is pending -> processing -> completed/failed, with cancellation, stale-context rejection and explicit retry. Only the claiming worker can publish a processing request. User edits, user review and consumer acceptance remain separate from agent output.

Run the startup helper or use the sidebar Start worker button. See [background agent operation](docs/background-agent.md) for lifecycle, logs and authentication. Codex CLI uses its existing login/service; this is not offline inference or an HTTP LLM endpoint implemented by the UI.

Manual/offline and local LLM endpoints remain optional. Host agent / interactive is a manual diagnostic fallback for an active chat, not the primary background path. Do not represent it as automatic service.

Synthetic smoke tests are isolated from user projects. Real user messages/answers, unapplied proposals and explicit user review form interactive evidence. No agent output automatically modifies a story or grants firmware/publication authorization.

## First experiment finish line

One real UI-originated story with user-reviewed meaning, measurable criteria/test intent and traceable capability references, exported as an offered Requirement package. Design accepts/rejects separately. Missing hardware is not a reason to invent test evidence, and the absence of a local LLM must remain visible.
