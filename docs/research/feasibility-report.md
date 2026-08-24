# Feasibility report

**PHASE:** Gate 1  
**STATUS:** Complete for research. Implementation of the agent product is **not** authorized.

## Verdict

```
VIABLE WITH LIMITATIONS
```

A safe, reproducible automation **layer** is viable if and only if it is **headless-first**. Record-level create/edit, Papyrus compilation, and static validation already have real backends (Mutagen, official `PapyrusCompiler.exe`, xEdit).

Creation Kit does **not** expose a supported authoring API. CKPE’s plugin host exists but currently offers **no high-level Editor interfaces** and collides with the CK EULA reverse-engineering clause. UI Automation of CK is **untested**. The product sketched in the brief already exists in substantial form (houseCARL, SkyrimForge, SkyrimCK-MCP).

Therefore the work is viable as a **differentiated, license-clean orchestrator with a brutal capability matrix** — not as “an agent that drives Creation Kit”.

This environment did not run CK, xEdit, or PapyrusCompiler. Those runtime claims remain `NO VERIFICADO`.

## Required closing fields

```
Recommended architecture: Option E (hybrid) with Option D as the primary route
Primary backend:          Mutagen worker (GPL process) or esper if LICENSE confirms
Fallback backend:         Allowlisted xEdit -script -autoexit; UIA only after POC-001
Highest technical risk:   Loadable but semantically wrong plugins (VMAD, SEQ, FaceGen, aliases)
Highest legal risk:       CKPE / reverse-engineering vs EULA §1.C; Bethesda asset redistribution
First experiment:         POC-002 synthetic TES4 header parse; POC-001 designed for Windows
MVP candidate:            NL → ModPlan → one typed write → candidate plugin → validate → HITL
```

## Gate 1 answers

| Question | Status | Answer |
| --- | --- | --- |
| Does CK expose sufficient interfaces? | VERIFICADO | No official authoring API. FO4 batch flags are not an SSE create-record CLI. |
| Does UIA detect useful CK controls? | NO VERIFICADO | Not tested. POC-001 required. |
| Does CKPE offer a viable plugin path? | LEGAL_REVIEW_REQUIRED | DLL can load; QueryInterface empty; EULA overlay. |
| Which operations can avoid CK? | VERIFICADO | Most record I/O, Papyrus compile, static validation, diffs. |
| Which licenses shape architecture? | VERIFICADO | CK EULA, Mutagen GPL-3.0-only, xEdit MPL execute-not-vendor, no Bethesda fixtures. |
| First reproducible PoC? | HIPÓTESIS | POC-002 here; POC-001 on a Windows runner. |
| How do we avoid corruption? | VERIFICADO | Candidates only, hashes, fail-fast, typed ops, no shell. |
| How do we rollback? | VERIFICADO | Discard candidate. Never overwrite originals. |
| How do we validate? | VERIFICADO | Plan schema → receipt → reopen → optional xEdit → HITL → later in-game. |

## What this phase did not do

- Did not run Creation Kit, xEdit, PapyrusCompiler, Inspect.exe, or CKPE
- Did not download unverified binaries
- Did not modify game files
- Did not implement adapters, planners, or click automation
- Did not invent compiler flags, CK APIs, or test results

## Recommendation

Do **not** pass into product implementation.

Authorize only:

1. **ADR-001** — hybrid headless-first + license split
2. **POC-002** — synthetic header parse, no Bethesda fixtures
3. A written **POC-001** protocol for a future Windows runner
4. Keep this desk updated when a status label changes

If those pass, Milestone 1 is still an inspector, not a quest generator.

## Next single unit of work

Write ADR-001. Then execute POC-002. Nothing else.
