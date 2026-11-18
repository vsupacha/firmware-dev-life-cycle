# Contributing

## Before you start

- Read [README.md](README.md), the [phase contract](docs/phase-contract.md) and, for the Auto and IDE
  pages, [docs/run-ui.md](docs/run-ui.md).
- This project coordinates the skill repositories; it does not copy their build, flash or test logic.
  A new board or stage is a change to `providers/<id>.json`, not new code here, unless no provider
  script can do the step for one app.

## What a change needs

1. `python -m pytest -q` passes.
2. A new stage in a manifest names its gate pattern. A step that changes a board or deletes files has an
   `approve_flag`; never make the runner add it without a recorded approval.
3. Evidence stays honest: created != built != flashed != tested != seen by a person. The pages never
   set the last one.

## Never commit

- Run records and logs (they live in `~/.firmware-dev-life-cycle/`, outside the repository), probe
  serials, COM ports, user names or user paths.
- Requirement drafts or exports of a real product: they belong in that product's own project.
