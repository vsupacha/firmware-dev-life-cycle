# Changelog

## Unreleased

- 2026-11-16: **Auto** and **IDE** pages. Provider manifests (`providers/*.json`) for the bare-metal, FreeRTOS,
  RT-Thread and EmbLinux skill repositories; run store and detached stage runner (`runstudio/`); stages pass
  only on exit 0 plus the gate line; steps that flash a board or delete an app need an Approve click that is
  bound to the image hash and used once. Auto: tools, create, build, connect, flash, test, debug status,
  delete. IDE: tools, create, open IDE. See docs/run-ui.md for what was run on hardware.
- 2026-11-16: release files (LICENSE, CONTRIBUTING.md, SECURITY.md, this file), README quick start and Related
  repositories, `scripts/check_provider_libs.py` (reports differences between the `lib/` copies of the skill
  repositories).
- 2026-10-31: Requirement workspace (Streamlit): capability snapshots imported from the provider repositories,
  story review, local LLM proposals, background agent worker, versioned Requirement to Design export with a
  schema and a hash manifest (`scripts/validate_handoff.py`).
