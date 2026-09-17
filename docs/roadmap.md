# Roadmap

This roadmap is evidence-gated. Passing one proof does not authorize every later feature.

## Gate 1 — Research

**Status:** complete with verdict `VIABLE WITH LIMITATIONS`.

## ADR-001 — Product architecture

**Status:** `ACCEPTED` (2026-08-25).

Next architectural unit at the time of acceptance: ADR-002 + POC-IPC identifiers (isolated-worker IPC protocol and transactional boundaries). Acceptance did not by itself authorize any implementation; POC-IPC-001 was authorized separately and is now `PASS`.

## ADR-002 — Isolated worker IPC and transactional boundaries

**Status:** `ACCEPTED` (2026-08-25, after four architecture review rounds).

Defines the trusted-root, bounded-I/O, success-contract, timeout/cleanup, path-containment, and evidence-semantics rules that **POC-IPC-001** implemented. Acceptance established the architecture contract only; the implementation arrived later with POC-IPC-001, under its own evidence rules (`OS_SANDBOX` remains `NO VERIFICADO`).

## ADR-004 — External tool execution contract

**Status:** `ACCEPTED` (2026-09-01, revised 2026-09-11).

Defines the execution contract for external tools that do not and cannot speak the [ADR-002](adr/ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) IPC protocol (governing `PapyrusCompiler.exe` under profile `PAPYRUS_COMPILE_DRYRUN_V1` and future xEdit validation). Acceptance established the architecture contract only; the acceptance of ADR-004 does NOT convert POC-003 into `PASS`.

## POC-002 — Synthetic TES4 safety pipeline

**Status:** **PASS**.

Demonstrates strict parsing and evidence semantics on a synthetic header fixture. It does not demonstrate real-plugin or runtime compatibility.

## Parallel / next experiments

### POC-001 — Creation Kit read-only UI inspection

Windows-only. Enumerate UIA/MSAA controls without coordinates and without saving. `BLOQUEADO` in non-Windows environments.

### POC-003 — PapyrusCompiler dry-invoke

**Status:** `NO VERIFICADO` (executed 2026-09-06, re-executed 2026-09-11; 13/15 mandatory criteria PASS, 2 mandatory criteria FAIL).

Verify deterministic external compiler invocation, timeout behavior, stdout/stderr capture, output existence/hash, and no shell use under [ADR-004](adr/ADR-004-external-tool-execution-contract.md) profile `PAPYRUS_COMPILE_DRYRUN_V1`.

Executed baseline:
- Mandatory criterion 12 failed with `UNEXPECTED_OUTPUT_PRESENT`: an interrupted PapyrusCompiler execution leaves an undeclared `candidates/<token>.pas` intermediate.
- Mandatory criterion 14 failed with `DETERMINISM_MISMATCH`: successful repeated compilations produced byte-different `.pex` artifacts (`SHA256_A != SHA256_B`).

Because mandatory criteria failed, status remains `NO VERIFICADO` and `DETERMINISTIC_OUTPUT` remains `NO VERIFICADO`. Research harness exists in `research/poc_003/`, but no production adapter exists (`harness exists ≠ production adapter exists`).

### POC-004 — xEdit allowlisted validator

**Status:** `NO VERIFICADO` (next relevant experiment).

Verify a user-installed xEdit invocation using an allowlisted/hash-pinned pre-written script with `-script -autoexit`, explicit completion evidence, bounded timeout, immutable originals, and independent validation (no generated Pascal).

### POC-IPC-001 — isolated worker protocol

**Status:** **PASS**. The minimal proof defined by [ADR-002](adr/ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) (accepted 2026-08-25) was implemented and validated by POC-IPC-001 (`OS_SANDBOX` remains `NO VERIFICADO`).

### POC-MUTAGEN-001 — Mutagen read-only inspector

**Status:** **BLOQUEADO** por [ADR-003](adr/ADR-003-mutagen-runtime-and-license-boundary.md) / license-runtime decision. Inspect a Skyrim plugin file header under an isolated .NET worker runtime.

## Later product milestones

1. NL → validated `ModPlan` → one supported operation → candidate → reopen/assert → HITL.
2. Narrow record writes (for example MISC) after a dedicated writer POC.
3. Weapons / armor / recipes.
4. NPCs with explicit FaceGen limitations.
5. Leveled lists.
6. Papyrus + VMAD after their own validation gates.
7. Quests only after alias/SEQ/VMAD semantics are independently validated.

## Explicitly unsupported until new evidence exists

- navmesh automation;
- arbitrary worldspace/Render Window driving;
- coordinate click bots;
- unrestricted CK automation;
- CKPE as MVP spine.
