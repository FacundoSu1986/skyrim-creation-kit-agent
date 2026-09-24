# Project status

Updated: 2026-09-24

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

## Governance gates (2026-09-24)

- `tools/check_manifest_coverage.py` (CI: `governance.yml`): proves the pin perimeter is fully
  pinned. At introduction it found 13 tracked `research/poc_ipc_001/tests/helper_workers/*.py`
  files inside `research/**` with no manifest row — undetectable by `sha256sum -c`. Now pinned.
- `tools/quality_ratchet.py` + `tools/quality-baseline.txt`: ruff (`E4,E7,E9,F,B`) and mypy over
  `research/**` + `tools/**`, gated as debt that may only shrink. Before this, mypy could not
  start at all (duplicate module names across POC roots), so the declared typecheck contract in
  `pyproject.toml` was unverified. Measured debt: 35 findings, all in `research/**`
  (`tools/**` is clean); `research/poc_002` is mypy-clean.
- `tests/desk-docs-consistency.test.ts` (CI: `discovery-desk.yml`): the Discovery Desk must agree
  with `docs/research/experiments.md` and `docs/status.md`. It was introduced because the desk
  still described POC-003 as blocked by a missing compiler after two executed runs whose measured
  failures are the actual reason for `NO VERIFICADO`; the desk also omitted POC-IPC-001 and
  POC-MUTAGEN-001. Desk rows and `research/poc_003/README.md` are corrected; statuses are
  unchanged (`POC-003` stays `NO VERIFICADO`).
- Hazard recorded (not fixed, by design): the POC trees share flat module names, so two POCs
  cannot be imported in one process. A combined pytest collection made the IPC suite import
  `poc_002/orchestrator.py`. See `pyproject.toml` and `docs/roadmap.md` "From POCs to product".
- `npm run build` requires network egress to Google Fonts (`next/font/google`) and fails without
  it; CI has egress, offline clones do not. Self-hosting via `next/font/local` would make the
  build hermetic; not done here because the font binaries are not in the repository. Status of
  this item: `NO VERIFICADO` fix, `VERIFICADO` failure mode (observed: `next/font: error: Failed
  to fetch IBM Plex Sans from Google Fonts`).

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
