# Development plan

Updated 2026-10-31. Contract-first plan for Capability / recipe preflight -> Requirement -> Design -> Code gen -> Test.

The four development phases remain the integration target. The owner prioritized a local Requirement UI and imported capability snapshot to experiment with preparing Design artifacts. Preflight, review, feedback, impact assessment and resume are coordination activities across the four phases. Release and Maintenance are later extensions.

## Delivered Requirement experiment

Implemented read-only timestamped capability Markdown/JSON imports with source hashes and drift checks; a local Streamlit chat/story editor; Ollama and OpenAI-compatible local model adapters; explicit model-proposal acceptance; durable per-PC drafts; user review/feasibility checks; and versioned Requirement to Design ZIP/JSON/Markdown export with schema/integrity validation. See [the UI guide](docs/req-ui.md).

This is a partial delivery of C0/C1/C3 for Requirement, not completion of the four-phase controller or firmware execution adapter. Local API behavior is tested against mock servers. Gemma E4B/E2B inference quality and VRAM performance remain an office experiment.

Next experiment: use the UI on office, prepare one reviewed story baseline against a pinned capability snapshot, inspect its exported artifact, and build a Design example that consumes that exact baseline. Use the outcome to refine the shared contract and minimum provider adapter.

## C0 Common contract and worked example

Use [phase-contract.md](docs/phase-contract.md) as the shared semantics. Build one versioned button/LED example covering a capability snapshot, requirements with test intent, a real design-to-recipe mapping, a generation/candidate record and a test/acceptance record. Include one bug-fix iteration.

Complete when the example demonstrates all of the following without private chat history:

- Preflight distinguishes supported capability, evidence level and current tools/hardware readiness.
- Each requirement maps to a recipe/configuration or an explicit feasibility gap, with a way to verify its acceptance criteria.
- Design is an explicit artifact; it supplies interfaces, customization boundaries and enough information to drive code generation.
- Every handoff names exact input/output revisions, its consumer and its completion/acceptance checks.
- An unsupported request remains visible; a needs-spike item is resolved before it is offered for implementation.
- Findings return to the responsible phase, including a test/bench failure that does not require changing requirements.
- A requirement change identifies downstream work and evidence requiring impact review.
- A missing board leaves required target tests NOT RUN, while completed offline activities remain usable.
- A changed candidate cannot inherit acceptance from the earlier image without applicable evidence.

Review this example before freezing contract v1. The current prose scenario is the starting point; it is not executable validation.

## C1 Executable contract checks

Derive a machine-readable schema and validator from the C0 example. Keep one authoritative representation for each fact; human-readable and machine-readable views must not silently diverge.

Complete when a coherent example is accepted structurally and meaningful negative cases are rejected: missing input references, wrong revisions, missing recipe mapping, unresolved feasibility in an implementation handoff, stale evidence, mismatched image identity and an unfulfilled required acceptance check.

Distinguish structural validity, engineering feasibility and behavioral acceptance. Schema validation alone does not accept a requirement, approve a design or prove firmware behavior.

## C2 Execution provider adapter

Specify and implement the minimum adapter to automated-firmware-skills before driving actual code generation. Reuse its scripts, tests, manifests and board profiles. The adapter must expose recipe inputs, output locations, customization/regeneration boundaries, capability evidence, current readiness and execution results.

Preserve provider version/profile references, active milestones, commands/configuration, exit statuses, gate lines, candidate identities and evidence references. Surface ACTION requests and unavailable operations without bypassing gates.

Complete when an offline example resolves a recipe and accurately records available versus unavailable operations, and the adapter can pass provider results into the common contract. Actual build and target execution require their corresponding tools and bench; their absence is not a provider PASS.

## C3 Coordinator and first four phase skills

Implement the lifecycle coordinator and Requirement, Design, Code gen and Test skills. Preflight may initially be part of the coordinator; a separate discovery skill is optional if actual usage justifies it.

Each phase skill declares its invocation scope, owned outputs, input checks, activities, exit checks and return-work behavior. Shared definitions stay in the contract. Code gen delegates engineering operations to the provider. Design is implemented in this first set rather than deferred.

Complete when the button/LED example runs through all four phases with the available capabilities, returns a finding to its owner and resumes in a fresh session from saved artifacts. An offline stop is a valid workflow outcome but does not establish target acceptance.

## C4 End-to-end qualification

Exercise one new feature, one bug fix and one changed requirement through the complete contract. Check both initial generation and regeneration with an existing user-owned edit. Perform target verification on a supported board when the correct bench is available.

Complete when handoffs, finding routing, source/image/evidence identities, change propagation and fresh-session resume work together. Required target checks must pass against the correct candidate for target acceptance. Keep the records of unavailable checks separate from the completed hardware run.

Use realistic behavioral walkthroughs to evaluate phase skills. Firmware tests evaluate the application; schema checks, agent behavior cases and clean-room checks evaluate different parts of the workflow and cannot substitute for each other.

## Later extensions

Add Release and Maintenance after C4. Release consumes the accepted candidate, configuration and matching evidence to prepare compatibility, known issues, installation/recovery and handover records. Deployment and publication remain separately authorized actions.

Maintenance preserves the released baseline, diagnoses an issue or upgrade request, assesses impact and routes work to the affected core phases. Record requalification and end-of-support decisions where applicable.

Review is already a gate on relevant outputs in the core workflow. Decide whether a separate review skill adds value after using the first four phase skills; review does not automatically require a new agent or human approval at every transition.

## Open design choices

1. Final invocation names and packaging of the coordinator and four phase skills.
2. Machine-readable schema, document generation and ownership of shared facts.
3. Minimal artifact set for a small bug fix and imported legacy baseline.
4. Initial concrete board/recipe for the example and supported regeneration behavior.
5. Contract version compatibility and raw-evidence storage/retention.
6. Whether discovery or review warrants a separate skill after practical use.

The first action is the C0 example. This plan does not authorize Git initialization, a remote, publication, CI/CD setup or changes to the execution toolkit's milestone policy.

## Agent-guided operation

Read [skills.md](skills.md) for role ownership, multi-agent handoffs and phase skill routing. The Requirement UI supports Host agent / interactive for an active host-agent session; this is distinct from a local LLM server or an unattended worker. Design/Code gen/Test skill procedures are documented, while their automated controllers remain planned.

## Background agent delivery

Implemented an independent Codex CLI queue worker with singleton ownership, heartbeat, per-request claiming, cancellation, timeout, interrupted-job recovery and structured result validation. The UI now supports automatic replies without requiring this chat or a local LLM API endpoint. Unit/UI tests and an isolated real CLI smoke test qualify this Requirement-only execution path. Design and other phase workers remain future extensions.
