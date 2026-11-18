# Capability snapshots

This directory stores immutable imports from automated-firmware-skills. Each `CAP-*.md` is a human-readable snapshot and has a matching `CAP-*.json` machine-readable sidecar. Filenames contain capture time in UTC; documents also record UTC and Bangkok timestamps, provider revision, source-file timestamps and SHA256 fingerprints.

## Refresh and compare

From this project root:

```powershell
python -m reqstudio.capabilities check --provider ../automated-firmware-skills
python -m reqstudio.capabilities refresh --provider ../automated-firmware-skills
```

Check defaults to the newest imported snapshot. Use `--snapshot docs/capabilities/<CAP-id>.json` to check a specific baseline's snapshot. Exit 0 means current; exit 2 means changed or provider unavailable. The JSON output distinguishes changed, added and removed source files and records the check timestamp.

Refresh reads only the provider and creates new snapshot files here; it never changes provider source, tool settings, firmware or active milestones. A capture is rejected if the source changes during acquisition. It records actual working-tree content, including uncommitted changes, instead of assuming Git HEAD describes all files.

The importer allowlists project/board/skill documentation, catalog/profile data and relevant source/scripts. It excludes apps, benches, private handoffs, logs, reports, caches, hidden subdirectories, binaries and oversized files. `CLAUDE.local.md` and personal runtime configuration are not imported. See `reqstudio/capabilities.py` for the exact selection.

Content hashes drive freshness. Filesystem timestamp changes alone do not mean a capability changed. Provider revision changes trigger review even when selected file hashes are unchanged. The comparison is deliberately conservative: it reports source drift, not a semantic proof that a particular requirement became invalid.

## Reading a snapshot

Separate documented support, imported evidence and current readiness. Operations present means the corresponding script exists, not that it ran successfully here or supports every option. The import never performs a build, device discovery, flash or test. Current readiness is `not_probed`.

The Markdown includes board/profile/template evidence, driver recipe declarations, integration limitations and source notes captured verbatim at that time. Source notes can contain their own older update dates or partial results; preserve those qualifications. A declared recipe status and a prose note with narrower evidence remain visible rather than being promoted to an invented aggregate PASS.

## Existing requirements

A draft pins one snapshot ID. Creating a newer snapshot does not rebind it. In the UI, select the new snapshot and explicitly apply it to the draft; all stories then require renewed feasibility assessment/review and old model proposals are discarded. Existing exported bundles keep their exact original snapshots.

Known source drift blocks a new handoff until refresh/review. If the source is unavailable on another PC, an offered handoff may be prepared from the pinned import, but it records freshness unavailable and requires Design to verify the provider before acceptance.
