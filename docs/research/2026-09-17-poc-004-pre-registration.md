# POC-004 pre-registration — xEdit allowlisted validator

- **Status:** `NO VERIFICADO` — criteria pre-registered 2026-09-17 (revised 2026-09-17 following adversarial technical review). **Experiment designed, pre-registered, and criteria frozen; NOT yet implemented or executed.**
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

## 2. Architectural Context: ETEC vs WIPC and Evidence Separation

POC-004 belongs exclusively to the **External Tool Execution Contract (ETEC)** established in [ADR-004](../adr/ADR-004-external-tool-execution-contract.md).

xEdit is **not** a worker under [ADR-002](../adr/ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) (WIPC):
- **No wire transport:** No request object on stdin, no response envelope on stdout.
- **No worker-emitted receipt:** xEdit cannot emit a WIPC Receipt or assert its own invariants.
- **No runtime protocol handshake:** `protocol_version` does not apply.
- **Strict Evidence Layer Separation:** xEdit only emits tool-level observations (`reports/validation_report.json`). The orchestrator independently verifies the run and synthesises the trusted evidence record (`logs/poc004-evidence.json`), correlating `job_id`, `executable_sha256`, `script_sha256`, `input_plugin_sha256`, `staged_plugin_sha256`, and `report_sha256`.

```text
Orchestrator (Trusted Side)
  │
  ├─ [Pre-spawn verification]
  │    ├── Pinned xEdit binary SHA-256 verified against configuration
  │    ├── Pinned Pascal script SHA-256 verified against version-controlled script
  │    ├── Source fixture SHA-256 verified identical to staged copy in data/
  │    └── Target report path absent (PRE_EXISTING_OUTPUT_PRESENT)
  │
  ├─ [Spawn with OS Confinement]
  │    ├── Windows Job Object (JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)
  │    ├── shell = False
  │    ├── Deny-by-default environment (TEMP/TMP redirected to temp/)
  │    └── Closed argv: [exe, -sse, -autoload, -autoexit, -D:..., -I:..., -P:..., -S:..., -R:..., -T:..., -B:..., -C:..., -script:...]
  │
  ▼
External Tool (Untrusted xEdit Execution)
  │
  ├── Loads: staged fixture from workspace data/ via -D: and -P:
  ├── Executes: static script located via -S: and -script:
  ├── Emits: tool observations to reports/validation_report.json
  └── Emits: execution log to logs/xedit.log via -R:
  │
  ▼
Orchestrator (Trusted Validation & Evidence Synthesis)
  │
  ├── Enforce execution deadline & verify zero surviving descendants (Job Object)
  ├── Verify source input/ fixture SHA-256 unchanged (INPUT_HASH_MISMATCH)
  ├── Verify staged data/ fixture SHA-256 unchanged (INPUT_HASH_MISMATCH)
  ├── Verify no undeclared files in workspace snapshot (UNEXPECTED_OUTPUT_PRESENT)
  ├── Verify report exists, non-empty, and fresh (EXPECTED_OUTPUT_MISSING)
  ├── Validate report against strict closed JSON Schema (POLICY_VIOLATION)
  ├── Verify explicit completion marker in report (EXPECTED_OUTPUT_MISSING)
  ├── Verify semantic determinism across independent workspaces (DETERMINISM_MISMATCH)
  └── Synthesise trusted evidence envelope (logs/poc004-evidence.json)
```

---

## 3. Objective of POC-004

To demonstrate or refute whether a user-installed copy of xEdit can be invoked as an independent, read-only, deterministic, fail-closed validator for Skyrim plugins, governed by a closed ETEC profile, without modifying original files, without modifying staged copies in-place, without escaping the workspace, and without permitting arbitrary LLM-generated code execution at runtime.

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
| **Script location** | Allowlisted static script staged in `<workspace>/scripts/` and located by xEdit via `-S:<workspace>\scripts\` |
| **Input fixture** | Own-authored synthetic `.esp` in `<workspace>/input/`; staged read-only copy in `<workspace>/data/` |
| **Input immutability** | Dual-path hash verification: both `input/<fixture>` and `data/<fixture>` must match pre-spawn and post-spawn |
| **Candidate output** | Read-only validation profile; no candidate plugin modifications permitted; `candidates/` remains empty |
| **Tool report output** | Exactly one machine-readable JSON report emitted by the script: `reports/validation_report.json` |
| **Tool log output** | Explicit log path directed inside workspace via `-R:<workspace>\logs\xedit.log` |
| **Evidence envelope** | Synthesised trusted-side by orchestrator: `logs/poc004-evidence.json` correlating all run parameters |
| **argv grammar** | Fully determined trusted-side; closed token list; no raw caller strings reach argv |
| **`cwd`** | Derived trusted-side to workspace root; never from request or caller data |
| **Environment** | Deny-by-default allowlist; `TEMP` and `TMP` redirected strictly to workspace `temp/` |
| **Shell** | `shell=False` strictly; no `cmd.exe` or `powershell.exe` in process tree |
| **Deadline** | Monotonic execution deadline (60.0 s default; configurable per fixture) plus bounded cleanup grace (5.0 s) |
| **stdout / stderr** | Capped transfer-time readers (65 536 bytes per stream); persisted under `logs/` as untrusted evidence |
| **OS Confinement** | Windows Job Object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`; `CREATE_SUSPENDED` assignment before resume |
| **Determinism gate** | Two independent runs over identical input in clean workspaces must produce semantically identical reports |

---

## 5. Upstream CLI Research & Fact Classification

Upstream sources were verified directly against the official `TES5Edit/TES5Edit` repository (including `xEdit/xeInit.pas` from release branch `dev-4.1.6`), official documentation (*The Tome of xEdit*), and Delphi runtime specifications.

### 5.1 Documented Upstream Flags

1. **`-S:"<path>\"`**:
   - **Path to look for scripts** (*The Tome of xEdit* Section 2.8.1).
   - Confirmed in upstream source (`xEdit/xeInit.pas`):
     ```pascal
     if not wbFindCmdLineParam('S', wbScriptsPath) then
       wbScriptsPath := wbProgramPath + 'Edit Scripts\';
     ```
   - When `-S:` is passed, xEdit overrides `wbScriptsPath` to the specified directory. This enables hermetic script sourcing from `<workspace>/scripts/` without touching `<xEdit_Install_Dir>\Edit Scripts\`. Requires trailing backslash.
2. **`-R:"<path><filename>"`**:
   - **Custom log file destination** (*The Tome of xEdit* Section 2.8.1).
   - Confirmed in upstream source (`xEdit/xeInit.pas`):
     ```pascal
     if wbFindCmdLineParam('R', s) then
       xeLogFile := s;
     ```
   - Directs xEdit's internal log file to `<workspace>/logs/xedit.log`, preventing uncontained log creation.
3. **`-script:"<ScriptName>"`** (or `-script:"<ScriptName.pas>"`):
   - Executes the named Pascal script upon completion of module loading.
4. **`-autoexit`**:
   - Instructs xEdit to terminate immediately after automated tasks or script execution complete.
5. **`-autoload`**:
   - Skips the interactive module selection dialog and automatically loads plugins active in `plugins.txt`.
6. **`-D:"<path>\"`**:
   - Overrides the Data directory. Requires trailing backslash.
7. **`-I:"<path><filename>"`**:
   - Overrides the game main INI file path.
8. **`-P:"<path><filename>"`**:
   - Overrides the `plugins.txt` file path.
9. **`-T:"<path>\"`**:
   - Overrides the temporary directory. Requires trailing backslash.
10. **`-C:"<path>\"`**:
    - Overrides the cache directory. Requires trailing backslash.
11. **`-B:"<path>\"`**:
    - Overrides the backups directory. Requires trailing backslash.
12. **Game mode flags (`-sse`, `-tes5`, `-fo4`)**:
    - Forces specific game mode regardless of the executable filename.
13. **Pascal Script Lifecycle**:
    - Pascal units expose `Initialize: integer;`, `Process(e: IInterface): integer;`, and `Finalize: integer;`.
    - Can write JSON output files using `TStringList.SaveToFile`.

### 5.2 Observed Facts

- **None** for xEdit in this repository: xEdit has never been executed in this repository or in CI. All runtime claims for xEdit remain unobserved.

### 5.3 Inferred Facts

- That passing `-D:`, `-I:`, `-P:`, `-S:`, `-R:`, and `-T:` simultaneously completely redirects xEdit's file operations into the workspace boundary.
- That xEdit exits with code `0` when `-autoexit` completes normally after a script finishes.

### 5.4 NO VERIFICADO (Frozen Unknowns)

The following behavioral unknowns cannot be verified without empirical execution of xEdit:

1. **Masterless Synthetic Plugin Support:**
   - Does xEdit 4.x allow opening a minimal synthetic `.esp` (containing only a TES4 header) without `Skyrim.esm` or official masters present in `-D:`? Or does it abort / popup an error dialog demanding official masters?
   - *Status:* `NO VERIFICADO`.
2. **GUI & Modal Dialog Suppression:**
   - xEdit is a Delphi VCL GUI application. When launched with `-autoload -script:... -autoexit`, does it instantiate a visible window?
   - Crucially: do non-fatal warnings, missing string tables, or syntax errors open modal popups (e.g. `ShowMessage`, `MessageDlg`) that block the main thread and prevent `-autoexit` until deadline timeout?
   - *Status:* `NO VERIFICADO`.
3. **Exit Codes on Failure:**
   - What exit code does xEdit return when a script encounters an unhandled exception or calls `Exit`? Does it return a non-zero code, or does it exit 0 regardless?
   - *Status:* `NO VERIFICADO`.
4. **`-P:` Argument Hermeticism:**
   - Does xEdit strictly honor `-P:<path><filename>` across all 4.x versions, or does it attempt to fall back to `%LOCALAPPDATA%\Skyrim Special Edition\plugins.txt`?
   - *Status:* `NO VERIFICADO`.
5. **Registry Probing & Ambient Host Leakage:**
   - Does xEdit query the Windows Registry (`HKLM\Software\Bethesda Softworks\Skyrim Special Edition` or Steam keys) even when `-D:` and `-I:` are specified on the command line?
   - *Status:* `NO VERIFICADO`.
6. **Process Tree & Descendants on Windows:**
   - Does xEdit spawn child helper processes or background worker threads that survive main window closure?
   - *Status:* `NO VERIFICADO`.
7. **External Filesystem Writes:**
   - Does xEdit attempt to write settings, view state, or MRU lists into `%LOCALAPPDATA%` or the Windows Registry upon exiting?
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
2. **Hermetic Staging via `-S:`**:
   - The script is staged into `<workspace>/scripts/ValidatePluginV1.pas` and pointed to via `-S:<workspace>\scripts\`.
   - The user's xEdit installation directory is never modified.
3. **Runtime Code Generation Prohibited:**
   - **Under NO circumstances may an LLM generate, mutate, or inject Pascal code at runtime.**
   - Dynamic script assembly, template expansion with untrusted tokens, and arbitrary user-supplied script paths are strictly forbidden.
   - *Development vs. Runtime distinction:* An LLM may assist human developers in authoring the static `.pas` script during offline development, but once authored, the script is static, audited, and immutable at the runtime boundary.
4. **Cryptographic Script Hash Pinning:**
   - Pre-spawn check:
     ```text
     actual_script_sha256 = sha256(script_path)
     if actual_script_sha256 != pinned_script_sha256:
         fail closed with POLICY_VIOLATION (no process spawned)
     ```

---

## 8. Controlled Input Fixture & Staging

1. **Synthetic and Own-Authored:**
   - Fixtures used by POC-004 must be minimal, synthetic, and created specifically for testing (e.g. extending the synthetic TES4 header fixture proven in POC-002).
2. **Zero Proprietary Material:**
   - Absolutely NO Bethesda-copyrighted records, official plugins (`Skyrim.esm`, `Update.esm`, `Dawnguard.esm`), third-party mod files, or live user Data folders may be used or committed.
3. **Staging Architecture:**
   - The original controlled fixture is placed in `<workspace>/input/<fixture_name>.esp`.
   - A copy is staged in `<workspace>/data/<fixture_name>.esp` for xEdit's `-D:` Data directory, alongside an isolated `<workspace>/data/plugins.txt` for `-P:`.
4. **Masterless Plugin Unknown:**
   - Whether xEdit permits loading a masterless synthetic plugin without crashing is a primary hypothesis to be tested by POC-004. It is recorded as `NO VERIFICADO`.

---

## 9. Input and Staged Plugin Immutability

To eliminate false security where `input/` is unmodified but `data/` was mutated in-place by xEdit:

1. **Pre-spawn baseline:**
   - Orchestrator records SHA-256, size, and mtime of `input/<fixture_name>.esp`.
   - Orchestrator records SHA-256, size, and mtime of `data/<fixture_name>.esp`.
   - Invariant: `sha256(input/<fixture_name>.esp) == sha256(data/<fixture_name>.esp)`.
2. **Post-spawn assertion:**
   - Orchestrator recomputes hashes immediately following process termination and cleanup:
     ```text
     source_hash_after = sha256("input/<fixture_name>.esp")
     staged_hash_after = sha256("data/<fixture_name>.esp")
     ```
3. **Pass rule (Strict Dual Immutability):**
   ```text
   source_hash_before == source_hash_after
   AND staged_hash_before == staged_hash_after
   AND source_hash_before == staged_hash_after
   ```
   If either hash changes: fail closed with `INPUT_HASH_MISMATCH`.

---

## 10. Workspace Contract

Every invocation runs inside an ephemeral, dedicated workspace directory created trusted-side:

```text
<workspace_root>/
  ├── input/          # Immutable source fixture (.esp)
  ├── data/           # Staged data folder for xEdit (-D:), contains .esp & plugins.txt
  ├── ini/            # Minimal dummy Skyrim.ini for xEdit (-I:)
  ├── scripts/        # Staged allowlisted static script for xEdit (-S:)
  ├── reports/        # Target directory for validation_report.json
  ├── logs/           # Captured stdout.log, stderr.log, xedit.log (-R:), poc004-evidence.json
  ├── backups/        # Empty directory for xEdit (-B:)
  ├── cache/          # Empty directory for xEdit (-C:)
  └── temp/           # Redirected TEMP / TMP directory (-T:)
```

1. **Declared Allowed Outputs:**
   - `reports/validation_report.json`
   - `logs/stdout.log`
   - `logs/stderr.log`
   - `logs/xedit.log`
   - `logs/poc004-evidence.json`
   - Ephemeral scratch files strictly contained within `temp/`.
2. **Workspace Snapshotting:**
   - **Pre-spawn:** Recursive regular-file snapshot of all files in `<workspace_root>`.
   - **Post-spawn:** Recursive regular-file snapshot of all files in `<workspace_root>`.
   - Any file appearing outside the declared allowed outputs fails closed with `UNEXPECTED_OUTPUT_PRESENT`.
3. **External Writes:**
   - Any file created outside `<workspace_root>` fails the run and is recorded as an isolation violation.

---

## 11. Output Contract: Two-Layer Architecture

To eliminate the self-reference paradox (where a script cannot embed its own hash) and ensure clean separation of concerns:

### 11.1 Layer 1: Tool-Emitted Report (`reports/validation_report.json`)
Written by the static Pascal script upon completing inspection. It contains **only tool observations**:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "XEditToolValidationReportV1",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "schema_version",
    "plugin_name",
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
    "plugin_name": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9_-]+\\.(esp|esm|esl)$"
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

### 11.2 Layer 2: Trusted Evidence Envelope (`logs/poc004-evidence.json`)
Constructed **trusted-side by the orchestrator** after execution. It records all cryptographic pins, correlation data, and process measurements:

```json
{
  "schema_version": 1,
  "job_id": "<uuid-or-token>",
  "profile_id": "XEDIT_VALIDATE_PLUGIN_V1",
  "executable_sha256": "<pinned_sha256>",
  "script_sha256": "<pinned_sha256>",
  "source_plugin_sha256": "<recomputed_sha256>",
  "staged_plugin_sha256": "<recomputed_sha256>",
  "report_sha256": "<sha256_of_validation_report_json>",
  "tool_report": { "...embedded or referenced contents of validation_report.json..." },
  "process_metrics": {
    "exit_code": 0,
    "elapsed_seconds": 1.25,
    "stdout_bytes": 1024,
    "stderr_bytes": 0,
    "descendants_observed": 0,
    "descendants_alive_after_cleanup": 0
  },
  "verdict": "SUCCESS"
}
```

---

## 12. Completion Evidence & Independent Correlation

An external process exiting with code `0` is **not evidence that the script ran or completed**.

To prove completion:
1. **Explicit Completion Marker:**
   - The tool report must contain `completion_marker: "XEDIT_VALIDATION_COMPLETE_V1"`.
   - Written exclusively by the Pascal script's `Finalize` block after all records are traversed.
   - Missing, empty, or altered marker fails closed with `EXPECTED_OUTPUT_MISSING` or `POLICY_VIOLATION`.
2. **Trusted-Side Cryptographic Correlation:**
   - The orchestrator asserts:
     - `tool_report.plugin_name` matches the expected fixture name.
     - `staged_plugin_sha256` matches `source_plugin_sha256`.
     - `report_sha256` recorded in the evidence envelope matches the recomputed SHA-256 of the generated report.
     - `script_sha256` recorded in the envelope matches the pre-spawn pinned script hash.

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
  "-S:<RESOLVED_WORKSPACE_SCRIPTS_DIR>\",
  "-R:<RESOLVED_WORKSPACE_LOGS_DIR>\xedit.log",
  "-T:<RESOLVED_WORKSPACE_TEMP_DIR>\",
  "-B:<RESOLVED_WORKSPACE_BACKUPS_DIR>\",
  "-C:<RESOLVED_WORKSPACE_CACHE_DIR>\",
  "-script:<RESOLVED_SCRIPT_TOKEN>"
]
```

- Every token is validated against safe-name grammar (`^[a-zA-Z0-9_.-]+$`).
- All path parameters are resolved to absolute paths strictly within `<workspace_root>`.
- Path switches (`-D:`, `-S:`, `-T:`, `-B:`, `-C:`) terminate with a trailing backslash per upstream xEdit requirements.
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

| Host Resource | Classification | Mitigation Strategy | Pre-registration Risk Status |
|---|---|---|---|
| **Script Sourcing** (`Edit Scripts\`) | `AVOIDABLE` via `-S:` | Provide `-S:<workspace>\scripts\` pointing to workspace. | Upstream verified in `xeInit.pas`. Eliminates installation write risk. |
| **Log Output** (`xEdit_log.txt`) | `AVOIDABLE` via `-R:` | Provide `-R:<workspace>\logs\xedit.log`. | Upstream verified in `xeInit.pas`. Eliminates installation write risk. |
| **Windows Registry** (`HKLM\Software\Bethesda Softworks\Skyrim Special Edition`) | `AVOIDABLE` via `-D:` | Provide explicit `-D:` pointing to workspace data folder. | `NO VERIFICADO` — test if xEdit queries registry if game path is specified. |
| **Active Load Order** (`%LOCALAPPDATA%\Skyrim Special Edition\plugins.txt`) | `AVOIDABLE` via `-P:` | Provide isolated `plugins.txt` via `-P:` containing only fixture. | `NO VERIFICADO` — verify xEdit does not read default AppData path. |
| **Game INI Files** (`%USERPROFILE%\Documents\My Games\Skyrim Special Edition\`) | `AVOIDABLE` via `-I:` | Provide dummy minimal INI in workspace via `-I:`. | `NO VERIFICADO` — verify xEdit does not probe Documents. |
| **Temporary Files** (`%TEMP%`, `%TMP%`) | `AVOIDABLE` via `-T:` + env | Set `-T:` to workspace `temp/` and override `TEMP`/`TMP` in process environment. | `NO VERIFICADO` — verify no files leak to system temp. |
| **Interactive Desktop Session (GDI/User32)** | `REQUIRED` | xEdit is a Delphi VCL application requiring a Win32 GUI subsystem. Cannot run in headless Linux containers or Windows Server Core without desktop session. | Confirmed limitation of xEdit; documented as architectural constraint. |

---

## 16. Negative Test Matrix (Pre-registered Fixtures)

| Case | Condition | Injected Fault | Expected Outcome Code | Required Evidence |
|---|---|---|---|---|
| **A** | Baseline Positive | Valid minimal synthetic TES4 `.esp` | `SUCCESS` | Report exists, valid schema, `validator_status: "VALID"`, marker present, hashes match |
| **B** | Malformed Plugin | Truncated file or corrupted header | `PROCESS_FAILED` or `POLICY_VIOLATION` | xEdit exits non-zero or report records `validator_status: "INVALID"` |
| **C** | Wrong Script Hash | Tampered or modified Pascal script | `POLICY_VIOLATION` | Pre-spawn check fails; zero processes spawned |
| **D** | Wrong Executable Hash | Tampered xEdit binary or incorrect pin | `EXECUTABLE_HASH_MISMATCH` | Pre-spawn check fails; zero processes spawned |
| **E** | Pre-existing Report | Stale `validation_report.json` placed before spawn | `PRE_EXISTING_OUTPUT_PRESENT` | Pre-spawn check fails; zero processes spawned |
| **F** | Forced Timeout | Execution deadline set to 0.1 s | `PROCESS_TIMEOUT` | Process tree terminated; `descendants_alive == []` |
| **G** | Unexpected Output | Extra undeclared file generated in workspace | `UNEXPECTED_OUTPUT_PRESENT` | Snapshot diff catches extraneous file; run rejected |
| **H** | Input Mutation | Script or tool modifies staged `.esp` bytes | `INPUT_HASH_MISMATCH` | Post-spawn hash differs from pre-spawn; run rejected |
| **I** | Missing Completion Marker | Report written without completion marker | `EXPECTED_OUTPUT_MISSING` / `POLICY_VIOLATION` | Validator rejects report; run rejected |
| **J** | Divergent Repeat Run | Two runs on identical input produce divergent reports | `DETERMINISM_MISMATCH` | Semantic comparison between Run A and Run B detects divergence |

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
- `INPUT_HASH_MISMATCH`: Source or staged input fixture hash altered across the run.
- `UNEXPECTED_OUTPUT_PRESENT`: Undeclared files detected in the workspace snapshot.
- `TOOL_DIAGNOSTICS_REJECTED`: Reserved if tool diagnostics violate acceptability rules.
- `DETERMINISM_MISMATCH`: Two runs on identical input produce divergent semantic reports.
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
    AND source_input_hash_unchanged
    AND staged_plugin_hash_unchanged
    AND process_exit_zero
    AND report_exists
    AND report_nonempty
    AND report_fresh
    AND report_schema_valid
    AND completion_marker_valid
    AND report_hash_recomputed
    AND no_unexpected_outputs
    AND stdout_bounded
    AND stderr_bounded
    AND deadline_respected
    AND no_surviving_descendants
    AND validation_is_deterministic
```

- No "warning but success".
- No "partial pass".
- Any failed term immediately yields `FAIL` with its specific taxonomy error code.

---

## 19. Numbered Frozen Acceptance Criteria

The following 18 criteria are permanently frozen:

| # | Criterion | Pass Rule | Failure Code |
|---|---|---|---|
| **1** | **Fixed argv grammar** | All argv elements are generated trusted-side by profile (including `-S:` and `-R:`); no caller strings; safe-name tokens only | `POLICY_VIOLATION` |
| **2** | **No shell execution** | Spawn uses `shell=False`; no `cmd.exe` or `powershell.exe` in process tree | `POLICY_VIOLATION` |
| **3** | **Executable integrity** | SHA-256 of xEdit binary matches pinned hash before spawn | `EXECUTABLE_HASH_MISMATCH` |
| **4** | **Script integrity** | SHA-256 of static Pascal script matches pinned hash before spawn | `POLICY_VIOLATION` |
| **5** | **No runtime code generation** | Script is pre-written and static; zero dynamic code generation from model output | `POLICY_VIOLATION` |
| **6** | **Workspace containment** | All paths resolve strictly inside `<workspace_root>`; no parent directory traversal | `WORKSPACE_VIOLATION` |
| **7** | **Input and staged immutability** | SHA-256 of both source fixture (`input/`) and staged copy (`data/`) are identical before spawn and after termination | `INPUT_HASH_MISMATCH` |
| **8** | **Output freshness & existence** | Target report absent before spawn; exists after exit code 0 with size > 0 bytes | `PRE_EXISTING_OUTPUT_PRESENT` / `EXPECTED_OUTPUT_MISSING` |
| **9** | **Strict report schema** | Report validates strictly against JSON Schema `XEditToolValidationReportV1` | `POLICY_VIOLATION` |
| **10** | **Explicit completion marker** | Report contains `completion_marker: "XEDIT_VALIDATION_COMPLETE_V1"` | `EXPECTED_OUTPUT_MISSING` / `POLICY_VIOLATION` |
| **11** | **Trusted evidence envelope** | Orchestrator synthesises evidence envelope correlating `job_id`, `executable_sha256`, `script_sha256`, `plugin_sha256`, and recomputed `report_sha256` | `POLICY_VIOLATION` / `OUTPUT_HASH_MISMATCH` |
| **12** | **Bounded stream capture** | stdout and stderr capped during transfer (<= 64 KiB); saved under `logs/` | `OUTPUT_LIMIT_EXCEEDED` |
| **13** | **Monotonic deadline** | Execution exceeding deadline budget is killed within grace period | `PROCESS_TIMEOUT` |
| **14** | **Process tree cleanup** | Windows Job Object confinement enforced; zero descendants outlive cleanup | `DESCENDANT_PROCESS_SURVIVED` / `INTERNAL_ERROR` |
| **15** | **No unexpected outputs** | Workspace snapshot post-spawn contains zero undeclared files (authorized set: report, stdout, stderr, xedit.log, evidence envelope) | `UNEXPECTED_OUTPUT_PRESENT` |
| **16** | **Fail-closed negative handling** | All negative fixtures (B through J) fail closed with their expected error codes | `PROCESS_FAILED`, `POLICY_VIOLATION`, etc. |
| **17** | **Redistributable fixture legality** | Synthetic own-authored fixture only; zero copyrighted Bethesda assets committed | `POLICY_VIOLATION` |
| **18** | **Semantic determinism** | Two independent runs on identical input in separate clean workspaces yield semantically identical validation reports | `DETERMINISM_MISMATCH` |

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
| **T7** | Report spoofing | Malicious plugin forging a valid report | Trusted-side correlation of `job_id`, `plugin_sha256`, and `report_sha256` | Recomputed SHA-256 comparison |
| **T8** | Partial / torn write | Process killed while writing JSON | Strict JSON schema parsing and EOF validation | Schema validator output log |
| **T9** | Runaway hang | xEdit modal dialog or infinite loop | Monotonic deadline + Windows Job Object termination | Process timeout timestamp log |
| **T10** | Surviving processes | Background workers or crash daemons surviving | Windows Job Object `KILL_ON_JOB_CLOSE` + Toolhelp32 audit | Post-cleanup process list (empty) |
| **T11** | Workspace pollution | Undocumented cache, ini, or backup dumps | Pre/post recursive workspace snapshot comparison | Workspace diff log (empty) |
| **T12** | Input corruption | Tool overwrites input or staged fixture in-place | Dual-path pre/post SHA-256 comparison of input and staged fixture | Input hash match log |
| **T13** | Stream denial of service | Massive output flooding stdout/stderr | Transfer-time stream cap at 64 KiB | Captured byte count log |
| **T14** | Vacuous exit-0 | xEdit exits 0 without running script | Requirement of explicit completion marker in report | Parsed completion marker log |
| **T15** | Silent script abort | Script throws runtime error before finalize | Missing report or missing completion marker fails closed | `EXPECTED_OUTPUT_MISSING` assertion |
| **T16** | Ambient state leak | xEdit modifying live game Data or AppData | Redirected flags (`-D:`, `-P:`, `-S:`, `-R:`, `-T:`) and isolation audit | Host filesystem state verification |
