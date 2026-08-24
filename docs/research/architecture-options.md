# Architecture options

**PHASE:** 3  
**STATUS:** Compared. Not implemented. No ADR filed yet — that is the next step, not this document claiming a finished design.

## Scoring

Each axis is 1–10, **higher is better** (including simplicity, safer deps, and lower corruption risk).

Weights:

- robustness 15
- security 15
- testability 12
- low corruption 12
- maintainability 10
- license fit 10
- automation 8
- compatibility 6
- performance 5
- simplicity 4
- external deps 3

Reported score = weighted sum / 10, rounded.

## Matrix

| Option | Name | Score | Recommendation |
| --- | --- | --- | --- |
| A | Pure vision agent | 30 | `DESCARTADO` as spine |
| B | UI Automation of CK | 47 | Fallback only after POC-001 |
| C | CKPE in-process bridge | 39 | Research track; legally blocked for MVP |
| D | Headless-first | **82** | Best isolated score; primary backend |
| E | Hybrid orchestrator | 74 | **Recommended product shape** |

D wins the number. E is recommended because it **contains D** and can later name CK-exclusive work without lying that headless coverage is complete.

## Option notes

**A — Vision.** LLM + screenshot + mouse. Fastest path to a corrupted plugin. DPI, localization, modals. Forbidden as primary.

**B — UIA.** Structured tools, no coordinates. Unknown whether CK exposes useful controls. FlaUI/pywinauto only after Inspect.exe.

**C — CKPE plugin.** Highest ceiling for true editor operations. Empty `QueryInterface`, EULA reverse-engineering clause, winhttp proxy. Not MVP.

**D — Headless.** Mutagen/esper + PapyrusCompiler + xEdit + Spriggit. Testable. Already proven by houseCARL and Synthesis. Incomplete for FaceGen/navmesh/Render Window.

**E — Hybrid.** Planner emits typed operations. Router selects D first, allowlisted xEdit second, CK last. HITL and candidate workspace on every write. This is the only option that matches the brief without pretending CK is the spine.

## Responsibilities (not a folder tree yet)

Do not create `src/agent` now. When an ADR authorizes code:

- planner / domain / validation stay license-clean if possible
- mutagen or esper worker is isolated
- papyrus / xedit adapters are subprocesses
- ui_automation is optional and off
- creation_kit is a capability with its own state machine **if** POC-001 warrants it

## Transaction

```
INPUT → SNAPSHOT → PLAN → VALIDATE PLAN → EXECUTE ON CANDIDATE
→ SAVE → STATIC VALIDATION → DIFF → HITL → COMMIT
```

Never edit the only copy.
