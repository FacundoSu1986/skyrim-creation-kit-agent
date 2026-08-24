# Capability matrix

Imported from the structured research archive and normalized to the current repository status.

| Capability | Milestone | Status | Preferred backend | Risk | Notes |
| --- | --- | --- | --- | --- | --- |
| Read plugin header / masters / hashes | MVP | POC-002 synthetic path verified | TES4 parser; future Mutagen | Low | No real game plugins as fixtures |
| List records / find by EditorID | MVP | Research — backend exists | Mutagen overlay | Low | Prefer EditorID over raw FormID |
| Create miscellaneous item | MVP candidate | Not implemented here | Mutagen write or dedicated writer POC | Low | Smallest honest write POC |
| Create actor base | V1 | Research — FaceGen gap | Mutagen write; CK for FaceGen | Medium | NPC record alone does not prove correct appearance |
| Create quest / stages | Not MVP | Experimental elsewhere | Mutagen / esper | High | Data-layer feasibility ≠ semantic correctness |
| Compile Papyrus | V1 | `NO VERIFICADO` here | Official PapyrusCompiler.exe | Low | Explicit args, timeout, reject stale PEX |
| Static plugin validation | MVP | Research — backend exists | xEdit / analyzers | Low | Static pass ≠ in-game behavior |
| CK window inspect | Milestone 1 | `NO VERIFICADO` | UIA / Inspect.exe | Medium | POC-001, read-only |
| CK UI write | Fallback only | Unsupported until POC-001 | UIA | High | Coordinate clicks forbidden |
| CKPE in-process bridge | Long-term research | `LEGAL_REVIEW_REQUIRED` | CKPE PluginAPI | Critical | Not MVP |
| Render Window | Out of scope | Unsupported | CK GUI | Critical | No headless equivalent verified |
| Navmesh | Out of scope | Unsupported | CK GUI | Critical | Do not automate without new evidence |
| Worldspace / landscape | Out of scope | Unsupported | CK GUI | Critical | Stop criterion |
