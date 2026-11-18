---
name: test-evidence
description: Verify a firmware candidate against pinned requirement/design criteria and maintain per-case evidence, coverage and routed findings. Use for Test planning, execution and acceptance assessment.
---

# Verify and report evidence

Read [skills.md](../../skills.md) and the Test/evidence sections of [phase-contract.md](../../docs/phase-contract.md). Identify exact criteria, test revisions, source/configuration, candidate image and target/profile before selecting checks.

Maintain criterion-to-case-to-run-to-evidence links. Execute supported provider checks through existing gates. Separate build, programming, boot, unit tests, target behavior and human observation. NOT RUN/SKIPPED applicable required checks block acceptance; a provider PASS on selected cases is not full-plan acceptance.

Preserve a reproducer and expected/actual evidence for findings. Route requirement ambiguity to Requirement, interface/recipe problems to Design, code defects to Code gen and test/bench faults to Test/readiness. Re-run affected checks after correction. Deliver identified results and an acceptance recommendation; do not modify upstream criteria to make a test pass.
