# Phase contract draft

Status: v0.3 draft, 2026-10-31. Core four-phase semantics remain a draft. The Requirement prototype now implements a handoff schema, local UI/LLM acquisition, durable drafts and read-only capability snapshots. Design/Code gen/Test controllers and firmware execution adapters remain planned.

## Workflow and scope

The core workflow is Capability / recipe preflight -> Requirement -> Design -> Code gen -> Test -> Acceptance. Preflight is a coordination activity before the four development phases; refresh it when relevant scope, provider/recipe versions or tools/hardware readiness change. Release and Maintenance are later extensions.

Start preflight from the initial user need or change request, without requiring a formal requirements baseline first. Discover what existing skills can do before committing to an implementation scope. Preserve unmet user needs as explicit gaps rather than silently replacing them with what a recipe happens to provide.

Code gen primarily invokes the existing automated-firmware-skills provider. Recipe-directed customization is part of code generation when the design identifies supported extension points and a verification method. Developing a missing provider capability is separately scoped work.

The coordinator selects eligible work from dependencies. Existing projects may enter with imported baseline artifacts and recorded provenance/acceptance limits. A bug fix may revisit only affected phases when the impact assessment explains the scope.

## Common interface

| Element | Meaning |
| --- | --- |
| Identity | Project, activity/phase, run and contract version; stable artifact IDs with explicit revisions. |
| Goal and scope | Requested outcome, offered slice, exclusions and completion criteria. |
| Inputs | Artifact ID/revision, origin, owner, required/optional role, acceptance state and current applicability. |
| Preconditions | Compatible inputs, resolved blocking gaps and execution capabilities/readiness required for the offered activity. |
| Activities | Bounded work, owned artifacts and relevant provider operations. |
| Outputs | Identified revisions, producer/owner and exact upstream dependencies. |
| Checks | Structural checks, engineering checks and any decisions required by project policy; each names its evidence. |
| Handoff | Offered output revisions, consuming role, acceptance/rejection decision, reasons and unresolved items. |
| Return work | Finding/change-request ID, affected revisions, requested correction, responsible phase and required rechecks. |
| Resume | Current run state, completed checks, remaining blockers, pending decisions and next eligible action. |

Artifact owners publish new revisions of their own outputs. Other phases request corrections through findings/change requests instead of silently modifying upstream artifacts. Ownership is per artifact, not implied by a folder name. Importing or generating a file does not transfer ownership automatically.

## Capability / recipe preflight

Inspect the provider's documented skills, board profiles, templates/recipes, accepted parameters, extension points, generated outputs and existing tests. Record provider/recipe/profile revisions and sources for capability claims.

Record three separate dimensions:

- Supported scope: boards/frameworks, behavior, configuration ranges, interfaces, extension points and known limitations.
- Evidence level: what was actually built, flashed, tested or observed, including which version/profile the evidence covers. A documented feature is not automatically hardware-proven.
- Current readiness: installed tools, active provider milestones, available hardware, console/probe access and which operations can run now.

The output is a versioned capability snapshot with candidate recipes, test capabilities and explicit gaps. Reuse the snapshot until a relevant dependency changes. A missing board can block execution without making the recipe unsupported.

A feasibility spike is optional for an uncertain assumption. Give it a bounded question, method, expected evidence and stopping condition. Record its result against the affected requirement/capability. A spike result does not accept the production candidate.

## Phase activities and outputs

### Requirement

Inputs: initial user need/change request, capability snapshot, constraints and any existing baseline.

Activities:

1. Preserve requested behavior and define the offered scope, exclusions and priorities.
2. Assign requirement IDs and measurable acceptance criteria. Include timing, memory, reliability or other nonfunctional limits when the requested work requires them.
3. For every criterion, define test intent: what is checked, method/stimulus, expected outcome/tolerance, required tools/hardware and the evidence needed. Declare any mandatory human observation.
4. Map each requirement to candidate recipes/configuration or a capability gap. Classify it as supported, needs-spike or unsupported, with rationale and source/evidence references.
5. Resolve blocking ambiguity and feasibility gaps for the offered implementation scope. An out-of-scope item retains the original need and records the scope decision and authority under project policy.
6. Publish the requirements baseline, acceptance test intent and scoped development plan.

Supported means the proposed path fits documented recipe/configuration/extension boundaries; its evidence level is recorded separately. A needs-spike or unsupported requirement can remain in the backlog but cannot silently enter an implementation-ready scope. Resolve it through a spike, another recipe, an explicit scope decision or separately scoped capability work.

Requirement validation checks clarity, consistency, testability and feasibility. It does not prove that generated firmware meets the criteria.

### Design

Inputs: accepted requirement revisions, test intent, capability snapshot and any accepted prior design.

Activities:

1. Define logical behavior, states/data flow, architecture and interface contracts separately from provider-specific mapping.
2. Map every offered requirement to recipe(s), exact configuration and modules/interfaces. Specify their integration when more than one recipe is involved; do not assume arbitrary recipes compose.
3. Identify supported customization, code to generate versus code to edit, ownership and regeneration boundaries. Record the expected provider commands/operations and output locations.
4. Refine test approach through design-owned instrumentation, observable interfaces, failure injection and applicable budgets. Request an upstream criterion change if the requirement cannot be verified; do not weaken it locally.
5. Check interface compatibility, resource assumptions, dependency versions and feasibility against the actual recipe. Return gaps to preflight/Requirement as appropriate.
6. Publish design decisions, coverage/mapping and the instructions needed for code generation.

Design is a first-class handoff in the initial example and first set of skills. A recipe name without the interfaces, configuration and customization mapping is insufficient.

### Code gen

Inputs: accepted requirement/design revisions, selected recipe/configuration, capability snapshot, source baseline and any existing user-owned edits.

Activities:

1. Check input revisions, provider version, configuration and readiness for the operations to run. Reconfirm the design's required capabilities before execution.
2. Record a source/configuration baseline. Check for existing edits and ownership before generation; choose the documented create/update/regenerate path.
3. Invoke existing provider skills/scripts. Apply only design-specified customization within supported extension boundaries. Return an unplanned extension to Design instead of inventing an unchecked path.
4. Preserve user-owned source and accepted test artifacts. Use documented merge/overlay boundaries; if safe regeneration is undefined, stop the destructive operation and record a blocker for resolution.
5. Run relevant build/static/layer checks when available and allowed by active provider milestones. Record warnings and all required unavailable checks; never bypass gates to obtain a pass.
6. Publish the generation record, source/configuration identity, generated/support changes, candidate manifest, build evidence and candidate test resources. Distinguish application images from unit-test images.

The generation record identifies provider/skill/recipe revisions, parameters, commands, customization, source baseline and resulting artifacts. Test receives a concrete candidate and enough information to reproduce its build; build success alone is not behavioral acceptance.

### Test

Inputs: requirements/acceptance test intent, design contracts/mapping, candidate manifest, relevant build evidence and candidate/existing test resources.

Activities:

1. Check test readiness: exact candidate/source/configuration, test revisions, board/profile, tools/bench and required build conditions. Confirm which image each check exercises.
2. Maintain versioned executable test specifications/procedures from the acceptance criteria and design contracts. Review generated candidate tests before accepting them; provider defaults alone do not establish requirement coverage.
3. Select applicable checks: unit, interface/integration, target behavior, negative/failure paths, timing/resource limits and regression. Selection follows requirements and change impact; every project need not run every category.
4. Run provider-supported checks with their gates. Keep build, programming, boot, unit tests, target behavior and human observation results separate. Hardware-dependent criteria require suitable target evidence.
5. Analyze failures and record findings with reproducers, expected/actual behavior, evidence and responsible phase/activity. Diagnose test/bench issues before attributing every failure to generated code.
6. Re-run affected acceptance and regression checks after corrections; confirm the candidate and applicable revisions again.
7. Publish requirement-to-evidence coverage, unresolved findings and the acceptance outcome for the exact offered scope/candidate. The coordinator records the final acceptance decision under project policy.

Test owns accepted executable test specifications/procedures and result records. Code gen may offer generated test resources and implement design-specified firmware test support, but cannot silently overwrite Test-owned artifacts. Changes to acceptance criteria remain owned by Requirement.

## Handoff gates

| Boundary | Consumer checks before accepting the offered work |
| --- | --- |
| Preflight -> Requirement | Snapshot identifies candidate recipes, capability/evidence/readiness dimensions, limitations and unknowns sufficiently to assess the requested scope. |
| Requirement -> Design | Offered requirements are identifiable, clear and testable; test intent exists; blocking feasibility/ambiguity gaps have been resolved. |
| Design -> Code gen | Accepted requirement revisions are covered; interfaces, recipe/configuration mapping, customization and regeneration boundaries are sufficient to generate the offered scope. |
| Code gen -> Test | Candidate/source/configuration identities and generation record are available; required build conditions for the planned tests are met; missing test-environment prerequisites are visible. |
| Test -> Acceptance | Applicable required checks pass against matching criteria, test revisions and candidate identities; no unresolved acceptance-blocking finding remains. |

A Test phase can receive the candidate, complete offline checks and record required target checks as NOT RUN while waiting for hardware. That does not satisfy target acceptance. A required build failure blocks tests that depend on that build; diagnostic work may still proceed with its own stated scope.

Review is part of relevant handoff checks. Reviewer role/independence follows project policy; this contract does not automatically require a new agent or human approval for every transition.

## Finding routing and change propagation

| Finding | Return target |
| --- | --- |
| Requested behavior, scope or acceptance criterion is ambiguous/inconsistent | Requirement |
| Recipe support or tool/bench readiness was misidentified or changed | Preflight/coordinator; revisit Requirement or Design only if their assumptions are affected |
| Architecture, interface, resource assumption or recipe mapping is inadequate | Design |
| Generated/custom code or configuration does not implement the accepted design | Code gen |
| Test specification, instrumentation use, capture or bench procedure is faulty | Test, with provider/setup actions recorded where needed |
| Root cause is not established | Test/coordinator keeps diagnosis open and records the next discriminating check |

Each finding names its reproducer, relevant revisions and evidence, proposed owner and closure/recheck criteria. Preserve reproducing baseline results when available. Do not reroute every failure to Requirement or weaken a criterion to make a test pass.

Every output declares exact upstream revisions. A change triggers downstream impact review of artifacts, accepted handoffs and evidence. Record what must be regenerated or retested and why retained evidence is still applicable. Prior PASS results remain historical; they do not automatically cover changed requirements, recipes, source, test specs, configuration or images.

Changes to provider/recipe/profile versions refresh affected preflight facts. Changed readiness refreshes operational eligibility; it need not invalidate a correct design unless an assumption changes. A final candidate cannot inherit application acceptance solely from a unit-test image built from related sources.

## Run, handoff and resume records

Phase-run states: ready, running, blocked, completed, failed, superseded. An unstarted phase need not have a run record. Completed records producer completion, not consumer acceptance.

Handoff states: offered, accepted, rejected, superseded. The consuming role checks offered revisions and records acceptance or rejection. Test's acceptance report is consumed by the coordinator/project acceptance role. Rejection includes reasons and return-work or missing-prerequisite records.

Track current applicability separately: current, needs-review or stale. Changed dependencies flag affected records for impact review without rewriting their historical result. The schema/validator must enforce the eventual transition rules; prose does not implement them.

Resume records include artifact references/revisions, active runs/handoffs, applicability, unresolved findings/gaps, completed evidence, pending decisions, readiness and the next eligible action. A new session refreshes volatile readiness and checks applicability before continuing.

## Evidence and execution contract

Each check records its ID/revision, result, command or method, time, tool/configuration identity, applicable requirement/design/test revisions, source revision or digest, image hash where relevant, board/profile revision where relevant and retained evidence references.

Use explicit PASS, FAIL, NOT RUN and SKIPPED results. Record non-applicability separately with rationale and the policy/requirement revision authorizing it. An applicable required check that is NOT RUN or SKIPPED remains unfulfilled. Distinguish measured facts, estimates and inferred capability.

A serial timeout only proves that expected data arrived in a time window; it cannot by itself prove a fine-grained timing requirement. Plan and use a suitable measurement method. Likewise, schema validation, agent behavior evals and skill clean-room checks do not substitute for firmware acceptance tests.

The first adapter targets [automated-firmware-skills](../../automated-firmware-skills/README.md). It records provider version, selected skill/recipe/profile, active capabilities, commands/configuration, exit status, gate lines and evidence locations. Reuse its engineering scripts rather than implementing a second build/flash/test path here.

Respect provider ACTION requests, identity checks and authorization. A lifecycle transition does not enable M2-M5, change flash policy, install tools, alter hardware security settings or authorize publishing/pushing. Unsupported capability and temporarily unavailable execution must be distinguishable.

Application artifacts live in their application project. Raw logs, generated build outputs and bench identifiers follow designated local/evidence-storage rules; shared records omit personal bench data. A missing raw evidence file prevents replay/review of that evidence; retain its historical result and record the access limit without claiming re-verification.

## Worked example to implement

These illustrative IDs do not identify implemented machine-readable artifacts yet.

1. CAP-001 revision 1 identifies a documented button/LED recipe, supported parameters, customization boundaries, existing tests, evidence levels and current bench readiness.
2. R-001 revision 1 requests press-on/release-off behavior. Its criteria define button stimulus and LED observation/readback, with required checks and target setup. Map it to CAP-001 and record any limitation; do not claim physical light was observed from a software readback alone.
3. D-001 revision 1 defines button/LED interfaces and behavior, maps R-001 to the selected recipe/configuration and identifies generated versus owned code, regeneration and test interfaces.
4. G-001 revision 1 records provider operations, source/configuration identities, customization, candidate image hash and actual build results. Existing user edits are preserved by the documented regeneration path.
5. T-001 revision 1 references accepted criteria, executable tests, design, G-001 and the actual candidate/board profile. Without hardware, target checks are NOT RUN and target acceptance remains unfulfilled; retain completed offline results.
6. With the correct bench and provider authorization, execute required checks and record acceptance only for the matching candidate and scope. Route a broken capture to Test, an interface mismatch to Design or an implementation defect to Code gen according to evidence.
7. R-001 revision 2 changes behavior to toggle-on-press. Identify impacted D-001, G-001, test definitions and T-001; retain revision 1 results as historical and obtain new applicable evidence before accepting revision 2.

## Qualification cases

- Complete preflight and all four phase handoffs for a new feature, including explicit Design.
- Keep an unsupported need visible and resolve a needs-spike item before implementation readiness.
- Reject a missing/wrong revision, missing recipe mapping or incompatible interface.
- Regenerate safely with a pre-existing user-owned edit; stop when preservation is undefined.
- Route a firmware defect and a separate test/bench defect to their responsible owners.
- Detect stale acceptance after a requirement, recipe, test or candidate image changes.
- Preserve required NOT RUN/SKIPPED checks without promoting target acceptance.
- Resume from stored artifacts in a fresh session and refresh readiness.

## Later extensions

Release will consume an accepted application candidate and matching evidence to prepare compatibility, known issues, installation/recovery and handover records. Preparation, deployment and publication are separate operations.

Maintenance will preserve the released baseline, assess an issue/upgrade and route corrections through affected phases with explicit regression/requalification and support-lifecycle decisions. These extensions do not add phases to the first implementation.

## Requirement prototype implementation

The [local workspace](req-ui.md) uses a canonical draft JSON with stable story/criterion IDs and revisions. User stories contain actor/want/benefit, criteria with test intent, questions, reviewed feasibility and capability references. Project constraints remain separate. Model proposals require explicit application into the draft and do not mark it reviewed.

The executable [Requirement handoff schema](../schemas/requirements-handoff.schema.json) is version 0.3. Export creates a new baseline revision with exact capability snapshot references, source freshness, target, constraints, stories and required Design checks. It is `offered`, with `consumer_acceptance: pending` and `readiness: not_probed`. These fields are implemented only for Requirement handoffs; the full generic phase state machine above is not implemented yet.

Known source drift blocks export. Provider unavailable is explicitly unverified and adds a Design source-check prerequisite. Rebinding snapshots or changing target/constraints clears feasibility/review, preserving historical handoffs. This prototype conservatively rechecks all stories rather than computing a fine-grained dependency impact graph.

The ZIP preserves requirements and the pinned capability snapshot as JSON/Markdown, plus schema, consumer instructions and hashes. Validation checks structure, member integrity and target/reference consistency; it does not establish engineering acceptance. Drafts/transcripts and historical export files are saved per PC outside Dropbox by default.

See [snapshot maintenance](capabilities/README.md), [local model setup](local-llm.md) and [remaining provider integration work](integration-gaps.md) before extending the prototype into Design or firmware execution.
