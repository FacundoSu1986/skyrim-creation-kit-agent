# POC-IPC-001 — isolated worker IPC protocol

Executable proof of [ADR-002](../../docs/adr/ADR-002-isolated-worker-ipc-and-transactional-boundaries.md)
(ACCEPTED 2026-08-25; clarifications 2026-08-26: D5a, D7a, D13/D13a): the
trusted orchestrator talks to a one-shot Python worker over local pipes using
the typed, bounded, fail-closed protocol the ADR defines.

This is a **research POC**, not a production authoring backend. Session
PASS/FAIL is reported per the ADR's success contract; no E2/E3/E4/E5
inference applies (ADR-002 §Evidence semantics).

## Status (honest)

- Session-level PASS/FAIL over real subprocesses: **VERIFICADO** locally;
  exercised end-to-end on Windows for the test set in this directory and on
  the CI matrix (`ubuntu-latest` and `windows-latest`, Python 3.11/3.12).
- `WINDOWS_DIRECT_CHILD_TERMINATION`: **VERIFICADO** by the ctypes-based
  `OpenProcess` / `GetExitCodeProcess` / `STILL_ACTIVE` test in
  `tests/test_platform_cleanup.py`. The test only runs on Windows runners
  and is reported as PASS only there.
- `WINDOWS_TREE_CLEANUP`: **NO VERIFICADO**. Job Objects / `taskkill /T` /
  AppContainer are out of scope for this POC and are not claimed.
- `OS_SANDBOX`: **NO VERIFICADO / OUT OF SCOPE** (ADR-002 D16). Process
  isolation is not an OS sandbox. Worker code is trusted code running with
  the host account's privileges; confinement is a separate future boundary.
- `POSIX` process-group cleanup: **VERIFICADO** on `ubuntu-latest` CI
  (`test_process_group_is_destroyed_after_timeout`).
- `INSPECT_SYNTHETIC_INPUT` operation-specific truthfulness: **VERIFICADO**
  (D5a: exactly one input ref with exact path and exact SHA-256, exactly
  zero outputs, `candidates/` empty).

## How to run

```bash
# from the repository root
python -m compileall research/poc_ipc_001
python -m unittest discover -s research/poc_ipc_001/tests -v
```

Skips are environment-capability skips (e.g. symlink creation rights on
the runner). They are reported as `NO VERIFICADO`, never converted to PASS.

## Public API

The orchestrator exposes a single entry point:

```python
orch.execute(operation_call: dict) -> SessionResult
```

`operation_call` is closed-world: only `job_id`, `operation`, `parameters`,
and the optional `timeout_ms`. The orchestrator adds `protocol_version` and
generates a fresh `request_id` (`uuid v4`) trusted-side. The JobWorkspace
is derived as `trusted_jobs_root / "jobs" / <job_id>`; callers **cannot**
supply a workspace, root, base directory, cwd, or any host path component.

Any attempt to inject a reserved field (`request_id`, `protocol_version`,
`trusted_jobs_root`, `workspace`, `base_dir`, `cwd`, `job_root`,
`worker_receipt`) is a pre-spawn `INVALID_REQUEST`.

## Architecture

```
trusted orchestrator (IPCOrchestrator)
  ├─ validates OperationCall closed-world (reserved fields reject pre-spawn)
  ├─ builds WireRequest trusted-side (protocol_version + fresh request_id)
  ├─ validates WireRequest: identifiers, size ≤ 64 KiB, policy, parameters
  ├─ derives jobs/<job_id>/ from trusted_jobs_root (never from the caller)
  ├─ spawns WITHOUT shell:
  │    <trusted python> -I -B worker.py --job-root <derived abs path>
  │    env: deny-by-default allowlist (SYSTEMROOT + TEMP/TMP→job temp on
  │    Windows; TMPDIR→job temp on POSIX; PATH absent)
  │    cwd: the job directory (trusted-derived)
  ├─ execution deadline (D13) starts immediately post-spawn and covers
  │  stdin write, stdout/stderr reads, worker execution, and natural wait
  ├─ bounded pumps: stdout ≤ 256 KiB, stderr ≤ 64 KiB; cap-hit aborts
  │  immediately (no waiting for the execution deadline); writer is
  │  chunked and deadline-aware
  ├─ bounded cleanup grace (D13a): terminate, reap, pipe close, thread join
  ├─ validates Response (strict JSON, closed world, presence/null rules,
  │  error.code == status), six-way correlation, receipt hashes,
  │  non-vacuous strict-boolean assertions, operation-specific
  │  truthfulness (D5a), workspace invariants
  └─ computes session PASS/FAIL itself; persists validated receipts to
     receipts/ and capped stderr to logs/ (worker never writes those areas)
```

Operation under proof: `INSPECT_SYNTHETIC_INPUT` — read-only inspection of a
synthetic fixture (`input/<input_name>`, safe-name token): SHA-256, byte
length, magic-marker check, four non-vacuous assertions. Per D5a:
`outputs == []`, `len(inputs) == 1` with the exact path and the exact
trusted recomputed SHA-256, and `candidates/` must be empty.

## Deadline model (D13 / D13a)

| Phase | Time source | Default ceiling | Purpose |
| --- | --- | --- | --- |
| Execution deadline (D13) | `monotonic()` | `timeout_ms` (default `DEFAULT_TIMEOUT_MS`) | stdin write, stdout/stderr read, worker run, normal wait |
| Cleanup grace (D13a) | `monotonic()` (separate) | `TERMINATE_GRACE_S` (SIGTERM/wait) → SIGKILL + `JOIN_GRACE_S` | terminate, reap, close pipes, thread join |

The cleanup grace is strictly bounded, never extends the session, never
resumes execution, never salvages partial output, and never converts a
`PROCESS_TIMEOUT` into `SUCCESS`. Both phases use `monotonic()`.

## Stdin pipe taxonomy (D7a)

Observable BrokenPipe / partial write / `ERROR_BROKEN_PIPE` during delivery
⇒ `PIPE_WRITE_FAILED`. The OS accepts the full write into the pipe buffer
before the child exits; the child exits 0 with no parseable response ⇒
`INVALID_RESPONSE`. Child exits nonzero ⇒ `PROCESS_FAILED`. POC v1 has no
ACK protocol; "write completed" is not the same as "worker consumed
request".

## Platform differences

| Property | POSIX | Windows |
| --- | --- | --- |
| Spawn flags | `start_new_session=True` | `CREATE_NEW_PROCESS_GROUP` |
| Readiness polling | non-blocking fd + select slices | PeekNamedPipe availability poll |
| Execution-deadline cleanup | child exits naturally; group TERM→KILL if not | `proc.terminate()` (TerminateProcess) on the direct child |
| Tree cleanup | group kill (exercised on Linux CI) | **NO VERIFICADO** (Job Objects / taskkill /T future work) |
| Thread lifetime | deadline-polled; join finite | same strategy; verified 0 leaked threads in every session test |
| Direct-child-reaped proof | `os.kill(pid, 0)` → `ProcessLookupError` | `OpenProcess` + `GetExitCodeProcess` returns a value other than `STILL_ACTIVE` |

## Failure-injection coverage (implemented)

OperationCall closed world: unknown field · reserved field (`request_id`,
`protocol_version`, `trusted_jobs_root`, `workspace`, `base_dir`, `cwd`,
`job_root`, `worker_receipt`) · missing required · wrong shape.

Wire-schema adversarial coverage (P1 request_id): invalid / non-v4 /
uppercase UUID · `protocol_version` true / float / string / 2.
These are exercised in `test_protocol.py` against `validate_request()`
directly because the public `execute()` no longer accepts these fields
from the caller (they are trusted-side wire fields).

Stdin: never-reads (timeout) · slow-reads (timeout/pipe failure) ·
closes immediately (D7a taxonomy).

Streams: stdout flood · stderr flood · invalid UTF-8 · malformed JSON ·
duplicate keys · NaN · Infinity · trailing data · unknown top-level field ·
unknown nested field · empty stdout with zero exit · empty stdout with
nonzero exit. **OUTPUT_LIMIT triggers early termination** well before the
configured deadline (P1).

Process: hang-to-timeout · crash · nonzero exit + plausible SUCCESS JSON ·
zero exit + invalid JSON · descendant inheriting pipes cannot stall the
session.

Response error handling: schema-valid error Response with
`worker_receipt = null` is handled without exception and the session
verdict is the worker's reported status (P0-2). Response-level correlation
is still enforced: an error Response with a wrong `job_id` or
`request_id` ⇒ `RECEIPT_MISMATCH`.

Receipt truthfulness (D5a) for `INSPECT_SYNTHETIC_INPUT`:
missing input ref · extra input ref · wrong input path · wrong input SHA ·
non-empty outputs ⇒ `WORKSPACE_VIOLATION`.

Receipt shape (generic schema): missing on SUCCESS · null-error rule ·
FAILED receipt under SUCCESS response · unknown nested field · SHA
uppercase/short/prefixed/whitespace · counts over MAX_INPUT/OUTPUT/
WARNING/ASSERTION.

Assertions: empty required set · `passed: false` propagated as
`ASSERTION_FAILED` · `passed: 1`/`passed: 0` rejected (strict boolean) ·
object `expected` rejected · float `actual` rejected.

Timeout/cleanup: direct child really dead after timeout (POSIX and Windows
real proof) · POSIX group destroyed · descendant-holding-pipes returns on
time · zero leaked I/O threads after every session.

## Exact claims

A PASSing session demonstrates: bounded transport in both directions,
one-shot process execution under the controlled environment/cwd, response/
receipt well-formedness and correlation, hash-format compliance, the
operation's own assertions passing at the worker level, and the
operation-specific truthfulness invariants re-derived by the orchestrator.

## Non-claims

- NOT plugin validity ("magic bytes match" is a fixture check, not format
  validation);
- NO evidence-ladder inference: no E2/E3/E4/E5 from IPC (session PASS/FAIL
  is orthogonal to the artifact ladder);
- `OS_SANDBOX`: **NO VERIFICADO** — process isolation is not an OS sandbox
  (ADR-002 D16). Worker code is trusted code running with host-account
  privileges; confinement is a separate future boundary.
- `WINDOWS_TREE_CLEANUP`: **NO VERIFICADO** (only direct-child cleanup is
  demonstrated on Windows).
