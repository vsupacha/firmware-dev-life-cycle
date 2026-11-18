# Requirement workspace

The local Streamlit prototype acquires user stories and prepares a Requirement to Design artifact. It does not build, flash or test firmware, implement a Design canvas, or change the execution provider.

## Start on Windows

Use Python 3.11+ (tested with Python 3.12.6). Keep the environment and working data outside Dropbox. From this project directory, create a local environment once:

```powershell
python -m venv "$env:LOCALAPPDATA\fwlc-venv"
& "$env:LOCALAPPDATA\fwlc-venv\Scripts\python.exe" -m pip install -r requirements.txt
& "$env:LOCALAPPDATA\fwlc-venv\Scripts\python.exe" -m streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Then open [the local requirement workspace](http://127.0.0.1:8501). Alternatively, activate your environment and run `./scripts/start-req-ui.ps1`. Stop the server with Ctrl+C. This is local-only; nothing is deployed to Sites hosting.

## Layout and workflow

The workspace uses sequential tabs rather than a split chat/editor screen. The default tab is **เริ่มต้น** (Start), an embedded guide explaining principles, inputs, outputs and a concrete example. The sidebar selects/creates/reloads drafts and contains a collapsed Settings section for agent/worker/capability controls.

1. **1 · ขอบเขต (Scope):** project name, optional initial target board and constraints. Name/board are required by handoff checks; unknown inputs may be clarified through chat first.
2. **2 · สนทนา (Conversation):** describe the real need in ordinary language and answer the agent's questions. Conversation defaults to project-wide goal discovery; choose a specific story explicitly in the conversation topic selector when refining it. Selecting a row for editing in Review does not force chat into that story. Chat is saved; it is not the exported contract.
3. **3 · ตรวจทาน (Review):** compare proposals and saved stories in tables with Story, As a, want to, so that, acceptance criteria and ambiguity columns. Ambiguity maps directly to saved open_questions; an empty list means no recorded questions, not proof of semantic completeness. Select a proposal to read its full criteria/questions and explicitly accept it; expand the saved-story editor to edit and save a story. Criteria include a test intent and hardware flag. Engineering feasibility/mapping is collapsed until needed before handoff. Mark a story reviewed only after checking its meaning. Technical before/after JSON is optional collapsed detail.
4. **4 · ส่งต่อ Design (Handoff):** resolve completeness issues, check source drift and create the offered baseline. Download the complete ZIP as the primary artifact. Human-readable preview and separate JSON/Markdown files are optional expandable details. Users do not author JSON.
**Sidebar → ตั้งค่า (Settings):** agent connection, per-draft data authorization, worker controls and capability snapshot management. Background agent / CLI is the primary automatic interaction path; local/API and offline modes remain available.

Tabs reduce visible controls; they are not phase gates. Users can return to earlier steps. Existing durable state, explicit proposal acceptance, revision checks, capability rebinding and handoff validation still apply. Changing scope/snapshot can require renewed review. A baseline is offered to Design; Design acceptance remains pending.

Test intent describes how a criterion will be proven; the requirement phase does not execute that test. Do not infer physical LED observation from console readback alone. The supported status is the user's reviewed feasibility assessment against imported claims, not a new hardware certification.

## Persistence and revisions

Drafts and transcripts are saved under `~/.firmware-dev-life-cycle/projects/<project-id>/state.json`. Set `FWLC_DATA_DIR` to use another local directory. API keys stay in session memory and are not persisted or exported. This prototype stores local conversation data unencrypted; use non-sensitive engineering input for experiments.

Edits increment story/workspace revisions. Target or constraint changes clear prior feasibility/review; rebinding to a new capability snapshot does the same and clears old proposals. A stale model update is rejected instead of overwriting a newer story. Concurrent saves use an exclusive lock plus a workspace-revision check; use Load latest after another tab changes a project.

Capability snapshots are shared project artifacts under `docs/capabilities/`. Drafts reference an exact snapshot ID. Refresh never silently changes a draft's pinned snapshot. This initial implementation conservatively requires review of all stories after rebinding; fine-grained impact assessment is future work.

Draft working data is per PC and does not automatically move to office/home. Transfer a downloaded handoff ZIP to continue in Design; full draft/transcript import into the UI is not implemented yet.

## Design handoff

The ZIP contains:

- `requirements.json`: canonical versioned requirement contract.
- `requirements.md`: readable view of that contract.
- `capability_snapshot.json` and `.md`: the exact pinned provider facts/source notes.
- `requirements-handoff.schema.json`: schema version 0.3.
- `README.md`: consumer instructions.
- `manifest.json`: baseline identity and SHA256 hashes of package members.

Validate before consuming:

```powershell
python scripts/validate_handoff.py <requirements-r001.zip>
```

Validation checks integrity, structure, target/reference consistency and completeness. Design still checks meaning, recipe composition, configuration, interfaces and engineering feasibility. A handoff made without the provider source carries a required source-verification check for Design. No hardware operation is performed by export.

Historical bundles are saved outside Dropbox in the project's local `handoffs/` directory and remain downloadable. Editing a draft does not rewrite them. Chat transcripts are not included in the handoff; source-turn IDs are provenance references to the local draft.

## Current limits

No automatic execution of provider skills, Design editor, test runner or full lifecycle controller exists yet. The agent uses the selected story in full, summaries of other stories and at most eight recent chat turns; old turns may be omitted to fit the estimated context budget. The complete transcript remains saved. Large requests/contracts may require selecting a narrower story or increasing local model context. Token estimation is approximate.

API adapters have automated local-mock coverage. Gemma inference quality, speed and VRAM usage must still be measured on the office RTX 4060 8GB. Readiness is deliberately not inferred from a saved capability snapshot.

## Host agent interactive mode

Choose Host agent / interactive to send a durable local request to the agent in the active chat. It does not call Ollama or install a model. The agent reads the inbox, replies and offers draft proposals; the UI polls for that reply and never applies it automatically. Pending requests can be cancelled. A context change invalidates an old response.

This mode works while a host agent is actively serving the experiment. It is not a background daemon: after the chat pauses/ends, no autonomous reply is promised. Use Ollama or a compatible server for self-contained inference. See [skills.md](../skills.md) for the request/response protocol.
## Background agent mode (primary interactive path)

Use Background agent / CLI to receive automatic replies independent of this chat. The startup helper now starts the worker unless -NoWorker is supplied; when running Streamlit directly, use Start worker in the sidebar Settings section. A logged-in Codex CLI is required, but no LLM API URL/key is configured in this mode. See [background-agent.md](background-agent.md) for status, timeouts, cancellation, retry and logs. The older host-agent section above describes a manual diagnostic fallback.

## Per-draft data authorization

Background processing requires explicit per-draft permission to send conversation, stories and capability context to the OpenAI Codex service through the CLI. The UI exposes a persistent authorization checkbox; the worker skips unapproved drafts and stops a running job if permission is revoked. This permission is not engineering approval of the resulting story. The first attempt to start the real-data worker was blocked by automatic approval review pending this explicit payload/destination authorization.

## Story grouping and draft navigation (2026-11-01)

The earlier selected-story prompt encouraged a single oversized story. Requirement acquisition now groups independently valuable/testable user goals, reuses an existing story only for the same goal and allows up to five focused proposals. Components and recipe steps are not user stories. Example: scan-and-save, setting time, clearing logs and viewing summary can be separate stories; CSV fields, duplicate-SSID handling and empty scans are criteria under scan-and-save. Previously unapplied proposals are supplied as unapproved context to avoid losing their unresolved details.

New draft and draft switching use callbacks before widgets are constructed. Project state, selector and URL are updated together; forms and selection keys are scoped to the project so repeated creation and identical story IDs in different drafts cannot reuse old form contents. New drafts have a distinct short identifier. Existing drafts and baseline files are retained.
