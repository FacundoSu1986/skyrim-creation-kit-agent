# ADR-002 — Isolated worker IPC protocol and transactional boundaries

- **Status:** ACCEPTED (2026-08-25; see [Acceptance record](#acceptance-record))
- **Date:** 2026-08-25 (original) / 2026-08-26 (clarifications D13/D13a, D7a, D5a)
- **Scope:** IPC protocol and transactional boundaries for isolated workers.
- **Depends on:** [ADR-001](ADR-001-hybrid-headless-first-architecture.md) (ACCEPTED).
- **Related:** POC-002 (PASS — synthetic TES4 safety pipeline), future **POC-IPC-001**.
- **Prior work:** previously reviewed exploratory IPC prototypes remain `CHANGES_REQUIRED`. They are **not** imported as validated code and are **not** POC-003. They are used here only as a catalog of known failure modes; each one is explicitly closed in [Known failures closed](#known-failures-closed).

## Context

ADR-001 accepted a hybrid, headless-first architecture whose execution layer consists of isolated deterministic workers behind a capability router. POC-002 validated the orchestration invariants inside one process: closed operation enum, truthful capability routing, candidate-only workspace with immutable originals, no-overwrite receipts, and the `E_NONE`/`E0`–`E5` evidence ladder.

What is still undefined is the **boundary**: how a trusted orchestrator talks to an out-of-process worker so that a buggy, hung, or lying worker cannot produce false success claims, unbounded resource consumption, or protocol confusion — while stating explicitly that process isolation does **not** confine what a compromised worker can do to the filesystem ([Process isolation is not a sandbox](#process-isolation-is-not-a-sandbox)). Prior exploratory prototypes attempted this boundary and failed review on specific, recurring defects (trusted root supplied by the request, ambiguous identifier bounds, `bool`-as-`int` schema confusion, thin success semantics, unbounded output capture, absent timeout/cleanup). This ADR defines the protocol so that the future POC-IPC-001 can be implemented without architectural ambiguity and so that reviewers can test against explicit invariants.

This document is **design only**. It implements nothing. Where behavior is a design decision that has never been demonstrated on the target platform, this ADR says **NO VERIFICADO** rather than implying support.

## Canonical principle (preserved from ADR-001)

AI decides WHAT. Deterministic software decides HOW. Validators decide WHETHER IT WORKED. Human decides WHETHER TO ACCEPT.

The IPC boundary exists to enforce this split mechanically: nothing crosses it except typed requests derived from allowlisted operations, and nothing comes back that can *declare* success — success is computed by the trusted side from independently checkable invariants.

## Decision summary

| # | Decision |
| --- | --- |
| D1 | Trusted jobs root lives only in trusted-side configuration; requests carry a validated `job_id`, never roots, base dirs, or host paths. |
| D2 | One-shot process model: one request per worker process over stdin → one JSON response on stdout. No daemon, broker, sockets, HTTP, or queues. |
| D3 | Strict JSON UTF-8 serialization; exact integer `protocol_version`; unsupported version fails closed. |
| D4 | Separate bounded identifier contracts (`job_id`, `request_id`, `operation`); identity is never composed by concatenating prefixed strings. |
| D5 | Success is an orchestrator-computed conjunction of process, transport, correlation, receipt, and assertion invariants — never inferred from `response.status` alone. Nonzero exit can never yield SUCCESS. |
| D6 | Every byte crossing the boundary is bounded during transfer — request write, stdout read, stderr read — by capped, deadline-aware readers/writer; limits exist to be applied, not declared. |
| D7 | Timeout is fail-closed: terminate, reap, close pipes, discard partial output, record `PROCESS_TIMEOUT`. |
| D8 | Worker environment is deny-by-default with an explicit trusted allowlist; `cwd` is derived trusted-side; no secrets cross the boundary. |
| D9 | No shell anywhere: operations map deterministically to argv-style invocations; generic command execution does not exist as an operation. |
| D10 | All paths derived from request data are resolved and re-contained inside the job workspace; traversal/symlink/junction escape attempts fail closed. |
| D11 | Workers write only `candidates/` and `temp/`; `originals/` is immutable; candidate→live promotion happens nowhere in this design. |
| D12 | POC-IPC-001 outcomes use a session-level `PASS`/`FAIL` verdict **separate** from the artifact evidence ladder; no E3/E4/E5 claims and no E2 reuse. |
| D13 | A single monotonic **execution deadline** starts immediately post-spawn and governs stdin write, stdout/stderr reads, worker execution, and the normal wait for completion. Once that deadline expires the outcome becomes irrevocably `PROCESS_TIMEOUT`. A separate bounded **cleanup grace** (D13a) handles terminate, reap, and thread join only. Wall-clock time is audit-only. |
| D14 | Workers — and any future validator process — emit all evidence as untrusted stdout bytes. Only the orchestrator persists `receipts/`, `logs/`, and `reports/` content, always after validation. No component writes trusted evidence areas directly. *(Protocol contract between well-behaved participants; not OS enforcement.)* |
| D13a | After the execution deadline (D13) expires, a separate bounded **cleanup grace** may be used only for terminate, process-tree cleanup per demonstrated platform support, pipe close, and finite thread join. The cleanup grace never resumes execution, never salvages partial output, and never converts a `PROCESS_TIMEOUT` into `SUCCESS`. It is itself strictly bounded and uses `monotonic()`. See [Deadline and cleanup time semantics](#deadline-and-cleanup-time-semantics-d13a). |
| D5a | Operation-specific receipt truthfulness. The generic Receipt schema is necessary but not sufficient. Each typed operation may define receipt invariants stronger than the schema. A schema-valid Receipt that violates those operation-specific truthfulness invariants cannot produce session PASS. POC-IPC-001 applies D5a to `INSPECT_SYNTHETIC_INPUT`: exactly one InputRef required, InputRef.path equals the exact canonical path derived from validated `input_name`, InputRef.sha256 equals the trusted-side recomputation of that exact provisioned file, `outputs` is exactly `[]`, and `candidates/` remains empty. The D5a checklist for any future operation lives in the operation registry. |
| D7a | `PIPE_WRITE_FAILED` requires an observed delivery failure (rejected/partial write, `BrokenPipeError`/`ERROR_BROKEN_PIPE`); a sub-buffer write accepted by the OS with the child exiting without producing a parseable response is `INVALID_RESPONSE`. See [Stdin pipe taxonomy clarification](#stdin-pipe-taxonomy-clarification-d7a). |
| D15 | Wire schemas are closed-world at every nesting level; unknown fields reject recursively. Extensions require a protocol version bump. |
| D16 | **Process isolation is not an OS sandbox**: worker code is trusted code running with the host account's privileges; only its outputs are untrusted data. OS confinement is a separate future boundary (`OS_SANDBOX: NO VERIFICADO / OUT OF SCOPE FOR POC-IPC-001`). |

## Trust boundaries

**TRUSTED (orchestrator side):**

- orchestrator configuration, including `TRUSTED_JOBS_ROOT`;
- operation allowlist and per-operation parameter schemas;
- worker registry: executable paths, interpreter path, environment allowlist, resource limits;
- protocol/schema validators;
- capability registry status (which backends actually exist);
- the code that computes SUCCESS/FAIL, validates responses/receipts, and persists evidence;
- generation of `request_id` values.

**SEMI-TRUSTED (machine-local, validated before use):**

- subprocess stdout/stderr until schema-validated;
- environment variable values passed through the allowlist;
- files already inside the job workspace (e.g., provisioned originals) — integrity enforced by SHA-256 invariants, not by trust;
- tool executables located at configured absolute paths (identity pinning is future work; see [Tool executable trust](#tool-executable-trust)).

**UNTRUSTED:**

- LLM output of any kind;
- ModPlan content and every string inside request parameters;
- user-controlled file/plugin names;
- worker responses until fully validated — a worker may be buggy or adversarial; "worker" is not automatically "friend";
- external tool output relayed through workers;
- candidate artifacts until independently re-opened/asserted.

Rule: data may flow upward only after the receiving layer validates it. The orchestrator treats the worker exactly as it treats any other untrusted producer of bytes.

## Process isolation is not a sandbox

The trust split above is between **code** and **data**:

- **Worker executable and its code: TRUSTED CODE.** They come exclusively from the trusted worker registry and run as an ordinary child process with the filesystem privileges of the account running the orchestrator.
- **Worker stdout/response/receipt/artifacts: UNTRUSTED DATA**, validated before any use or persistence.

Process isolation therefore draws a *data* boundary, not a *privilege* boundary:

> **Process isolation ≠ security sandbox.**
>
> POC-IPC-001 proves protocol/process isolation, not OS-level filesystem confinement.
> A compromised worker executable may retain the filesystem privileges of the account running it — it could ignore this entire protocol and read or write anything its user can access.
> OS-level confinement is a separate future security boundary (for example dedicated low-privilege account + ACLs / restricted tokens / AppContainer on Windows) and must be designed and validated **before untrusted third-party worker code is ever permitted**. Job Objects alone do not restrict arbitrary filesystem access.

`OS_SANDBOX`: **NO VERIFICADO — OUT OF SCOPE FOR POC-IPC-001.**

Everything in this ADR constrains *legitimate* operations and defines how untrusted *outputs* are judged; none of it prevents a hostile process from acting outside the protocol. Where that distinction matters (evidence areas, threat model), this ADR says so explicitly instead of implying enforcement that does not exist.

## Deadline and cleanup time semantics (D13 / D13a)

Two independent monotonic phases:

| Phase | Time source | Default ceiling | Purpose |
| --- | --- | --- | --- |
| Execution deadline (D13) | `monotonic()` | `timeout_ms` (≤ `MAX_TIMEOUT_MS`, default `DEFAULT_TIMEOUT_MS`) | stdin write, stdout/stderr read, worker run, `wait()` for natural exit |
| Cleanup grace (D13a) | `monotonic()` (separate deadline) | `TERMINATE_GRACE_S` (SIGTERM/wait) → SIGKILL + `JOIN_GRACE_S` (thread join) | terminate, reap, close pipes, finite thread join |

Rules:

- The execution deadline is the only place where the outcome is decided.
  When it expires, the outcome becomes irrevocably `PROCESS_TIMEOUT`.
- The cleanup grace exists only to clean up; it never resumes execution,
  never salvages partial output, and never converts `PROCESS_TIMEOUT` into
  `SUCCESS`. It is itself strictly bounded; nothing about it may grow
  unbounded.
- Both phases use `monotonic()`. NTP/calendar corrections affect neither.
  Wall-clock `*_at_ms` timestamps are audit-only.
- The cleanup grace is NOT added to the execution budget and does NOT
  extend the session.

## Stdin pipe taxonomy clarification (D7a)

The original ADR text read "child closes stdin early ⇒ `PIPE_WRITE_FAILED`"
as a single bullet. Empirically (POC-IPC-001 / README note) this collapses
deterministically into two distinct cases for sub-buffer payloads where the
kernel accepts the parent's full write before observing the child's exit:

- The OS **rejects the write** with `BrokenPipeError`, returns a partial
  write, or surfaces `ERROR_BROKEN_PIPE` (Windows) — observed during
  mid-delivery — ⇒ **`PIPE_WRITE_FAILED`**.
- The OS **accepts the full request into the pipe buffer** before the child
  exits, the child exits 0 with empty stdout — write success is unobservable
  ⇒ **`INVALID_RESPONSE`**.

`PIPE_WRITE_FAILED` therefore means *the parent demonstrably could not
deliver the request*. The combination "OS accepted the write + child exited
without producing a parseable response" is **`INVALID_RESPONSE`**, not a
pipe failure. This amendment is a clarification of intent, not a behavior
change: the orchestrator already classifies these deterministically as
fail-closed; the table now matches reality.

## Process and transport model

```
trusted orchestrator (Python)
  └─ spawns, without shell:
       <trusted absolute python> -I -B <trusted worker entry> \
           --job-root <derived absolute job dir>
       stdin:  exactly one UTF-8 JSON Request (≤ MAX_REQUEST_BYTES)
       stdout: exactly one UTF-8 JSON Response (≤ MAX_RESPONSE_BYTES)
       stderr: diagnostics/logs (≤ MAX_STDERR_BYTES)
```

- **One request per process.** The process ends after emitting its response. This eliminates framing protocols, multiplexing, partial-delivery ambiguity, and long-lived-worker state corruption in one decision.
- No network, no sockets, no daemons, no message brokers, no shared memory. Local anonymous pipes only.
- The worker entry point and interpreter come exclusively from the trusted worker registry (D8/D9 context); the request cannot choose or influence them.
- Rationale for `-I -B`: isolated mode ignores user site-packages and `PYTHON*` environment variables; `-B` avoids writing bytecode caches into or near the workspace. These flags are part of the contract, not optimizations.

## Serialization

- Format: **JSON, UTF-8, strict**.
- Decoding rejects, failing closed:
  - invalid UTF-8 (strict decode; no replacement-char fallbacks);
  - `NaN` / `Infinity` / `-Infinity` literals;
  - duplicate object keys (duplicate-key hook → malformed document);
  - trailing data after the single top-level document.
- Encoding of emitted documents uses sorted keys and compact separators so identical logical content produces identical bytes where practical (deterministic receipts).
- Prohibited forever: pickle, eval/exec of any content, dynamic deserialization of Python objects, host-language object graphs across the boundary.

## Protocol versioning

- `protocol_version` is the exact integer literal `1`.
- Schema validation requires `type(x) is int` semantics — see [Boolean/int confusion](#booleanint-confusion); `True` is not a valid version.
- The orchestrator accepts only versions it implements; the worker likewise. An unsupported version produces `UNSUPPORTED_PROTOCOL_VERSION` on whichever side detects it, and the orchestrator records overall FAIL.
- **No negotiation, no fallback to "best common" semantics, no defaulting when the field is missing.** Ambiguous compatibility is precisely what a first protocol must not have. Version bump policy (what changes require version 2) is out of scope until a second version is actually needed.

## Identifier contracts

Identifiers are separate namespaces with separate bounds. **Composing identities by concatenation (e.g., `"REQ-" + operation_id`) is forbidden**: derived strings silently violate the base bound. If a display label needs a prefix, it is presentation-only and not used for matching, storage paths, or receipts.

### job_id

Validation performs these steps in order, rejecting on the first failure:

1. value is a string (`type(v) is str`);
2. length ≤ 64 characters;
3. matches `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`;
4. does **not** contain the substring `..` anywhere (the character class alone admits it; the explicit check closes it);
5. is not exactly `.` or `.`-only forms (already excluded by rules 3–4; stated for validator clarity).

The grammar excludes separators, drive letters (`:`), backslashes, UNC prefixes, and whitespace by construction. Identity comparison is exact-match; case-insensitive filesystem aliasing is handled under [Path containment](#path-containment).

### request_id (normative)

- **Required**, canonical **UUID v4**: lowercase, hyphenated, exactly **36 ASCII characters**, shape `xxxxxxxx-xxxx-4xxx-[89ab]xxx-xxxxxxxxxxxx`.
- Generated **exclusively by the trusted orchestrator**. Never sourced from the LLM, user input, ModPlan content, or the worker; the worker only echoes it.
- Validation rejects: uppercase hex; non-v4 versions (v1/v3/v5); malformed shapes; wrong length; arbitrary opaque strings up to 64 chars; non-string types (boolean/null/number). Rejection code: `INVALID_REQUEST`.
- Uniqueness semantics: fresh value per attempt; see [Idempotency, retries, replay](#idempotency-retries-replay).

### operation

- Member of the closed operation enum, ≤ 64 chars, same safe-name discipline as above. Must exist in both orchestrator and worker registries for the negotiated backend.

Correlation invariants — all six are mandatory; any mismatch ⇒ `RECEIPT_MISMATCH`:

- `response.request_id == request.request_id`
- `response.job_id == request.job_id`
- `response.operation == request.operation`
- `receipt.request_id == request.request_id`
- `receipt.job_id == request.job_id`
- `receipt.operation == request.operation`

Wrong-job or wrong-request responses are rejected even if everything else looks perfect. The taxonomy deliberately keeps the single code `RECEIPT_MISMATCH` for all six; a future split into `CORRELATION_MISMATCH` would be a taxonomy change and is out of scope for protocol v1.

Normative rejection mapping per identifier field (exactly one code per case, so future tests assert an exact value):

| Violation | Code |
| --- | --- |
| `protocol_version` wrong type (bool/float/string/missing/null) | `INVALID_REQUEST` |
| `protocol_version` well-typed integer but ≠ 1 | `UNSUPPORTED_PROTOCOL_VERSION` |
| `request_id` violates its contract (shape/version/case/length/type) | `INVALID_REQUEST` |
| `job_id` violates its contract (grammar/length/embedded `..`) | `INVALID_JOB_ID` |
| `operation` not in the closed enum / malformed | `INVALID_OPERATION` |

All of these orphan the request before any process spawns.

## Message schemas

Logical schemas only — field tables plus invariants. Implementation types (dataclasses/Pydantic) are deliberately **not** introduced by this ADR.

### Closed-world rule

Every object defined here — **Request, Response, Error, Receipt, InputRef, OutputRef, Assertion** — rejects unknown fields **recursively**, at every nesting level. Unknown field ⇒ `INVALID_REQUEST` / `INVALID_RESPONSE` respectively. There are no extension bags, no free-form metadata maps. Changing any wire schema requires a protocol version bump.

All wire hashes follow one format: **SHA-256 rendered as lowercase hexadecimal, exactly 64 characters, no `sha256:` prefix, no whitespace**. Any other representation rejects.

### Request

| Field | Type | Constraints |
| --- | --- | --- |
| `protocol_version` | integer | exactly `1`; `type(v) is int` |
| `request_id` | string | canonical UUID v4 per [Identifier contracts](#identifier-contracts) |
| `job_id` | string | contract above |
| `operation` | string | closed enum member |
| `parameters` | object | must satisfy the per-operation parameter schema; total serialized request size ≤ `MAX_REQUEST_BYTES`; individual strings ≤ `MAX_STRING_BYTES` |
| `timeout_ms` | integer, optional | omitted → `DEFAULT_TIMEOUT_MS`. Accepted iff `type(x) is int` AND `1 ≤ x ≤ MAX_TIMEOUT_MS`. **Any other value rejects with `INVALID_REQUEST` — there is no clamping.** |

No other fields.

**Parameters and paths.** The request never carries `TRUSTED_JOBS_ROOT`, any workspace root, `base_dir`, `cwd`, a drive-qualified path, a UNC path, or any absolute host path — no field exists for them. What a typed operation *may* declare, under its own parameter schema, are **workspace-relative path tokens** (see [Path containment](#path-containment)). For POC-IPC-001 even those are avoided: the single operation takes an `input_name` safe-name token identifying a file under `input/`.

### Response

| Field | Type | Constraints |
| --- | --- | --- |
| `protocol_version` | integer | exactly `1` |
| `request_id` / `job_id` / `operation` | string | echo of request values |
| `status` | string | `SUCCESS` or an error code from the taxonomy |
| `started_at_ms` / `finished_at_ms` | integers | epoch millis for **audit only**; `type(x) is int`. No ordering invariant is enforced between them — wall-clock corrections must not fail an otherwise-valid exchange; durations derive from the monotonic clock, never from these fields |
| `worker_receipt` | object or null | **always present.** Receipt object iff `status == "SUCCESS"`; otherwise exactly `null` |
| `error` | object or null | **always present.** Error object iff `status != "SUCCESS"`; otherwise exactly `null` |

Presence/null invariants (normative, testable):

- `status == "SUCCESS"` ⇒ `worker_receipt` is a schema-valid Receipt object AND `error` is exactly `null`.
- `status != "SUCCESS"` ⇒ `error` is a schema-valid Error object with `error.code == status` AND `worker_receipt` is exactly `null`.
- Omitting either field is invalid — the closed-world validator requires both keys on every Response.

Canonical shapes:

```json
{"protocol_version": 1, "request_id": "…", "job_id": "…", "operation": "…",
 "status": "SUCCESS", "started_at_ms": 0, "finished_at_ms": 0,
 "worker_receipt": {"…": "…"}, "error": null}
```

```json
{"protocol_version": 1, "request_id": "…", "job_id": "…", "operation": "…",
 "status": "PROCESS_FAILED", "started_at_ms": 0, "finished_at_ms": 0,
 "worker_receipt": null,
 "error": {"code": "PROCESS_FAILED", "message": "worker exited with code 3"}}
```

Total serialized response ≤ `MAX_RESPONSE_BYTES`.

#### Error object

| Field | Type | Constraints |
| --- | --- | --- |
| `code` | string | member of the failure taxonomy; bounded ASCII identifier |
| `message` | string | bounded UTF-8 ≤ `MAX_STRING_BYTES`; diagnostics only — never parsed, never used for control flow, must not embed secret material |

Unknown fields reject. Additionally: whenever `status != "SUCCESS"`, `code` MUST equal `status` (a response cannot claim `PROCESS_FAILED` while carrying `error.code = INVALID_RESPONSE`; such responses reject as `INVALID_RESPONSE`).

### Receipt (worker_receipt)

Machine-readable, produced by the worker, validated by the orchestrator **before** any persistence (see [Workspace ownership](#workspace-ownership)):

| Field | Type | Constraints |
| --- | --- | --- |
| `protocol_version` | integer | `1` |
| `request_id` / `job_id` / `operation` | string | correlate to request |
| `status` | string | `SUCCESS` or worker-level error code |
| `started_at_ms` / `finished_at_ms` | integers | epoch millis, audit-only; no ordering invariant enforced (same rationale as Response) |
| `inputs` | array of InputRef | ≤ `MAX_INPUT_COUNT` |
| `outputs` | array of OutputRef | ≤ `MAX_OUTPUT_COUNT` |
| `worker_assertions` | array of Assertion | ≤ `MAX_ASSERTION_COUNT`; non-empty for operations that define assertions |
| `warnings` | array of strings | ≤ `MAX_WARNING_COUNT` items, each ≤ `MAX_STRING_BYTES` |

#### InputRef

| Field | Type | Constraints |
| --- | --- | --- |
| `path` | string | workspace-relative canonical path token (contract below), ≤ `MAX_STRING_BYTES` |
| `sha256` | string | hash contract above |

#### OutputRef

| Field | Type | Constraints |
| --- | --- | --- |
| `path` | string | workspace-relative canonical path token; **must resolve inside `candidates/`** — `temp/` scratch is never cited as final evidence output |
| `sha256` | string | hash contract above |

#### Assertion

| Field | Type | Constraints |
| --- | --- | --- |
| `name` | string | bounded identifier-style name ≤ `MAX_STRING_BYTES` |
| `expected` / `actual` | JSON scalar | **string | exact integer | boolean | null** — arrays, objects, and floats are prohibited in protocol v1 to keep validators trivially total and payloads simple |
| `passed` | boolean | strict real JSON boolean (`type(v) is bool`). The integer-exactness rule deliberately does **not** apply here: `1`/`0` reject — an assertion result is true/false, never truthy numerics |
| `details` | string, optional | bounded UTF-8 ≤ `MAX_STRING_BYTES` |

Unknown fields reject at every level above.

Three artifact kinds remain distinct and never merged: **worker receipt** (this object), **orchestrator execution summary** (POC-002's `ExecutionSummary`, including verdict/outcome/invariant hashes and monotonic-derived duration), **validator report** (future third-party static validation, E3 territory).

## Size and resource limits

Limits exist to be enforced at read/write time ([Bounded I/O](#bounded-io-strategy)), not measured afterwards. Exceeding any limit is fail-closed.

| Limit | Value | Applies to |
| --- | --- | --- |
| `PROTOCOL_VERSION` | `1` | all messages |
| `MAX_REQUEST_BYTES` | 65 536 (64 KiB) | serialized request |
| `MAX_RESPONSE_BYTES` | 262 144 (256 KiB) | serialized response incl. receipt |
| `MAX_STDOUT_BYTES` | 262 144 (256 KiB) | raw stdout captured |
| `MAX_STDERR_BYTES` | 65 536 (64 KiB) | raw stderr captured |
| `MAX_STRING_BYTES` | 4 096 | any single string field value |
| `MAX_INPUT_COUNT` | 32 | `receipt.inputs` length |
| `MAX_OUTPUT_COUNT` | 16 | `receipt.outputs` length (POC operations produce few artifacts; headroom without enabling flooding — response cap still dominates) |
| `MAX_WARNING_COUNT` | 32 | `receipt.warnings` length |
| `MAX_ASSERTION_COUNT` | 100 | `worker_assertions` length |
| `DEFAULT_TIMEOUT_MS` | 30 000 | session deadline if `timeout_ms` omitted |
| `MAX_TIMEOUT_MS` | 600 000 | hard ceiling; out-of-range values reject |

Values are constants proposed for POC scale; changing them later changes this ADR, not a request field.

## Bounded I/O strategy

`communicate()`-style full-buffered capture is **forbidden**: it consumes memory proportional to attacker-chosen output and only measures afterwards. All three pipes operate under the **execution deadline** (D13); cleanup after that deadline follows the bounded grace in D13a.

**Deadline model.** Immediately after `spawn()` — before any I/O — the orchestrator computes `deadline = monotonic_clock() + effective_timeout_ms` where `effective_timeout_ms` is `DEFAULT_TIMEOUT_MS` or the validated request value. Every subsequent step (stdin write, stdout read, stderr read, worker execution, normal wait) runs under this single execution deadline. It never starts "after stdin is sent": a worker that never reads its stdin cannot stall the parent outside the deadline. Wall-clock/calendar corrections (NTP, manual clock change) never alter the allowed duration; epoch timestamps are recorded for audit only.

**Stdin writer.**

- The request is fully serialized and size-checked against `MAX_REQUEST_BYTES` **before spawn**; the writer transmits exactly that buffer and nothing more, then closes stdin.
- The writer is deadline-aware: each write attempt checks remaining budget; on expiry it stops, and the timeout path runs.
- It never blocks indefinitely: POSIX uses non-blocking fds / poll-based write loops; Windows uses a bounded writer thread that respects the deadline remainder and is joined with a finite wait — a thread must never outlive the session. Windows thread mechanics are **design decision — NO VERIFICADO** until POC-IPC-001 demonstrates them.
- `BrokenPipeError` / partial delivery / child-closed-stdin-early map deterministically to `PIPE_WRITE_FAILED` (see taxonomy). A worker that simply never consumes stdin is killed by the deadline as `PROCESS_TIMEOUT` — controlled failure, never a hang.

**Readers (stdout/stderr).**

- Dedicated capped reader loops accumulate at most their stream cap. The byte after the cap is **discarded**, the exchange is marked `OUTPUT_LIMIT_EXCEEDED`, and the orchestrator terminates the child immediately (no waiting for the execution deadline). Reading continues to detect a natural EOF in case the child exits cleanly before flooding past the cap.
- Reading stops unconditionally at the execution deadline regardless of bytes seen; EOF before a complete valid response is classified deterministically (see taxonomy notes).
- stderr is captured for diagnostics, size-capped, never parsed as protocol.
- POSIX: non-blocking reads/select satisfy this directly. Windows: reader threads with bounded accumulators — same joinability/deadline requirements as the writer; **NO VERIFICADO** until demonstrated.

## Environment control

Deny-by-default: the child inherits **nothing** except explicitly allowlisted names. The allowlist itself is trusted-side configuration stored in the worker registry — not request data.

Proposed baseline allowlist:

- Windows: `SYSTEMROOT` (required by the C runtime/encodings), `TEMP`/`TMP` redirected into the job `temp/` directory.
- POSIX: `TMPDIR` redirected into the job `temp/` directory; `PATH` either unset (absolute executable paths everywhere) or set to a minimal trusted value from configuration.

Rules:

- No secrets, tokens, credentials, or orchestrator state cross the boundary — the allowlist makes accidental leakage structurally difficult, and adding a name to it is a reviewed configuration change.
- Tool discovery never relies on an inherited `PATH`; executables are addressed by configured absolute paths (see [Tool executable trust](#tool-executable-trust)).
- Values are copied from the orchestrator machine scope; they are semi-trusted inputs to the worker, never attested output.

## Working directory

`cwd` is derived exclusively by the trusted side and set to the job workspace directory (the `jobs/<job_id>/` root) or a fixed worker-internal directory. Requests cannot read, hint, or alter it. Setting cwd to the job root means accidental relative writes land inside the contained area — defense in depth on top of explicit path checks, never a substitute for them.

## Tool executable trust

- Executable paths (interpreters, future external tools) originate **only** from trusted configuration and the worker registry. They are never taken from LLM output, ModPlan content, request parameters, or environment.
- Tools are addressed by **absolute configured path**, mitigating PATH hijacking by construction.
- Hash/version pinning of tool binaries is acknowledged as a desirable future control; it is **not designed in detail and NOT VERIFICADO — not implemented**. Until then, the trust anchor is the machine's configured filesystem, which is the same anchor the orchestrator itself stands on.

## Execution lifecycle

Every request follows this sequence; any step failing aborts the sequence fail-closed with the mapped error code:

1. Caller constructs a typed request (LLM intent already reduced to allowlisted operation + parameters upstream).
2. Trusted orchestrator validates the request completely pre-spawn: sizes, encodings, unknown fields (recursive), identifier contracts, `type-is-int` numerics, `timeout_ms` range (reject-out-of-range), parameter schemas.
3. Policy validates the operation: membership in the allowlist, capability status SUPPORTED, risk class acceptable.
4. Orchestrator validates `job_id` and derives the job workspace as `TRUSTED_JOBS_ROOT/jobs/<job_id>/` — the request supplies no path component beyond `job_id` (+ declared safe-name tokens, which stay abstract until resolution).
5. Orchestrator selects the deterministic worker executable from the registry and constructs the controlled environment (allowlist, temp redirection, no shell, `-I -B`, cwd = job workspace).
6. Request is serialized and re-checked against `MAX_REQUEST_BYTES` (still pre-spawn).
7. Subprocess spawned without shell; resources prepared (pipes, readers, writer).
8. **The single execution deadline (D13) starts immediately post-spawn.**
9. Bounded stdout/stderr readers attach; the bounded stdin writer transmits the request under the execution deadline and closes stdin on completion.
10. Read/wait continues under the execution deadline. On deadline expiry the outcome is irrevocably `PROCESS_TIMEOUT`; all I/O stops, the process/tree is terminated per platform support, pipes are closed, and the bounded cleanup grace (D13a) runs to reap and join threads. Partial output is never salvaged.
11. Exit code awaited; nonzero exit ⇒ `PROCESS_FAILED`, and any stdout content is treated as untrusted diagnostics, never as a result.
12. Response schema validated: encoding, JSON strictness, size, recursive closed-world fields, `type-is-int` numerics, echo/correlation fields, status vocabulary.
13. If `status == SUCCESS`: receipt presence, receipt-schema validation (recursive), correlation re-checked at receipt level, hash formats verified.
14. Assertions validated: required worker assertions present, non-empty, all passing (`passed` strict boolean); protocol assertions (transport, schema, correlation, exit code) evaluated by the orchestrator itself.
15. Workspace invariants validated where applicable: originals' SHA-256 unchanged; candidates confined to `candidates/`; no-overwrite respected.
16. Only now may the exchange be considered successful; the orchestrator computes the execution summary (verdict + session outcome + invariant hashes + `duration_ms` derived from the monotonic clock) and persists the validated receipt and stderr under trusted areas ([Workspace ownership](#workspace-ownership)).

Every terminal state — PASS or FAIL — produces a durable summary; silence is not a state.

## Success contract

Overall SUCCESS is the **conjunction** of all of the following; failing any one yields FAIL with its specific code. Success is computed by the orchestrator; a worker cannot assert it into existence.

1. process exit code == 0 (nonzero exit can never produce SUCCESS — even with plausible JSON on stdout);
2. response structurally valid (encoding, JSON, size, recursive closed-world schema, version supported);
3. `response.status == "SUCCESS"`;
4. receipt exists and schema-valid;
5. `receipt.status == "SUCCESS"`;
6. `receipt.operation == request.operation`;
7. correlation holds at response and receipt level (`request_id`, `job_id`);
8. required assertions exist and are non-empty (per-operation definition), with strict-boolean results;
9. all assertions pass;
10. protocol version supported end-to-end;
11. workspace invariants hold where applicable (originals untouched, containment, no-overwrite).

There is no partial success. There is no "success with warnings" distinct from `warnings` being carried inside a fully-passing receipt.

## Failure taxonomy

Stable codes for tests and summaries. Emission point noted; both sides use the same vocabulary.

| Code | Meaning | Emitted by |
| --- | --- | --- |
| `INVALID_REQUEST` | schema/size/encoding/unknown-field violations; wrong-typed numerics (including wrong-typed `protocol_version`); malformed `request_id`; out-of-range or wrong-typed `timeout_ms`. Identifier violations use their own codes (`INVALID_JOB_ID`, `INVALID_OPERATION`) — never this one | orchestrator (pre-spawn) or worker |
| `REQUEST_LIMIT_EXCEEDED` | request above `MAX_REQUEST_BYTES` | orchestrator |
| `UNSUPPORTED_PROTOCOL_VERSION` | `protocol_version` is exactly an integer but its value ≠ 1 (wrong types ⇒ `INVALID_REQUEST`, per the normative identifier table) | both |
| `INVALID_JOB_ID` | identifier contract violation incl. embedded `..` | orchestrator (pre-spawn) |
| `INVALID_OPERATION` | not in allowlist / unsupported by worker | both |
| `POLICY_VIOLATION` | policy engine rejection pre-spawn | orchestrator |
| `WORKSPACE_VIOLATION` | path containment breach; no-overwrite breach; originals mutation detected | both |
| `PROCESS_TIMEOUT` | session deadline exceeded | orchestrator |
| `PROCESS_FAILED` | nonzero exit, spawn failure, crash | orchestrator |
| `PIPE_WRITE_FAILED` | parent could not deliver the full request: broken pipe, child closed stdin early, partial write | orchestrator |
| `OUTPUT_LIMIT_EXCEEDED` | any stream past its cap | orchestrator |
| `INVALID_RESPONSE` | response fails schema/JSON/UTF-8 validation, or stdout reaches clean EOF without a valid response while exit code was zero | orchestrator |
| `RECEIPT_MISMATCH` | missing receipt or failed correlation | orchestrator |
| `ASSERTION_FAILED` | required assertions missing/empty/failing/non-boolean | orchestrator |
| `INTERNAL_ERROR` | unexpected local condition (e.g., OS I/O error orchestrator-side), always fail-closed | both |

Deterministic classification for pipe edge cases (no aesthetic codes beyond `PIPE_WRITE_FAILED`); cross-references D7a above:

- OS-rejected / partial write / observed `BrokenPipeError` / `ERROR_BROKEN_PIPE` (Windows) during delivery → `PIPE_WRITE_FAILED`;
- write accepted by the OS, child exits without consuming the request, exit 0 with no parseable response → `INVALID_RESPONSE` (see D7a);
- stdout hits EOF before a parseable response **and** exit code was nonzero → `PROCESS_FAILED` (exit gate dominates);
- stdout hits EOF before a parseable response with exit code zero → `INVALID_RESPONSE`;
- local OS errors raising around pipe machinery → `INTERNAL_ERROR` with cause recorded.

## Timeout and process-tree cleanup

- Deadline semantics: `deadline = monotonic_clock() + timeout_ms` — a **monotonic** clock, never wall-clock/calendar time. NTP corrections or manual clock changes cannot extend or shorten an operation's allowed duration. Epoch `*_at_ms` timestamps exist purely for audit trails.
- The execution deadline (D13) covers stdin write, stdout read, stderr read, worker execution, and the normal wait. The bounded cleanup grace (D13a) handles terminate, reap, pipe close, and thread join.
- On expiry: readers/writer stop immediately; terminate; reap via `wait()`; close pipes in `finally`; discard all partial output; record `PROCESS_TIMEOUT`; verdict FAIL. Partial output is never salvaged into a result.
- **POSIX:** spawn with `start_new_session=True` → the child leads its own process group; cleanup escalates `SIGTERM` (grace) → `SIGKILL` to the whole group via `os.killpg`. Group kill on POSIX is standard practice; its specific exercise in tests remains to be demonstrated by POC-IPC-001.
- **Windows:** `Process.terminate()` maps to `TerminateProcess` and kills **only** the direct child. Full tree termination via Job Objects (assign child at spawn, `TerminateJobObject`) or `taskkill /T /F` via a trusted absolute path is a recorded **design direction — NO VERIFICADO**. Console-control alternatives (`CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT`) are equally **NO VERIFICADO**.
- Honesty rule for the future POC: if POC-IPC-001 demonstrates only direct-child termination on Windows, its claim must say exactly that ("direct-child termination demonstrated; tree cleanup NO VERIFICADO"). A design direction never converts into a verified decision without a demonstration.
- Orphan risk note: descendants that outlive the worker and inherit the pipes cannot stall the exchange — every reader/writer is deadline-bounded. Orphan detection/reaping of grandchildren is **NO VERIFICADO** and explicitly out of POC-IPC-001 scope.

## Path containment

**Canonical statement:** the request never carries a trusted filesystem root, workspace root, `base_dir`, `cwd`, drive-qualified path, UNC path, or any absolute host path. The only host-identity ingredient entering the protocol is `job_id`. Typed operations may additionally declare explicit **workspace-relative path tokens** under their own parameter schemas; POC-IPC-001 uses none of those — it carries an `input_name` safe-name token only, deferring generic path tokens to future operations that genuinely need them.

**Safe-name tokens (POC-IPC-001):** `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$` with no `..` substring — resolved trusted-side to exactly one file under the appropriate area (`input/`).

**Workspace-relative path tokens (future operations):** permitted only when an operation's schema explicitly declares them, subject to all of:

- bounded string; no NUL; no empty string;
- no absolute path; no drive prefix; no UNC; no leading `/` or `\`;
- separators in exactly one canonical representation (forward slash), no mixed separators;
- no `.` component; no `..` component; no repeated/empty components;
- no trailing separator; no normalization ambiguities (the token must be already-canonical);
- resolved trusted-side against the allowed area root; final resolved target re-contained within that area;
- symlink/junction resolution checks apply identically (below);
- case-handling per platform rules below.

**Containment mechanics (all path-bearing data):**

- Derived paths are built trusted-side as `TRUSTED_JOBS_ROOT/jobs/<job_id>/<area>/<token>`; then resolved (`resolve()`) and required to remain inside the resolved trusted root/area.
- Post-resolve comparison normalizes case on Windows (case-insensitive platform).
- Drive switching and UNC are excluded by grammar and re-caught by containment.
- Symlink/junction escapes: resolution follows links, so planted links pointing outward are caught by the post-resolve re-check **if** the platform resolves junctions identically. Junction-specific behavior and TOCTOU windows on Windows are **NO VERIFICADO**; POC-IPC-001's injection suite includes planted-link cases before any stronger claim.
- Case collisions (two tokens differing only by case): mitigated by exact-match receipt bookkeeping; collision tests pending (**NO VERIFICADO**).

## Workspace contract and ownership

Conceptual layout preserved from POC-002:

```text
TRUSTED_JOBS_ROOT/
  jobs/<job_id>/
    input/        provisioned request materials
    originals/    immutable sources (SHA-256 pinned; opened read-only by workers)
    candidates/   the ONLY worker write target for produced artifacts
    temp/         disposable scratch (also the redirected TEMP/TMPDIR)
    reports/      validator outputs (future)
    receipts/     append-only, no-overwrite receipts
    logs/         captured stderr and orchestrator logs
```

### Access matrix

| Area | Worker | Orchestrator | Validator (future) |
| --- | --- | --- | --- |
| `input/` | READ | provision / read | read, optional |
| `originals/` | READ | provision / hash-verify | read |
| `candidates/` | WRITE (no-overwrite) | verify / hash | read |
| `temp/` | WRITE | cleanup at will | no contract |
| `receipts/` | **NO WRITE** | **WRITE append-only** | read |
| `reports/` | **NO WRITE** | **WRITE** (only after validating an emitted report) | emits its typed report through a validated stdout channel; **no direct write** |
| `logs/` | **NO WRITE** | WRITE | optional read |

Principle: trusted evidence areas (`receipts/`, `reports/`, `logs/`) are written by the orchestrator alone, always after validation. Workers and validators alike produce only untrusted bytes on their output channel; neither ever writes these areas directly.

### Evidence flow

1. Evidence leaves its producing process — worker receipt now, ValidatorReport in the future — as untrusted stdout bytes.
2. The orchestrator validates it fully: recursive schema, hash formats, correlation, status, assertions.
3. Only after validation may the orchestrator persist its own canonical copy under the matching trusted area (`receipts/` for worker receipts; `reports/` for validated validator reports) and the capped stderr under `logs/`.

Because the protocol never lets producing processes write these areas, a well-behaved worker — or validator — can forge no filesystem evidence; the worst it can do is emit bytes that validation rejects. This is a **contract between participants that follow the protocol, not OS enforcement**: a compromised worker retains the host account's privileges and could still tamper with files outside the protocol ([Process isolation is not a sandbox](#process-isolation-is-not-a-sandbox)). Detecting such out-of-band tampering (hash re-checks, append-only expectations) is defense in depth; preventing it requires the future confinement layer.

### Invariants

- `originals/` immutability is enforced, not assumed: hashes before/after; any change aborts with `WORKSPACE_VIOLATION`.
- `candidates/` is write-once per operation run; overwrite attempts fail (`WORKSPACE_VIOLATION`).
- `temp/` may be wiped between runs without notice.
- Workers never address live Skyrim/Data directories; the concept does not exist in this protocol. Promotion of candidates toward any game location is a separate, HITL-gated concern outside IPC scope entirely.

## Transactional boundaries and atomicity

- A worker mutates only `candidates/` + `temp/`. An operation either produces its complete artifact(s) and a passing receipt, or it FAILs; intermediate states are never reported as success.
- Write-temp-then-move within `candidates/` is the recommended worker pattern for artifact completeness; the no-overwrite rule makes the final placement effectively single-shot.
- There is **no automatic promotion** of candidates to any live location anywhere in this design; transactionality stops at the workspace edge by intention (HITL owns acceptance per ADR-001).
- Originals are never mutated; "success" that altered an original is a detected invariant breach, not a transactional rollback problem.

## Idempotency, retries, replay

- Operations declare (in the registry) whether they are read-only or effectful. Read-only operations may be retried by caller policy. Effectful (write-to-candidates) operations are **never auto-retried** absent an explicit idempotency contract, because candidate no-overwrite turns a blind retry into a guaranteed `WORKSPACE_VIOLATION` — a loud failure, not silent duplication.
- Every attempt carries a fresh `request_id`, generated by the orchestrator. Reuse of a `request_id` within the same trusted job lifecycle SHOULD be rejected where duplicate tracking exists; tracking itself is optional defense in depth for POC-IPC-001, not a mandate.
- **Honest replay position:** this design does **not** implement a general nonce/replay-protection system. Effectful replay usually collides with no-overwrite and fails loudly — that collision is defense in depth, not replay prevention. Read-only replay remains possible by construction and is accepted as low-risk for POC scale; anything stronger requires an explicit future contract.

## Assertion semantics

Three distinct classes; conflating them is a review defect:

- **Protocol assertions** — evaluated by the orchestrator about the exchange itself: bounded transfer completed (including the stdin write), exit code zero, schema valid, correlation held, deadlines respected. ("response JSON parsed" lives here.)
- **Worker assertions** — recorded in the receipt by the worker about its own processing steps.
- **Artifact assertions** — independent re-opening/re-parsing/hash verification of produced artifacts (POC-002's reopen-after-write pattern is the exemplar).

Rules: operations define which worker/artifact assertions are *required*; SUCCESS demands every required assertion present, non-empty, and passing with a strict boolean result. A vacuous receipt (empty assertions for an operation requiring them) is `ASSERTION_FAILED`. No protocol assertion ever substitutes for an artifact assertion: parsing the envelope says nothing about plugin validity.

## Evidence semantics

This protocol introduces a **session outcome** — `PASS` / `FAIL` — attached to the execution summary. It is deliberately orthogonal to the artifact evidence ladder (`E_NONE`, `E0`–`E5`):

- A PASSing IPC session evidences: bounded transport occurred (both directions), the worker executed under the constrained environment, the response/receipt was well-formed and correlated, and the operation's own assertions passed at the protocol/worker level.
- It does **not** evidence plugin validity, format conformance beyond the operation's own checks, xEdit conclusions, Creation Kit compatibility, PapyrusCompiler behavior, Mutagen equivalence, runtime correctness, or in-game results.
- `E2` remains tied to artifact re-open/assert semantics (POC-002's meaning). An IPC session must **not** self-declare `E2` merely for completing a round trip; whether a given operation's artifact assertions rise to E2 is judged by the artifact-assertion definitions, not by transport success.
- `E3` (independent static validation), `E4` (HITL approval), `E5` (runtime) are **not inferable** from IPC and are not touched by this ADR.
- Extending the ladder (e.g., adding a transport-evidence tier) requires an explicit future ADR/migration decision; until then POC-IPC-001 reports session `PASS`/`FAIL` plus plain-language claims limited to the bullet list above.

## Known failures closed

Mapping from the prior exploratory prototype review (`CHANGES_REQUIRED`) to the decisions that close each failure:

| Known failure | Closed by |
| --- | --- |
| Trusted root/base_dir supplied by request | [Trust boundaries](#trust-boundaries), [Identifier contracts](#identifier-contracts), [Path containment](#path-containment) (D1) |
| Shared ambiguous `MAX_ID_LENGTH`; `"REQ-"+id` overflow | Separate bounded contracts, composition forbidden (D4) |
| `isinstance(x, int)` accepting `bool` | [Boolean/int confusion](#booleanint-confusion) (D3) |
| Thin SUCCESS (`status == SUCCESS` only) | [Success contract](#success-contract) (D5) |
| Nonzero exit yielding success via plausible stdout | Success contract item 1 (D5) |
| Declared-but-unenforced stdout/stderr caps; unbounded `communicate()` | [Size and resource limits](#size-and-resource-limits), [Bounded I/O](#bounded-io-strategy) (D6/D13) |
| Missing timeout/process-tree cleanup | [Timeout and process-tree cleanup](#timeout-and-process-tree-cleanup) (D7/D13) |
| Inherited environment / secret exposure | [Environment control](#environment-control) (D8) |
| Request-controlled cwd | [Working directory](#working-directory) (D8) |
| Arbitrary shell / free-form commands | [Process and transport model](#process-and-transport-model) (D9) |
| Stdin write blocking outside any deadline | Single monotonic session deadline + bounded writer (D13/D6) |
| Worker forging filesystem evidence directly | [Workspace ownership](#workspace-contract-and-ownership) access matrix (D14) |

## Boolean/int confusion

Python `bool` subclasses `int`; therefore `isinstance(protocol_version, int)` accepts `true`. Contract rule: wherever a schema says *integer*, validation MUST use exact-type semantics (`type(v) is int`). This applies to `protocol_version`, `timeout_ms`, timestamps, counts, and integer-typed assertion scalars. Conversely, where a schema says *boolean* (`Assertion.passed`), validation MUST require a real JSON boolean (`type(v) is bool`) — numeric truthiness rejects. Documented here explicitly so implementation and tests encode both rules once, identically, on both sides.

## Threat model

| Threat | Mitigation (design element) | Residual / status |
| --- | --- | --- |
| Path traversal via request | safe-name/token grammar; trusted-side derivation; post-resolve containment | injection tests mandated in POC-IPC-001 |
| Workspace escape | same as above + `resolve()` re-check | — |
| Symlink/junction escape | post-resolve containment | junction specifics **NO VERIFICADO** pending tests |
| Arbitrary command injection | no shell; closed op enum; argv-style deterministic invocation; no EXECUTE_COMMAND concept | — |
| Shell injection | shell does not exist at this boundary | — |
| Environment secret leakage | deny-by-default allowlist; temp redirection | allowlist contents are config-reviewed |
| Output flooding (stdout/stderr) | capped readers + deadline stop | thread-based Windows readers **NO VERIFICADO** |
| Stdin-blocking worker (never/slow reads) | single monotonic session deadline started pre-I/O; deadline-aware writer | injection cases mandated |
| Parent blocked writing request | same deadline governs the writer; bounded buffer prepared pre-spawn | Windows writer thread **NO VERIFICADO** |
| Hang / timeout abuse | fail-closed deadline, terminate+reap, partial output discarded | Windows tree kill **NO VERIFICADO** |
| Malformed JSON | strict decode, duplicate-key rejection, trailing-data rejection | — |
| JSON bombs / oversized payload | request/response/stream caps enforced during transfer; size cap bounds nesting | depth cap optional future hardening |
| Response spoofing (foreign process on pipes) | one-shot pipes created per spawn; dual-level correlation; exit-code gating | local-machine adversary out of scope (out of threat model) |
| Receipt mismatch / forged filesystem evidence | six-way dual-level correlation; receipts/logs/reports unwritable to producing processes; orchestrator-only persistence after validation | contract-level rule; rogue out-of-band writes by a compromised worker are detectable defense in depth, prevented only by the future OS_SANDBOX layer |
| Compromised worker bypassing the protocol entirely (direct arbitrary file access) | out of scope for this design: worker code is trusted code; process isolation is not a sandbox | `OS_SANDBOX`: NO VERIFICADO / OUT OF SCOPE FOR POC-IPC-001 — future dedicated account/ACL/AppContainer boundary |
| Request replay | fresh orchestrator-generated `request_id`; optional duplicate tracking; no-overwrite collision as defense in depth | not a general nonce system (stated, not overclaimed) |
| Wrong-job response | `job_id` echo checked at both levels | — |
| Partial write presented as success | atomicity rules; complete-artifact-or-FAIL; invariant re-checks | — |
| Stale candidate confusion | no-overwrite; receipts reference hashes; temp disposable | — |
| Process-tree orphan (Windows) | deadline-bounded I/O; terminate+reap direct child | tree kill **NO VERIFICADO** |
| Nonzero exit with plausible stdout | success contract gate 1 | — |
| bool/int schema confusion | exact-type integer rule; strict-boolean assertion results | — |
| Unexpected encoding | strict UTF-8 both directions | console codepage caveat noted (Windows section) |
| Tool executable substitution | absolute trusted paths; registry-only sourcing | hash pinning future (**not implemented**) |
| PATH hijacking | PATH removed/minimal; absolute addressing | — |

## Windows-specific design

Target product platform; called out so POSIX abstractions don't hide risks:

- Drive letters, UNC, backslashes: excluded at the identifier/token grammar level; containment compares normalized, case-folded resolved paths.
- Case-insensitive collisions: known hazard, mitigations listed under [Path containment](#path-containment); tests pending (**NO VERIFICADO**).
- Junctions vs symlinks: containment relies on resolution semantics; junction behavior differs subtly — explicitly **NO VERIFICADO** until planted-junction tests run.
- Process trees: Job Objects / `taskkill /T` directions recorded as design decisions, **NO VERIFICADO** (see cleanup section).
- Thread-based bounded readers/writer: designated approach for pipes, **NO VERIFICADO** until demonstrated.
- Encodings: streams are bytes decoded as strict UTF-8; the console codepage plays no role because pipes carry bytes, not console text — this expectation itself gets exercised by POC-IPC-001 before being claimed.

## POSIX compatibility

Linux stays a first-class CI/test environment: the whole protocol (pipes, JSON, exit codes, group-kill cleanup, non-blocking fd I/O) is platform-neutral by construction. Constraint: POSIX cleanliness must not launder Windows risk — any behavior that differs (tree kill, junctions, case folding, pipe `select()`) carries its own Windows-specific row above and cannot be marked verified from a Linux run alone.

## Relationship to prior exploratory IPC work

Prior prototypes stay `CHANGES_REQUIRED`: no code is imported, nothing is declared PASS, and the work is not numbered as a POC. Their value here is the failure catalog above. Should future implementation want to salvage fragments, that happens inside POC-IPC-001 under this ADR's contracts, subject to normal review — never by importing the old branch as-is.

## POC-IPC-001 scope (future)

Minimal executable proof of this ADR, defined narrowly so it can pass or fail fast:

**Included:**

- one isolated Python worker process model per [Process and transport model](#process-and-transport-model) (`python -I -B`, stdin/stdout pipes, one request per process, no shell);
- one **read-only synthetic operation** taking an `input_name` safe-name token (hash-and-inspect a synthetic fixture already inside the job workspace — no new parser work, no generic path tokens);
- typed JSON request/response/receipt exactly per this ADR's schemas and bounds;
- trusted jobs root external to the request; job-id-only addressing;
- bounded stdin (deadline-aware writer), stdout, stderr; single monotonic session deadline covering the whole session;
- per-request timeout with terminate+reap and honest per-platform cleanup claims;
- controlled environment allowlist and derived `cwd`;
- typed receipt with correlation, hash-format checks, and required (non-vacuous) assertions;
- the failure-injection matrix below;
- reporting limited to what each platform demonstration actually shows.

**Failure-injection matrix (mandatory acceptance surface for the future POC):**

Request / schema: oversize request · unknown request field · `protocol_version: true` · invalid/malformed UUID · non-v4 UUID version · uppercase UUID · invalid `job_id` · `job_id` containing `..` · `job_id` = `.`/`..` forms · `timeout_ms` below minimum · `timeout_ms` above maximum · `timeout_ms` as float/bool/string.

Stdin: worker never reads stdin → `PROCESS_TIMEOUT`, terminated+reaped, pipes closed, orchestrator returns · worker reads stdin too slowly → same controlled timeout · child closes stdin immediately → `PIPE_WRITE_FAILED`.

Stdout/stderr: oversize stdout · oversize stderr · malformed UTF-8 · malformed JSON · duplicate JSON keys · NaN/Infinity literal · trailing JSON data · unknown response field (top level and nested) · response EOF / empty stdout with zero exit → `INVALID_RESPONSE` · empty stdout with nonzero exit → `PROCESS_FAILED`.

Process: hang hitting the deadline · crash · nonzero exit + plausible valid JSON · zero exit + invalid JSON.

Correlation: wrong `request_id` · wrong `job_id` · wrong `operation` · receipt/response mismatch · `error.code` differing from `status`.

Receipt: missing receipt on SUCCESS · null/absent `error` on failure · `error.code` ≠ `status` · receipt `FAILED` while response `SUCCESS` · unknown nested receipt field · malformed SHA-256 (uppercase, short, prefixed, whitespace) · output path outside `candidates/` · counts over `MAX_INPUT_COUNT` / `MAX_OUTPUT_COUNT` / `MAX_WARNING_COUNT` / `MAX_ASSERTION_COUNT` · warning item over `MAX_STRING_BYTES` · backwards wall-clock timestamps accepted (audit-only; locks the no-ordering-invariant decision).

Assertions: empty required assertions · `passed: false` correctly propagated to FAIL · `passed: 1` rejected (non-boolean) · array/object `expected`/`actual` rejected.

Paths: traversal-shaped token · absolute-path token · drive-qualified token · UNC token · planted symlink escape · planted junction escape (Windows) · case-collision pair (Windows).

Timeout/cleanup: direct-child termination on deadline · descendant holding pipes cannot extend the session · Windows cleanup claim limited to what is demonstrated · POSIX process-group cleanup exercised.

**Explicitly excluded:** real Skyrim files; PapyrusCompiler; xEdit; Mutagen; Creation Kit automation; CKPE; live Data writes; network transports; persistent daemons; performance benchmarking; **OS-level confinement/sandboxing** (a separate future security boundary per [Process isolation is not a sandbox](#process-isolation-is-not-a-sandbox)).

**Expected evidence claim:** session-level PASS/FAIL over transport/execution/correlation properties only, per [Evidence semantics](#evidence-semantics), with per-platform honesty about which cleanup strategies were demonstrated. The POC proves protocol/process isolation — **not** OS filesystem confinement (`OS_SANDBOX` remains NO VERIFICADO / out of scope).

## Acceptance criteria for this ADR

ADR-002 may move PROPOSED → ACCEPTED when:

- the threat model above is judged covered by review;
- request/response/receipt contracts are unambiguous — the closed-world schemas here suffice to write validators without further decisions;
- trusted root provenance is outside the request;
- arbitrary shell/command execution is impossible by construction;
- output/input bounds are enforceable by design (bounded transfer requirement, not aspiration) and the deadline covers the whole session;
- SUCCESS invariants are complete and testable;
- timeout and process cleanup are defined, with Windows gaps honestly labeled NO VERIFICADO;
- the failure taxonomy covers observable states, including pipe-edge classifications;
- path containment rules are concrete enough to test, with the trusted-vs-token separation stated canonically;
- evidence semantics make no overclaims;
- the process-isolation vs OS-sandbox boundary is stated without overclaims (`OS_SANDBOX` explicitly NO VERIFICADO / out of POC scope);
- POC-IPC-001's scope is minimal and verifiable.

## Acceptance record

- **Status change:** PROPOSED → ACCEPTED
- **Date:** 2026-08-25
- **Authorized by:** the repository owner, after four architecture review rounds.

Accepted by the repository owner on 2026-08-25 after four architecture review rounds. Acceptance establishes the IPC/process-isolation architecture contract. It does not claim that POC-IPC-001 is implemented or that OS-level sandboxing has been verified (`OS_SANDBOX` remains NO VERIFICADO). The next work item is POC-IPC-001, implementing this contract under its own evidence rules.

## Out of scope

- Any implementation (no `ipc.py`, no runner, no worker entry, no tests) — this PR is ADR-only.
- POC-IPC-001 execution; POC-003 (PapyrusCompiler dry-invoke); POC-004 (xEdit validator); Creation Kit UIA (POC-001 domain); CKPE; Mutagen.
- External tool integration contracts beyond the executable-trust rules.
- Performance tuning, persistent workers, multi-request sessions, remote transports — rejected for the first iteration by [Process and transport model](#process-and-transport-model).
