# Auto and IDE pages: execute and monitor provider stages

Added 2026-11-16 (home); the first version was one page called Run, renamed **Auto** the same day
when the **IDE** page was added. Both are pages of the local Streamlit workspace
(`pages/1_Auto.py`, `pages/2_IDE.py`; shared body `runstudio/ui.py`). They invoke the existing skill scripts of the provider
repositories for a selected board and shows stages, gates, logs and artifacts. It does not replace
or copy those scripts.

```powershell
./scripts/start-req-ui.ps1          # then open http://127.0.0.1:8501/Auto or /IDE
```

## Parts

| Part | File | Role |
| --- | --- | --- |
| Provider manifests | `providers/<id>.json` | Per repository: targets (board, skill, templates) and stages (command, gate pattern, approval flag, image the approval is bound to, artifact globs, evidence level). The provider repositories are not changed. |
| Run store | `runstudio/store.py` | Run record `<data>/runs/<run_id>/run.json`, append-only `events.jsonl`, `logs/<nn>-<stage>-a<attempt>.log`; approvals, retry, skip, cancel request. `<data>` = `FWLC_DATA_DIR` or `~/.firmware-dev-life-cycle` (outside Dropbox). |
| Stage runner | `runstudio/runner.py` | Detached process per "Run" click: `python -m runstudio.runner <run_id> [--one]`. Runs stages in order until one stops; survives a closed browser. |
| Flows | `flows` in each manifest | `auto` = the scripted path; `ide` = tools, create, open IDE. A run belongs to one flow and holds only that flow's stages. |
| Delete step | `runstudio/builtin.py` | The manager's own per-app delete (see Stages). |
| Pages | `pages/1_Auto.py`, `pages/2_IDE.py`, `runstudio/ui.py` | Target picker, stage rail, action panel, live log (1 s refresh), artifact table, history. |

## Rules the page cannot override

- A stage is **passed** only when its script exits 0 **and** prints a line matching the manifest's
  gate. Exit 0 without the gate line is a failure.
- Exit 10 or an `ACTION:` line = **waiting**. Nothing after it runs until the developer acts.
- The approval flag (`--yes`) is added only after **Approve** on a stage waiting on
  `ACTION: APPROVE`. The approval records the action text, the board and the image hash; a changed
  image invalidates it, and it is used for one execution.
- Other actions (`CONNECT`, `SETUP`, `CHOOSE`) offer only **Retry stage** and **Skip stage**.
- A skipped stage stays visible and adds no evidence. Evidence levels are shown separately:
  created, built, flashed, tested. "Seen by a person" is never set by the page.
- A stage left running with no live runner is shown as failed (interrupted), never passed.
- Provider bench locks, identity checks and milestones still apply inside the scripts.

## Milestone 1 targets

| Platform | Manifest | Board | Skill | Templates |
| --- | --- | --- | --- | --- |
| Bare metal | `bare-metal.json` | `nucleo-c562re` | `cubemx2-hal2-stm32c562nucleo` | blink, hello-world |
| FreeRTOS | `freertos.json` | `stm32l476g-disco` | `cubemx-freertos-stm32l476disco` | blink, hello-world |
| RT-Thread | `rt-thread.json` | `titan-board` | `scons-rtthread-titanboard` | blink, hello-world |
| EmbLinux | `emblinux.json` | `uno-q` | `applab-zephyr-unoq` | hello-world, blink |

## Stages

| Flow | MCU targets | UNO Q |
| --- | --- | --- |
| Auto | 1 tools, 2 create, 3 build, 4 connect, 5 flash, 6 test, 7 debug, 16 delete | tools, create, req, arch, code, connect, build, run, test, 16 clean board, 16 delete |
| IDE | 1 tools, 2 create, 2d open IDE | tools, create, 2d open IDE (App Lab) |

- **7 debug** is the read-only status: `debug.sh status <board>` (gate `DEBUG: STATUS ...`, exit 1 =
  fault) on the two ST targets; `msh_status.py` on the Titan Board (label "7 status"). Scripted
  breakpoint scenarios (`debug.sh run`) are not wired.
- **16 delete** removes this run's app folder on the PC and nothing else. The provider `clean.sh`
  scripts work on the whole apps workspace, so the manager does this step itself
  (`runstudio/builtin.py`): it lists the folder, stops with `ACTION: APPROVE`, and after the Approve
  click deletes only a direct child of the apps workspace that holds the skill's marker file
  (`cubemx-app.env`, `l476-app.env`, `rtt-app.env`, `uq-app.env`). The board keeps its image.
  **Skip stage** keeps the app.
- **16 clean board** (UNO Q) is the provider's `clean.py`: removes the app copy on the board, asks first.
- **2d open IDE** runs the skill's `open_ide` script (VS Code + STM32CubeIDE extension, RT-Thread
  Studio, App Lab); a missing IDE is `ACTION: SETUP`. Build, flash and debug are then done in the IDE
  and are not recorded by the page.
- Runs made before the flows existed keep their six (or nine) stages and are listed under Auto.
 Adding a board = one more entry in a manifest's `targets`.

Settings: `FWLC_PROVIDER_BARE_METAL` / `_FREERTOS` / `_RT_THREAD` / `_EMBLINUX` override a provider
folder; `FWLC_BASH` names Git Bash (default `Program Files/Git/bin/bash.exe`, never WSL's bash);
the apps workspace is the providers' own (`FW_WS` or `~/.fw-skills.env`).

## Verified 2026-11-16 (home PC), nothing flashed

- Tests: 8 new cases in `tests/test_runs.py` against a fake provider (pass chain, exit 0 without
  gate, approval bound to the image and used once, non-approvable action, fail/skip/warnings, cancel
  and interrupted, real manifests name existing scripts, name checks). Whole suite: 55 passed.
- Real runs through the runner, no approval given:
  - bare metal `nucleo-c562re` blink: tools, create (59 s), build, connect passed; flash stopped
    at `ACTION: APPROVE`.
  - FreeRTOS `stm32l476g-disco` blink: tools, create (30 s), build, connect passed; flash stopped
    at `ACTION: APPROVE`.
  - RT-Thread `titan-board` blink: tools stopped at `ACTION: SETUP` (SDK Titan-Board 1.0.2 is not
    installed in RT-Thread Studio on this PC), so create and build did not run here.
  - EmbLinux `uno-q` hello-world: tools, create, req, arch, code passed; connect stopped at
    `ACTION: CONNECT` (no board attached).
- Browser: the page rendered the four runs; selecting a run showed the stage rail, the approval
  panel with image hash, the log and the artifact table; **Retry stage** on the UNO Q connect stage
  started the runner and the page showed the new attempt.

## Not verified

- Approve, flash and test from the page on any board (needs the developer's click).
- Titan Board create and build on this PC; UNO Q connect, build, run and test.
- hello-world for the three MCU targets; Cancel from the page during a real stage (covered only by
  the automated test); two runs started at the same time on one board.

## Added later on 2026-11-16 (home)

- Gate and `ACTION:` lines with the test runner's time stamp (`[   2.937] RESULT: PASS ...`) are
  recognised (the first C5 test stage was shown as failed although the test passed).
- The owner approved the C5 flash from the page: flash passed, test `RESULT: PASS (6/6 passed, 1
  skipped)` after the fix - evidence "tested" (the look step was skipped, so not "observed").
- Auto / IDE split, 7 debug, 16 delete. Suite: 57 passed. Real checks on the C5: `7 debug` passed
  (`DEBUG: STATUS running fault=none`); `16 delete` stopped at `ACTION: APPROVE` for
  `C:/fw-ws/ui-bl-c5` and was NOT approved (nothing deleted on a real app; the delete itself is
  covered by the automated test); IDE flow `ide-bl-c5`: tools, create, open IDE passed
  (`IDE: OPENED in VS Code`). Both pages rendered in the browser.
- Not verified: IDE flow and the new stages on the L476, Titan and UNO Q; `16 clean board`; delete
  approved from the page on a real app.
