# Firmware Development Life Cycle

Skills that control firmware development phases through shared contracts, so each phase can consume identified inputs, produce usable outputs and return work for correction without losing context.

The first implementation follows a capability-aware workflow: inspect existing skills and recipes, then run Requirement -> Design -> Code gen -> Test. Code generation primarily uses the existing automated-firmware-skills toolkit.

## Quick start

Clone this repository and the skill repositories you need side by side in one folder (see Related
repositories), then:

```powershell
python -m pip install -r requirements.txt
./scripts/start-req-ui.ps1 -NoWorker
```

Open http://127.0.0.1:8501 and choose a page:

| Page | Use it to |
|---|---|
| **Auto** | pick a platform, board and template, then run tools > create > build > connect > flash > test by script, with gate results, live logs and artifacts; flashing and deleting need your Approve click |
| **IDE** | create the app and open it in the skill's IDE (VS Code + vendor extension, RT-Thread Studio, App Lab) |
| start page | the Requirement workspace: stories, capability references, export to Design |

Each skill repository needs its own toolchain on the PC; the first stage (`1 tools`) says what is missing.
Requirements: Windows 10/11, Python 3.12, Git for Windows (the stage scripts run in Git Bash).

## Workflow

```text
Initial user need or change request
    -> Capability / recipe preflight
    -> Requirement -> Design -> Code gen -> Test -> Acceptance

Findings -> responsible phase/activity -> affected work and rechecks
```

Preflight is a coordination activity before the four phases. Refresh it when relevant scope, recipes, provider versions or bench availability change. It establishes what is supported and how it can be tested; it does not generate the production candidate or prove that the requested behavior works.

| Step | Main work | Handoff output |
| --- | --- | --- |
| Capability / recipe preflight | Inspect supported boards/frameworks, recipe parameters, extension points, evidence levels, test capabilities and current tools/hardware readiness. | Versioned capability snapshot and feasibility gaps. |
| Requirement | Preserve user intent, define scope and acceptance criteria, classify feasibility and plan how each criterion will be checked. | Requirements baseline, capability mapping, acceptance test intent and scoped development plan. |
| Design | Define behavior and interfaces, map them onto recipes/configuration, and specify supported customization and test instrumentation. | Design baseline with requirement coverage, recipe mapping and code-generation instructions. |
| Code gen | Use provider skills to create or update code/configuration, preserve owned changes on regeneration, build and identify the candidate. | Generation record, source/configuration baseline, candidate manifest and build evidence. |
| Test | Check readiness, run applicable acceptance and regression checks, analyze results and route findings. | Requirement-to-evidence report and explicit acceptance outcome for the identified candidate. |

Design is included in the first complete example. Test planning starts in Requirement and is refined in Design; execution against the candidate happens in Test. Requirements feasibility is separate from proof that the firmware meets its requirements.

## Contract and coordination

The [phase contract](docs/phase-contract.md) defines input/output ownership and revisions, entry/exit conditions, handoff acceptance, evidence identity, change propagation and resumable state. A completed producer run is separate from consumer acceptance.

The coordinator selects eligible work, records blockers and returns findings to the phase that owns the problem. It preserves the requested scope when a recipe cannot support it: record the gap and resolve it through an alternative recipe, an explicit scope decision or separately scoped capability development.

## Execution boundary

The primary development environment is Claude Code. Contracts and project state must remain usable without private conversation history. The execution providers are the four sibling skill repositories (bare metal, FreeRTOS, RT-Thread, EmbLinux; see Related repositories). This project coordinates its skills rather than reproducing their build, flash, debug and target-test scripts.

The provider's M1-M5 milestones describe available engineering capabilities; Requirement, Design, Code gen and Test describe development phases. Record them independently. Supported capability, historical verification level and current bench readiness are separate facts.

Keep execution local initially, consistent with the existing decision to defer CI/CD. Provider identity, authorization and ACTION gates continue to apply. A phase transition grants no additional permission to install tools, enable milestones, flash hardware or publish work.

## Project scope and documents

- [Phase contract](docs/phase-contract.md): draft v0.3, with activities, artifacts, gates, feedback and the implemented Requirement handoff.
- [Development plan](PLAN.md): contract example, schema/validator, provider adapter and first four phase skills.
- [Handoff](HANDOFF.md): current state, decisions and the next concrete task.

Reusable contracts, skills and examples belong here. Application-specific requirements, design, sources and evidence records belong in that application's own project. Raw evidence and bench data follow the execution provider's local-storage rules.

Release and Maintenance remain later extensions. Release preparation will consume an accepted candidate and its evidence; maintenance will route changes through the affected phases. Their implementation is outside the first four-phase workflow.

## Requirement prototype

The local Streamlit workspace now implements the Requirement experiment: a Start guide and step-based tabs for scope, conversation, story review and Design handoff, imported capability references, local LLM proposals, durable drafts and a versioned Requirement to Design export.

```powershell
python -m pip install -r requirements.txt
./scripts/start-req-ui.ps1
```

Open [the local UI](http://127.0.0.1:8501). For a per-PC environment outside Dropbox, follow the [UI setup and workflow](docs/req-ui.md). Model options and the office RTX 4060 experiment are described in [local LLM setup](docs/local-llm.md). Ollama and OpenAI-compatible local endpoints are supported; Manual/offline mode works without a model. No model is downloaded automatically.

Provider facts are imported read-only into [timestamped Markdown/JSON snapshots](docs/capabilities/README.md). Source hashes detect changes; drafts keep their selected snapshot until explicitly rebound. See the [integration assessment](docs/integration-gaps.md) for provider features and remaining adapter work.

Exported ZIPs include requirements JSON/Markdown, the pinned capability snapshot, a schema and a hash manifest. Validate with `python scripts/validate_handoff.py <bundle.zip>`. A valid package is offered to Design, not accepted by Design or proven on hardware.

The [req-acquire skill](skills/req-acquire/SKILL.md) documents the acquisition workflow. Only the Requirement schema/UI and snapshot acquisition are implemented so far; Design tools, firmware execution integration and the full lifecycle controller remain planned.

## Auto and IDE pages (milestone 1)

Two pages of the UI execute the provider skill scripts. **Auto** runs the scripted path (tools, create, build, connect, flash, test, debug status, delete) and **IDE** creates the app and opens it in the skill's IDE. Auto executes the existing provider skill scripts for a selected board and shows stages, gate results, live logs and artifacts. Four targets are wired through `providers/*.json`: NUCLEO-C562RE (bare metal), STM32L476G-DISCO (FreeRTOS), Titan Board (RT-Thread) and UNO Q (EmbLinux), with blink or hello-world. Steps that change a board stop and need the developer's Approve click, tied to the image hash. Deleting an app also needs an Approve click. See [Auto and IDE pages](docs/run-ui.md) for the rules, the files and what was verified. The Requirement and Design hand-offs do not feed a run yet.

## Related repositories

Five repositories work together; each one is usable on its own.

| Repository | Scope |
|---|---|
| [automated-firmware-skills](https://github.com/vsupacha/automated-firmware-skills) | bare-metal MCU skills (STM32Cube, PlatformIO, ModusToolbox, MCUXpresso) and the support tool skills: firmware-test, cleanroom-test, hw-troubleshooting, sensor-debug, web-wizard |
| [automated-firmware-skills-freertos](https://github.com/vsupacha/automated-firmware-skills-freertos) | FreeRTOS skills (STM32 C5, F3, L476) |
| [automated-firmware-skills-rtthread](https://github.com/vsupacha/automated-firmware-skills-rtthread) | RT-Thread skills with Kconfig recipes (Renesas RA8 Vision Board and Titan Board, PSOC Edge Edgi-Talk) |
| [automated-firmware-skills-emblinux](https://github.com/vsupacha/automated-firmware-skills-emblinux) | embedded-Linux boards (Arduino UNO Q: App Lab Bricks + Zephyr sketch) |
| **firmware-dev-life-cycle** (this repository) | local web UI and phase contracts: pick a board, run the stages of any repository above (Auto page) or create an app and open its IDE (IDE page), with gates, logs and artifacts on screen |

To use several, clone them side by side in one folder; `firmware-dev-life-cycle` then finds the skill
repositories there (its `providers/*.json`). They share conventions - stage numbers, gate lines, exit code
10 with an `ACTION:` line for a developer step, one per-PC apps workspace in `~/.fw-skills.env` - but no
code: `lib/` is a copy in each repository.

## Agent-guided operation

Read [skills.md](skills.md) for role ownership, multi-agent handoffs and phase skill routing. The Requirement UI now supports an independent Background agent / CLI worker. It receives UI requests and replies automatically through the saved-state bridge; no chat notification or direct HTTP LLM endpoint is needed. Design/Code gen/Test skill procedures are documented, while their automated controllers remain planned.

See [background agent setup](docs/background-agent.md) for the CLI login, start/stop, job states and local logs. Local LLM endpoints remain optional.

## License

MIT - see [LICENSE](LICENSE). See also [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
