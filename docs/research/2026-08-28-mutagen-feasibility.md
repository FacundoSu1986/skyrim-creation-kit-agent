# Mutagen Feasibility and External-Runtime Boundary

**PHASE:** 2 (Research & Feasibility)  
**STATUS:** `LEGAL_REVIEW_REQUIRED` / `ARCHITECTURE_REVIEW_REQUIRED`  
**DATE:** 2026-08-28

---

## 1. Executive Summary

This report evaluates the feasibility of integrating [Mutagen](https://github.com/Mutagen-Modding/Mutagen), a C#/.NET library for Bethesda plugin parsing, into the MIT-licensed `skyrim-creation-kit-agent` project. It addresses the licensing considerations (GPL-3.0 vs. MIT) and the runtime constraints imposed by ADR-002.

Key findings:
1. Mutagen is the strongest/mature candidate identified in this research for Bethesda plugin manipulation.
2. Direct linking (L1) likely makes GPL obligations relevant to distribution of the combined work.
3. Process separation via exec and pipes (L2/L3) is evidence in favor of separate-program treatment under GNU GPL guidance, but is not a legal safe harbor. Communication semantics and distribution packaging also matter.
4. Repository separation (L3) improves provenance and compliance, but does not itself decide whether programs form one combined work.
5. ADR-002's launch model can be extended via closed-world typed worker profiles (`PYTHON_ISOLATED_V1`, `DOTNET_MUTAGEN_READONLY_V1`) without altering wire Protocol Version 1 schemas or introducing generic command runners.
6. The legal determination remains `LEGAL_REVIEW_REQUIRED`.

---

## 2. Mutagen Facts

- **Official Repository**: [Mutagen-Modding/Mutagen](https://github.com/Mutagen-Modding/Mutagen)
- **License**: GPL-3.0-only (explicit LICENSE file in repository).
- **Candidate Stable Version**: `0.54.4` (candidate release to be pinned upon acceptance).
- **Active Prerelease Branch**: `0.55.0-alpha.7`.
- **Target Frameworks**: Official NuGet package `Mutagen.Bethesda.Skyrim` release `0.54.4` targets `net9.0` and `net10.0` (it does not target `net8.0`). Target runtime framework is **TO BE DECIDED** following deployment/packaging evaluation.
- **Platform Support**: Cross-platform (Windows, Linux, macOS) on supported .NET runtimes.
- **Single-File Read API**: 
  - **API Signature**: `public static SkyrimMod CreateFromBinaryOverlay(ModPath path, SkyrimRelease release, StringsReadParameters stringsParam = default)`
  - **Single-file read possible**: **YES**.
  - **Skyrim installation required**: **NO**.
  - **Steam / load order discovery avoidable**: **YES** (by avoiding `GameEnvironment.Typical`).

---

## 3. License Analysis & GNU GPL FAQ Guidance

The repository is MIT-licensed. Mutagen is licensed under GPL-3.0-only. MIT code is GPL-compatible, but distributing a combined work requires fulfilling GPL obligations.

### GNU GPL FAQ Citations

1. **[GPL FAQ #GPLPlugins](https://www.gnu.org/licenses/gpl-faq.html#GPLPlugins) (Separate vs. Combined Programs)**:
   > *"A main program that uses simple fork and exec to invoke plug-ins and does not establish intimate communication between them results in the plug-ins being separate programs."*
2. **[GPL FAQ #GPLInProprietarySystem](https://www.gnu.org/licenses/gpl-faq.html#GPLInProprietarySystem) (Pipes and Sockets)**:
   > *"Pipes, sockets and command-line arguments are the communication mechanisms normally used between two separate programs... But if the semantics of the communication are intimate enough, exchanging complex internal data structures, that too could be a basis to consider the two parts as combined into a larger program."*
3. **[GPL FAQ #MereAggregation](https://www.gnu.org/licenses/gpl-faq.html#MereAggregation) (Mere Aggregation)**:
   > *"An 'aggregate' consists of a number of separate programs, distributed on the same compilation or distribution medium... If the two programs remain well separated, like the compiler and the kernel, then it is an aggregate."*

### Analysis of Architectural Models (L1–L5)

#### L1 — Direct Linking (In-Process)
- Direct linking likely makes GPL obligations relevant to distribution of the combined work.
- *Verdict: REJECTED.*

#### L2 — External Process (Same Repository, Separate Binary)
- Uses JSON IPC over standard pipes. Process separation is evidence in favor of separate-program treatment, but is not a legal safe harbor. Distributing both together requires review under aggregation principles.
- *Verdict: LEGAL_REVIEW_REQUIRED.*

#### L3 — Separately Maintained GPL Adapter (Separate Repository)
- Maintains the GPL worker in an independent repository under GPL-3.0. Keeps the main MIT repository free of GPL source code, improving provenance. Distribution coupling must still be evaluated.
- *Verdict: TECHNICAL PREFERENCE / LEGAL_REVIEW_REQUIRED.*

#### L4 — User-Supplied Tool
- The orchestrator acts purely as a client to a user-provided or externally installed tool. Avoids distributing the GPL worker from this project, reducing project-side distribution obligations; this is not a legal safe harbor.
- *Verdict: UX BLOCKER / HIGH COMPLEXITY.*

#### L5 — Permissive Alternatives
- `esp_extractor` (Rust, MIT OR Apache-2.0, v0.8.1): Capable within its translation and string extraction domain (with writing/applying capabilities for translations), but has a much smaller general authoring/record scope than Mutagen.
- `tes4py` (Python, BSD-2-Clause): Legacy Oblivion parser; not a mature Skyrim SE/AE alternative.
- *Verdict: Incomplete coverage for general plugin authoring.*

---

## 4. License Matrix

| Option | Linking / Transport | Distributed Together | Technical Separation | License-Compliance Complexity | Legal Determination | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| **L1** | Direct (in-process) | Yes | LOW | HIGH | GPL obligations apply to distribution | **REJECTED** |
| **L2** | JSON IPC over pipes | Yes | HIGH | MEDIUM | `LEGAL_REVIEW_REQUIRED` | **FEASIBLE WITH REVIEW** |
| **L3** | JSON IPC over pipes | No (separate repo) | HIGH | MEDIUM | `LEGAL_REVIEW_REQUIRED` | **TECHNICAL PREFERENCE** |
| **L4** | JSON IPC over pipes | No (user-provided) | HIGH | LOW | `LEGAL_REVIEW_REQUIRED` | **UX FALLBACK** |
| **L5** | Permissive library | N/A | N/A | LOW | Permissive (MIT/Apache) | **REJECTED (INCOMPLETE)** |

---

## 5. Architectural Generalization of ADR-002

ADR-002 currently specifies a Python command line (`python -I -B`). To support non-Python workers without introducing generic command execution, the model uses closed-world typed worker profiles:

- `PYTHON_ISOLATED_V1`: Deterministic `<trusted absolute python> -I -B <trusted worker entry> --job-root <derived absolute job dir>`.
- `DOTNET_MUTAGEN_READONLY_V1`: Deterministic trusted `.NET` host or self-contained binary execution without shell, deny-by-default environment, and fixed operation set (`INSPECT_PLUGIN_HEADER`).
- Wire schemas, error taxonomy, and correlation rules remain **Protocol Version 1**.
- Generic command execution (`RUN_TOOL`, `EXECUTE_COMMAND`, dynamic `argv` templates) is strictly forbidden.

---

## 6. Ambient Host State Contract (No Overclaim)

The Mutagen worker contract strictly forbids intentional interaction with ambient Steam files, Skyrim Data directories, or the Windows registry. This is an application-level contract between cooperating components, not an OS sandbox (`OS_SANDBOX` remains `NO VERIFICADO`).

---

## 7. Proposed POC-MUTAGEN-001 Design

- **Operation**: `INSPECT_PLUGIN_HEADER` (Read-only)
- **Profile**: `DOTNET_MUTAGEN_READONLY_V1`
- **Candidate Package Version**: `0.54.4` (to be locked via `packages.lock.json`).
- **Target Framework**: TO BE DECIDED after supported-TFM/deployment review.
- **Transitive License Inventory**: `NOT YET RECORDED (PENDING DEPENDENCY REVIEW)`.
- **Inputs**: `input/<plugin_name>` (safe-name token only).
- **Outputs**: `[]` (no candidate writes).
- **Fixture Strategy**: **EXPERIMENT REQUIRED**. Requires an author-owned, redistributable clean-room fixture with documented provenance. POC-002 synthetic fixture cannot be assumed compatible.

---

## 8. External Source Record

- **TITLE**: Mutagen Release 0.54.4
  - **PUBLISHER**: Mutagen-Modding
  - **URL**: https://github.com/Mutagen-Modding/Mutagen/tree/0.54.4
  - **VERSION**: 0.54.4
  - **COMMIT**: 0188012c607ce8bb283d2704400d37737f089134
  - **DATE ACCESSED**: 2026-08-28
  - **CLAIM SUPPORTED**: GPL-3.0 license, `0.54.4` release, `CreateFromBinaryOverlay` signature, supported TFMs (net9.0, net10.0).

- **TITLE**: GNU General Public License Frequently Asked Questions
  - **PUBLISHER**: Free Software Foundation (FSF)
  - **URL**: https://www.gnu.org/licenses/gpl-faq.html
  - **DATE ACCESSED**: 2026-08-28
  - **CLAIM SUPPORTED**: GPL guidance on plug-ins (#GPLPlugins), pipes/sockets (#GPLInProprietarySystem), and mere aggregation (#MereAggregation).

- **TITLE**: esp_extractor Crate Documentation
  - **PUBLISHER**: Orcax-1399 (crates.io)
  - **URL**: https://crates.io/crates/esp_extractor/0.8.1
  - **DATE ACCESSED**: 2026-08-28
  - **CLAIM SUPPORTED**: Version 0.8.1, MIT OR Apache-2.0 license, translation application capability.
