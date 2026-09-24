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

## Governance gates (added 2026-09-24)

`.github/workflows/governance.yml` runs two gates that no earlier workflow covered:

- **manifest coverage** — `python3 tools/check_manifest_coverage.py --check` proves every file
  inside the declared pin perimeter is actually pinned (13 tracked `research/**` files were
  unpinned when this was introduced, which `sha256sum -c` cannot detect); then re-verifies hashes.
- **static-analysis ratchet** — `python3 tools/quality_ratchet.py --check` runs `ruff`
  (`E4,E7,E9,F,B`) and `mypy` over `research/**` and `tools/**` against the debt ledger
  `tools/quality-baseline.txt`. Recorded debt is grandfathered; new findings fail. A missing
  analyzer exits 2, never 0.

The Discovery Desk workflow additionally runs `tests/desk-docs-consistency.test.ts`, which fails
when the desk's mirrored research state disagrees with `docs/research/experiments.md` or
`docs/status.md` (status identity, row presence, canonical vocabulary, and execution-vs-pending
framing).

## From POCs to product

No step below is authorized by a POC passing. Promotion requires its own evidence.

1. **Namespace the primitives first.** The POC directories are flat module roots and deliberately
   reuse module names (`orchestrator.py`, `workspace.py`, `protocol.py`, `errors.py` exist in more
   than one POC). Verified hazard: a single pytest collection over `research/poc_002` and
   `research/poc_ipc_001/tests` makes the IPC suite import `poc_002/orchestrator.py`. Therefore
   **two POCs cannot be loaded in one process today**, and no product may import them as
   libraries until each is a real package (`__init__.py` + relative imports) with its own
   collision test. Suites must be invoked one per process (see `pyproject.toml`).
2. **Then the plan spine, not the model.** `ModPlan` schema → intent normalizer → policy engine →
   capability router, routed only to operations that already have `PASS` evidence
   (`INSPECT_HEADER`, `INSPECT_SYNTHETIC_INPUT`). No `EXECUTE_COMMAND`-class primitive, ever.
3. **Only then a planner.** An LLM behind the normalizer, with a closed vocabulary, and a receipt
   per operation. Nothing about the model changes the safety properties above; if the spine is
   absent, the model has nothing safe to call.
4. **Verification wedge as the first shippable product** (see
   [viability review](research/2026-09-24-viability-and-improvement-review.md) §6):
   `POC-VERIFY-001` (real-plugin read-only inventory + strict-format gaps) and `POC-PEX-001`
   (`.pex` structural validation, privacy redaction gate, semantic equivalence) need neither
   Mutagen nor Creation Kit and stay clear of the ADR-003 decision.
5. **ADR-003 stays a gate, not a backlog item.** Authoring beyond read-only requires the
   runtime/license decision; until then the writer path stays `BLOQUEADO`.

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
