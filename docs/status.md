# Project status

Updated: 2026-09-17

## Overall

```text
VIABLE WITH LIMITATIONS
```

## Implemented and validated

- POC-002 synthetic TES4 inspection/safety pipeline.
- 44/44 unit/security tests on the supplied implementation (initial validated baseline: 43 tests; +1 adversarial regression for policy-rejection evidence semantics).
- Candidate workspace/path containment.
- Fail-closed receipts and immutable-original hash invariant.
- POC-IPC-001 is implemented and PASS as the validated isolated-worker protocol/process research baseline.
- POC-IPC-001 PASS demonstrates the protocol/process-isolation contract only; it does NOT demonstrate OS-level sandboxing. `OS_SANDBOX` remains `NO VERIFICADO`.

## Executed research experiments (unverified / failed criteria)

- POC-003 — PapyrusCompiler dry-invoke contract: executed 2026-09-06, re-executed 2026-09-11 under ADR-004 profile `PAPYRUS_COMPILE_DRYRUN_V1`. Status: `NO VERIFICADO`.
  - 13/15 mandatory criteria PASS, 2 mandatory criteria FAIL:
    - Criterion 12 (`UNEXPECTED_OUTPUT_PRESENT`): interrupted PapyrusCompiler execution leaves an undeclared `candidates/<token>.pas` intermediate in the workspace.
    - Criterion 14 (`DETERMINISM_MISMATCH`): successful repeated compilations produced byte-different `.pex` artifacts (`SHA256_A != SHA256_B`).
  - `DETERMINISTIC_OUTPUT` remains `NO VERIFICADO`.
  - Research harness exists in `research/poc_003/` (hermetic test suite 105 tests), but no production adapter exists (`harness exists ≠ production adapter exists`).

## Accepted architecture

- ADR-001: `ACCEPTED` (2026-08-25).
- ADR-002 — isolated worker IPC protocol and transactional boundaries: `ACCEPTED` (2026-08-25).
- ADR-003 — Mutagen runtime and license boundary: `PROPOSED` (2026-08-28).
- ADR-004 — External Tool Execution Contract: `ACCEPTED` (2026-09-01, revised 2026-09-11). Acceptance establishes the external tool execution contract only; it does NOT convert POC-003 into PASS (`architecture contract accepted ≠ experiment PASS`).
- Hybrid orchestrator with headless-first primary path.

## Not implemented / not verified

- general real-plugin writer;
- Mutagen worker (BLOQUEADO por ADR-003 / license-runtime decision);
- PapyrusCompiler production adapter (research/POC harness exists in `research/poc_003/`, but production adapter does not exist; POC-003 is `NO VERIFICADO`);
- xEdit validator (POC-004: `NO VERIFICADO`);
- Creation Kit UI automation;
- CKPE bridge;
- LLM planner;
- in-game runtime validation;
- OS-level sandboxing / filesystem confinement (`OS_SANDBOX`: `NO VERIFICADO`).
