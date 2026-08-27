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
- Preserve the canonical status identifiers EXACTLY: `VERIFICADO`, `PASS`, `NO VERIFICADO`, `HIPOTESIS`, `EXPERIMENTAL`, `BLOQUEADO`, `DESCARTADO`, `LEGAL_REVIEW_REQUIRED`.
- Do not invent new evidence/status identifiers without an ADR or explicit migration.
- Status and evidence are different dimensions: status `PASS` means an experiment's defined gate passed; evidence levels (`E_NONE`, `E0`–`E5`) record how much was independently verified. A `PASS` experiment is not automatically `E5`, and a rejected plan has no evidence at all (`E_NONE`), never `E0`.
- Never claim in-game correctness from a parser or serializer round-trip.
- Never add an arbitrary `EXECUTE_COMMAND`, shell, eval, or click primitive to a plan schema.
- Use immutable originals and candidate-only writes.
- Fail closed on malformed inputs, unsupported operations, missing evidence, crashes, and timeouts.
- Every write path needs rollback semantics and a receipt/audit trail.
- Never commit Bethesda binaries/assets, `Skyrim.esm`, Creation Kit binaries, or vanilla `.psc` files.
- External tool execution, library linking, and redistribution are distinct licensing acts.

## Current implementation boundary

Validated executable research baselines include:

- `research/poc_002/` - synthetic TES4 parser/safety pipeline (POC-002, `INSPECT_HEADER` against a synthetic fixture);
- `research/poc_ipc_001/` - isolated-worker IPC proof (POC-IPC-001, one trusted read-only operation `INSPECT_SYNTHETIC_INPUT`).

Both remain research POCs and are NOT production authoring backends. Do not silently promote either into production code.

## Canonical experiment numbering

- POC-001: CK UIA/MSAA read-only inspect
- POC-002: synthetic TES4 parser/safety pipeline
- POC-003: PapyrusCompiler dry-invoke
- POC-004: allowlisted xEdit validation

Subprocess IPC work must use an ADR or a distinct `POC-IPC` identifier unless the research index is intentionally migrated.
