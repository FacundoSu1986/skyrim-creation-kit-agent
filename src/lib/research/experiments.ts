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
      "Header fields round-trip. Hash logged. No game files touched. Achieved: python -m compileall PASS; python -m unittest test_suite.py → Ran 43 tests / OK; evidence E2_REOPENED_ASSERTIONS_PASS on the synthetic fixture scope.",
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
      "If the user machine has CK: invoke PapyrusCompiler.exe with argument arrays, timeout, no shell. Compile a workspace-authored script that does not include leaked Bethesda sources beyond the user's local -i path.",
    successCriteria:
      "Exit codes documented. stdout/stderr captured. Output PEX hash differs from any pre-existing file. Timeout kills the process.",
    status: "NO VERIFICADO",
    blockedBy: "Compiler binary not present here.",
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
