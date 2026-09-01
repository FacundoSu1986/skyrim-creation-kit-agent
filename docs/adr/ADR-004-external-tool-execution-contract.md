# ADR-004 — External tool execution contract

- **Status:** PROPOSED
- **Date:** 2026-09-01 (Revised: 2026-09-05)
- **Scope:** Execution contract for third-party executable tools that do not and cannot speak the [ADR-002](ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) IPC protocol.
- **Depends on:** [ADR-001](ADR-001-hybrid-headless-first-architecture.md) (ACCEPTED), [ADR-002](ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) (ACCEPTED).
- **Related:** [ADR-003](ADR-003-mutagen-runtime-and-license-boundary.md) (PROPOSED) acceptance criterion 3; POC-003 (PapyrusCompiler dry-invoke); POC-004 (xEdit validator).

## Context

[ADR-002](ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) defines a single
boundary contract between a trusted orchestrator and an isolated worker: a typed JSON
request is written to the worker's stdin, and a typed JSON response plus a receipt is
read back from its stdout. Call that the **Worker IPC Contract** (WIPC). WIPC presumes a
worker that was written to speak it — the worker parses `protocol_version`, validates a
closed-world request schema, and emits a receipt with its own assertions.

Several required tools are not, and will never be, such workers. `PapyrusCompiler.exe`
accepts `PapyrusCompiler.exe <source> -f=<flags> -i=<imports> -o=<output>` and writes
diagnostics to the console. It does not parse JSON, does not emit a receipt, and cannot
be modified to do so — it is a Bethesda binary. The same is true of xEdit's
`-script -autoexit` mode.

This is not a gap that ADR-002 left accidentally. Its **Out of scope** section states:

> External tool integration contracts beyond the executable-trust rules.

That exclusion is deliberate and correct. It also means the gap is currently unfilled:
there is no contract under which the project may invoke such a tool. Two ways of
filling it were considered and rejected:

1. **Reuse WIPC and treat the tool as a worker.** Rejected: it requires the tool to
   parse and emit JSON, which it cannot do. Any adapter inserted to translate would
   reintroduce exactly the generic-command-execution surface that ADR-002 D9 forbids,
   unless the adapter is itself a closed profile — in which case the contract being
   used is not WIPC at all.
2. **Wrap the tool in a Python worker.** Rejected on process-tree grounds: it makes the
   tool a *grandchild* of the orchestrator, while POC-IPC-001 demonstrates direct-child
   termination only (`WINDOWS_TREE_CLEANUP` remains `NO VERIFICADO`). It also adds an
   intermediate process without adding a verification boundary.

The repository's own research index anticipated this separation. `docs/research/experiments.md`
carries an explicit identifier rule:

> Subprocess IPC hardening is **not** canonical POC-003. Use `ADR-002` or a distinct
> `POC-IPC` identifier unless the research index is intentionally migrated.

This ADR therefore defines a **second, narrower contract class** — the **External Tool
Execution Contract** (ETEC) — and does **not** amend, extend, or version ADR-002.

This document is **design only**. It implements nothing. Where behaviour has never been
demonstrated on the target platform, this ADR says `NO VERIFICADO` rather than implying
support.

## Canonical principle (preserved from ADR-001)

AI decides WHAT. Deterministic software decides HOW. Validators decide WHETHER IT WORKED.
Human decides WHETHER TO ACCEPT.

Under ETEC this principle is enforced more sharply, not less: because the tool cannot
participate in a protocol, **the tool decides nothing about success**. It emits untrusted
bytes on stdout/stderr and untrusted files in the workspace. Every verdict is computed by
the trusted orchestrator from independently recheckable invariants.

## Decision summary

| # | Decision |
| --- | --- |
| E1 | Two contract classes exist: **WIPC** (ADR-002) and **ETEC** (this ADR). Every launch profile declares which class it uses. They are not interchangeable and no profile uses both. |
| E2 | ETEC has **no wire transport**. The tool receives argv at spawn and nothing thereafter. There is no request object, no stdin request, and no response envelope. |
| E3 | The tool **never emits a Receipt** and never emits assertions. The orchestrator synthesises the evidence record after independent verification. |
| E4 | argv is fully determined trusted-side by the profile. No caller-supplied string reaches argv except through the same safe-name grammar and trusted-side resolution that ADR-002 already mandates for path tokens. |
| E5 | Success is an orchestrator-computed conjunction of process, executable-integrity, output, containment, input-integrity, cleanup, and profile-applicable validation invariants. Nonzero exit can never yield SUCCESS. |
| E6 | Bounded stdout/stderr, a single monotonic execution deadline, and a bounded cleanup grace are **inherited verbatim** from ADR-002 D6, D13, and D13a. |
| E7 | Workspace containment, deny-by-default environment, derived `cwd`, and the absence of any shell are **inherited verbatim** from ADR-002 D8, D9, D10, and D11. |
| E8 | The ADR-002 error taxonomy is **partitioned, not inherited wholesale**. Codes that cannot fire under ETEC must not be declared as part of an ETEC profile's outcome set. See [Error taxonomy partition](#error-taxonomy-partition). |
| E9 | Process-tree cleanup is a first-class acceptance item for every ETEC profile, and the demonstrated mechanism is recorded per profile. Absent a demonstration — or kernel-enforced confinement — the profile reports `WINDOWS_TREE_CLEANUP: NO VERIFICADO`. |
| E10 | ETEC does not change `protocol_version`. That value remains `1` and applies only to WIPC. ETEC has no versioned envelope because it has no envelope. |

## Contract classes

| Property | WIPC (ADR-002) | ETEC (this ADR) |
| --- | --- | --- |
| Example profiles | `PYTHON_ISOLATED_V1`, `DOTNET_MUTAGEN_READONLY_V1` | `PAPYRUS_COMPILE_DRYRUN_V1` (defined; POC-003 pre-registered), xEdit profile (future) |
| Transport | stdin request → stdout response, strict JSON | none; argv at spawn only |
| Who emits evidence | the worker emits an untrusted receipt | nobody; the orchestrator synthesises the record |
| Assertions source | worker receipt assertions | orchestrator-derived invariants |
| Correlation | request/response/receipt correlation on ids | job-scoped path and hash correlation only |
| Error taxonomy | all 15 ADR-002 codes | partitioned subset plus ETEC-specific codes (E8) |
| `protocol_version` | 1 | not applicable |

A profile is therefore not merely an argv template. It is a declaration of which contract
class governs the launch, and the orchestrator's validation logic for that profile is
selected by that declaration.

## Profile specification: `PAPYRUS_COMPILE_DRYRUN_V1`

No raw caller-controlled string reaches argv. Operation-specific values may reach argv only as validated typed tokens resolved trusted-side under the profile's closed grammar and containment rules.

| Field | Value |
| --- | --- |
| Executable | absolute path from trusted configuration; never resolved via `PATH` |
| Executable integrity | SHA-256 pinned in trusted configuration; mismatch before spawn fails closed |
| Source script | must resolve inside the job's `input/`; safe-name grammar per ADR-002 |
| Flags file (`-f`) | allowlisted, hash-pinned, read-only |
| Import root (`-i`) | allowlisted absolute path; read-only; no caller-supplied component; immutability governed by recursive regular-file snapshot (`IMPORT_ROOT_SNAPSHOT_V1`) |
| Output (`-o`) | resolved trusted-side; **must** land in `candidates/`; post-resolve re-containment strictly under `candidates/` required (`temp/` is reserved for environment redirects) |
| argv | fully determined by the profile; no free-form element |
| `cwd` | derived trusted-side, never from request data |
| Environment | deny-by-default allowlist; `TEMP`/`TMP` redirected to the job's `temp/` |
| Shell | `shell=False` always; no shell process is introduced into the process tree rooted at tool launch |
| Deadline | single monotonic execution deadline, plus bounded cleanup grace |
| stdout / stderr | capped, deadline-aware readers; bytes decoded as strict UTF-8 |

Rationale for pinning the executable hash: ADR-002's threat model lists *tool executable
substitution* as mitigated by "absolute trusted paths; registry-only sourcing", with
**hash pinning future (not implemented)**. Under ETEC the executable is the whole
contract, so that debt becomes a precondition rather than an improvement.

### Diagnostics handling in PAPYRUS_COMPILE_DRYRUN_V1

In `PAPYRUS_COMPILE_DRYRUN_V1` v1, stdout and stderr are strictly captured, deadline-aware,
stream-capped, and persisted under `logs/` as untrusted evidence per ADR-002 D14.
Because Bethesda's compiler diagnostic strings are not yet empirically catalogued here,
diagnostics text is **not** used as a semantic pass gate for this profile — doing so
would risk either vacuous acceptance or brittle regex tweaking after observing output.
Instead, the primary gates are exit code zero, pre-spawn artifact absence, post-spawn
artifact creation, non-empty size, containment, and determinism.

The error code `TOOL_DIAGNOSTICS_REJECTED` remains in the ETEC error taxonomy for future
profiles that define and freeze a stable, versioned diagnostics predicate before execution.

## Error taxonomy partition

ADR-002 defines 15 outcome codes. Reusing them wholesale under ETEC was proposed during
external review and is **rejected here**, because nine of the fifteen are structurally
unreachable when no wire transport exists. A code that cannot fire is worse than an
absent code: in a fail-closed taxonomy it reads as a handled failure mode and inflates
apparent coverage without adding any.

### Inherited — applies under ETEC

| Code | Why it survives |
| --- | --- |
| `PROCESS_TIMEOUT` | deadline expiry is platform-behaviour, not transport |
| `PROCESS_FAILED` | nonzero exit |
| `OUTPUT_LIMIT_EXCEEDED` | stream caps |
| `WORKSPACE_VIOLATION` | containment invariants and path-traversal prevention (input mutation is governed separately by `INPUT_HASH_MISMATCH`) |
| `POLICY_VIOLATION` | profile violations detected before or after spawn |
| `INTERNAL_ERROR` | orchestrator-side defects (for example leaked I/O threads) |

### Not applicable — transport- or receipt-bound, must not be declared

| Code | Bound to | Evidence in `research/poc_ipc_001/orchestrator.py` |
| --- | --- | --- |
| `INVALID_REQUEST` | request object validation | line 254 |
| `REQUEST_LIMIT_EXCEEDED` | `MAX_REQUEST_BYTES` on stdin | line 304 |
| `UNSUPPORTED_PROTOCOL_VERSION` | `protocol_version` field | `schemas.py` line 88 |
| `INVALID_JOB_ID` | job id arriving over the wire | `schemas.py` line 122 |
| `INVALID_OPERATION` | `operation` field from the request | line 312 |
| `PIPE_WRITE_FAILED` | "could not deliver the full request over stdin" | line 504 |
| `INVALID_RESPONSE` | strict JSON decode of worker stdout | line 525 |
| `RECEIPT_MISMATCH` | response/receipt id correlation | line 541 |
| `ASSERTION_FAILED` | `receipt["worker_assertions"]` | line 562 |

The last row is the one that matters most for POC-003. Under WIPC, `ASSERTION_FAILED` is
the gate that rejects *vacuous* success — an empty or failing assertion set. Under ETEC
there is no receipt, so the equivalent gate has no code at all. Simply dropping
`ASSERTION_FAILED` would leave POC-003 with no way to express "the compiler exited zero
but produced nothing verifiable".

### New codes required by ETEC

These are proposed by this ADR and do not exist in ADR-002:

| Code | Fires when |
| --- | --- |
| `PRE_EXISTING_OUTPUT_PRESENT` | target candidate output path already exists before spawn (fail-closed pre-spawn check) |
| `EXPECTED_OUTPUT_MISSING` | exit code zero but the expected artifact is absent or empty (size == 0) |
| `OUTPUT_HASH_MISMATCH` | hash recorded in evidence differs from independent recomputation of that produced artifact (or differs from pre-registered golden fixture expectation if declared by profile) |
| `INPUT_HASH_MISMATCH` | a declared read-only input hash (source script, allowlisted flags, or import root recursive snapshot) changed across the run |
| `UNEXPECTED_OUTPUT_PRESENT` | files appeared outside the declared output set |
| `TOOL_DIAGNOSTICS_REJECTED` | the tool's diagnostics fail the profile's acceptability rule (retained for profiles declaring a diagnostics predicate) |
| `DETERMINISM_MISMATCH` | two independent runs of the same profile over identical input in separate workspaces disagree (e.g. SHA256_A != SHA256_B) |
| `EXECUTABLE_HASH_MISMATCH` | the pinned tool binary does not match its pinned hash |
| `DESCENDANT_PROCESS_SURVIVED` | a process descended from the tool outlived cleanup |

`UNEXPECTED_OUTPUT_PRESENT` overlaps `WORKSPACE_VIOLATION`. Both are retained because
they answer different questions: `WORKSPACE_VIOLATION` means "a path escaped the
workspace", while `UNEXPECTED_OUTPUT_PRESENT` means "a file stayed inside the workspace
but was not declared". Conflating them would make the failure ambiguous in the record.

## Evidence model

The orchestrator synthesises the record after the process exits, in this order:

```text
1. pre-spawn check: pinned executable SHA-256 matches trusted configuration (EXECUTABLE_HASH_MISMATCH if failing)
2. pre-spawn check: expected output path is absent in candidates/ (fail-closed via PRE_EXISTING_OUTPUT_PRESENT if pre-existing)
3. pre-spawn check: hashes of all declared read-only inputs recorded (source script, flags file, and recursive regular file snapshot for import root per IMPORT_ROOT_SNAPSHOT_V1)
4. exit_code == 0 (PROCESS_FAILED if nonzero)
5. expected output exists (post-spawn creation check)
6. output size > 0 bytes (non-empty check; EXPECTED_OUTPUT_MISSING if absent or 0 bytes)
7. output resolves strictly inside candidates/ (post-resolve re-containment; WORKSPACE_VIOLATION)
8. output SHA-256 recomputed and recorded in evidence (OUTPUT_HASH_MISMATCH if recomputation differs)
9. input hashes unchanged across the run (including exact import root file set and byte hashes; INPUT_HASH_MISMATCH)
10. no unexpected outputs present in workspace (UNEXPECTED_OUTPUT_PRESENT)
11. untrusted stdout/stderr captured, deadline-aware, and bounded under logs/ (OUTPUT_LIMIT_EXCEEDED if stream cap breached)
12. process-tree cleanup verified: no descendant outlived cleanup (DESCENDANT_PROCESS_SURVIVED if alive; INTERNAL_ERROR if unmeasurable)
13. (if determinism is claimed) second run over identical input in a separate clean workspace agrees (DETERMINISM_MISMATCH if hashes differ)
```

Every step is independently recheckable from the workspace. The tool's own stdout and
stderr are stored as **untrusted** material under `logs/`, exactly as ADR-002 D14
requires for worker output. SUCCESS requires all applicable steps; any failure is
recorded with its code and never downgraded to a warning.

## Process tree cleanup

POC-IPC-001 demonstrates direct-child termination on Windows and records the rest
honestly. `research/poc_ipc_001/tests/test_platform_cleanup.py` carries the anchor:

> `WINDOWS_TREE_CLEANUP` remains NO VERIFICADO — Job Objects / taskkill /T are future
> work and are never claimed by this POC.

ETEC does not inherit that gap silently. E9 requires every ETEC profile to do one of two
things:

- **(a) Demonstrate** that no descendant survives cleanup, by spawning the tool, forcing
  a timeout, and showing the tree is empty afterwards; or
- **(b) Confine** the tool in a Windows Job Object created with
  `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, so cleanup is enforced by the kernel rather than
  inferred from a `terminate()` call.

Option (b) is preferred where available. It replaces a claim of the form "we killed
what we could enumerate" with one of the form "the OS released everything in the set",
which does not depend on enumerating the tree at all. It also applies symmetrically to
WIPC: adopting it for `PYTHON_ISOLATED_V1` is the mechanism by which
`WINDOWS_TREE_CLEANUP` could move from `NO VERIFICADO` to `VERIFICADO`.

**Retroactive debt, stated not deferred silently:** POC-IPC-001 carries the same gap.
Applying Job Objects there is separate follow-up work; it does not block POC-003, and
POC-003 passing does not close it.

## Explicit Non-Claims

- Does not amend, supersede, or version ADR-002. WIPC remains the contract for workers
  that speak it.
- Does not authorise any generic command executor. ETEC profiles are individually
  specified, individually reviewed, and individually named.
- Does not demonstrate that `PapyrusCompiler.exe` spawns or does not spawn descendants.
  That is measured by POC-003, not assumed here.
- Does not demonstrate OS-level confinement. `OS_SANDBOX` remains `NO VERIFICADO`.
- Does not claim that any ETEC profile's tool is trustworthy. The tool is untrusted
  code executed with the host account's privileges; ETEC bounds what it can *claim*, not
  what it can *reach*.
- Does not authorise POC-003 to begin. This ADR is `PROPOSED`; POC-003 status remains `NO VERIFICADO` (acceptance criteria pre-registered; execution has not started) awaiting explicit owner authorisation.
- Does not demonstrate structural or runtime validity of compiled Papyrus binaries. `PEX_STRUCTURAL_VALIDITY` and `PEX_RUNTIME_VALIDITY` remain `NO VERIFICADO`; this contract proves deterministic execution and non-empty artifact creation only.

## Acceptance criteria for this ADR

ADR-004 may move PROPOSED → ACCEPTED when:

1. The WIPC/ETEC distinction is judged unambiguous — a reviewer can tell, for any
   profile, which contract class governs it and which outcome codes may fire.
2. The error taxonomy partition is accepted: six inherited codes, nine explicitly
   excluded with justification, nine new codes.
3. The evidence model is accepted as sufficient to detect vacuous success under ETEC —
   specifically enforcing pre-spawn artifact absence, non-empty creation, hash
   recomputation, and determinism.
4. The `PAPYRUS_COMPILE_DRYRUN_V1` profile table is complete, with typed-token safe-name
   resolution and bounded log capture.
5. Executable hash pinning is accepted as a precondition for ETEC profiles, converting
   ADR-002's stated future work into a requirement here.
6. E9 is accepted: no ETEC profile may report a cleanup guarantee it has not
   demonstrated or enforced.
7. ADR-003 acceptance criterion 3 is updated to reference this ADR as the ETEC boundary.

## Out of scope

- Any implementation. No launcher, no profile registry code, no tests.
- POC-003 execution; POC-004; Creation Kit UIA; Mutagen.
- The xEdit ETEC profile, which will be specified when POC-004 is designed.
- POSIX semantics for Job Objects, which do not exist; the POSIX equivalent is process
  groups and is already exercised by POC-IPC-001.
- Converting POC-IPC-001 to Job Objects. Recorded as debt in
  [Process tree cleanup](#process-tree-cleanup), not attempted here.
