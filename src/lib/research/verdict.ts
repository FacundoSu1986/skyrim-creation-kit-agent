export const verdictRow = {
  verdict: "VIABLE WITH LIMITATIONS",
  rationale:
    "A safe, reproducible automation layer is viable if and only if it is headless-first. Record-level create/edit, Papyrus compilation, and static validation already have real backends (Mutagen, official PapyrusCompiler, xEdit). Creation Kit does not expose a supported authoring API. CKPE's plugin host exists but currently offers no high-level Editor interfaces and collides with the CK EULA reverse-engineering clause. UI Automation of CK is untested. The product sketched in the brief already exists in substantial form (houseCARL, SkyrimForge, SkyrimCK-MCP). Therefore the work is viable as a differentiated, license-clean orchestrator with a brutal capability matrix — not as 'an agent that drives Creation Kit'. This environment did not run CK, xEdit, or PapyrusCompiler; those runtime claims remain unverified.",
  recommendedArchitecture:
    "Option E — hybrid orchestrator whose primary path is Option D (headless). CK is a capability, not the spine. No vision bot. No CKPE plugin in MVP.",
  primaryBackend:
    "Mutagen worker (GPL-3.0 process) or, if EXP-ESPER-LICENSE passes, a permissively licensed parser for a MIT core. Planner/HITL stay license-clean and never emit clicks.",
  fallbackBackend:
    "Allowlisted xEdit scripts with -autoexit and completion markers. Coordinate-free UIA only after POC-001, only for CK-exclusive dialogs, disabled by default.",
  highestTechnicalRisk:
    "Semantic incorrectness that still produces a loadable plugin: unbound VMAD properties, missing SEQ, grey-face NPCs, quest aliases that never fill, FormID collisions, header 1.71 mismatches. Second: assuming CK controls are automatable.",
  highestLegalRisk:
    "In-process CKPE/reverse-engineering versus Creation Kit EULA §1.C, plus accidental redistribution of Bethesda compilers, headers, or plugins. Mutagen GPL is a product-license constraint, not a Bethesda issue.",
  firstExperiment:
    "POC-002 synthetic TES4 header parse in a workspace (can run without CK). In parallel, design-only POC-001 for a future Windows runner. Do not write a quest. Do not click.",
  mvpCandidate:
    "Natural language → validated ModPlan → one supported write (create MISC item or inspect+clone a workspace record) → candidate plugin in workspace/candidates → reopen + hash + optional xEdit error check → human approval. Never touch live Data.",
  nextStep:
    "ADR-001 (hybrid headless-first) is PROPOSED and awaits owner acceptance. POC-002 already passed its synthetic-fixture gate (43/43 tests, E2 evidence). Next executable units keep canonical numbering: POC-003 (PapyrusCompiler dry-invoke) and POC-004 (allowlisted xEdit validator). Isolated-worker IPC work continues under ADR-002 / POC-IPC identifiers, not POC-003.",
};
