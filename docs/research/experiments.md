# Canonical experiments

Imported from the structured research archive (`src/lib/research/experiments.ts`). Statuses below are evidence labels, not promises.

## POC-001 — Read-only Creation Kit process and control inspect

**Status:** `BLOQUEADO`

**Hypothesis:** A running SSE Creation Kit 1.6.x process exposes at least one useful UIA or MSAA control (window title, menu, Data dialog list) that can be read without coordinates and without saving.

**Method:** On a dedicated Windows machine with a legal CK install: launch CK, attach Inspect.exe / Accessibility Insights and optionally FlaUI/pywinauto, enumerate the main window, record control tree depth, AutomationIds, and whether Object Window / Data dialog children are accessible. Close without saving. Repeat 20 times first, 100 if stable.

**Success:** Structured JSON report; zero file writes under `Data`; zero coordinate clicks; no crash attributable to the inspector; reproducible window identity (process name + title + PID).

**Blocked by:** no Creation Kit / Windows environment in the original research sandbox.

## POC-002 — Read-only plugin open via header parser

**Archive status:** `HIPOTESIS` at research time.  
**Current repository status:** **PASS** after implementation and independent revalidation.

**Hypothesis:** A synthetic ESP containing only a TES4 header (no Bethesda records copied) can be parsed for header information without Creation Kit.

**Success:** Header fields round-trip; hash logged; no game files touched.

Implementation: [`../../research/poc_002/`](../../research/poc_002/).

## POC-003 — PapyrusCompiler dry-invoke contract

**Status:** `NO VERIFICADO`

Verify that the official compiler is invoked with explicit arguments, no shell, bounded timeout, captured stdout/stderr and output PEX verification.

**(Pre-execution context)** The compiler is a local/proprietary dependency: it was not available to CI at the time the acceptance criteria were designed (2026-09-01), which is why the real experiment is locally executable but not CI-runnable. That pre-execution constraint is historical context; it no longer describes the current execution state.

**Executed 2026-09-06, re-executed 2026-09-11** after the harness was corrected
so that criteria 11 and 12 fail closed on every execution path (previously they
could return a vacuous `PASS`). Result recorded in
[2026-09-06-poc-003-results.md](2026-09-06-poc-003-results.md): 13 of 15
pre-registered criteria passed; mandatory criterion 12 (no unexpected outputs)
failed with `UNEXPECTED_OUTPUT_PRESENT` — the interrupted run leaves an
undeclared `candidates/<token>.pas` behind — and mandatory criterion 14
(determinism) failed with `DETERMINISM_MISMATCH`. POC-003 is not `PASS`;
repository status remains `NO VERIFICADO` and `DETERMINISTIC_OUTPUT` is
`NO VERIFICADO`. The hermetic test suite (105 tests) is CI-gated by
`.github/workflows/poc003.yml` and never requires the compiler. Implementation:
[`../../research/poc_003/`](../../research/poc_003/). Acceptance criteria are
pre-registered (2026-09-01) in the [POC-003 pre-registration](2026-09-01-poc-003-pre-registration.md),
under the `PAPYRUS_COMPILE_DRYRUN_V1` profile defined by
[ADR-004](../adr/ADR-004-external-tool-execution-contract.md) (ACCEPTED).
POC-003 does not use the ADR-002 IPC protocol: the compiler cannot speak it.
See the identifier rule below.

## POC-004 — xEdit allowlisted `-script -autoexit`

**Status:** `NO VERIFICADO`

Use a user-installed xEdit copy, an allowlisted/hash-pinned reporting script and an explicit completion marker. Missing marker is failure. Originals remain untouched.

## POC-IPC-001 — Isolated worker protocol and transactional boundaries

**Status:** **PASS**

**Hypothesis:** a trusted orchestrator can drive an out-of-process worker over a bounded JSON
stdio protocol and never report success on inference: verdict computed by the trusted side as a
conjunction of invariants (exit code, schema validation, assertions, deadline, stream caps,
cleanup), with fail-closed behavior on every defect class.

**Method:** implement the ADR-002 lifecycle literally for one trusted read-only operation
(`INSPECT_SYNTHETIC_INPUT`) against a synthetic fixture: full pre-spawn validation (invalid
requests spawn nothing), a single monotonic session deadline, bounded deadline-aware stdin writer
and stdout/stderr pumps (never `communicate()`), platform-honest cleanup, path containment,
no-overwrite receipts. Adversarial helper workers hang, spam, close stdin, emit malformed JSON,
mis-correlate, spawn descendants, or violate their receipt shape.

**Success:** every defect yields a deterministic taxonomy code and no false `PASS`. Achieved:
181 hermetic tests (7 platform-gated skips) in `research/poc_ipc_001/`.

**What it does not prove:** OS-level confinement. `OS_SANDBOX` remains `NO VERIFICADO`; worker
code is trusted code running with host privileges (ADR-002 D16). This is an intentionally
**migrated** index entry: the subprocess IPC work was carried under a distinct `POC-IPC`
identifier rather than as canonical POC-003, and is recorded here so the index is complete.

## POC-MUTAGEN-001 — Mutagen read-only inspector

**Status:** `BLOQUEADO` by [ADR-003](../adr/ADR-003-mutagen-runtime-and-license-boundary.md)
(PROPOSED) license/runtime decision.

**Hypothesis:** Mutagen can read a plugin header and inventory records headlessly, with no game
install and no Creation Kit.

**Method (not started):** isolated .NET worker under a launch profile that ADR-002 does not yet
define, read-only, workspace-contained, hash-pinned.

**Blocked by:** the ADR-003 runtime/license decision (GPL-3.0-only; execute vs link vs
distribute). No C#/.NET/NuGet dependency exists in this repository and none may be added while
this entry is `BLOQUEADO`.

## EXP-CK-CLI — enumerate actual Creation Kit flags

**Status:** `NO VERIFICADO`

Do not invent command-line switches in product code. Verify behavior on a legal local CK installation.

## EXP-ESPER-LICENSE — confirm C# esper license

**Status:** `NO VERIFICADO` + `LEGAL_REVIEW_REQUIRED`

Read the canonical repository LICENSE directly and record the SPDX identifier before using esper as an architectural dependency.

## EXP-CKPE-QIFACE — inspect CKPE PluginAPI interfaces

**Status:** `HIPOTESIS`

Pin a CKPE commit and inventory every interface after legal review. Do not implement an in-process bridge while the legal overlay remains unresolved.

## Identifier rule

Subprocess IPC hardening is **not** canonical POC-003. Use `ADR-002` or a distinct `POC-IPC` identifier unless the research index is intentionally migrated.
