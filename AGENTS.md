# AGENTS.md

## Mission

Build a safety-first Skyrim SE/AE authoring agent without overstating runtime evidence.

## Non-negotiable priorities

1. Security
2. Data integrity
3. Correctness
4. Reproducibility
5. Tests
6. Maintainability
7. Performance
8. Convenience

## Architectural rule

- AI decides **WHAT**.
- Deterministic software decides **HOW**.
- Validators decide **WHETHER IT WORKED**.
- Human approval decides **WHETHER TO ACCEPT**.

## Required behavior

- Work on a branch; never push experimental work directly to `main`.
- Preserve evidence labels: `VERIFIED`, `NO_VERIFICADO`, `HIPOTESIS`, `EXPERIMENTAL`, `BLOQUEADO`, `DESCARTADO`, `LEGAL_REVIEW_REQUIRED`.
- Never claim in-game correctness from a parser or serializer round-trip.
- Never add an arbitrary `EXECUTE_COMMAND`, shell, eval, or click primitive to a plan schema.
- Use immutable originals and candidate-only writes.
- Fail closed on malformed inputs, unsupported operations, missing evidence, crashes, and timeouts.
- Every write path needs rollback semantics and a receipt/audit trail.
- Never commit Bethesda binaries/assets, `Skyrim.esm`, Creation Kit binaries, or vanilla `.psc` files.
- External tool execution, library linking, and redistribution are distinct licensing acts.

## Current implementation boundary

Only `research/poc_002/` is executable and validated. It supports `INSPECT_HEADER` against a synthetic fixture. Do not silently promote it into production code.

## Canonical experiment numbering

- POC-001: CK UIA/MSAA read-only inspect
- POC-002: synthetic TES4 parser/safety pipeline
- POC-003: PapyrusCompiler dry-invoke
- POC-004: allowlisted xEdit validation

Subprocess IPC work must use an ADR or a distinct `POC-IPC` identifier unless the research index is intentionally migrated.
