# Mutagen Feasibility and External-Runtime Boundary

**PHASE:** 2 (Research & Feasibility)  
**STATUS:** `LEGAL_REVIEW_REQUIRED` / `ARCHITECTURE_REVIEW_REQUIRED`  
**DATE:** 2026-08-28

---

## 1. Executive Summary

This report evaluates the feasibility of integrating [Mutagen](https://github.com/Mutagen-Modding/Mutagen), a C#/.NET library for Bethesda mod parsing, into the MIT-licensed `skyrim-creation-kit-agent` project. It addresses the licensing conflict (GPL-3.0 vs MIT) and the runtime constraints imposed by ADR-002.

We conclude that:
1. Mutagen is the only mature, actively maintained library for complete Skyrim SE/AE plugin manipulation.
2. Direct linking (L1) violates the project's MIT license constraints.
3. Separation via standard JSON-IPC pipes (L2/L3) creates a valid legal and architectural boundary, but requires generalizing the worker runtime model defined in ADR-002.
4. Formal legal review is required before proceeding to implementation.

---

## 2. Mutagen Facts

- **Official Repository**: [Mutagen-Modding/Mutagen](https://github.com/Mutagen-Modding/Mutagen)
- **License**: GPL-3.0-only (GPL-3.0 header and LICENSE file in repo).
- **NuGet Packages**:
  - `Mutagen.Bethesda` (Core package)
  - `Mutagen.Bethesda.Skyrim` (Skyrim-specific classes)
  - Latest version: `0.55.0-alpha.7` / stable `0.54.0` (as of NuGet release history).
- **Target Frameworks**: `.NET 9.0` (latest releases target `net9.0`).
- **Platform Support**: Cross-platform (Windows, Linux, macOS) via standard .NET Core runtimes.
- **Single-File Read API**: 
  - **API Signature**: `public static SkyrimMod CreateFromBinaryOverlay(ModPath path, SkyrimRelease release, StringsReadParameters stringsParam = default)`
  - **Single-file read possible**: **YES**. Bypasses environment auto-discovery.
  - **Skyrim installation required**: **NO**.
  - **Steam discovery avoidable**: **YES**, when loading via overlay without invoking `GameEnvironment.Typical`.

---

## 3. License Analysis

### License Architectures (L1-L5)

#### L1 — Link Directo
- **Description**: MIT application references NuGet Mutagen (GPL) directly in the same compiled binary.
- **Result**: GPL copyleft applies to the entire project. The project cannot be distributed under MIT.
- **Verdict**: **REJECTED**.

#### L2 — Proceso Externo (Same Repo, Separate Binary)
- **Description**: The orchestrator is MIT; the worker is a separate GPL-3.0 executable running via stdin/stdout JSON IPC.
- **Result**: Permitted under GPL guidelines since communication uses standard pipes and a simple format. However, shipping them together under a single installer/package is high-risk for copyleft contamination claims.
- **Verdict**: **ACCEPTED WITH CAUTION**.

#### L3 — GPL Adapter Separado (Separate Repo)
- **Description**: The Mutagen worker is maintained in a completely separate GitHub repository under GPL-3.0. The main repo has zero GPL code.
- **Result**: Clean legal boundary. No risk of source contamination.
- **Verdict**: **RECOMMENDED**.

#### L4 — User-Supplied Tool
- **Description**: The agent does not bundle the worker. The user must provide it.
- **Result**: Eliminates distribution liability completely.
- **Verdict**: **UX BLOCKER**.

#### L5 — Permissive Alternative
- **Description**: Use `esp_extractor` (Rust, MIT/Apache) or `tes4py` (Python, BSD-2-Clause).
- **Result**: Incomplete feature set (no write support, immature APIs).
- **Verdict**: **REJECTED**.

---

## 4. Architectural Analysis & ADR-002 Generalization

ADR-002 currently defines the launch command as strictly Python (`python -I -B`). Implementing a C# worker directly contradicts ADR-002.

### Generalization Proposal
We propose generalizing the trusted worker registry to support multiple launch profiles (e.g. `dotnet` runtime host or native binary hosts) while preserving the security boundaries (no shell, absolute paths, deny-by-default environment). The wire JSON protocol remains v1.

---

## 5. Proposed POC-MUTAGEN-001 Design

- **Operation**: `INSPECT_PLUGIN_HEADER` (Read-only)
- **Runtime**: .NET 9.0 worker.
- **Inputs**: `input/<plugin_name>` (safe-name token).
- **Outputs**: `[]` (no candidate writes).
- **Assertions**: Non-vacuous check on Magic Number, FormVersion, and Master references.
- **Fixture Strategy**: Synthetic plugin generated programmatically (e.g., via POC-002 synthetic generator) to avoid licensing issues with Bethesda assets.

---

## 6. External Source Record

- **TITLE**: Mutagen GitHub Repository
  - **PUBLISHER**: Mutagen-Modding
  - **URL**: https://github.com/Mutagen-Modding/Mutagen
  - **DATE ACCESSED**: 2026-08-28
  - **CLAIM SUPPORTED**: GPL-3.0 license, .NET 9.0 target, `CreateFromBinaryOverlay` availability.

- **TITLE**: NuGet Gallery Mutagen.Bethesda
  - **PUBLISHER**: Noggog (NuGet Profile)
  - **URL**: https://www.nuget.org/packages/Mutagen.Bethesda/
  - **DATE ACCESSED**: 2026-08-28
  - **CLAIM SUPPORTED**: Latest version and dependency license metadata.
