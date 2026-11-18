# Background Requirement agent

Updated 2026-10-31. The normal interactive path is UI -> durable request queue -> independent local worker -> authenticated Codex CLI -> validated reply/proposals -> UI refresh. Users do not need to notify this chat after sending a message.

## Runtime and start

Codex CLI is the first implemented runtime because it is installed and logged in on this machine. Claude Code CLI was not found; no Claude backend is claimed. The UI does not call an LLM HTTP endpoint in background mode. The CLI uses its own login, service and usage limits; this is not offline inference.

From this project, run `./scripts/start-req-ui.ps1`. It starts one worker for the current FWLC_DATA_DIR and then Streamlit. Add `-NoWorker` for manual/local-LLM-only use. Alternatively run Streamlit and click Start worker in the sidebar. New sessions default to Background agent / CLI when a worker is ready; links with agent=background select it explicitly. Existing agent=host links now default to background mode, with the manual host fallback still selectable.

The worker is a hidden independent Python process. It survives browser refresh and this chat ending; stop it using the sidebar or `python -m reqstudio.worker stop`. It is not installed as an OS startup service and must be started again after a reboot. Starting it twice returns the existing worker instead of duplicating it. Authentication changes are handled by the user through `codex login`, never by the application.

## Execution contract

Each request pins its user turn, selected story, snapshot/target/constraints and context signature. The worker reads skills.md and req-acquire/SKILL.md into a bounded Requirement-only assignment, together with the contract context and recent conversation. It starts a fresh ephemeral `codex exec` run, passing the prompt via stdin, using read-only sandboxing and an output schema. No bypass flags are used. The agent is instructed to return only reply/questions/proposals without tools or engineering operations.

Only the worker applies the validated response to the conversation/proposal queue. It does not apply a proposal to a story, mark review complete, export a baseline, change provider firmware or execute other SDLC phases. Parent requirements and consumer acceptance gates remain intact. The future extension point is a role/runtime adapter, not an unrestricted shell-command text box.

Request states: pending -> processing -> completed or failed. Cancelled and stale are terminal alternatives. The claiming worker ID owns publication. New requests are blocked while one is pending/processing. A changed context stops/discards the obsolete run. Failed/stale/cancelled requests can be explicitly retried against current context through the UI; errors do not trigger automatic paid retry loops.

## Visibility and recovery

The UI polls worker heartbeat and project state every two seconds. It shows idle/running/offline, request errors, cancellation and retry actions. The timeout is selected before starting the worker; restart it to change the timeout of the active process. Default is 180 seconds, selectable up to 600 seconds.

Worker stop/cancellation terminates only the CLI process tree owned by that job. On restart, a processing request whose owner process has died is marked failed for explicit retry. Locks are replaced only when their recorded owner is dead. Concurrent draft saves still use the existing revision/lock checks; a stale response cannot overwrite a later user edit.

Worker status and logs live outside Dropbox under the current data directory:

- worker/status.json: process identity, heartbeat, active/last job and last error.
- worker/worker.log: worker startup/process diagnostics.
- worker/jobs/<request-id>/prompt.txt, agent.log and response.json: per-request input and output.

These local files contain engineering conversation data and are not exported or committed automatically. Preserve a useful job log when diagnosing failure. No credentials are copied into the project. Installed executable paths are discovered at runtime.

## Verification

37 automated tests passed, including singleton ownership, context staleness, duplicate claims, cancellation, timeout, interrupted requests, malformed CLI output and UI queue/reply behavior. Existing Requirement/export/API fallback tests remain passing.

Two isolated jobs ran through the real logged-in Codex CLI, with synthetic data in TEMP. The first completed in about 10 seconds. A headless Edge browser then submitted a second message through the UI and received a Thai clarification automatically, without a chat notification or direct HTTP LLM client. No Streamlit exception occurred; see the [background UI screenshot](screenshots/background-worker-ui.png). These jobs are test data, not approved user requirements or firmware verification.

Official CLI references: [non-interactive execution](https://developers.openai.com/codex/noninteractive), [CLI flags](https://developers.openai.com/codex/cli/reference). Installed CLI help was also checked for output-schema, output-last-message, ephemeral and read-only support.

## Per-draft data authorization

Background processing requires explicit per-draft permission to send conversation, stories and capability context to the OpenAI Codex service through the CLI. The UI exposes a persistent authorization checkbox; the worker skips unapproved drafts and stops a running job if permission is revoked. This permission is not engineering approval of the resulting story. The first attempt to start the real-data worker was blocked by automatic approval review pending this explicit payload/destination authorization.

Current regression result after the per-draft authorization gate: **37 tests passed**. The user subsequently explicitly authorized walking SSID scanner and its future messages for the OpenAI Codex service. Its worker was started successfully; other unapproved drafts remain excluded. Synthetic CLI/browser smoke tests remain separate evidence.

Live status update: user-authorized walking SSID scanner uses the independent Codex CLI worker. No chat notification is required. UI start/stop and per-draft revocation remain available.

## Windows status-file contention fix 2026-10-31

Fixed the reported WinError 5 while replacing status.json. Windows readers and writers now coordinate with a per-path named mutex, readers allow delete sharing, and replace uses bounded retry for transient sharing/access errors. A heartbeat lock no longer turns a successful agent job into failure; the last good JSON is preserved and only the writer's temporary file is cleaned up. Worker lock cleanup is protected even if final status publication fails.

43 regression tests passed, including a real Windows delete-sharing lock, concurrent JSON readers, persistent-denial preservation and successful job completion despite a heartbeat lock. UI and worker were reloaded. The matching failed request is retained as history and retried only if its original user turn is still current; draft authorization and story-review boundaries are unchanged.
