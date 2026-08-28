# ADR-003 — Mutagen runtime and license boundary

- **Status:** PROPOSED
- **Date:** 2026-08-28
- **Scope:** Technical and legal boundary for Mutagen integration.
- **Depends on:** [ADR-001](ADR-001-hybrid-headless-first-architecture.md) (ACCEPTED), [ADR-002](ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) (ACCEPTED).

## Context

The agent requires a robust, headless Skyrim SE/AE plugin reader and writer to analyze and patch plugin records without relying on Windows UI automation of the Creation Kit or xEdit for routine tasks. 
[Mutagen](https://github.com/Mutagen-Modding/Mutagen) is the community standard strongly typed .NET/C# library for Bethesda plugin manipulation. However, Mutagen is licensed under **GNU General Public License v3.0 (GPL-3.0)**, while this repository is licensed under the permissive **MIT License**. Furthermore, ADR-002 strictly prescribes a Python runtime (`python -I -B`) for out-of-process workers.

This ADR defines how the project will address these legal, architectural, and dependency-related tensions.

## Problem statement

1. **Licensing Tension**: Can an MIT-licensed project use/interoperate with a GPL-3.0 library without copyleft contamination?
2. **Runtime Tension**: ADR-002 specifies a Python-only worker launch command (`python -I -B`). A .NET-based worker violates the current text of ADR-002.
3. **Hermetic Execution**: How can we run a Mutagen worker in a fail-closed, read-only manner without touching Steam registry, Skyrim's data folders, or exposing the host OS to risks?

## Current architecture constraints

- **ADR-001 Section: Worker boundaries**: Specifies that process isolation is a technical architecture choice, not a legal conclusion about GPL obligations.
- **ADR-002 Section: Process and transport model**: Mandates the launch command: `<trusted absolute python> -I -B <trusted worker entry> --job-root <derived absolute job dir>`. This is Python-specific.
- **ADR-002 Section: Success contract**: Mandates that process exit code must be zero, schema must validate, and all assertions must pass.
- **ADR-002 Section: Workspace contract and ownership**: Workers only read `input/` and `originals/`, and write only to `candidates/` and `temp/`.

---

## Mutagen technical facts

- **Official Repository**: [Mutagen-Modding/Mutagen](https://github.com/Mutagen-Modding/Mutagen)
- **License**: GPL-3.0-only (explicit LICENSE file in repository).
- **Target Framework**: `.NET 9.0` (as of modern versions in August 2026).
- **NuGet Packages**: `Mutagen.Bethesda` and `Mutagen.Bethesda.Skyrim` are published under the GPL-3.0 license.
- **Platform Support**: Cross-platform (Windows, Linux, macOS) via standard .NET Core runtimes.
- **Single-file Read**: Verified. The API offers `SkyrimMod.CreateFromBinaryOverlay(filePath, release)` which parses a single plugin from a path.
- **Skyrim Installation Dependency**: Not required. Bypassing `GameEnvironment.Typical` allows loading isolated files directly, avoiding Steam auto-discovery and loading order assembly.

---

## License Gate Analysis (L1-L5)

### L1 — Link Directo (MIT + NuGet Reference in same executable)
- **Obligations**: A combined work that references Mutagen must be licensed under GPL-3.0. The MIT license is contaminated/invalidated for distribution.
- **Technical Cost**: Low.
- **Legal Confidence**: High (GPL violation if distributed as MIT).
- **Recommendation**: Rejected.

### L2 — Proceso Externo (MIT Orchestrator + GPL Mutagen Worker via IPC)
- **Obligations**: IPC boundary (stdin/stdout pipes, JSON schemas) constitutes separate programs under FSF GPL guidance. The orchestrator remains MIT; the worker source code remains GPL-3.0.
- **Technical Cost**: Medium (requires IPC marshalling).
- **Legal Confidence**: Medium-High (standard industry boundary).
- **Recommendation**: Acceptable, but carries distribution risks if bundled together.

### L3 — GPL Adapter Separado (Separate Repo/Binary for GPL Worker)
- **Obligations**: Worker is hosted in a completely separate GPL-3.0 repository. The MIT repository contains zero GPL code. Interoperability occurs over a public protocol.
- **Technical Cost**: High (dual-repository maintenance).
- **Legal Confidence**: High (zero MIT repo contamination).
- **Recommendation**: Recommended.

### L4 — User-Supplied Tool
- **Obligations**: The agent does not distribute the worker. The user compiles or downloads the `mutagen-worker` binary.
- **Technical Cost**: Very High (complex UX/setup).
- **Legal Confidence**: Critical (highest possible safety).
- **Recommendation**: High, but bad UX.

### L5 — Permissive Alternative
- **Obligations**: Use an MIT/Apache alternative like `esp_extractor` (Rust).
- **Technical Cost**: Very High (incomplete Skyrim SE/AE coverage, writing is unsupported).
- **Legal Confidence**: Highest (permissive).
- **Recommendation**: Rejected due to lack of mature API.

---

## License Decision Matrix

| Option | Linking | Distributed Together | Repo License Impact | Technical Cost | Legal Confidence | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| **L1** | Direct | Yes | Contaminates (must be GPL) | Low | High (GPL) | **REJECTED** |
| **L2** | IPC | Yes | None (separate process) | Medium | Medium-High | **ACCEPTED WITH CAUTION** |
| **L3** | IPC | No (separate repo) | None | High | High | **RECOMMENDED SPINE** |
| **L4** | IPC | No | None | Very High | Critical | **UX BLOCKER** |
| **L5** | None | N/A | None | Extreme | Critical | **API INCOMPLETE** |

> [!IMPORTANT]
> Because distributing a GPL-3.0 binary (even in a separate process) alongside an MIT application introduces legal ambiguity under the "mere aggregation" vs "combined work" GPL doctrines, this ADR declares:
> **STATUS: LEGAL_REVIEW_REQUIRED**
> Final selection between L2 and L3 requires formal legal verification of the distribution model before production release.

---

## Architecture options

### Option A: .NET Worker Direct (Generalize ADR-002)
- **Description**: The Python orchestrator launches a trusted .NET worker directly.
- **Pros**: Single IPC boundary, low latency, no nested subprocesses.
- **Cons**: Requires modifying ADR-002's launch command.
- **Recommendation**: Preferred technical path.

### Option B: Python Worker + .NET Child
- **Description**: The orchestrator spawns a Python worker, which spawns the .NET child.
- **Pros**: Satisfies ADR-002's Python requirement unchanged.
- **Cons**: Nested subprocesses, complex process-tree cleanup, higher timeout/failure surface.
- **Recommendation**: Rejected.

### Option C: External GPL Tool Adapter
- **Description**: The orchestrator interacts with a separately installed worker executable via registry.
- **Pros**: Fits L3/L4 boundaries.
- **Cons**: Extra environment check overhead.
- **Recommendation**: Supported as a deployment variant of Option A.

---

## Runtime generalization (ADR-002 Amendment)

To support .NET workers, we propose generalizing the trusted worker registry to define **Worker Launch Profiles**:

```python
class WorkerLaunchProfile:
    runtime_kind: str          # "python" | "dotnet" | "native"
    executable_path: str       # Absolute path of trusted host (e.g. /usr/bin/dotnet)
    args_template: list[str]   # Args list, e.g. ["-I", "-B", "{entrypoint}"]
    entrypoint: str            # Absolute path to DLL or script
    environment_allowlist: list[str]
    cwd_policy: str
```

- For Python, `-I -B` remains strictly enforced.
- For .NET, execution uses absolute executable paths (e.g., dotnet host) with no shell, keeping the deny-by-default environment.
- The wire schemas and protocol semantics remain **Protocol Version 1**; no wire changes are needed.

---

## Proposed POC-MUTAGEN-001 scope

If approved, the next research task will be `POC-MUTAGEN-001`:

- **Operation**: `INSPECT_PLUGIN_HEADER`
- **Runtime**: .NET 9.0 worker.
- **Input**: `input/<plugin_name>` (safe-name token only; no absolute paths).
- **Output**: `[]` (read-only; no candidate writes).
- **API Call**: `SkyrimMod.CreateFromBinaryOverlay(filePath, release)`.
- **Expected Metadata**:
  - `ModKey` (identity)
  - `HeaderVersion`
  - `Flags` (ESM/ESL detection)
  - `MasterFiles` (dependencies list)
  - `Author` / `Description`
- **Fixture Strategy**: We will use a synthetic fixture generated programmatically (e.g., via our existing POC-002 tool) to avoid distributing Bethesda files.

---

## Claims / Non-claims

### Claims
- The .NET worker is launched out-of-process via standard pipes.
- The worker is read-only and does not touch Steam or game paths.
- All exit codes and schemas are validated orchestrator-side.

### Non-claims
- Does not prove load order correctness or xEdit equivalence.
- Does not authorize writing/mutating Skyrim plugins.
- Does not claim that the worker is sandboxed at the OS level (`OS_SANDBOX` remains `NO VERIFICADO`).

---

## Supply Chain & Security

- **Pinning**: All NuGet dependencies will use locked mode (`--locked-mode` via `packages.lock.json`).
- **Target SDK**: .NET 9.0 SDK.
- **CI**: Runs on Windows and Linux runners with the dotnet toolchain installed.

---

## Open questions

1. Should the C# worker compile as a self-contained executable to avoid needing a pre-installed .NET 9.0 runtime on the user's host?
2. How does `CreateFromBinaryOverlay` handle corrupt/truncated files, and does it throw deterministic exceptions we can map to `INVALID_RESPONSE` or `PROCESS_FAILED`?

---

## STOP Conditions

- **STOP** if NuGet dependencies introduce transitive copyleft licenses other than GPL-compatible ones (e.g. AGPL).
- **STOP** if `CreateFromBinaryOverlay` attempts background Steam registry lookups that cannot be disabled.
- **STOP** if legal counsel rejects L2/L3 process separation for distribution.
