# ADR-003 — Mutagen runtime and license boundary

- **Status:** PROPOSED
- **Date:** 2026-08-28
- **Scope:** Technical and legal boundary for Mutagen integration.
- **Depends on:** [ADR-001](ADR-001-hybrid-headless-first-architecture.md) (ACCEPTED), [ADR-002](ADR-002-isolated-worker-ipc-and-transactional-boundaries.md) (ACCEPTED).

## Context

The agent requires a robust, headless Skyrim SE/AE plugin reader and writer to analyze and patch plugin records without relying on Windows UI automation of the Creation Kit or xEdit for routine tasks. 
[Mutagen](https://github.com/Mutagen-Modding/Mutagen) is the strongest/mature candidate identified in this research for Bethesda plugin manipulation in C#/.NET. However, Mutagen is licensed under the **GNU General Public License v3.0 (GPL-3.0)**, while this repository is licensed under the permissive **MIT License**. Furthermore, ADR-002 strictly prescribes a Python runtime (`python -I -B`) for out-of-process workers.

This ADR defines the technical options, license implications, and runtime boundaries required before any implementation may begin.

## Problem statement

1. **Licensing Boundary**: How can an MIT-licensed project interact with a GPL-3.0 library upon distribution without violating or misrepresenting licensing obligations?
2. **Runtime Generalization**: ADR-002 specifies a Python-only worker launch command (`python -I -B`). A .NET-based worker requires extending the trusted worker launch profile.
3. **Hermetic Execution**: Ensuring that Mutagen execution is fail-closed, read-only, workspace-contained, and isolated from ambient host state (Steam, Skyrim Data directory, registry).

## Current architecture constraints

- **ADR-001 (§Worker boundaries)**: Establishes that process isolation is an architectural and security separation, **not** a legal safe harbor regarding GPL obligations.
- **ADR-002 (§Process and transport model)**: Specifies `<trusted absolute python> -I -B <trusted worker entry> --job-root <derived absolute job dir>`. The `-I -B` flags are normative for Python workers.
- **ADR-002 (§Success contract & Workspace ownership)**: Mandates that exit code must be zero, schema must validate closed-world, assertions must pass, and workers may only read `input/`/`originals/` and write to `candidates/`/`temp/`.

---

## Mutagen technical facts

- **Official Repository**: [Mutagen-Modding/Mutagen](https://github.com/Mutagen-Modding/Mutagen)
- **License**: GPL-3.0-only (per repository LICENSE file and NuGet package metadata).
- **Candidate Stable Release**: `0.54.4` (candidate version to be pinned upon acceptance).
- **Active Prerelease Branch**: `0.55.0-alpha.7` (under active development).
- **Target Frameworks**: Release `0.54.4` packages support modern .NET TFMs including `net8.0` and `net9.0`. Target runtime framework is **TO BE DECIDED** following a deployment/runtime packaging review.
- **NuGet Packages**: `Mutagen.Bethesda`, `Mutagen.Bethesda.Skyrim`.
- **Platform Support**: Cross-platform (Windows, Linux, macOS) on supported .NET runtimes.
- **Single-file Read API**:
  - `SkyrimMod.CreateFromBinaryOverlay(ModPath path, SkyrimRelease release, StringsReadParameters stringsParam = default)`
  - Direct single-file read: **YES**.
  - Skyrim installation required: **NO**.
  - Steam / load order discovery avoidable: **YES** (by avoiding `GameEnvironment.Typical`).

---

## License Analysis and GNU GPL FAQ Citations

The repository is licensed under the permissive **MIT License**. Mutagen is licensed under **GPL-3.0-only**. MIT is GPL-compatible, meaning MIT-licensed code can be combined into a GPL work; however, a distributed combined work containing GPL components must comply with all GPL obligations (including source code availability for the entire combined work).

To evaluate how process separation and distribution models affect licensing obligations, we reference authoritative guidance from the [GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html):

1. **Separate vs. Combined Programs ([GPL FAQ #GPLPlugins](https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins))**:
   > *"If the main program uses fork and exec to invoke plug-ins, and they establish intimate communication by sharing complex data structures, or shipping complex data structures back and forth, that can make them one single combined program. A main program that uses simple fork and exec to invoke plug-ins and does not establish intimate communication between them results in the plug-ins being separate programs."*
2. **Pipes and Sockets ([GPL FAQ #GPLInProprietarySystem](https://www.gnu.org/licenses/gpl-faq.html#GPLInProprietarySystem))**:
   > *"Pipes, sockets and command-line arguments are the communication mechanisms normally used between two separate programs... But if the semantics of the communication are intimate enough, exchanging complex internal data structures, that too could be a basis to consider the two parts as combined into a larger program."*
3. **Mere Aggregation ([GPL FAQ #MereAggregation](https://www.gnu.org/licenses/gpl-faq.html#MereAggregation))**:
   > *"An 'aggregate' consists of a number of separate programs, distributed on the same compilation or distribution medium... If the two programs remain well separated, like the compiler and the kernel, then it is an aggregate."*

### Evaluation of Options (L1–L5)

- **L1 — Direct Linking (In-Process / NuGet Reference)**:
  Direct linking likely makes GPL obligations relevant to distribution of the combined work. The distributed combined binary could not be offered under MIT alone without fulfilling GPL source obligations.
  *Verdict: REJECTED.*

- **L2 — External Process (Same Repository, Separate Executable via JSON IPC)**:
  Process separation via exec and pipes is evidence in favor of separate-program treatment, **NOT** a legal safe harbor. Because communication semantics also matter, restricting IPC to a minimal, typed JSON protocol with bounded scalars strengthens the separate-program characterization. However, distributing both binaries together on the same release medium introduces questions under "mere aggregation" vs. "combined work" doctrines.
  *Verdict: LEGAL_REVIEW_REQUIRED.*

- **L3 — Separately Maintained GPL Adapter (Separate Repository & Package)**:
  Maintaining the GPL worker in a distinct, explicitly GPL-3.0 repository improves provenance and clarity of obligations, ensuring the MIT repository contains zero copyleft source code. However, repository separation does not by itself decide whether two programs distributed or used together form a single combined work.
  *Verdict: TECHNICAL PREFERENCE / LEGAL_REVIEW_REQUIRED.*

- **L4 — User-Supplied Tool**:
  The orchestrator acts purely as a client to a user-provided or externally installed tool. This avoids distributing the GPL worker from this project, reducing project-side distribution obligations; this is not a legal safe harbor, but minimizes distribution touchpoints.
  *Verdict: HIGH COMPLEXITY / UX BLOCKER.*

- **L5 — Permissive Alternatives**:
  - `esp_extractor` (Rust, MIT OR Apache-2.0, v0.8.1): Capable within its focused domain of string extraction and translation file application/writing, but general authoring and record coverage is much smaller than Mutagen.
  - `tes4py` (Python, BSD-2-Clause): A legacy parser targeting Oblivion (TES4); not a mature Skyrim SE/AE alternative.
  - *Verdict: Insufficient coverage for comprehensive plugin inspection/authoring.*

---

## License Decision Matrix

| Option | Linking / Transport | Distributed Together | Technical Separation | License-Compliance Complexity | Legal Determination | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| **L1** | Direct (in-process) | Yes | LOW | HIGH | GPL obligations apply to distribution | **REJECTED** |
| **L2** | JSON IPC over pipes | Yes | HIGH | MEDIUM | `LEGAL_REVIEW_REQUIRED` | **FEASIBLE WITH REVIEW** |
| **L3** | JSON IPC over pipes | No (separate repo) | HIGH | MEDIUM | `LEGAL_REVIEW_REQUIRED` | **TECHNICAL PREFERENCE** |
| **L4** | JSON IPC over pipes | No (user-provided) | HIGH | LOW | `LEGAL_REVIEW_REQUIRED` | **UX FALLBACK** |
| **L5** | Permissive library | N/A | N/A | LOW | Permissive (MIT/Apache) | **REJECTED (INCOMPLETE)** |

---

## Architecture options & Runtime Generalization

### Architecture Options Considered

1. **Option A: Direct .NET Worker Profile (Recommended Technical Model)**:
   The orchestrator spawns a trusted `.NET` worker binary directly via standard pipes. This maintains a single process boundary, eliminates nested subprocesses, and avoids lifecycle/timeout propagation issues.
2. **Option B: Python Worker + .NET Child Process**:
   Spawning a Python shim worker that spawns a .NET child process. Rejected due to nested process tree management, double timeout bookkeeping, and elevated risk of orphaned processes.

### Generalizing ADR-002 Worker Registry

ADR-002 currently defines worker execution in Python-specific terms. We propose extending the trusted worker registry with typed **Worker Launch Profiles**:

```python
class WorkerLaunchProfile:
    runtime_kind: str          # "python" | "dotnet" | "native"
    executable_path: str       # Configured absolute path to trusted host/binary
    args_template: list[str]   # Arguments list template (e.g. ["-I", "-B", "{entrypoint}"])
    entrypoint: str            # Absolute path to script or assembly
    environment_allowlist: list[str]
    cwd_policy: str
```

- For Python workers: `-I -B` flags remain strictly normative.
- For .NET workers: Direct invocation of the trusted host/binary without shell, deny-by-default environment, and workspace-relative redirection.
- **Protocol Version**: The wire schema (Request, Response, Receipt, Error) is language-agnostic. **Protocol Version 1** remains unchanged.

---

## Proposed POC-MUTAGEN-001 Scope

- **Status**: **BLOQUEADO** pending ADR-003 acceptance and legal review.
- **Operation**: `INSPECT_PLUGIN_HEADER` (read-only).
- **Runtime**: Out-of-process .NET worker.
- **Package Version**: `0.54.4` candidate (to be pinned via `packages.lock.json` after approval).
- **Target Framework**: TO BE DECIDED after supported-TFM and deployment packaging review.
- **Input**: Single file at `input/<plugin_name>` (safe-name token only).
- **Output**: `receipt.outputs == []` (candidate directory remains empty).
- **API Call**: `SkyrimMod.CreateFromBinaryOverlay(filePath, release)`.
- **Expected Metadata**:
  - `ModKey` (plugin identity)
  - `HeaderVersion`
  - `Flags` (ESM/ESL indicators)
  - `MasterFiles` (dependencies list)
  - `Author` and `Description` strings

---

## Fixture Strategy: EXPERIMENT REQUIRED

> [!IMPORTANT]
> POC-002's synthetic TES4 fixture is **not** a general valid Skyrim plugin generator and must not be assumed compatible with Mutagen.
> The fixture strategy for POC-MUTAGEN-001 is designated as **EXPERIMENT REQUIRED**.

Requirements for a future Mutagen test fixture:
1. Must be author-owned or generated via clean-room tooling;
2. Must be explicitly redistributable under the repository license;
3. Must document provenance and SHA-256 integrity hash;
4. Must be validated as parseable by Mutagen;
5. Must not use or distribute proprietary Bethesda master files (`Skyrim.esm`, DLCs, Creation Club content);
6. Must not claim that POC-002 synthetic tests prove Mutagen compatibility.

---

## Claims and Non-Claims

### Future Evidence Claims (if implemented)
- Demonstrates out-of-process .NET worker launch and execution under ADR-002 protocol v1.
- Demonstrates single-file overlay parsing of a controlled, non-Bethesda fixture.
- Demonstrates receipt generation and orchestrator-side verification without candidate writes.

### Explicit Non-Claims
- Does not demonstrate validity of arbitrary real-world Skyrim plugins.
- Does not demonstrate load order correctness, winning overrides, or LinkCache resolution.
- Does not demonstrate in-game, Creation Kit, or xEdit compatibility.
- Does not demonstrate OS-level sandboxing (`OS_SANDBOX` remains `NO VERIFICADO`).

---

## Recommendation & Legal Status

### Technical Preference
**L3 (Separately maintained GPL worker repository) + Option A (Direct typed IPC launch profile)**.

### Legal Authorization
**NOT GRANTED. Status: `LEGAL_REVIEW_REQUIRED`.**
Formal legal review must evaluate the distribution model (L2 vs. L3 vs. L4) before any productive or research packaging occurs.

---

## Acceptance Criteria for ADR-003

1. Complete review of the GNU GPL FAQ citations and separate-program boundaries.
2. Formal resolution of the distribution model (L2 vs L3).
3. Agreement on the Worker Launch Profile abstraction generalizing ADR-002.
4. Definition of a validated clean-room fixture strategy.
