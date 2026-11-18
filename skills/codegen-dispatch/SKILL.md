---
name: codegen-dispatch
description: Execute an accepted firmware design through existing provider skills, preserving source ownership and returning candidate/build provenance. Use for the Code gen phase after design and readiness checks.
---

# Dispatch code generation

Read [skills.md](../../skills.md), the Code gen contract in [phase-contract.md](../../docs/phase-contract.md), and only the selected provider skill. Validate design/requirement/snapshot revisions, recipe parameters, readiness and existing source ownership before any change.

Use automated-firmware-skills operations rather than a second build/flash path. Follow its gates and ACTION requests. Record provider/profile/configuration versions, source baseline, customization and actual output/image hashes. Preserve user-owned edits and Test-owned specifications; stop regeneration when preservation is undefined.

Return architectural or recipe changes to Design. Separate build and behavior evidence, application and unit-test images, and planned versus executed operations. This skill is agent-guided; the project's automatic execution adapter is not implemented. A design or assignment is not additional hardware/publication authorization.
