# HANDOFF - Firmware development life cycle

Updated 2026-10-31 (local Windows session).

## Release files and quick start (2026-11-16, home)

Added LICENSE (MIT, same holder line as the skill repositories - owner to confirm), CHANGELOG.md, CONTRIBUTING.md,
SECURITY.md; README: Quick start (pages Auto / IDE / Requirement), Related repositories, four providers instead of
one; `scripts/check_provider_libs.py` (lib copies: 20 shared, 4 differ by design). Suite: 57 passed. Still no git
here. The workspace-level story and open decisions: `../HANDOFF.md` (top section).

## Run page, milestone 1 (2026-11-16, home, Claude Code session opened in automated-firmware-skills)

Owner decisions: this project is the UI that invokes the provider skills for the selected hardware; manifests live here (provider repositories untouched); milestone 1 includes flash and test behind approval; keep Streamlit; first targets blink / hello-world on NUCLEO-C562RE (bare metal), STM32L476G-DISCO (FreeRTOS), Titan Board (RT-Thread), UNO Q (EmbLinux).

Added: `providers/*.json` (4 manifests), `runstudio/store.py` + `runstudio/runner.py`, `pages/1_Run.py`, `tests/test_runs.py`, `docs/run-ui.md`, README section. Suite: 55 passed. Real runs without approval: C5 and L476 reached `ACTION: APPROVE` at flash (create, build, connect passed); Titan stopped at tools (`ACTION: SETUP`, Titan-Board SDK not installed on home); UNO Q stopped at connect (no board). Nothing was flashed. Details and the not-verified list: [docs/run-ui.md](docs/run-ui.md).

Later the same day: time-stamped gate lines fixed (C5 flash approved by the owner, test 6/6 = tested); page Run renamed **Auto**, new page **IDE** (tools, create, open IDE), new stages 7 debug (status) and 16 delete (manager's own per-app delete behind approval, `runstudio/builtin.py`), flows in the manifests, shared page body `runstudio/ui.py`. Suite 57 passed. C5: debug status passed, delete ask shown (not approved), IDE flow opened VS Code on `C:/fw-ws/ide-bl-c5`. Not run: the new stages / IDE flow on L476, Titan, UNO Q.

Left on home: runs in `~/.firmware-dev-life-cycle/runs/`, apps `C:/fw-ws/ui-bl-c5`, `ui-bl-l4`, `ui-hw-q`. Next: the owner approves a flash from the page and runs the test stage; Titan and UNO Q on the PC that has them; then decide what feeds a run from Requirement/Design.

## Goal and decisions

The project controls Requirement -> Design -> Code gen -> Test through shared contracts, preceded by capability/recipe preflight. Existing automated-firmware-skills remains the external firmware execution provider. The owner explicitly requested changes only in this project.

The current experiment is a local Streamlit Requirement workspace, using chat on the left and editable user stories/criteria on the right, to prepare a versioned artifact for Design. Ollama and OpenAI-compatible local endpoints are supported; the office target is RTX 4060 8GB, with Gemma 4 E4B requested and E2B available as a smaller fallback. No model download or real GPU inference was performed here.

## Implemented

- Read-only capability importer: immutable timestamped Markdown/JSON snapshots with provider revision, source hashes/timestamps, board/template evidence, driver recipes and source notes.
- Source drift comparison distinguishes current, changed and unavailable. Existing drafts pin their snapshot; refresh does not silently rebind them. Rebinding or changed target/constraints clears feasibility/review.
- Streamlit conversation/story editor, manual mode, local LLM adapters, JSON proposal validation and explicit proposal acceptance with stale-revision checks.
- Durable per-PC draft/transcript storage outside Dropbox, stable story/criterion IDs, workspace/story revisions and cross-tab save protection.
- Requirement handoff schema 0.3, completeness checks and immutable baseline ZIP/JSON/Markdown exports. ZIP includes the pinned capability snapshot, schema and SHA256 manifest. Design consumer acceptance remains pending.
- req-acquire skill, startup helper, handoff validator and setup/integration/model documentation.

Entry point: streamlit_app.py. See [UI setup](docs/req-ui.md), [local LLM options](docs/local-llm.md), [snapshots](docs/capabilities/README.md) and [integration gaps](docs/integration-gaps.md).

Design tooling, full lifecycle state/impact control and firmware execution integration are still planned. The provider was only read; its source changed independently during this work and the importer captured subsequent immutable snapshots rather than modifying it.

## Verification

See [verification](docs/verification.md): automated contract/persistence/API/UI cases passed; req-acquire structure validated; headless Edge rendered the local workspace without an application exception. API tests used a local mock LLM. Real office Gemma inference and hardware work remain NOT RUN.

## Git and local state

No Git repository or remote has been initialized here; no staging, commit or push. Test/preview drafts are external temporary data, not actual user requirements. Actual use defaults to ~/.firmware-dev-life-cycle unless FWLC_DATA_DIR is set. Drafts/transcripts are per PC; exported Design bundles are portable. Dropbox sync status was not independently verified; wait for Up to date before switching PCs.

## Next steps

1. On office, create/activate a Python environment outside Dropbox, install requirements.txt, and launch streamlit_app.py as documented.
2. Install/start Ollama if needed; pull the selected Gemma tag manually, choose Ollama in the UI, list installed models and test E4B versus E2B with short context. Record VRAM, latency and requirement quality.
3. Check provider drift against the desired snapshot. Prepare one reviewed story baseline with criteria/test intent and target-matching recipe references; download and validate the ZIP.
4. Create a Design example consuming that exact baseline, then refine interfaces/recipe mapping and define the minimum firmware execution adapter.
5. Expand source-impact analysis and phase control after the Requirement-to-Design experiment supplies actual findings.

## Open decisions

- Preferred model/quantization/context after office measurements.
- First concrete board/recipe and user requirement for Design integration.
- Long-term repository packaging, state storage and draft transfer across PCs.
- Contract migration, finer-grained impact review and future Design/test UI choices.

## Chat history

| Date | Platform / machine | Chat | Role | App state |
| --- | --- | --- | --- | --- |
| 2026-10-31 .. 11-01 | Codex / portable | `01a19002` ([summary](../../history_chats/codex/portable/2026-10-31_firmware-dev-life-cycle-requirement-workspace.md)) | Defined phase contracts, inspected provider integration gaps, imported timestamped capabilities and built/tested the local Requirement prototype for preparing Design artifacts | Active; no archive action |

## Multi-agent skills and interactive UI experiment

The owner requested root skills.md and an interactive test starting from the UI. Added the role/ownership/assignment playbook and standard skill entrypoints for coordination, Design, Code gen dispatch and Test; req-acquire now supports UI-originated host-agent requests. No parallel engineering agents or automatic phase controllers are implied.

Host agent / interactive queues durable requests through reqstudio.bridge and receives real host-agent responses during the active session, without a local LLM server. Proposals remain user-applied drafts; stale/cancelled requests cannot overwrite newer work. Interactive test started from the existing user-authored walking SSID scanner UI draft. The host agent sent three clarification questions and one unapplied update proposal for US-001, preserving the original story. See docs/interactive-test.md and docs/interactive-session.json. Automated tests: 23 passed; five skills validated. Next: receive user answers/review in the UI, then refine requirements toward an offered Design package. Host mode is served by the active chat agent, not an unattended worker.
## Current operation: independent background agent

Supersedes the manual host-chat requirement above. The owner requested background-agent interaction instead of direct LLM API calls. Implemented reqstudio.worker using installed/logged-in Codex CLI, read-only ephemeral agent runs, structured output and the existing bridge. UI Background agent / CLI provides start/stop, live state, cancellation and explicit retry. Startup helper starts the worker automatically unless -NoWorker is supplied. No chat notification is required.

Verified 37 automated cases and one real isolated CLI job; browser end-to-end results are in docs/background-agent.md. Requests/proposals and existing real drafts are preserved; stories are not auto-applied. Existing Ollama/compatible modes remain optional, not prerequisites. Claude Code CLI was not found on this machine, so Codex CLI is the first implemented runtime. No firmware provider files were changed.

Next: use the active walking SSID scanner draft in Background agent / CLI, submit answers in the UI and review proposals. Check worker state/logs if an error occurs; complete requirements review before offering a Design baseline.

## Per-draft data authorization

Background processing requires explicit per-draft permission to send conversation, stories and capability context to the OpenAI Codex service through the CLI. The UI exposes a persistent authorization checkbox; the worker skips unapproved drafts and stops a running job if permission is revoked. This permission is not engineering approval of the resulting story. The first attempt to start the real-data worker was blocked by automatic approval review pending this explicit payload/destination authorization.

Current regression result after the per-draft authorization gate: **37 tests passed**. The user subsequently explicitly authorized walking SSID scanner and its future messages for the OpenAI Codex service. Its worker was started successfully; other unapproved drafts remain excluded. Synthetic CLI/browser smoke tests remain separate evidence.

Live status update: user-authorized walking SSID scanner uses the independent Codex CLI worker. No chat notification is required. UI start/stop and per-draft revocation remain available.

## Windows status-file contention fix 2026-10-31

Fixed the reported WinError 5 while replacing status.json. Windows readers and writers now coordinate with a per-path named mutex, readers allow delete sharing, and replace uses bounded retry for transient sharing/access errors. A heartbeat lock no longer turns a successful agent job into failure; the last good JSON is preserved and only the writer's temporary file is cleaned up. Worker lock cleanup is protected even if final status publication fails.

43 regression tests passed, including a real Windows delete-sharing lock, concurrent JSON readers, persistent-denial preservation and successful job completion despite a heartbeat lock. UI and worker were reloaded. The matching failed request is retained as history and retried only if its original user turn is still current; draft authorization and story-review boundaries are unchanged.

## Requirement UI simplification 2026-11-01

Replaced the simultaneous left/right workspace with a default Start guide and Scope, Conversation, Review, Handoff and Settings tabs. Sidebar now keeps draft navigation only. Proposals use human-readable stories/criteria by default; JSON diff, engineering mapping and separate artifact files are expandable details. ZIP is the primary Design artifact. Existing data, worker processing, explicit proposal acceptance and contract gates are preserved. No firmware provider changes, no Git initialization or publishing. See docs/req-ui.md for the updated walkthrough.

UI verification: 43 automated cases passed; Edge previews captured for all tabs and 1024 px width. Pending proposals appear first in Review; the saved-story editor is expandable. Live local preview uses port 8501.

## Review tables and draft navigation — 2026-11-01

Settings moved into the sidebar, leaving five workflow tabs. Draft creation/switching now uses callbacks that synchronize active project, selector and URL; forms have project-specific identities. Added regression cases for three successive new-draft clicks, returning to the original draft and preserving original messages.

Review presents proposed and saved stories as tables: Story, As a, want to, so that, acceptance criteria, ambiguity (open_questions). A proposal is still explicitly accepted per row; full criteria/test intent and manual story editing remain expandable. Chat defaults to project-wide discovery, independently of the story editor. Removed the prompt rule restricting new goals to the selected story; req-acquire now decomposes by user value and testability, and context includes unapproved proposals plus criteria/questions of existing goals. No schema change or automatic user-review/Design acceptance. Provider files unchanged. No Git initialization or publishing.
