# Firmware provider integration assessment

Updated 2026-10-31. The sibling automated-firmware-skills project is a read-only execution provider in this project. Its detailed imported state is pinned in [timestamped capability snapshots](capabilities/README.md).

## Responsibilities

This project owns lifecycle contracts, phase skills, Requirement chat/editor, future Design canvas, test dashboard, revisions, acceptance policy and job coordination. The provider owns board/toolchain facts and engineering operations. The adapter maps structured lifecycle requests to provider operations and normalizes their results.

The Requirement agent and UI are separate from the contract store. Model replies propose changes; the user reviews them. Future Design canvas coordinates are presentation metadata, while semantic graph changes create design revisions. Future test dashboards consume test-plan/case/run/image/evidence relationships from the shared core.

## Reusable features and remaining work

| Area | Existing provider basis | Remaining integration work | Owner |
| --- | --- | --- | --- |
| Discovery | Board/profile index, per-template evidence and pinned tools | Unified capability/parameter/interface catalog; this prototype imports facts without probing readiness | Provider facts + lifecycle adapter |
| Composition | Vision Board driver recipe JSON, dependencies/resource conflicts and read-only recipe check | Separate early catalog feasibility from app/configuration-specific validation; expose typed software interfaces for Design | Provider checks + adapter |
| Generation | Shared create/build stages, templates and layered sources | Structured generation request, recipe/version/configuration mapping and operation plan | Lifecycle adapter |
| Provenance | Build manifests and image hashes | Complete relevant source/configuration identity plus requirement/design/run references | Provider manifests + lifecycle references |
| Test results | Shared serial engine, target unit tests on selected skills | Stable case IDs, structured per-case results, planned/selected/executed sets, skip reasons and candidate identity | Provider result format + lifecycle acceptance |
| Updates | Generator-specific regeneration/overlays | Declared owned/generated regions, safe update plan and preservation checks | Provider metadata + lifecycle change control |
| Runtime identity | Board identity, boot/sync markers and command inspection on RT-Thread | Correlate running build ID with candidate/flash record; keep application and unit-test images distinct | Provider + adapter |
| UI execution | Existing gates, ACTION requests and bench locks | Structured jobs/events, bounded execution, resource coordination and explicit resume | Lifecycle runner using provider gates |

Recipe check readiness does not mean hardware behavior passed. Driver recipes can have prepared or tested status with partial evidence; read their imported dated notes. Likewise, provider test PASS can coexist with skipped/filtered cases and cannot by itself satisfy a project's complete acceptance plan.

## Implemented in this project

Read-only snapshot importer, source-hash drift checking, explicit draft rebinding/review, local Requirement UI/agent adapters and Requirement to Design export/validation are implemented. Firmware execution adapters, Design tooling, dashboard execution and provider enhancements above are future work. No provider files were modified.

Next, consume one exported requirement artifact in a concrete Design example and use the resulting mapping to define the minimum generation adapter. Limit the first execution integration to one board/skill before generalizing.
