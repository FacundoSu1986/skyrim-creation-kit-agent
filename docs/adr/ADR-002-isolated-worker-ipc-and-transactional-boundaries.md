# ADR-002 — Isolated worker IPC protocol and transactional boundaries

- **Status:** PROPOSED
- **Date:** 2026-08-25
- **Scope:** IPC protocol and transactional boundaries for isolated workers.
- **Depends on:** [ADR-001](ADR-001-hybrid-headless-first-architecture.md) (ACCEPTED).
- **Related:** POC-002 (PASS — synthetic TES4 safety pipeline), future **POC-IPC-001**.
- **Prior work:** previously reviewed exploratory IPC prototypes remain `CHANGES_REQUIRED`. They are **not** imported as validated code and are **not** POC-003. They are used here only as a catalog of known failure modes; each one is explicitly closed in [Known failures closed](#known-failures-closed).

## Context

ADR-001 accepted a hybrid, headless-first architecture whose execution layer consists of isolated deterministic workers behind a capability router. POC-002 validated the orchestration invariants inside one process: closed operation enum, truthful capability routing, candidate-only workspace with immutable originals, no-overwrite receipts, and the `E_NONE`/`E0`–`E5` evidence ladder.

What is still undefined is the **boundary**: how a trusted orchestrator talks to an out-of-process worker such that a compromised, buggy, hung, or lying worker cannot escalate into arbitrary execution, workspace escape, unbounded resource consumption, or false success claims. Prior exploratory prototypes attempted this boundary and failed review on specific, recurring defects (trusted root supplied by the request, ambiguous identifier bounds, `bool`-as-`int` schema confusion, thin success semantics, unbounded output capture, absent timeout/cleanup). This ADR defines the protocol so that the future POC-IPC-001 can be implemented without architectural ambiguity and so that reviewers can test against explicit invariants.

This document is **design only**. It implements nothing. Where behavior is a design decision that has never been demonstrated on the target platform, this ADR says **NO VERIFICADO** rather than implying support.

## Canonical principle (preserved from ADR-001)

AI decides WHAT. Deterministic software decides HOW. Validators decide WHETHER IT WORKED. Human decides WHETHER TO ACCEPT.

The IPC boundary exists to enforce this split mechanically: nothing crosses it except typed requests derived from allowlisted operations, and nothing comes back that can *declare* success — success is computed by the trusted side from independently checkable invariants.

## Decision summary

| # | Decision |
| --- | --- |
| D1 | Trusted jobs root lives only in trusted-side configuration; requests carry a validated `job_id`, never a root/base_dir/path prefix. |
| D2 | One-shot process model: one request per worker process over stdin → one JSON response on stdout. No daemon, broker, sockets, HTTP, or queues. |
| D3 | Strict JSON UTF-8 serialization; exact integer `protocol_version`; unsupported version fails closed. |
| D4 | Separate bounded identifier contracts (`job_id`, `request_id`, `operation`); identity is never composed by concatenating prefixed strings. |
| D5 | Success is an orchestrator-computed conjunction of process, transport, correlation, receipt, and assertion invariants — never inferred from `response.status` alone. Nonzero exit can never yield SUCCESS. |
| D6 | All stream sizes are enforced during reading via capped readers; limits exist to be applied, not declared. |
| D7 | Timeout is fail-closed: terminate, close pipes, discard partial output, record `PROCESS_TIMEOUT`. |
| D8 | Worker environment is deny-by-default with an explicit trusted allowlist; `cwd` is derived trusted-side; no secrets cross the boundary. |
| D9 | No shell anywhere: operations map deterministically to argv-style invocations; generic command execution does not exist as an operation. |
| D10 | All request-derived paths are derived, resolved, and re-contained inside the job workspace; traversal/symlink/junction escape attempts fail closed. |
| D11 | Workers write only `candidates/` and `temp/`; `originals/` is immutable; receipts are append-only; candidate→live promotion happens nowhere in this design. |
| D12 | POC-IPC-001 outcomes use a session-level `PASS`/`FAIL` verdict **separate** from the artifact evidence ladder; no E3/E4/E5 claims and no E2 reuse. |

## Trust boundaries

**TRUSTED (orchestrator side):**

- orchestrator configuration, including `TRUSTED_JOBS_ROOT`;
- operation allowlist and per-operation parameter schemas;
- worker registry: executable paths, interpreter path, environment allowlist, resource limits;
- protocol/schema validators;
- capability registry status (which backends actually exist);
- the code that computes SUCCESS/FAIL and emits the execution summary.

**SEMI-TRUSTED (machine-local, validated before use):**

- subprocess stdout/stderr until schema-validated;
- environment variable values passed through the allowlist;
- files already inside the job workspace (e.g., provisioned originals) — integrity enforced by SHA-256 invariants, not by trust;
- tool executables located at configured absolute paths (identity pinning is future work; see [Tool executable trust](#tool-executable-trust)).

**UNTRUSTED:**

- LLM output of any kind;
- ModPlan content and every string inside request parameters;
- user-controlled file/plugin names;
- worker responses until fully validated (a worker may be buggy or adversarial — "worker" is not automatically "friend");
- external tool output relayed through workers;
- candidate artifacts until independently re-opened/asserted.

Rule: data may flow upward only after the receiving layer validates it. The orchestrator treats the worker exactly as it treats any other untrusted producer of bytes.

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

| Identifier | Form | Hard bound | Notes |
| --- | --- | --- | --- |
| `job_id` | `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$` | ≤ 64 chars | Same character discipline as POC-002's `operation_id`: no separators, no `..`, case preserved but compared case-sensitively for identity; path derivation additionally re-validated after resolve (see [Path containment](#path-containment)). |
| `request_id` | UUID v4 canonical lowercase hyphenated form (recommended) | ≤ 64 chars | Globally unique per attempt; generated by the caller/orchestrator, echoed by worker. |
| `operation` | member of the closed operation enum | ≤ 64 chars | Must exist in both orchestrator and worker registries for the negotiated backend. |

Invariants:

- `response.request_id == request.request_id` and `receipt.request_id == request.request_id` — else `RECEIPT_MISMATCH`.
- `response.job_id == request.job_id` and `receipt.job_id == request.job_id` — else `RECEIPT_MISMATCH` (wrong-job responses are rejected even if everything else looks perfect).
- `receipt.operation == request.operation` — else `RECEIPT_MISMATCH`.
- Any identifier outside its form/bound → `INVALID_REQUEST` (orphaning the request before any process spawns).

## Message schemas

Logical schemas only — field tables plus invariants. Implementation types (dataclasses/Pydantic) are deliberately **not** introduced by this ADR.

### Request

| Field | Type | Constraints |
| --- | --- | --- |
| `protocol_version` | integer | exactly `1`; `type(v) is int` |
| `request_id` | string | UUID v4 recommended, ≤ 64 chars |
| `job_id` | string | table above |
| `operation` | string | closed enum member |
| `parameters` | object | must satisfy the per-operation parameter schema; total serialized request size ≤ `MAX_REQUEST_BYTES`; individual strings ≤ `MAX_STRING_BYTES`; relative paths within the job workspace only |
| `timeout_ms` | integer, optional | `1 ≤ x ≤ MAX_TIMEOUT_MS`; `type(x) is int`; clamped/rejected otherwise |

No other fields. Unknown fields reject (`INVALID_REQUEST`) — forward-compatible extensions come with a protocol version bump, not silent tolerance.

### Response

| Field | Type | Constraints |
| --- | --- | --- |
| `protocol_version` | integer | exactly `1` |
| `request_id` / `job_id` | string | echo of request values |
| `operation` | string | echo of request value |
| `status` | string | `SUCCESS` or an error code from the taxonomy |
| `started_at_ms` / `finished_at_ms` | integers | epoch millis; `finished ≥ started`; `type(x) is int` |
| `worker_receipt` | object or null | present iff `status == SUCCESS`; must satisfy Receipt schema |
| `error` | object or null | `{code, message}` present iff `status != SUCCESS`; `message` free text ≤ `MAX_STRING_BYTES`, **must not** embed secret material |

Total serialized response ≤ `MAX_RESPONSE_BYTES`.

### Receipt (worker_receipt)

Machine-readable, produced by the worker, validated by the orchestrator:

| Field | Type | Constraints |
| --- | --- | --- |
| `protocol_version` | integer | `1` |
| `request_id` / `job_id` / `operation` | string | correlate to request |
| `status` | string | `SUCCESS` or worker-level error code |
| `started_at_ms` / `finished_at_ms` | integers | monotone pair |
| `inputs` | array | references + SHA-256 of consumed inputs (e.g., original hash observed) |
| `outputs` | array | candidate paths (workspace-relative) + SHA-256, when the operation produces artifacts |
| `worker_assertions` | array | assertion objects `{name, expected, actual, passed, details?}`; non-empty for operations that define assertions |
| `warnings` | array of strings | non-fatal observations |

Three artifact kinds are deliberately distinct and never merged: **worker receipt** (this object), **orchestrator execution summary** (POC-002's `ExecutionSummary`, including verdict/evidence level/invariant hashes), **validator report** (future third-party static validation, E3 territory).

## Size and resource limits

Limits exist to be enforced at read time ([Bounded I/O](#bounded-io-strategy)), not measured afterwards. Exceeding any limit is fail-closed.

| Limit | Value | Applies to |
| --- | --- | --- |
| `PROTOCOL_VERSION` | `1` | all messages |
| `MAX_REQUEST_BYTES` | 65 536 (64 KiB) | serialized request |
| `MAX_RESPONSE_BYTES` | 262 144 (256 KiB) | serialized response incl. receipt |
| `MAX_STDOUT_BYTES` | 262 144 (256 KiB) | raw stdout captured |
| `MAX_STDERR_BYTES` | 65 536 (64 KiB) | raw stderr captured |
| `MAX_STRING_BYTES` | 4 096 | any single string field value |
| `MAX_ASSERTION_COUNT` | 100 | `worker_assertions` length |
| `DEFAULT_TIMEOUT_MS` | 30 000 | per-request deadline if omitted |
| `MAX_TIMEOUT_MS` | 600 000 | hard ceiling regardless of configuration |

Values are constants proposed for POC scale; changing them later changes this ADR, not a request field.

## Bounded I/O strategy

`communicate()`-style full-buffered capture is **forbidden**: it consumes memory proportional to attacker-chosen output and only measures afterwards. The required strategy:

- stdout and stderr are read by dedicated reader loops that accumulate **at most** their cap. The byte after the cap is discarded and the exchange is marked `OUTPUT_LIMIT_EXCEEDED`; the process is then terminated per the timeout path.
- Reading is additionally bounded by the request deadline: after the deadline, readers stop unconditionally and the process is terminated. An orphaned descendant inheriting the pipes therefore cannot extend resource consumption past the deadline — the orchestrator stops listening, not just stops waiting.
- POSIX: non-blocking reads/select on the pipe fds satisfy this directly.
- Windows: `select()` does not work on pipes; reader threads with bounded accumulators are the designated approach. Thread-based bounded readers on Windows are a **design decision — NO VERIFICADO** until POC-IPC-001 demonstrates them.
- stderr is captured for diagnostics, size-capped, never parsed as protocol, and truncated content is flagged in the summary.

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
2. Trusted orchestrator validates request schema: sizes, encodings, unknown fields, `type-is-int` numerics, bounds.
3. Orchestrator validates `job_id` against the identifier contract.
4. Orchestrator derives the job workspace as `TRUSTED_JOBS_ROOT/jobs/<job_id>/` — the request never supplies any path component beyond `job_id`.
5. Policy validates the operation: membership in the allowlist, capability status SUPPORTED, risk class acceptable, parameters against the operation schema.
6. Orchestrator selects the deterministic worker executable from the registry (never from the request).
7. Controlled environment constructed: allowlisted variables, temp redirection, no shell, `-I -B`, cwd = job workspace.
8. Subprocess spawned; stdin receives the bounded request; bounded readers attach to stdout/stderr; deadline starts.
9. Bounded transfer completes or trips a limit/deadline (`OUTPUT_LIMIT_EXCEEDED` / `PROCESS_TIMEOUT`).
10. Exit code awaited via `wait()` (reaping prevents zombies); nonzero exit ⇒ `PROCESS_FAILED`, and any stdout content is treated as untrusted diagnostics, never as a result.
11. Response schema validated: encoding, JSON strictness, size, field types (`type-is-int`), echo/correlation fields, status vocabulary.
12. If `status == SUCCESS`: receipt presence and receipt-schema validation; correlation re-checked at receipt level.
13. Assertions validated: required worker assertions present, non-empty, all passing; protocol assertions (transport, schema, correlation, exit code) evaluated by the orchestrator itself.
14. Workspace invariants validated where applicable: originals' SHA-256 unchanged; candidates confined to `candidates/`; no-overwrite respected; receipts appendable.
15. Only now may the exchange be considered successful; the orchestrator computes the execution summary (verdict + outcome + invariant hashes).
16. Summary persisted; branch ends. Every terminal state — PASS or FAIL — produces a durable summary; silence is not a state.

## Success contract

Overall SUCCESS is the **conjunction** of all of the following; failing any one yields FAIL with its specific code. Success is computed by the orchestrator; a worker cannot assert it into existence.

1. process exit code == 0 (nonzero exit can never produce SUCCESS — even with plausible JSON on stdout);
2. response structurally valid (encoding, JSON, size, schema, version supported);
3. `response.status == "SUCCESS"`;
4. receipt exists and schema-valid;
5. `receipt.status == "SUCCESS"`;
6. `receipt.operation == request.operation`;
7. correlation holds at response and receipt level (`request_id`, `job_id`);
8. required assertions exist and are non-empty (per-operation definition);
9. all assertions pass;
10. protocol version supported end-to-end;
11. workspace invariants hold where applicable (originals untouched, containment, no-overwrite).

There is no partial success. There is no "success with warnings" distinct from `warnings` being carried inside a fully-passing receipt.

## Failure taxonomy

Stable codes for tests and summaries. Emission point noted; both sides use the same vocabulary.

| Code | Meaning | Emitted by |
| --- | --- | --- |
| `INVALID_REQUEST` | schema/size/encoding/unknown-field/type violations | orchestrator (pre-spawn) or worker |
| `REQUEST_LIMIT_EXCEEDED` | request above `MAX_REQUEST_BYTES` | orchestrator |
| `UNSUPPORTED_PROTOCOL_VERSION` | version ≠ 1 or wrong type | both |
| `INVALID_JOB_ID` | identifier contract violation | orchestrator (pre-spawn) |
| `INVALID_OPERATION` | not in allowlist / unsupported by worker | both |
| `POLICY_VIOLATION` | policy engine rejection pre-spawn | orchestrator |
| `WORKSPACE_VIOLATION` | path containment breach; no-overwrite breach; originals mutation detected | both |
| `PROCESS_TIMEOUT` | deadline exceeded | orchestrator |
| `PROCESS_FAILED` | nonzero exit, spawn failure, crash | orchestrator |
| `OUTPUT_LIMIT_EXCEEDED` | any stream past its cap | orchestrator |
| `INVALID_RESPONSE` | response fails schema/JSON/UTF-8 validation | orchestrator |
| `RECEIPT_MISMATCH` | missing receipt or failed correlation | orchestrator |
| `ASSERTION_FAILED` | required assertions missing/empty/failing | orchestrator |
| `INTERNAL_ERROR` | unexpected condition, always fail-closed | both |

## Timeout and process-tree cleanup

- Deadline = `timeout_ms` from the request, clamped to `[1, MAX_TIMEOUT_MS]`; wall-clock enforced by the orchestrator.
- On expiry: readers stop immediately; terminate; reap via `wait()`; close pipes in `finally`; discard all partial output; record `PROCESS_TIMEOUT`; verdict FAIL. Partial output is never salvaged into a result.
- **POSIX:** spawn with `start_new_session=True` → the child leads its own process group; cleanup escalates `SIGTERM` (grace) → `SIGKILL` to the whole group via `os.killpg`. Group kill on POSIX is standard practice; its specific exercise in tests remains to be demonstrated by POC-IPC-001.
- **Windows:** `Process.terminate()` maps to `TerminateProcess` and kills **only** the direct child. Full tree termination via Job Objects (assign child at spawn, `TerminateJobObject`) or `taskkill /T /F` via a trusted absolute path is a recorded **design direction — NO VERIFICADO**. Console-control alternatives (`CREATE_NEW_PROCESS_GROUP` + `CTRL_BREAK_EVENT`) are equally **NO VERIFICADO**. This ADR intentionally does not claim verified tree cleanup on Windows; POC-IPC-001 must include a hang-and-kill demonstration before any stronger claim is written.
- Orphan risk note: descendants that outlive the worker and inherit the stdout pipe cannot stall the exchange — readers are deadline-bounded (see [Bounded I/O](#bounded-io-strategy)). Orphan detection/reaping of grandchildren is **NO VERIFICADO** and explicitly out of POC-IPC-001 scope.

## Path containment

All filesystem access resolves inside the job workspace:

- The only request-borne path ingredient is `job_id`, which by grammar cannot contain separators, drives, or `..`. Absolute request paths are **forbidden**: there is no field that could carry one.
- Derived paths are built trusted-side as `TRUSTED_JOBS_ROOT/jobs/<job_id>/<area>/<relative>`; `relative` components, when a request carries names (e.g., target plugin names), are validated against the same safe-name grammar and rejected on violation (`WORKSPACE_VIOLATION`).
- Before any access, final paths are resolved (`resolve()`) and required to remain inside the resolved trusted root. Comparison is performed on normalized forms; on Windows normalization includes case folding, because the platform is case-insensitive.
- Drive switching and UNC paths are excluded by construction: the grammar admits neither `:` nor `\` nor leading `//`, and post-resolve containment re-check catches anything that slips another way.
- Symlink/junction escapes: `resolve()` follows links, so a link planted inside the workspace pointing outward is caught by the post-resolve re-check **if** the platform resolves junctions identically. Junction-specific and TOCTOU-window behaviors on Windows are **NO VERIFICADO**; POC-IPC-001's failure-injection suite must include planted-link cases before this ADR's containment claim is upgraded from design to verified.
- Case-collision handling (two names differing only by case on Windows) is a known aliasing hazard; the safe-name grammar plus exact-match receipt bookkeeping mitigates confusion, but collision tests are likewise pending (**NO VERIFICADO**).

## Workspace contract

Conceptual layout preserved from POC-002:

```text
TRUSTED_JOBS_ROOT/
  jobs/<job_id>/
    input/        provisioned request materials
    originals/    immutable sources (SHA-256 pinned; opened read-only by workers)
    candidates/   the ONLY write target for produced artifacts
    temp/         disposable scratch (also the redirected TEMP/TMPDIR)
    reports/      validator outputs (future)
    receipts/     append-only, no-overwrite receipts
    logs/         captured stderr and orchestrator logs
```

- `originals/` immutability is enforced, not assumed: hashes before/after; any change aborts with `WORKSPACE_VIOLATION`.
- `candidates/` is write-once per operation run; overwrite attempts fail (`WORKSPACE_VIOLATION`), preserving evidence integrity.
- `temp/` may be wiped between runs without notice.
- Workers never address live Skyrim/Data directories; the concept does not exist in this protocol. Promotion of candidates toward any game location is a separate, HITL-gated concern outside IPC scope entirely.

## Transactional boundaries and atomicity

- A worker mutates only `candidates/` + `temp/`. An operation either produces its complete artifact(s) and a passing receipt, or it FAILs; intermediate states are never reported as success.
- Write-temp-then-move within `candidates/` is the recommended worker pattern for artifact completeness; the no-overwrite rule makes the final placement effectively single-shot.
- There is **no automatic promotion** of candidates to any live location anywhere in this design; transactionality stops at the workspace edge by intention (HITL owns acceptance per ADR-001).
- Originals are never mutated; "success" that altered an original is a detected invariant breach, not a transactional rollback problem.

## Idempotency, retries, replay

- Operations declare (in the registry) whether they are read-only or effectful. Read-only operations may be retried by caller policy. Effectful (write-to-candidates) operations are **never auto-retried** absent an explicit idempotency contract, because candidate no-overwrite turns a blind retry into a guaranteed `WORKSPACE_VIOLATION` — which is the desired loud failure, not silent duplication.
- Every attempt carries a fresh unique `request_id`; requests are individually traceable end-to-end via summaries and receipts.
- Replay of a captured request (same `request_id` re-fed to a new process) is structurally blunted by the one-shot model and the append-only workspace: a replayed effectful request collides with existing candidate/receipt and fails loudly. Orchestrator-side duplicate-`request_id` tracking is permitted as defense in depth but not mandated for POC-IPC-001.

## Assertion semantics

Three distinct classes; conflating them is a review defect:

- **Protocol assertions** — evaluated by the orchestrator about the exchange itself: bounded transfer completed, exit code zero, schema valid, correlation held, deadlines respected. ("response JSON parsed" lives here.)
- **Worker assertions** — recorded in the receipt by the worker about its own processing steps.
- **Artifact assertions** — independent re-opening/re-parsing/hash verification of produced artifacts (POC-002's reopen-after-write pattern is the exemplar).

Rules: operations define which worker/artifact assertions are *required*; SUCCESS demands every required assertion present, non-empty, and passing. A vacuous receipt (empty assertions for an operation requiring them) is `ASSERTION_FAILED`. No protocol assertion ever substitutes for an artifact assertion: parsing the envelope says nothing about plugin validity.

## Evidence semantics

This protocol introduces a **session outcome** — `PASS` / `FAIL` — attached to the execution summary. It is deliberately orthogonal to the artifact evidence ladder (`E_NONE`, `E0`–`E5`):

- A PASSing IPC session evidences: bounded transport occurred, the worker executed under the constrained environment, the response/receipt was well-formed and correlated, and the operation's own assertions passed at the protocol/worker level.
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
| Declared-but-unenforced stdout/stderr caps; unbounded `communicate()` | [Size and resource limits](#size-and-resource-limits), [Bounded I/O](#bounded-io-strategy) (D6) |
| Missing timeout/process-tree cleanup | [Timeout and process-tree cleanup](#timeout-and-process-tree-cleanup) (D7) |
| Inherited environment / secret exposure | [Environment control](#environment-control) (D8) |
| Request-controlled cwd | [Working directory](#working-directory) (D8) |
| Arbitrary shell / free-form commands | [Process and transport model](#process-and-transport-model) (D9) |

## Boolean/int confusion

Python `bool` subclasses `int`; therefore `isinstance(protocol_version, int)` accepts `true`. Contract rule: wherever a schema says *integer*, validation MUST use exact-type semantics (`type(v) is int`). This applies to `protocol_version`, `timeout_ms`, timestamps, counts, and assertion fields. JSON schema tables in this ADR mean exact integers; floats (`1.0`) and booleans are invalid wherever an integer is specified. Documented here explicitly so implementation and tests encode it once, identically, on both sides.

## Threat model

| Threat | Mitigation (design element) | Residual / status |
| --- | --- | --- |
| Path traversal via request | safe-name grammar; trusted-side derivation; post-resolve containment | injection tests mandated in POC-IPC-001 |
| Workspace escape | same as above + `resolve()` re-check | — |
| Symlink/junction escape | post-resolve containment | junction specifics **NO VERIFICADO** pending tests |
| Arbitrary command injection | no shell; closed op enum; argv-style deterministic invocation; no EXECUTE_COMMAND concept | — |
| Shell injection | shell does not exist at this boundary | — |
| Environment secret leakage | deny-by-default allowlist; temp redirection | allowlist contents are config-reviewed |
| Output flooding | capped readers + deadline stop | thread-based Windows readers **NO VERIFICADO** |
| Hang / timeout abuse | fail-closed deadline, terminate+reap, partial output discarded | Windows tree kill **NO VERIFICADO** |
| Malformed JSON | strict decode, duplicate-key rejection, trailing-data rejection | — |
| JSON bombs / oversized payload | request/response/stream caps enforced during read; nesting depth implicitly bounded by size cap | depth cap optional future hardening |
| Response spoofing (foreign process on pipes) | one-shot pipes created per spawn; correlation ids; exit-code gating | local-machine adversary out of scope (out of threat model) |
| Receipt mismatch | dual-level correlation (response + receipt) vs request | — |
| Request replay | fresh `request_id` per attempt; no-overwrite workspace; optional duplicate tracking | — |
| Wrong-job response | `job_id` echo checked at both levels | — |
| Partial write presented as success | atomicity rules; complete-artifact-or-FAIL; invariant re-checks | — |
| Stale candidate confusion | no-overwrite; receipts reference hashes; temp disposable | — |
| Process-tree orphan (Windows) | deadline-bounded readers; terminate+reap direct child | tree kill **NO VERIFICADO** |
| Nonzero exit with plausible stdout | success contract gate 1 | — |
| bool/int schema confusion | exact-type integer rule | — |
| Unexpected encoding | strict UTF-8 both directions | console codepage caveat noted (Windows section) |
| Tool executable substitution | absolute trusted paths; registry-only sourcing | hash pinning future (**not implemented**) |
| PATH hijacking | PATH removed/minimal; absolute addressing | — |

## Windows-specific design

Target product platform; called out so POSIX abstractions don't hide risks:

- Drive letters, UNC, backslashes: excluded at the identifier grammar level; containment compares normalized, case-folded resolved paths.
- Case-insensitive collisions: known hazard, mitigations listed under [Path containment](#path-containment); tests pending (**NO VERIFICADO**).
- Junctions vs symlinks: containment relies on resolution semantics; junction behavior differs subtly — explicitly **NO VERIFICADO** until planted-junction tests run.
- Process trees: Job Objects / `taskkill /T` directions recorded as design decisions, **NO VERIFICADO** (see cleanup section).
- Encodings: streams are bytes decoded as strict UTF-8; the console codepage plays no role because pipes carry bytes, not console text — this expectation itself gets exercised by POC-IPC-001 before being claimed.

## POSIX compatibility

Linux stays a first-class CI/test environment: the whole protocol (pipes, JSON, exit codes, group-kill cleanup) is platform-neutral by construction. Constraint: POSIX cleanliness must not launder Windows risk — any behavior that differs (tree kill, junctions, case folding, pipe `select()`) carries its own Windows-specific row above and cannot be marked verified from a Linux run alone.

## Relationship to prior exploratory IPC work

Prior prototypes stay `CHANGES_REQUIRED`: no code is imported, nothing is declared PASS, and the work is not numbered as a POC. Their value here is the failure catalog above. Should future implementation want to salvage fragments, that happens inside POC-IPC-001 under this ADR's contracts, subject to normal review — never by importing the old branch as-is.

## POC-IPC-001 scope (future)

Minimal executable proof of this ADR, defined narrowly so it can pass or fail fast:

**Included:**

- one isolated Python worker process model per [Process and transport model](#process-and-transport-model) (`python -I -B`, stdin/stdout pipes, one request per process, no shell);
- one **read-only synthetic operation** (e.g., hash-and-inspect a synthetic fixture already inside the job workspace — no new parser work required);
- typed JSON request/response/receipt exactly per this ADR's schemas and bounds;
- trusted jobs root external to the request; job-id-only addressing;
- bounded stdin/stdout/stderr with enforced caps; per-request timeout with terminate+reap;
- controlled environment allowlist and derived `cwd`;
- typed receipt with correlation and required (non-vacuous) assertions;
- failure-injection test matrix, at minimum: oversize request; oversize stdout; oversized stderr; deliberate hang hitting timeout; nonzero exit with valid-looking JSON on stdout; malformed JSON response; duplicate JSON keys; `protocol_version` sent as `true`; wrong `request_id`; wrong `job_id`; wrong `operation`; empty assertions on an operation requiring them; traversal-shaped `job_id`; planted symlink/junction escape attempt; NaN literal in response; unknown response field.
- honest reporting of which cleanup strategies were demonstrated per platform (POSIX vs Windows rows separately).

**Explicitly excluded:** real Skyrim files; PapyrusCompiler; xEdit; Mutagen; Creation Kit automation; CKPE; live Data writes; network transports; persistent daemons; performance benchmarking.

**Expected evidence claim:** session-level PASS/FAIL over transport/execution/correlation properties only, per [Evidence semantics](#evidence-semantics).

## Acceptance criteria for this ADR

ADR-002 may move PROPOSED → ACCEPTED when:

- the threat model above is judged covered by review;
- request/response/receipt contracts are unambiguous (field tables + invariants sufficient to write validators without further decisions);
- trusted root provenance is outside the request;
- arbitrary shell/command execution is impossible by construction;
- output bounds are enforceable by design (bounded-read requirement, not aspiration);
- SUCCESS invariants are complete and testable;
- timeout and process cleanup are defined, with Windows gaps honestly labeled NO VERIFICADO;
- the failure taxonomy covers observable states;
- path containment rules are concrete enough to test;
- evidence semantics make no overclaims;
- POC-IPC-001's scope is minimal and verifiable.

## Out of scope

- Any implementation (no `ipc.py`, no runner, no worker entry, no tests) — this PR is ADR-only.
- POC-IPC-001 execution; POC-003 (PapyrusCompiler dry-invoke); POC-004 (xEdit validator); Creation Kit UIA (POC-001 domain); CKPE; Mutagen.
- External tool integration contracts beyond the executable-trust rules.
- Performance tuning, persistent workers, multi-request sessions, remote transports — rejected for the first iteration by [Process and transport model](#process-and-transport-model).
