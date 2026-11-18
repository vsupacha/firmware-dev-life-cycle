---
name: design-contract
description: Consume a versioned firmware Requirement package and produce architecture, interface and recipe mappings for Code gen, or return precise requirement/capability gaps. Use for the Design phase, including a consumer review of a requirement handoff.
---

# Produce a design contract

Use [skills.md](../../skills.md) for ownership and [the phase contract](../../docs/phase-contract.md) for Design activities and handoff gates. Validate the input ZIP with scripts/validate_handoff.py; this validates structure, not feasibility. Record consumer acceptance/rejection separately from the immutable Requirement package.

Cover each offered criterion. Define behavior, states/data flow, interfaces, relevant budgets and error handling, then map them to provider skill/recipe/profile revisions, parameters and supported customization. Declare generated/owned regions, regeneration behavior, outputs and checks needed by Code gen. Reference board facts; do not invent pins or APIs.

Return a finding to Requirement for ambiguous behavior/criteria, or to preflight for unsupported capabilities. Do not silently change the upstream requirement to suit a recipe. Deliver an identified Design artifact with exact input references and unresolved blockers; no executable Design controller or canvas is implied.
