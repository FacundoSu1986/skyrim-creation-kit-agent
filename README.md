# Skyrim Creation Kit Agent

Safety-first research and engineering for AI-assisted Skyrim Special Edition / Anniversary Edition authoring.

> **Current status:** research + validated synthetic proof of concept. This repository is **not yet a general-purpose mod authoring agent** and does not currently automate Creation Kit.

## Core principle

> **AI decides WHAT.**  
> **Deterministic software decides HOW.**  
> **Validators decide WHETHER IT WORKED.**  
> **A human decides WHETHER TO ACCEPT.**

The project converts high-level modding intent into typed, reversible, evidence-backed operations. The target product is a hybrid orchestrator whose primary path is headless and deterministic; Creation Kit is treated as a narrow capability, not the spine of the system.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `VERIFIED` | Supported by direct evidence or a reproducible test |
| `NO_VERIFICADO` | Plausible or documented elsewhere, but not reproduced here |
| `HIPOTESIS` | Proposed experiment or design claim |
| `EXPERIMENTAL` | Implemented only as an experiment |
| `BLOQUEADO` | Cannot currently proceed in the available environment |
| `DESCARTADO` | Explicitly rejected for the intended architecture |
| `LEGAL_REVIEW_REQUIRED` | Technical path exists, but licensing/EULA implications are unresolved |

## Repository map

```text
docs/
  adr/                     Architecture decisions
  research/                Gate-1 research archive
research/
  poc_002/                 Validated synthetic TES4 inspection POC
src/                       Discovery Desk research UI (Next.js) — see below; NOT the agent runtime
.github/workflows/          Reproducible validation
```

## Discovery Desk research UI

This repository originated as a "Discovery Desk" research snapshot and still contains a
small Next.js + Drizzle/PostgreSQL research app. It is **preserved**, with clear boundaries:

- `src/app/`, `src/db/`, and `src/lib/research/` belong to the **Discovery Desk / research UI**.
- They are **not** the runtime of the future authoring agent and must not be promoted into product code.

Development requires `DATABASE_URL` (see [`.env.example`](.env.example); the checked-in value is a
loopback development fixture, not a secret). Note that `next build` needs the variable to *exist*,
because `src/db/index.ts` fails fast at import time while Next.js collects page data; the build
itself never opens a database connection (the `pg` pool is lazy), so no live PostgreSQL server is
required for CI. `drizzle.config.json` intentionally carries the same loopback fixture for the
drizzle-kit CLI.

## Current architecture decision

The recommended product shape is **hybrid orchestrator + headless-first primary path**:

```text
User intent
   ↓
Intent normalizer
   ↓
Planner / LLM
   ↓
Typed ModPlan
   ↓
Policy / safety engine
   ↓
Capability router
   ├─ Headless plugin worker
   ├─ Papyrus worker
   ├─ xEdit validator
   └─ Creation Kit worker [disabled until independently verified]
   ↓
Candidate workspace
   ↓
Validator
   ↓
Human approval
```

The planner may decide **what** operation is desired. It must not receive an arbitrary shell, click, or generic command primitive.

See [`docs/adr/ADR-001-hybrid-headless-first-architecture.md`](docs/adr/ADR-001-hybrid-headless-first-architecture.md).

## Validated implementation: POC-002

`research/poc_002/` is the first executable proof:

- synthetic TES4 fixture only;
- strict parser;
- HEDR `1.70` fixture and FormVersion `44`;
- closed operation enum;
- truthful capability registry (`INSPECT_HEADER` only);
- candidate-only workspace with path containment;
- fail-closed orchestration;
- no-overwrite receipts;
- SHA-256 invariant for the original;
- **43 automated tests**.

Run it:

```bash
cd research/poc_002
python -m compileall .
python -m unittest test_suite.py -v
```

Expected result:

```text
Ran 43 tests
OK
```

POC-002 does **not** prove compatibility with arbitrary real Skyrim plugins, Creation Kit runtime behavior, xEdit, PapyrusCompiler, Mutagen, or in-game correctness.

## Research verdict

Current Gate-1 verdict:

```text
VIABLE WITH LIMITATIONS
```

Most record-level operations can plausibly avoid Creation Kit, but several CK-exclusive or high-risk areas remain unresolved: FaceGen, navmesh, Render Window placement, lip generation, some complex quest/alias semantics, and runtime semantic correctness.

The research archive is under [`docs/research/`](docs/research/).

## Experiment roadmap

| Unit | Purpose | Current status |
| --- | --- | --- |
| POC-001 | Read-only Creation Kit UIA/MSAA inspection on Windows | `BLOQUEADO` here; designed, not executed |
| POC-002 | Synthetic TES4 header parse + safety pipeline | **PASS** |
| POC-003 | PapyrusCompiler dry-invoke | `NO_VERIFICADO` / not started |
| POC-004 | Allowlisted xEdit `-script -autoexit` validation | `NO_VERIFICADO` / not started |
| EXP-CK-CLI | Verify actual Creation Kit command-line behavior | `NO_VERIFICADO` |
| EXP-ESPER-LICENSE | Confirm C# esper licensing | `LEGAL_REVIEW_REQUIRED` |
| EXP-CKPE-QIFACE | Inspect CKPE interfaces after legal clearance | `HIPOTESIS` |

**Important:** subprocess IPC hardening is architectural work, but it is **not** canonical POC-003. Use an ADR or a separate `POC-IPC` identifier if continued. Previously reviewed exploratory IPC prototypes remain `CHANGES_REQUIRED` — **not accepted**, and intentionally not imported as passing implementation.

## Safety rules

- Never modify a user's only copy of a plugin.
- Originals are immutable inputs; writes go to candidates.
- No arbitrary shell command in an AI-generated plan.
- No coordinate-click GUI automation as the primary path.
- Missing completion evidence is failure, not success.
- Never commit Bethesda game/editor binaries, vanilla plugins, or vanilla Papyrus sources.
- Process isolation is a technical boundary, **not** an automatic licensing conclusion.

## Licensing

Repository-authored core code is MIT licensed. That MIT grant covers original repository code only; it does **not** relicence external components, which retain their own licenses and obligations:

- **Mutagen / Synthesis / Spriggit** — GPL-3.0-only. Any component linking them inherits copyleft obligations.
- **xEdit** — MPL-2.0 upstream; intended for external execution of a user install, never vendored or bundled.
- **CKPE** — LGPLv3 code plus a Creation Kit EULA/legal overlay; remains `LEGAL_REVIEW_REQUIRED`.
- **Creation Kit, PapyrusCompiler, vanilla `.psc`, Skyrim assets** — proprietary user-installed components; never redistributed or committed.

Process isolation is an architectural boundary, not an automatic licensing conclusion.

See [`docs/research/licensing.md`](docs/research/licensing.md).

## Relationship to Sky-Claw

This is a **separate repository and research track**. It may later integrate with Sky-Claw through a documented protocol, but it must remain independently testable and must not assume Sky-Claw internals as its safety boundary.

## Disclaimer

This project is unaffiliated with Bethesda Game Studios, ZeniMax Media, Valve, Nexus Mods, or the authors of the third-party tools discussed in the research archive.
