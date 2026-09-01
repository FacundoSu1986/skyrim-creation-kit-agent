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

Verify that the official compiler is invoked with explicit arguments, no shell, bounded timeout, captured stdout/stderr and output PEX verification. The compiler binary was not present in the research environment.

**Not started.** Acceptance criteria are pre-registered (2026-09-01) in the [POC-003 pre-registration](2026-09-01-poc-003-pre-registration.md), under the `PAPYRUS_COMPILE_DRYRUN_V1` profile defined by [ADR-004](../adr/ADR-004-external-tool-execution-contract.md) (PROPOSED). POC-003 does not use the ADR-002 IPC protocol: the compiler cannot speak it. See the identifier rule below.

## POC-004 — xEdit allowlisted `-script -autoexit`

**Status:** `NO VERIFICADO`

Use a user-installed xEdit copy, an allowlisted/hash-pinned reporting script and an explicit completion marker. Missing marker is failure. Originals remain untouched.

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
