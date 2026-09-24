export const experimentRows = [
  {
    code: "POC-001",
    title: "Read-only Creation Kit process and control inspect",
    hypothesis:
      "A running SSE Creation Kit 1.6.x process exposes at least one useful UIA or MSAA control (window title, menu, Data dialog list) that can be read without coordinates and without saving.",
    method:
      "On a dedicated Windows machine with a legal CK install: launch CK, attach Inspect.exe / Accessibility Insights and optionally FlaUI/pywinauto, enumerate the main window, record control tree depth, AutomationIds, and whether Object Window / Data dialog children are accessible. Close without saving. Repeat 20 times first, 100 if stable.",
    successCriteria:
      "Structured JSON report. Zero file writes under Data. Zero coordinate clicks. No crash attributable to the inspector. Reproducible window identity (process name + title + PID).",
    status: "BLOQUEADO",
    blockedBy:
      "This sandbox is Linux and has no CreationKit.exe. Experiment is designed, not executed.",
  },
  {
    code: "POC-002",
    title: "Synthetic TES4 header/parser safety pipeline",
    hypothesis:
      "A synthetic ESP that contains only a TES4 header (no Bethesda records copied) can be parsed for masters, flags, and header version without CK.",
    method:
      "Executed against a synthetic TES4 fixture only (HEDR 1.70, FormVersion 44). Strict binary parser; INSPECT_HEADER as the only routed operation with fail-closed capability routing; candidate-only workspace with path containment and immutable originals guarded by SHA-256 invariants; immutable/no-overwrite receipts; empty ModPlan rejected; evidence level E2 reached only after reopen/assertions. No game files touched. Creation Kit, xEdit, PapyrusCompiler, and Mutagen were not executed.",
    successCriteria:
      "Header fields round-trip. Hash logged. No game files touched. Achieved: python -m compileall PASS; python -m unittest test_suite.py → Ran 44 tests / OK (initial validated baseline: 43); evidence E2_REOPENED_ASSERTIONS_PASS on the synthetic fixture scope.",
    status: "PASS",
    blockedBy:
      "Validated baseline reached (research/poc_002/). Does not prove real ESP/ESM/ESL compatibility, header 1.71, complex records, quests, VMAD, FaceGen, navmesh, or any runtime behavior.",
  },
  {
    code: "POC-003",
    title: "PapyrusCompiler dry-invoke contract",
    hypothesis:
      "The official compiler returns a nonzero exit code on invalid input and a zero exit code on a tiny script that only exists in the workspace, when -i/-o/-f are explicit.",
    method:
      "Executed on a Windows host with a local, hash-pinned PapyrusCompiler.exe under the ADR-004 profile PAPYRUS_COMPILE_DRYRUN_V1: explicit argv, no shell, bounded 64 KiB streams, monotonic deadline, Job Object confinement, pre/post workspace snapshots. Five pre-registered runs (success x2, compile error, long, forced timeout) evaluated against 15 mandatory criteria. Fixtures are own-authored .psc files; no Bethesda source or compiler binary is committed.",
    successCriteria:
      "15/15 mandatory criteria. Measured: 13 PASS / 2 FAIL. Criterion 12 failed (UNEXPECTED_OUTPUT_PRESENT — an interrupted run leaves candidates/<token>.pas); criterion 14 failed (DETERMINISM_MISMATCH — repeated compiles of byte-identical input produced byte-different .pex). The long run exited 0 and produced nothing and was correctly rejected as EXPECTED_OUTPUT_MISSING.",
    status: "NO VERIFICADO",
    blockedBy:
      "Executed twice (2026-09-06, re-executed 2026-09-11) and NOT passed: two mandatory criteria failed. Not a missing-environment blocker. Determinism is unrecoverable with this compiler as invoked (PEX header timestamp plus unstable string-table ordering); the compiler also writes its host account and machine name into the .pex string table. Research harness exists in research/poc_003/ (105 hermetic tests, Windows-gated); no production adapter exists.",
  },
  {
    code: "POC-004",
    title: "xEdit allowlisted -script -autoexit",
    hypothesis:
      "SSEEdit can load a candidate plugin, run a hashed allowlisted script that only reports errors, write a completion marker, and exit.",
    method:
      "User-installed xEdit. Command line -SSE -quickedit:candidate.esp -autoload -script:ForgeCheck.pas -autoexit. Require a completion marker file. Treat missing marker as failure.",
    successCriteria:
      "Marker present. Nonzero without marker. No write to originals.",
    status: "NO VERIFICADO",
    blockedBy: "Windows + xEdit not available here.",
  },
  {
    code: "POC-IPC-001",
    title: "Isolated worker IPC protocol and transactional boundaries",
    hypothesis:
      "A trusted orchestrator can drive an out-of-process worker over a bounded JSON stdio protocol with full pre-spawn validation, a single monotonic deadline, capped streams, fail-closed cleanup, and a receipt that reports a verdict computed by the trusted side.",
    method:
      "Implemented under ADR-002. One trusted read-only operation (INSPECT_SYNTHETIC_INPUT) against a synthetic fixture. Bounded stdin writer plus stdout/stderr pumps (never communicate()), platform-honest cleanup (POSIX process group, Windows direct child), closed error taxonomy, no-overwrite receipts, path containment, and adversarial helper workers that hang, spam, close stdin, emit malformed JSON, mis-correlate or spawn descendants.",
    successCriteria:
      "181 hermetic tests (7 platform-gated skips), including failure injection: every defect must produce a deterministic taxonomy code and no false PASS. Achieved. It demonstrates the protocol and process-isolation contract only — NOT OS-level sandboxing (OS_SANDBOX: NO VERIFICADO).",
    status: "PASS",
    blockedBy:
      "Validated research baseline (research/poc_ipc_001/). Not a production authoring backend and not a sandbox.",
  },
  {
    code: "POC-MUTAGEN-001",
    title: "Mutagen read-only plugin inspector in an isolated .NET worker",
    hypothesis:
      "Mutagen can read a Skyrim plugin header and record inventory headlessly, without a game install and without Creation Kit.",
    method:
      "Not started by decision: it requires an accepted runtime and license boundary (ADR-003, PROPOSED) and a .NET worker launch profile that ADR-002 does not yet define.",
    successCriteria:
      "Would require a read-only, hash-pinned, workspace-contained .NET worker plus the ADR-003 license decision (GPL-3.0-only; execute vs link vs distribute).",
    status: "BLOQUEADO",
    blockedBy:
      "ADR-003 license/runtime decision (PROPOSED, LEGAL_REVIEW_REQUIRED). Mutagen is not vendored and no C#/.NET/NuGet dependency exists in this repository.",
  },
  {
    code: "EXP-CK-CLI",
    title: "Enumerate SSE CreationKit.exe command-line flags",
    hypothesis:
      "SSE CK may accept undocumented flags similar to FO4 -GeneratePrecombined. Unknown.",
    method:
      "On the user's CK: CreationKit.exe /? and CreationKit.exe -help, plus community string extraction. Do not guess flags in product code.",
    successCriteria:
      "A table of flags that actually change process behavior, each marked VERIFICADO by execution.",
    status: "NO VERIFICADO",
    blockedBy: "No CK binary in this environment. Do not invent flags.",
  },
  {
    code: "EXP-ESPER-LICENSE",
    title: "Confirm C# esper LICENSE file",
    hypothesis:
      "matortheeternal/esper is MIT like esper-js and esper-cpp.",
    method:
      "Fetch raw LICENSE from https://github.com/matortheeternal/esper. Record SPDX. Only then consider it as a Mutagen alternative.",
    successCriteria:
      "SPDX identifier recorded. If missing, esper stays LEGAL_REVIEW_REQUIRED.",
    status: "NO VERIFICADO",
    blockedBy:
      "README fetch did not include a license badge. Needs a direct LICENSE read.",
  },
  {
    code: "EXP-CKPE-QIFACE",
    title: "Re-read CKPE PluginAPI headers for any unpublished interfaces",
    hypothesis:
      "QueryInterface may have gained interfaces after the wiki sentence was written.",
    method:
      "Read CKPE.PluginAPI.PluginAPI.h and TestPlugin on a pinned commit. List every interface ID. Do not implement a plugin until LEGAL_REVIEW_REQUIRED is resolved.",
    successCriteria:
      "Interface inventory with commit hash. If still empty, keep CKPE as host-only.",
    status: "HIPOTESIS",
    blockedBy: "Legal overlay + no need before Gate 1 ADR.",
  },
];
