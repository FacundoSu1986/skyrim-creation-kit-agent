# POC-IPC-001 — isolated worker IPC protocol

Executable proof of [ADR-002](../../docs/adr/ADR-002-isolated-worker-ipc-and-transactional-boundaries.md)
(ACCEPTED 2026-08-25): the trusted orchestrator talks to a one-shot Python
worker over local pipes using the typed, bounded, fail-closed protocol the
ADR defines.

Status: **IMPLEMENTED — session PASS demonstrated end-to-end on
Windows (direct-child cleanup) with the full failure-injection matrix green;
POSIX process-group rows are exercised by CI on ubuntu runners.**

## How to run

```bash
# from the repository root
python -m compileall research/poc_ipc_001
python -m unittest discover -s research/poc_ipc_001/tests -v
```

Expected: all tests OK (skips are environment-capability skips, reported as
`NO_VERIFICADO`, never converted to PASS).

## Architecture

```
trusted orchestrator (IPCOrchestrator)
  ├─ validates Request fully pre-spawn (closed-world schema, identifiers,
  │  timeout range, per-operation parameters, serialized size ≤ 64 KiB)
  ├─ derives jobs/<job_id>/ from TRUSTED_JOBS_ROOT (never from the request)
  ├─ spawns WITHOUT shell:
  │    <trusted python> -I -B worker.py --job-root <derived abs path>
  │    env: deny-by-default allowlist (SYSTEMROOT + TEMP/TMP→job temp on
  │    Windows; TMPDIR→job temp on POSIX; PATH absent)
  │    cwd: the job directory (trusted-derived)
  ├─ ONE monotonic deadline starts immediately post-spawn and covers stdin
  │  write, stdout/stderr reads, execution, wait/reap
  ├─ bounded pumps: stdout ≤ 256 KiB, stderr ≤ 64 KiB, enforced during
  │  transfer (PeekNamedPipe polling on Windows, select on non-blocking fds
  │  on POSIX); writer is chunked and deadline-aware
  ├─ validates Response (strict JSON, closed world, presence/null rules,
  │  error.code == status), six-way correlation, receipt hashes,
  │  non-vacuous strict-boolean assertions, workspace invariants
  └─ computes session PASS/FAIL itself; persists validated receipts to
     receipts/ and capped stderr to logs/ (worker never writes those areas)
```

Operation under proof: `INSPECT_SYNTHETIC_INPUT` — read-only inspection of a
synthetic fixture (`input/<input_name>`, safe-name token): SHA-256, byte
length, magic-marker check, four non-vacuous assertions, `outputs == []`.

## Exact claims

A PASSing session demonstrates: bounded transport in both directions, one-shot
process execution under the controlled environment/cwd, response/receipt
well-formedness and correlation, hash-format compliance, and the operation's
own assertions passing at the worker level.

## Non-claims

- NOT plugin validity ("magic bytes match" is a fixture check, not format
  validation);
- NO evidence-ladder inference: no E2/E3/E4/E5 from IPC (session PASS/FAIL is
  orthogonal to the artifact ladder);
- `OS_SANDBOX`: **NO_VERIFICADO** — process isolation is not an OS sandbox
  (ADR-002 D16). Worker code is trusted code running with host-account
  privileges; confinement is a separate future boundary.

## Platform differences

| Property | POSIX | Windows |
| --- | --- | --- |
| Spawn flags | `start_new_session=True` | `CREATE_NEW_PROCESS_GROUP` |
| Readiness polling | non-blocking fd + select slices | PeekNamedPipe availability poll |
| Deadline cleanup | SIGTERM→SIGKILL to process group, reap | direct-child TerminateProcess |
| Tree cleanup | group kill (exercised on Linux CI) | **NO_VERIFICADO** (Job Objects/taskkill future work) |
| Thread lifetime | deadline-polled; join finite | same strategy; verified 0 leaked threads in every session test |

## Failure-injection coverage (implemented)

Request/schema: oversize · unknown field · missing fields · `protocol_version`
true/float/string/2 · invalid/non-v4/uppercase UUID · bad `job_id` (slash,
embedded `..`) · timeout below min / above max / wrong type · unknown or
malformed operation · disabled capability (`POLICY_VIOLATION`) · parameter
schema violations (wrong shape, unknown key) · traversal/absolute/drive/UNC
`input_name` tokens.

Stdin: never-reads (timeout) · slow-reads (timeout/pipe failure) · closes
immediately (fail-closed; see note below).

Streams: stdout flood · stderr flood · invalid UTF-8 · malformed JSON ·
duplicate keys · NaN · Infinity · trailing data · unknown top-level field ·
unknown nested field · empty stdout with zero exit · empty stdout with nonzero
exit.

Process: hang-to-timeout · crash · nonzero exit + plausible SUCCESS JSON ·
zero exit + invalid JSON · descendant inheriting pipes cannot stall the
session.

Correlation: six-way echo checks with exactly one corrupted leg each.

Receipt: missing on SUCCESS · null-error rule · FAILED receipt under SUCCESS
response · unknown nested field · SHA uppercase/short/prefixed/whitespace ·
output path outside `candidates/` · counts over MAX_INPUT/OUTPUT/WARNING/
ASSERTION.

Assertions: empty required set · `passed: false` propagated as
`ASSERTION_FAILED` · `passed: 1`/`passed: 0` rejected (strict boolean) ·
object `expected` rejected · float `actual` rejected.

Timeout/cleanup: direct child really dead after timeout · POSIX group
destroyed · descendant-holding-pipes returns on time · zero leaked I/O threads
after every session.

Known classification note (documented divergence candidate): with protocol-v1
requests far smaller than the OS pipe buffer, an immediate-close worker
collapses deterministically to `INVALID_RESPONSE` (empty stdout, clean exit)
instead of `PIPE_WRITE_FAILED` — BrokenPipe is unobservable for sub-buffer
payloads without a consumption ack. Both outcomes are fail-closed. Proposed
ADR clarification tracked with the owner.
