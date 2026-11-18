# Requirement prototype verification

Date: 2026-10-31 (Asia/Bangkok).

## Automated checks

Twenty pytest cases passed using Python 3.12.6 and Streamlit 1.55.0. Test data and caches were placed outside Dropbox. Coverage includes source-content drift versus timestamp-only changes, snapshot immutability, incomplete requirements, stale proposals, rebinding/constraint-change review invalidation, cross-tab revision conflicts, portable bundle hashes/schema, corrupt bundle rejection, Ollama/OpenAI-compatible local HTTP adapters and Streamlit interactions.

Streamlit AppTest exercised a manual conversation, saved project reload, baseline export, local-model proposal creation and the explicit accept-proposal action. Model output was served by a local mock server; no real Gemma inference is claimed.

The req-acquire SKILL.md passed the bundled skill validator. This validates its structure, not its reasoning quality.

```powershell
python -B -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\fwlc-tests"
```

## Browser check

The local Streamlit server served successfully. An isolated headless Edge browser opened the workspace, created the button/LED example and rendered the story editor without a Streamlit exception. The [UI screenshot](screenshots/requirement-ui.png) records that representative draft view. Built-in browser automation failed to initialize in this environment; the existing Playwright/Edge installation was used for the local rendering check.

## Capability acquisition

The importer read the provider without executing its skills. During implementation, a comparison detected seven changed files and two added recipe/test files despite an unchanged provider Git revision. New immutable snapshots were captured; earlier snapshots remain available. A later provider revision change with identical selected source content was also flagged conservatively. This checks detection of content drift, not semantic impact on every story.

The snapshots themselves record exact UTC/Bangkok capture times, source revision, file hashes/timestamps and imported partial evidence. Provider activity can continue after a capture; run the comparison command before using a snapshot for a new baseline.

## Not yet verified

- Real Gemma E4B/E2B inference, output quality, latency or VRAM usage on office's RTX 4060 8GB.
- Firmware build, flashing, hardware test or current bench readiness.
- Actual Design phase acceptance or code-generation execution integration.
- A full four-phase lifecycle controller or dependency-level semantic impact analysis.

These remain visible experiment/integration tasks; the Requirement artifact is offered to Design with consumer acceptance pending.

## Background worker qualification

37 automated checks passed for the worker-enabled code. Two isolated real Codex CLI jobs and a headless Edge UI-to-worker round trip completed without requiring a chat notification or LLM HTTP endpoint. See [background agent operation](background-agent.md). No actual firmware verification or automatic story acceptance was performed.

Current regression result after the per-draft authorization gate: **37 tests passed**. The user subsequently explicitly authorized walking SSID scanner and its future messages for the OpenAI Codex service. Its worker was started successfully; other unapproved drafts remain excluded. Synthetic CLI/browser smoke tests remain separate evidence.

Live status update: user-authorized walking SSID scanner uses the independent Codex CLI worker. No chat notification is required. UI start/stop and per-draft revocation remain available.

## Windows status-file contention fix 2026-10-31

Fixed the reported WinError 5 while replacing status.json. Windows readers and writers now coordinate with a per-path named mutex, readers allow delete sharing, and replace uses bounded retry for transient sharing/access errors. A heartbeat lock no longer turns a successful agent job into failure; the last good JSON is preserved and only the writer's temporary file is cleaned up. Worker lock cleanup is protected even if final status publication fails.

43 regression tests passed, including a real Windows delete-sharing lock, concurrent JSON readers, persistent-denial preservation and successful job completion despite a heartbeat lock. UI and worker were reloaded. The matching failed request is retained as history and retried only if its original user turn is still current; draft authorization and story-review boundaries are unchanged.

## Tabbed Requirement UI — 2026-11-01

43 existing automated cases passed after the UI restructure (isolated temporary data; no actual requirement changes). Headless Edge rendered all six tabs without Streamlit application exceptions, with screenshots in docs/screenshots/requirement-tabs-0.png through requirement-tabs-5.png and a 1024 px compact view. The default guide, scope form, conversation and review screens were visually inspected. Proposals are presented before the optional story editor, technical JSON is collapsed, and the existing export/proposal acceptance tests pass. No real LLM request or firmware operation was submitted for this UI preview.
