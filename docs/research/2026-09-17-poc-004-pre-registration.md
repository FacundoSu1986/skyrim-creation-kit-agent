# POC-004 pre-registration — xEdit allowlisted validator

- **Status:** `NO VERIFICADO` — criteria pre-registered 2026-09-17. **Experiment designed, pre-registered, and criteria frozen; NOT yet implemented or executed.**
- **Profile:** `XEDIT_VALIDATE_PLUGIN_V1`, defined under [ADR-004](../adr/ADR-004-external-tool-execution-contract.md) (ACCEPTED, ETEC contract class).
- **Contract class:** External Tool Execution Contract (ETEC).
- **Authorised by:** Pending owner decision. This document defines the design and freezes acceptance criteria; it does not implement the runtime harness and does not execute xEdit.

---

## Canonical Principle (ADR-001 / ADR-004)

> **AI decides WHAT. Deterministic software decides HOW. Validators decide WHETHER IT WORKED. Human decides WHETHER TO ACCEPT.**

Under ETEC, this principle is enforced with absolute strictness:
1. The external tool (xEdit) is not a cooperative worker and cannot participate in a bidirectional protocol.
2. The external tool **never decides whether it succeeded**.
3. Its exit code, console output, and generated files are **untrusted candidate evidence** until verified trusted-side by the orchestrator against independently recheckable invariants.

---

## 1. Why this document exists

An acceptance criterion decided after observing experimental results is an ex-post rationalisation, not a scientific or security gate.

POC-004 introduces an external, interactive, third-party Win32 GUI binary (`xEdit.exe` / `SSEEdit.exe`) into an automated validation pipeline. Because xEdit is complex, has interactive GUI origins, depends on ambient system state, and was not designed as an isolated headless daemon, the risk of "making it work" by quietly relaxing containment, tolerating ambient pollution, or trusting ambiguous exit codes is severe.

This document pre-registers and freezes every acceptance criterion, the exact argv grammar, the trust boundary, the machine-readable output schema, the negative test cases, and the error taxonomy **before** any harness code is written or xEdit is executed.

If empirical execution later contradicts an expectation:
> **The experiment FAILS. The criteria DO NOT MOVE.**

---

## 2. Architectural Context: ETEC vs WIPC

POC-004 belongs exclusively to the **External Tool Execution Contract (ETEC)** established in [ADR-004](../adr/ADR-004-external-tool-execution-contract.md).

xEdit is **not** a worker under [ADR-002](../adr/ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) (WIPC):
- **No wire transport:** No request object on stdin, no response envelope on stdout.
- **No worker-emitted receipt:** xEdit cannot emit a WIPC Receipt or assert its own invariants.
- **No runtime protocol handshake:** `protocol_version` does not apply.
- **Orchestrator-synthesised evidence:** The trusted orchestrator constructs argv, isolates workspace paths, bounds process execution, captures streams, measures process trees, recomputes file hashes, and validates report schemas.

```text
Orchestrator (Trusted)
  │
  ├─ [Pre-spawn verification]
  │    ├── Executable hash == pinned hash
  │    ├── Static script hash == pinned hash
  │    ├── Expected report path absent (PRE_EXISTING_OUTPUT_PRESENT)
  │    └── Input fixture SHA-256 recorded
  │
  ├─ [Spawn with OS Confinement]
  │    ├── Windows Job Object (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
  │    ├── shell = False
  │    ├── Deny-by-default environment (TEMP/TMP redirected)
  │    └── Closed argv: [exe, -sse, -autoload, -autoexit, -D:..., -P:..., -T:..., -script:...]
  │
  ▼
External Tool (Untrusted xEdit execution)
  │
  ├── Reads: input fixture in isolated workspace data dir
  ├── Runs: pinned static Pascal script
  └── Writes: reports/validation_report.json + logs
  │
  ▼
Orchestrator (Trusted Validation & Evidence Synthesis)
  │
  ├── Enforce execution deadline & verify zero surviving descendants
  ├── Verify input fixture SHA-256 unchanged (INPUT_HASH_MISMATCH)
  ├── Verify no undeclared files in workspace (UNEXPECTED_OUTPUT_PRESENT)
  ├── Verify report exists, non-empty, and fresh (EXPECTED_OUTPUT_MISSING)
  ├── Validate report against strict closed JSON Schema (POLICY_VIOLATION)
  ├── Correlate job_id, plugin_sha256, script_sha256 (POLICY_VIOLATION)
  └── Verify explicit completion marker (XEDIT_VALIDATION_COMPLETE_V1)
```

---

## 3. Objective of POC-004

To demonstrate or refute whether a user-installed copy of xEdit can be invoked as an independent, read-only, deterministic, fail-closed validator for Skyrim plugins, governed by a closed ETEC profile, without modifying original files, without escaping the workspace, and without permitting arbitrary LLM-generated code execution at runtime.

---

## 4. Profile Specification: `XEDIT_VALIDATE_PLUGIN_V1`

The canonical profile identifier is **`XEDIT_VALIDATE_PLUGIN_V1`**.

| Dimension | Specification |
|---|---|
| **Contract class** | ETEC ([ADR-004](../adr/ADR-004-external-tool-execution-contract.md)) |
| **Executable sourcing** | Absolute path from external trusted configuration; never resolved via `PATH` |
| **Executable integrity** | SHA-256 pinned in trusted configuration; pre-spawn mismatch fails closed (`EXECUTABLE_HASH_MISMATCH`) |
| **Executable metadata** | Informational only (read from PE headers: `FileVersion`, `ProductVersion`, `CompanyName`, `FileDescription`); never a trust gate |
| **Validation script** | Pre-written, static, allowlisted, version-controlled, and hash-pinned; runtime LLM generation strictly prohibited |
| **Script location** | Allowlisted static script path mapped into workspace `scripts/`; never arbitrary user path |
| **Input fixture** | Own-authored synthetic `.esp` located in workspace `input/`; safe-name token grammar per ADR-002 |
| **Candidate output** | Read-only validation profile; no candidate plugin modifications permitted; `candidates/` remains empty |
| **Report output** | Exactly one machine-readable report resolved trusted-side: `reports/validation_report.json` |
| **argv grammar** | Fully determined trusted-side; closed token list; no raw caller strings reach argv |
| **`cwd`** | Derived trusted-side to workspace root; never from request or caller data |
| **Environment** | Deny-by-default allowlist; `TEMP` and `TMP` redirected strictly to workspace `temp/` |
| **Shell** | `shell=False` strictly; no `cmd.exe` or `powershell.exe` in process tree |
| **Deadline** | Monotonic execution deadline (60.0 s default; configurable per fixture) plus bounded cleanup grace (5.0 s) |
| **stdout / stderr** | Capped transfer-time readers (65 536 bytes per stream); persisted under `logs/` as untrusted evidence |
| **OS Confinement** | Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; `CREATE_SUSPENDED` assignment before resume |

---

## 5. Upstream CLI Research & Fact Classification

To prevent inventing command-line flags or making unsupported architectural assumptions, upstream sources (official repository `TES5Edit/TES5Edit`, official documentation *The Tome of xEdit*, and community Delphi automation sources) were analyzed.

Findings are strictly classified into:
- **DOCUMENTED**: Directly confirmed in official upstream documentation or repository documentation.
- **OBSERVED**: Empirically measured in this repository's environment.
- **INFERRED**: Deduced from architecture or Delphi runtime semantics, but not yet empirically proven.
- **NO VERIFICADO**: Critical behavioral details that cannot be verified without running xEdit.

### 5.1 Documented Upstream Flags

1. `-script:"<ScriptName>"` (or `-script:"<ScriptName.pas>"`):
   - Executes the specified Pascal script automatically after plugins load.
   - Upstream documentation specifies that scripts reside in the `Edit Scripts\` directory of the xEdit installation.
2. `-autoexit`:
   - Closes xEdit automatically once automated tasks (script, Quick Auto Clean, LODGen) complete.
3. `-autoload`:
   - Skips the manual module selection dialog and automatically loads plugins active in `plugins.txt` or the default load order.
4. `-D:"<path>\"`:
   - Overrides the Data directory. Upstream documentation notes all path switches require a trailing backslash.
5. `-I:"<path><filename>"`:
   - Overrides the game main INI file path.
6. `-P:"<path><filename>"`:
   - Overrides the `plugins.txt` file path.
7. `-T:"<path>\"`:
   - Overrides the temporary working directory.
8. `-C:"<path>\"`:
   - Overrides the cache directory.
9. `-B:"<path>\"`:
   - Overrides the backups directory.
10. `-R:"<path><filename>"`:
    - Overrides the log file path.
11. Game mode flags (`-sse`, `-tes5`, `-fo4`):
    - Forces the specific game mode regardless of the executable filename.

### 5.2 Observed Facts

- **None** for xEdit in this repository: xEdit has never been executed in this repository or in CI. All runtime claims for xEdit remain unobserved.

### 5.3 Inferred Facts

- That `-D:"<workspace>\data\"` together with `-P:"<workspace>\data\plugins.txt"` isolates plugin loading from the user's live Skyrim installation.
- That xEdit exits with code `0` when `-autoexit` completes normally after script execution.
- That Pascal scripts in xEdit can serialize structured JSON via standard `TStringList.SaveToFile` or file I/O routines.

### 5.4 NO VERIFICADO (Frozen Unknowns)

The following items are **explicitly unverified** and must not be assumed to pass:

1. **Masterless Synthetic Plugin Support:**
   - Does xEdit 4.x allow opening a minimal synthetic `.esp` (containing only a TES4 header) without `Skyrim.esm` or official masters present in `-D:`? Or does it abort / popup an error dialog demanding official masters?
   - *Status:* `NO VERIFICADO`.
2. **GUI & Dialog Suppression:**
   - xEdit is a Delphi VCL GUI application. When launched with `-autoload -script:... -autoexit`, does it run completely silently, or does it instantiate a visible window / taskbar icon?
   - Crucially: do non-fatal warnings, missing string tables, or syntax errors open modal popups (e.g. `ShowMessage`, `MessageDlg`) that block the main thread and prevent `-autoexit` until deadline timeout?
   - *Status:* `NO VERIFICADO`.
3. **Script Sourcing & Redirection (`-S:` vs `Edit Scripts\`):**
   - Does xEdit support an undocumented switch `-S:<path>\` to redirect the scripts directory to `workspace/scripts/`, or does `-script:` strictly require the script to reside physically within `<xEdit_Install_Dir>\Edit Scripts\`?
   - If physically required inside the installation, running the tool without mutating the user's installation directory is an open problem that must be measured.
   - *Status:* `NO VERIFICADO`.
4. **Exit Codes on Failure:**
   - What exit code does xEdit return when a script encounters an unhandled exception or calls `Exit`? Does it return a non-zero code, or does it exit 0 regardless?
   - *Status:* `NO VERIFICADO`.
5. **`-P:` Argument Robustness:**
   - Does xEdit strictly honor `-P:<path><filename>` across all 4.x versions, or does it attempt to fall back to `%LOCALAPPDATA%\Skyrim Special Edition\plugins.txt`?
   - *Status:* `NO VERIFICADO`.
6. **Registry Probing & Ambient Host Leakage:**
   - Does xEdit query the Windows Registry (`HKLM\Software\Bethesda Softworks\Skyrim Special Edition` or Steam keys) even when `-D:` and `-I:` are specified on the command line?
   - *Status:* `NO VERIFICADO`.
7. **Process Tree & Descendants on Windows:**
   - Does xEdit spawn child helper processes or background worker threads that survive main window closure?
   - *Status:* `NO VERIFICADO`.

---

## 6. Executable Trust Model

1. **User-Installed External Dependency:**
   - `xEdit.exe` / `SSEEdit.exe` is never vendored, downloaded, or bundled into the repository.
   - Licensed upstream under MPL-2.0. The repository operates purely as an external caller.
2. **Absolute Path from Trusted Configuration:**
   - The executable path must be configured explicitly in an external trusted configuration file outside the repository (e.g. `poc004.local.json`).
   - Sourcing via `PATH` lookup is strictly prohibited.
3. **Cryptographic Hash Pinning:**
   - The trusted configuration must specify `executable_sha256`.
   - Pre-spawn check:
     ```text
     actual_sha256 = sha256(executable_path)
     if actual_sha256 != pinned_sha256:
         fail closed with EXECUTABLE_HASH_MISMATCH (no process spawned)
     ```
4. **Informational Metadata:**
   - PE version headers (`FileVersion`, `ProductVersion`, `CompanyName`, `FileDescription`) are recorded in the evidence record for debugging and traceability, but are **never** used to authorize execution.

---

## 7. Script Trust Model

1. **Pre-written, Static, and Allowlisted:**
   - The validation script (e.g. `ValidatePluginV1.pas`) must be written, reviewed, committed to version control, and hash-pinned in the profile definition before execution.
2. **Runtime Code Generation Prohibited:**
   - **Under NO circumstances may an LLM generate, mutate, or inject Pascal code at runtime.**
   - Dynamic script assembly, template expansion with untrusted tokens, and arbitrary user-supplied script paths are strictly forbidden.
   - *Development vs. Runtime distinction:* An LLM may assist human developers in authoring the static `.pas` script during offline development, but once authored, the script is static, audited, and immutable at the runtime boundary.
3. **Cryptographic Script Hash Pinning:**
   - Pre-spawn check:
     ```text
     actual_script_sha256 = sha256(script_path)
     if actual_script_sha256 != pinned_script_sha256:
         fail closed with POLICY_VIOLATION (no process spawned)
     ```

---

## 8. Controlled Input Fixture

1. **Synthetic and Own-Authored:**
   - Fixtures used by POC-004 must be minimal, synthetic, and created specifically for testing (e.g. extending the synthetic TES4 header fixture proven in POC-002).
2. **Zero Proprietary Material:**
   - Absolutely NO Bethesda-copyrighted records, official plugins (`Skyrim.esm`, `Update.esm`, `Dawnguard.esm`), third-party mod files, or live user Data folders may be used or committed.
3. **Masterless Plugin Unknown:**
   - The fixture will be a standalone synthetic `.esp` without masters.
   - Whether xEdit permits loading a masterless plugin in headless mode without crashing is a primary hypothesis to be tested by POC-004. It is recorded as `NO VERIFICADO`.

---

## 9. Original Input Immutability

1. **Pre-spawn baseline:**
   - Orchestrator records `input_sha256_before`, file size, and modification timestamp of the input fixture.
2. **Post-spawn assertion:**
   - Orchestrator recomputes `input_sha256_after` immediately following process termination and cleanup.
3. **Pass rule:**
   ```text
   input_sha256_before == input_sha256_after
   ```
   If the hash changes: fail closed with `INPUT_HASH_MISMATCH`.
4. Secondary invariant: file size and mtime must remain unmodified.

---

## 10. Workspace Contract

Every invocation runs inside an ephemeral, dedicated workspace directory created trusted-side:

```text
<workspace_root>/
  ├── input/          # Read-only input fixture (.esp)
  ├── data/           # Staged data folder for xEdit (-D:), contains input fixture & plugins.txt
  ├── scripts/        # Staged allowlisted static script (.pas)
  ├── reports/        # Target directory for validation_report.json
  ├── logs/           # Captured stdout.log, stderr.log, xEdit logs
  └── temp/           # Redirected TEMP / TMP directory (-T:)
```

1. **Prohibited Paths:**
   - xEdit must never be pointed to, read from, or write to:
     - The live Skyrim installation directory.
     - `%USERPROFILE%\AppData\Local\Skyrim Special Edition\` (except if unavoidable by binary design, which must fail or be recorded as an architectural limitation).
     - The xEdit installation directory (except read-only binary execution).
     - Arbitrary user directories.
2. **Workspace Snapshotting:**
   - **Pre-spawn:** Recursive snapshot of all regular files in `<workspace_root>`.
   - **Post-spawn:** Recursive snapshot of all regular files in `<workspace_root>`.
   - The only allowed new files are:
     - `reports/validation_report.json`
     - `logs/stdout.log`
     - `logs/stderr.log`
     - Optionally declared temporary logs inside `logs/` or `temp/`.
   - Any other file appearing in `input/`, `data/`, or root fails closed with `UNEXPECTED_OUTPUT_PRESENT`.
3. **External Writes:**
   - If xEdit writes outside `<workspace_root>` (e.g. creating logs, ini files, or backups in its own folder or `%LOCALAPPDATA%`), this is recorded as an experimental risk / violation and cannot be hidden.

---

## 11. Output Contract: Strict Machine-Readable Report

The xEdit Pascal script must emit exactly one machine-readable JSON report: `reports/validation_report.json`.

Free-form text reports, console log regex parsing, and substrings such as `"Validation Completed Successfully"` are **prohibited** as success criteria.

### 11.1 JSON Schema: `XEDIT_VALIDATE_PLUGIN_V1`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "XEditValidationReportV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "job_id",
    "plugin_name",
    "plugin_sha256",
    "script_sha256",
    "validator_status",
    "completion_marker",
    "records_inspected",
    "errors_detected",
    "warnings_detected",
    "diagnostics"
  ],
  "properties": {
    "schema_version": {
      "type": "integer",
      "const": 1
    },
    "job_id": {
      "type": "string",
      "minLength": 1,
      "maxLength": 128
    },
    "plugin_name": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9_-]+\\.(esp|esm|esl)$"
    },
    "plugin_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "script_sha256": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "validator_status": {
      "type": "string",
      "enum": ["VALID", "INVALID", "ERROR"]
    },
    "completion_marker": {
      "type": "string",
      "const": "XEDIT_VALIDATION_COMPLETE_V1"
    },
    "records_inspected": {
      "type": "integer",
      "minimum": 0
    },
    "errors_detected": {
      "type": "integer",
      "minimum": 0
    },
    "warnings_detected": {
      "type": "integer",
      "minimum": 0
    },
    "diagnostics": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": false,
        "required": ["code", "severity", "message"],
        "properties": {
          "code": {
            "type": "string",
            "minLength": 1,
            "maxLength": 64
          },
          "severity": {
            "type": "string",
            "enum": ["ERROR", "WARNING", "INFO"]
          },
          "record_formid": {
            "type": "string",
            "pattern": "^[0-9A-Fa-f]{8}$"
          },
          "record_signature": {
            "type": "string",
            "pattern": "^[A-Z0-9_]{4}$"
          },
          "message": {
            "type": "string",
            "maxLength": 1024
          }
        }
      }
    }
  }
}
```

---

## 12. Completion Evidence & Independent Correlation

An external process exiting with code `0` is **not evidence that the script ran or completed**. xEdit may exit 0 on empty tasks, aborts, or early GUI closes.

To prove completion and prevent spoofing or stale reuse, the orchestrator enforces:
1. **Explicit Completion Marker:**
   - The report must contain `completion_marker: "XEDIT_VALIDATION_COMPLETE_V1"`.
   - Written only by the script's `Finalize` block after all records are traversed.
   - Missing or altered marker fails closed with `EXPECTED_OUTPUT_MISSING` or `POLICY_VIOLATION`.
2. **Cryptographic and Job Correlation:**
   - The orchestrator independently verifies:
     - `report["job_id"] == orchestrator.current_job_id`
     - `report["plugin_sha256"] == orchestrator.input_sha256_before`
     - `report["script_sha256"] == orchestrator.pinned_script_sha256`
   - Any mismatch indicates stale report reuse, directory collision, or script tampering, failing closed with `POLICY_VIOLATION`.

---

## 13. Closed argv Grammar

No caller-provided string reaches argv. The argv list is constructed strictly trusted-side:

```text
[
  <TRUSTED_XEDIT_EXE_PATH>,
  "-sse",
  "-autoload",
  "-autoexit",
  "-D:<RESOLVED_WORKSPACE_DATA_DIR>\",
  "-I:<RESOLVED_WORKSPACE_INI_PATH>",
  "-P:<RESOLVED_WORKSPACE_PLUGINS_TXT_PATH>",
  "-T:<RESOLVED_WORKSPACE_TEMP_DIR>\",
  "-B:<RESOLVED_WORKSPACE_BACKUPS_DIR>\",
  "-C:<RESOLVED_WORKSPACE_CACHE_DIR>\",
  "-script:<RESOLVED_SCRIPT_TOKEN>"
]
```

- Every token is validated against safe-name grammar (`^[a-zA-Z0-9_.-]+$`).
- All path parameters are resolved to absolute paths strictly within `<workspace_root>`.
- `shell=False` is strictly enforced.
- Command-line chaining (`&`, `|`, `;`, `>`, `<`), cmd.exe wrappers, and PowerShell invocations are prohibited.

---

## 14. Process Model & Confinement

1. **OS-Level Confinement on Windows:**
   - Invocations must use a Windows Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
   - The process is spawned with `CREATE_SUSPENDED`, immediately assigned to the Job Object, and then resumed.
   - Closing the job handle or encountering a timeout forcefully terminates the entire process tree at the kernel level.
2. **Process Tree Sampling:**
   - Toolhelp32 process-tree enumeration samples direct children and descendants during execution.
   - Post-cleanup assertion: zero descendants associated with the process outlive cleanup.
   - If any descendant survives: fail closed with `DESCENDANT_PROCESS_SURVIVED`.
3. **Monotonic Execution Deadline:**
   - Execution is bounded by a strict timeout (e.g. 60.0 s).
   - If the deadline expires: termination triggered, failing with `PROCESS_TIMEOUT`.
4. **Stream Readers:**
   - stdout and stderr are captured with hard transfer caps (64 KiB) to prevent memory exhaustion from runaway logging. Exceeding caps triggers `OUTPUT_LIMIT_EXCEEDED`.

---

## 15. Ambient Host State Analysis

Because xEdit was built for interactive mod management, it may probe ambient host locations. The following matrix audits every known ambient touchpoint:

| Host Resource | Classification | Mitigation Strategy | Pre-registration Risk Status |
|---|---|---|---|
| **Windows Registry** (`HKLM\Software\Bethesda Softworks\Skyrim Special Edition`) | `AVOIDABLE` via `-D:` | Provide explicit `-D:` pointing to workspace data folder. | `NO VERIFICADO` — must test if xEdit still queries registry if game path is specified. |
| **Active Load Order** (`%LOCALAPPDATA%\Skyrim Special Edition\plugins.txt`) | `AVOIDABLE` via `-P:` | Provide isolated `plugins.txt` via `-P:` containing only fixture. | `NO VERIFICADO` — verify xEdit does not read default AppData path. |
| **Game INI Files** (`%USERPROFILE%\Documents\My Games\Skyrim Special Edition\`) | `AVOIDABLE` via `-I:` | Provide dummy minimal INI in workspace via `-I:`. | `NO VERIFICADO` — verify xEdit does not probe Documents. |
| **Temporary Files** (`%TEMP%`, `%TMP%`) | `AVOIDABLE` via `-T:` + env | Set `-T:` to workspace `temp/` and override `TEMP`/`TMP` in process environment. | `NO VERIFICADO` — verify no files leak to system temp. |
| **xEdit Installation Directory** (`Edit Scripts\`, `xEdit_log.txt`) | `POTENTIALLY REQUIRED` | Script may need staging in `Edit Scripts\` if `-S:` is unsupported. | `NO VERIFICADO` — high architectural risk; writing into install dir violates read-only isolation. |
| **Interactive Desktop Session (GDI/User32)** | `REQUIRED` | xEdit is a Delphi VCL application requiring a Win32 GUI subsystem. Cannot run in headless Linux containers or Windows Server Core without desktop session. | Confirmed limitation of xEdit; documented as architectural constraint. |

---

## 16. Negative Test Matrix (Pre-registered Fixtures)

The subsequent experiment must execute and verify the following 10 negative/edge fixtures:

| Case | Condition | Injected Fault | Expected Outcome Code | Required Evidence |
|---|---|---|---|---|
| **A** | Baseline Positive | Valid minimal synthetic TES4 `.esp` | `SUCCESS` | Report exists, valid schema, `validator_status: "VALID"`, marker present, hashes match |
| **B** | Malformed Plugin | Truncated file or corrupted header | `PROCESS_FAILED` or `POLICY_VIOLATION` | xEdit exits non-zero or report records `validator_status: "INVALID"` |
| **C** | Wrong Script Hash | Tampered or modified Pascal script | `POLICY_VIOLATION` | Pre-spawn check fails; zero processes spawned |
| **D** | Wrong Executable Hash | Tampered xEdit binary or incorrect pin | `EXECUTABLE_HASH_MISMATCH` | Pre-spawn check fails; zero processes spawned |
| **E** | Pre-existing Report | Stale `validation_report.json` placed before spawn | `PRE_EXISTING_OUTPUT_PRESENT` | Pre-spawn check fails; zero processes spawned |
| **F** | Forced Timeout | Execution deadline set to 0.1 s | `PROCESS_TIMEOUT` | Process tree terminated; `descendants_alive == []` |
| **G** | Unexpected Output | Extra undeclared file generated in workspace | `UNEXPECTED_OUTPUT_PRESENT` | Snapshot diff catches extraneous file; run rejected |
| **H** | Input Mutation | Script or tool modifies input `.esp` bytes | `INPUT_HASH_MISMATCH` | Post-spawn hash differs from pre-spawn; run rejected |
| **I** | Missing Completion Marker | Report written without completion marker | `EXPECTED_OUTPUT_MISSING` / `POLICY_VIOLATION` | Validator rejects report; run rejected |
| **J** | Corrupted Correlation | Report with mismatched `job_id` or plugin hash | `POLICY_VIOLATION` | Orchestrator correlation gate rejects report |

---

## 17. Error Taxonomy Partition

POC-004 adopts the ADR-004 ETEC partitioned error taxonomy:

### 17.1 Inherited from ADR-002 (Applicable under ETEC)
- `PROCESS_TIMEOUT`: Execution exceeded deadline budget.
- `PROCESS_FAILED`: Non-zero process exit code.
- `OUTPUT_LIMIT_EXCEEDED`: stdout or stderr breached stream transfer caps.
- `WORKSPACE_VIOLATION`: Path traversal or resolution outside `<workspace_root>`.
- `POLICY_VIOLATION`: Profile rule breach, schema mismatch, or correlation failure.
- `INTERNAL_ERROR`: Harness defect or OS error (e.g. Job Object assignment failure).

### 17.2 ETEC-Specific Codes (ADR-004)
- `PRE_EXISTING_OUTPUT_PRESENT`: Report already existed before spawn.
- `EXPECTED_OUTPUT_MISSING`: Exit code zero but report absent, empty, or lacking completion marker.
- `OUTPUT_HASH_MISMATCH`: Recorded report hash does not match independent recomputation.
- `INPUT_HASH_MISMATCH`: Input fixture hash altered across the run.
- `UNEXPECTED_OUTPUT_PRESENT`: Undeclared files detected in the workspace snapshot.
- `TOOL_DIAGNOSTICS_REJECTED`: Reserved if tool diagnostics violate acceptability rules.
- `DETERMINISM_MISMATCH`: Two runs on identical input produce divergent reports.
- `EXECUTABLE_HASH_MISMATCH`: Executable hash differs from pinned trusted configuration.
- `DESCENDANT_PROCESS_SURVIVED`: Process tree cleanup failed; descendants outlived job close.

### 17.3 Explicitly Excluded Codes (WIPC Transport-Bound)
The following 9 ADR-002 codes are structurally unreachable under ETEC and must **never** be declared:
- `INVALID_REQUEST`, `REQUEST_LIMIT_EXCEEDED`, `UNSUPPORTED_PROTOCOL_VERSION`, `INVALID_JOB_ID`, `INVALID_OPERATION`, `PIPE_WRITE_FAILED`, `INVALID_RESPONSE`, `RECEIPT_MISMATCH`, `ASSERTION_FAILED`.

---

## 18. Frozen Success Conjunction

POC-004 declares success if and only if **all** terms of the following boolean conjunction evaluate to true:

```text
SUCCESS =
    executable_hash_verified
    AND script_hash_verified
    AND argv_is_closed
    AND shell_is_false
    AND pre_existing_output_absent
    AND input_hash_unchanged
    AND process_exit_zero
    AND report_exists
    AND report_nonempty
    AND report_fresh
    AND report_schema_valid
    AND completion_marker_valid
    AND job_correlation_valid
    AND plugin_hash_correlation_valid
    AND script_hash_correlation_valid
    AND no_unexpected_outputs
    AND stdout_bounded
    AND stderr_bounded
    AND deadline_respected
    AND no_surviving_descendants
    AND independent_validation_passes
```

- No "warning but success".
- No "partial pass".
- Any failed term immediately yields `FAIL` with its specific taxonomy error code.

---

## 19. Numbered Frozen Acceptance Criteria

The following 17 criteria are permanently frozen:

| # | Criterion | Pass Rule | Failure Code |
|---|---|---|---|
| **1** | **Fixed argv grammar** | All argv elements are generated trusted-side by profile; no caller strings; safe-name tokens only | `POLICY_VIOLATION` |
| **2** | **No shell execution** | Spawn uses `shell=False`; no `cmd.exe` or `powershell.exe` in process tree | `POLICY_VIOLATION` |
| **3** | **Executable integrity** | SHA-256 of xEdit binary matches pinned hash before spawn | `EXECUTABLE_HASH_MISMATCH` |
| **4** | **Script integrity** | SHA-256 of static Pascal script matches pinned hash before spawn | `POLICY_VIOLATION` |
| **5** | **No runtime code generation** | Script is pre-written and static; zero dynamic code generation from model output | `POLICY_VIOLATION` |
| **6** | **Workspace containment** | All paths resolve strictly inside `<workspace_root>`; no parent directory traversal | `WORKSPACE_VIOLATION` |
| **7** | **Input immutability** | SHA-256 of input plugin fixture is identical before spawn and after termination | `INPUT_HASH_MISMATCH` |
| **8** | **Output freshness & existence** | Target report absent before spawn; exists after exit code 0 with size > 0 bytes | `PRE_EXISTING_OUTPUT_PRESENT` / `EXPECTED_OUTPUT_MISSING` |
| **9** | **Strict report schema** | Report validates strictly against JSON Schema `XEDIT_VALIDATE_PLUGIN_V1` | `POLICY_VIOLATION` |
| **10** | **Explicit completion marker** | Report contains `completion_marker: "XEDIT_VALIDATION_COMPLETE_V1"` | `EXPECTED_OUTPUT_MISSING` / `POLICY_VIOLATION` |
| **11** | **Trusted-side correlation** | `job_id`, `plugin_sha256`, and `script_sha256` in report match orchestrator records | `POLICY_VIOLATION` |
| **12** | **Bounded stream capture** | stdout and stderr capped during transfer (<= 64 KiB); saved under `logs/` | `OUTPUT_LIMIT_EXCEEDED` |
| **13** | **Monotonic deadline** | Execution exceeding deadline budget is killed within grace period | `PROCESS_TIMEOUT` |
| **14** | **Process tree cleanup** | Windows Job Object confinement enforced; zero descendants outlive cleanup | `DESCENDANT_PROCESS_SURVIVED` / `INTERNAL_ERROR` |
| **15** | **No unexpected outputs** | Workspace snapshot post-spawn contains zero undeclared files | `UNEXPECTED_OUTPUT_PRESENT` |
| **16** | **Fail-closed negative handling** | All negative fixtures (B through J) fail closed with their expected error codes | `PROCESS_FAILED`, `POLICY_VIOLATION`, etc. |
| **17** | **Redistributable fixture legality** | Synthetic own-authored fixture only; zero copyrighted Bethesda assets committed | `POLICY_VIOLATION` |

---

## 20. Evidence Ladder & Explicit Non-Claims

### 20.1 Evidence Ladder Position
- **E0 (Design / Schema Accepted):** Achieved by ADR-004 and this pre-registration.
- **E1 (Tool / Process Evidence):** Targeted by POC-004 (demonstrating xEdit execution, stream bounding, Job Object cleanup).
- **E2 (Report Reopened & Asserted):** Targeted by POC-004 (orchestrator parsing and schema validation of JSON report).
- **E3 (Independent Static Validation):** POC-004 proves whether xEdit *can serve* as an E3 validator. It does **not** achieve E3 for Skyrim plugins generally.
- **E4 (Human Approval):** HITL review gate.
- **E5 (In-game Runtime Validation):** Future milestone.

### 20.2 Explicit Non-Claims
- **LOAD SUCCESS != PLUGIN CORRECT:** That xEdit loads a plugin without crashing does not prove that the plugin is semantically correct, bug-free, or functional in the Skyrim game engine.
- Does not authorize runtime execution of xEdit in this PR.
- Does not authorize dynamic Pascal generation.
- Does not claim that xEdit can run in headless Linux CI.
- Does not claim that `OS_SANDBOX` is verified (`OS_SANDBOX` remains `NO VERIFICADO`).
- Does not alter the repository status of POC-004: it remains strictly **`NO VERIFICADO`**.

---

## 21. Threat Model & Security Mitigations

| # | Threat Scenario | Attack Vector / Failure Mode | ETEC Mitigation | Mandatory Evidence |
|---|---|---|---|---|
| **T1** | Binary substitution | Malicious binary placed at tool path | Pre-spawn SHA-256 hash pin against trusted config | Pre-spawn hash comparison log |
| **T2** | Script tampering | Script altered on disk to inject code | Pre-spawn SHA-256 hash pin against static reviewed script | Pre-spawn script hash log |
| **T3** | Runtime Pascal injection | LLM crafts malicious Pascal instructions | Static script only; no dynamic generation permitted | Profile enforcement; zero generator code |
| **T4** | Command injection | Special characters (`&`, `|`, `;`) in plugin name | Safe-name token validation, `shell=False`, no cmd.exe | Structured argv array log |
| **T5** | Workspace traversal | Relative paths escaping sandbox (`..\..\`) | Post-resolve containment check strictly inside `<workspace_root>` | Normalized path assertion |
| **T6** | Stale report replay | Reusing report from earlier run | Pre-spawn absence check; monotonic mtime verification | Pre-spawn directory listing log |
| **T7** | Report spoofing | Malicious plugin forging a valid report | Trusted-side correlation of `job_id` and `plugin_sha256` | Recomputed SHA-256 comparison |
| **T8** | Partial / torn write | Process killed while writing JSON | Strict JSON schema parsing and EOF validation | Schema validator output log |
| **T9** | Runaway hang | xEdit modal dialog or infinite loop | Monotonic deadline + Windows Job Object termination | Process timeout timestamp log |
| **T10** | Surviving processes | Background workers or crash daemons surviving | Windows Job Object `KILL_ON_JOB_CLOSE` + Toolhelp32 audit | Post-cleanup process list (empty) |
| **T11** | Workspace pollution | Undocumented cache, ini, or backup dumps | Pre/post recursive workspace snapshot comparison | Workspace diff log (empty) |
| **T12** | Input corruption | Tool overwrites input fixture in-place | Pre/post SHA-256 comparison of input fixture | Input hash match log |
| **T13** | Stream denial of service | Massive output flooding stdout/stderr | Transfer-time stream cap at 64 KiB | Captured byte count log |
| **T14** | Vacuous exit-0 | xEdit exits 0 without running script | Requirement of explicit completion marker in report | Parsed completion marker log |
| **T15** | Silent script abort | Script throws runtime error before finalize | Missing report or missing completion marker fails closed | `EXPECTED_OUTPUT_MISSING` assertion |
| **T16** | Ambient state leak | xEdit modifying live game Data or AppData | Redirected flags (`-D:`, `-P:`, `-T:`) and isolation audit | Host filesystem state verification |
