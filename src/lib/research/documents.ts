export const documentRows = [
  {
    slug: "problem-definition",
    title: "Problem definition",
    phase: "Phase 0",
    summary:
      "What we are actually trying to automate, who it is for, and which operations belong in an MVP versus a stop list.",
    sortOrder: 1,
  },
  {
    slug: "creation-kit-analysis",
    title: "Creation Kit analysis",
    phase: "Phase 1",
    summary:
      "What the official editor is, what it is not, versions, plugin format, and the absence of a public authoring API.",
    sortOrder: 2,
  },
  {
    slug: "automation-options",
    title: "Automation options",
    phase: "Phase 1",
    summary:
      "Headless libraries, compilers, xEdit, UI Automation, vision, and CKPE — ranked by determinism, not convenience.",
    sortOrder: 3,
  },
  {
    slug: "existing-projects",
    title: "Existing projects",
    phase: "Phase 1",
    summary:
      "Prior art. The brief's product already exists in pieces. Copying any of them would be a failure of research.",
    sortOrder: 4,
  },
  {
    slug: "licensing",
    title: "Licensing and legal audit",
    phase: "Phase 2",
    summary:
      "Execute versus link versus distribute. CK EULA, Mutagen GPL, CKPE LGPL overlay, and fixture rules.",
    sortOrder: 5,
  },
  {
    slug: "threat-model-preliminary",
    title: "Preliminary threat model",
    phase: "Phase 5 preview",
    summary:
      "File corruption, agent hallucination, hung processes, and classic injection/path issues — with concrete mitigations.",
    sortOrder: 6,
  },
  {
    slug: "architecture-options",
    title: "Architecture options",
    phase: "Phase 3",
    summary:
      "Five architectures scored with explicit weights. Hybrid recommended; headless wins the numeric matrix.",
    sortOrder: 7,
  },
  {
    slug: "feasibility-report",
    title: "Feasibility report",
    phase: "Gate 1",
    summary:
      "Verdict, remaining unknowns, and the single next unit of work. Implementation of the agent product is not authorized.",
    sortOrder: 8,
  },
];

export const documentSectionRows = [
  {
    documentSlug: "problem-definition",
    heading: "Principal problem",
    status: "VERIFICADO",
    sortOrder: 1,
    body: `The problem is not "drive Creation Kit with an AI". The problem is: convert a high-level, often ambiguous modding intent into a sequence of typed, reversible, evidence-backed operations against Skyrim SE/AE plugin data and the few tools that can legally and correctly mutate that data.

A sentence such as "create a quest where an NPC in Whiterun gives a mission after level 20" decomposes into many heterogeneous acts: a base actor, a placed reference, a quest, stages, aliases, conditions, dialogue, possibly Papyrus, possibly AI packages, and a FaceGen export if the NPC must not be grey-faced. Some of those acts are binary record edits. Some are compiler invocations. Some are still exclusive to the official editor. Treating them as one GUI script is how plugins get corrupted.

This research therefore reframes the product as a capability router with a human approval gate, not as a Creation Kit puppeteer.`,
  },
  {
    documentSlug: "problem-definition",
    heading: "Intended users",
    status: "HIPOTESIS",
    sortOrder: 2,
    body: `Likely users, not yet validated by interviews:

• Beginner modders who can describe content but cannot operate CK safely.
• Advanced modders who want batch, reviewable edits and diffs.
• Tool authors who need a stable adapter (the brief mentions Sky-Claw; no such CK project was found).
• Autonomous agents that must be denied arbitrary shell and arbitrary clicks.
• Accessibility users — SkyrimCK-MCP already exists specifically because CK is unusable with screen readers.
• Researchers studying whether editor automation is even honest.

The first user of any write path must be the author of this system, on throwaway candidate plugins, never on a live load order.`,
  },
  {
    documentSlug: "problem-definition",
    heading: "What we refuse to call the product",
    status: "VERIFICADO",
    sortOrder: 3,
    body: `This is not a replacement for Creation Kit. It is not a complete editor. It is not a click bot. It is not a magical mod generator. It is not affiliated with Bethesda, ZeniMax, Steam, or Nexus.

If a future README claims "creates quests automatically" before quest contract tests exist, that README is false. Status badges are forbidden until a measured backend exists.`,
  },
  {
    documentSlug: "problem-definition",
    heading: "MVP versus stop list",
    status: "VERIFICADO",
    sortOrder: 4,
    body: `MVP is a single supported write on a candidate plugin plus validation and HITL. The preferred first write is a MISC item or a header-only inspect — not a quest.

Out of scope until a later gate: Render Window, navmesh, worldspace, landscape, master-file surgery, FormID compaction of foreign mods, in-place edits of the user's only copy, arbitrary Pascal, arbitrary PowerShell, CKPE injection.

Stop if an implementation depends on an invented API, cannot rollback, cannot verify the operation, requires fixed mouse coordinates, or redistributes Bethesda binaries.`,
  },
  {
    documentSlug: "creation-kit-analysis",
    heading: "What Creation Kit is",
    status: "VERIFICADO",
    sortOrder: 1,
    body: `Creation Kit (historically Construction Set) is Bethesda's official Windows editor for viewing and editing game data. SSE CK is distributed on Steam as app 1946180 and must live beside the game. Community-confirmed current version: 1.6.1378.1 (Steam thread 2025-02-23). CKPE's table marks 1.5.73.0, 1.6.1130.0, and 1.6.1378.1 as Active.

The editor loads master files (Skyrim.esm and DLCs) and plugins. Only one plugin is the active file; saves write that file. Multiple masters require INI flags (bAllowMultipleMasterLoads). Papyrus compilation is invoked as a child process. There is a Render Window, Object Window, Cell View, and a large set of modal record editors.

None of this is an API. It is a desktop application.`,
  },
  {
    documentSlug: "creation-kit-analysis",
    heading: "Plugin format the editor consumes",
    status: "VERIFICADO",
    sortOrder: 2,
    body: `UESP documents the binary layout: TES4 header, GRUP groups, records with type/size/flags/FormID/version, and typed fields. SSE record version is 44. ESL (light) plugins arrived with SSE 1.5 and use flag 0x00000200. After game/CK 1.6.1130, plugins often use header 1.71; older CK without CKPE cannot read them.

ESL FormID space is limited (community-known light-plugin constraints). EditorIDs are the stable handle agents should prefer; FormIDs are load-order sensitive once masters shift.

This format is independently implemented by Mutagen, xEdit, and esper. That is why headless authoring is possible at all.`,
  },
  {
    documentSlug: "creation-kit-analysis",
    heading: "Interfaces that were not found",
    status: "VERIFICADO",
    sortOrder: 3,
    body: `Searched and not found as official SSE authoring surfaces:

• A public Creation Kit SDK or PluginAPI from Bethesda
• A documented RPC or object-model for creating NPC_/QUST from code
• A general CLI such as CreationKit.exe create-actor
• Official UI Automation support or AutomationId conventions

Found, but out of scope or non-general:

• Fallout 4 batch flags (-GeneratePrecombined, -GeneratePreVisData, -BuildCDX, -CompressPSG)
• PapyrusCompiler.exe CLI (a compiler, not an editor)
• Archive.exe / BSArch for BSA
• CKPE's third-party loader

HIPÓTESIS: SSE CK may have undocumented switches. EXP-CK-CLI must prove them. Until then, product code must not mention invented flags.`,
  },
  {
    documentSlug: "creation-kit-analysis",
    heading: "CKPE in one paragraph",
    status: "VERIFICADO",
    sortOrder: 4,
    body: `CKPE (perchik71) is a community platform that patches CK for speed, Unicode, UI, and plugin-header compatibility. License LGPLv3 since v0.6. Plugins are C++ DLLs in CKPEPlugins exporting CKPEPlugin_Version and CKPEPlugin_Load. The wiki states QueryInterface returns nothing useful and no interfaces are implemented. The author says you need C/C++, x64 ASM, and reverse engineering. Loading uses a winhttp.dll proxy. That is enough to classify CKPE as a research track, not an MVP backend.`,
  },
  {
    documentSlug: "automation-options",
    heading: "Headless-first rule",
    status: "VERIFICADO",
    sortOrder: 1,
    body: `Before any GUI automation, ask: can this be done with a structured file format, a library, a CLI, or a deterministic tool?

Yes, for most record edits → Mutagen (or esper if licensed).
Yes, for compile → PapyrusCompiler.exe.
Yes, for conflict/error reports → xEdit.
Yes, for text diffs → Spriggit.
No, for FaceGen, navmesh, Render Window, lip generation → CK, later, with HITL.

This rule is not aesthetic. Headless paths are testable on CI without redistributing CK. GUI paths are not.`,
  },
  {
    documentSlug: "automation-options",
    heading: "Windows UI Automation",
    status: "NO VERIFICADO",
    sortOrder: 2,
    body: `Microsoft UIA + MSAA can expose native controls. Inspect.exe / Accessibility Insights are the correct first instruments. FlaUI (MIT, active 2025) is the preferred .NET wrapper. pywinauto can use backend="uia". WinAppDriver is abandoned and DESCARTADO.

Whether CK's Object Window, record tabs, and Render Window appear as usable AutomationIds is unknown. Many native editors expose only the outer frame. SkyrimForge already treats UIA as a disabled-by-default, coordinate-free fallback.

Vision (screenshots, VLM, image match, PyAutoGUI) is worse: DPI, theme, language, and latency. It is a last resort with no place in MVP.`,
  },
  {
    documentSlug: "automation-options",
    heading: "Papyrus and xEdit contracts",
    status: "VERIFICADO",
    sortOrder: 3,
    body: `PapyrusCompiler.exe usage (Skyrim flavor):
PapyrusCompiler <script.psc> -f=TESV_Papyrus_Flags.flg -i=<imports> -o=<out>

Always: argument arrays, no shell, timeout, explicit encoding, reject PEX older than the invocation.

xEdit unattended flavor:
SSEEdit.exe -SSE -quickedit:Mod.esp -autoload -script:Allowlisted.pas -autoexit

Always: SHA-256 allowlist of scripts, completion marker, treat missing marker as failure, never agent-authored Pascal.`,
  },
  {
    documentSlug: "existing-projects",
    heading: "The uncomfortable finding",
    status: "VERIFICADO",
    sortOrder: 1,
    body: `Three public systems already occupy this design space:

1. houseCARL — Mutagen MCP, reflection schemas, new-plugin-by-default, dialogue, SEQ, Papyrus, BSA. GPL-3.0-only. Does not drive CK.
2. SkyrimForge — typed JSON jobs, workspace receipts, allowlisted xEdit, pinned workers, UIA forbidden from containing coordinates, Nexus rights gate. The safety model in the brief is not original; Forge shipped it.
3. SkyrimCK-MCP — esper writer so blind modders can avoid CK. MIT. Alpha, but already authors QUST/PACK/SCEN.

A fourth project that "lets an agent click Creation Kit" would be a regression. A fourth project that ignores these three would be negligent.

Differentiation, if this continues: license-clean planner, stricter rollback than houseCARL's in-place lane, published capability matrix that says Unsupported out loud, and a research-grade CK inspect track that those tools do not claim to have finished.`,
  },
  {
    documentSlug: "existing-projects",
    heading: "Sky-Claw",
    status: "NO VERIFICADO",
    sortOrder: 2,
    body: `No Skyrim Creation Kit automation project named Sky-Claw was found. Search results are unrelated agent models (SkyworkAI/skyclaw) and Rust runtimes. Keep a stable adapter surface. Do not import a ghost. Do not take the name.`,
  },
  {
    documentSlug: "licensing",
    heading: "Three different acts",
    status: "VERIFICADO",
    sortOrder: 1,
    body: `Execute an external tool the user already installed.
Link a library into our process.
Distribute code or binaries to third parties.

These are not equivalent. Executing the user's PapyrusCompiler is aligned with how CK itself works. Linking Mutagen makes our worker GPL-3.0. Distributing CreationKit.exe or vanilla .psc is forbidden.

CKPE sits in a fourth category: a third-party patch of a tool whose EULA forbids modification. That is LEGAL_REVIEW_REQUIRED even though CKPE is LGPLv3.`,
  },
  {
    documentSlug: "licensing",
    heading: "EULA excerpts that constrain design",
    status: "VERIFICADO",
    sortOrder: 2,
    body: `SSE CK EULA (Steam 1946180), retrieved 2026-03-22:

• Editor is licensed, not sold.
• Use is personal non-commercial, or Creations Paid Content.
• You may not reverse engineer, derive source, modify, disassemble, decompile, or create derivative works of the Editor.
• Game Mods you distribute grant ZeniMax a broad irrevocable license.
• Mods must say they are not made, guaranteed, or supported by ZeniMax.
• You may not charge for Game Mods except through Bethesda Creations or with written consent.

This project must never look official, never RE the editor for MVP, never ship paid-mod infrastructure, never include Bethesda assets in git.`,
  },
  {
    documentSlug: "threat-model-preliminary",
    heading: "File integrity",
    status: "VERIFICADO",
    sortOrder: 1,
    body: `Threats: overwrite of the only plugin, partial writes, wrong masters, FormID reuse, ESL overflow, header 1.71 written for a 1.70 load order, missing SEQ, unbound VMAD.

Mitigations: originals/ hashed and read-only; candidates/ only; temp write then rename; reopen-and-assert; refuse in-place; refuse master edits; explicit header version; fail-fast; no second write if hash of input drifted.`,
  },
  {
    documentSlug: "threat-model-preliminary",
    heading: "Agent and process threats",
    status: "VERIFICADO",
    sortOrder: 2,
    body: `Threats: hallucinated operations, loops, clicking through modal error dialogs, treating a crash as success, command injection, path traversal to Data/, DLL hijack via crafted working directories, secret leakage in logs.

Mitigations: closed operation enum; idempotent ensure_*; no "do what you think"; no shell; path allowlists rooted at workspace; timeouts; completion markers; redacted logs; UIA jobs cannot contain coordinates; unexpected dialogs abort the transaction.`,
  },
  {
    documentSlug: "architecture-options",
    heading: "How scoring worked",
    status: "VERIFICADO",
    sortOrder: 1,
    body: `Each axis is 1–10, higher is better (including simplicity, fewer dangerous deps, and lower corruption risk). Weights: robustness 15, security 15, testability 12, corruption risk 12, maintainability 10, license fit 10, automation 8, compatibility 6, performance 5, simplicity 4, external deps 3. Scores are (weighted sum)/10, rounded.

Option D scored 79. Option E scored 74. E is still the recommendation because D cannot name CK-exclusive work without lying. E uses D as the default route.`,
  },
  {
    documentSlug: "architecture-options",
    heading: "Rejected spines",
    status: "DESCARTADO",
    sortOrder: 2,
    body: `A (vision) — rejected as primary. Coordinate and screenshot agents violate the non-negotiable integrity order.

B (UIA-only) — rejected as primary until POC-001. May become a narrow adapter.

C (CKPE bridge) — rejected as primary. Empty QueryInterface + EULA + winhttp proxy.`,
  },
  {
    documentSlug: "feasibility-report",
    heading: "Verdict",
    status: "VERIFICADO",
    sortOrder: 1,
    body: `VIABLE WITH LIMITATIONS.

Viable: typed plans, candidate plugins, Mutagen/esper record I/O, Papyrus CLI, xEdit validation, HITL, local telemetry.

Limited: no official CK API; CKPE not a usable SDK; UIA unknown; CK-exclusive ops remain human; legal overlay on any in-process CK hack; prior art already covers most of the "agent writes an ESP" story.

Not currently viable: "natural language → finished quest mod via Creation Kit clicks".

Blocked: CKPE authoring plugin, redistribution of CK/compiler/headers, in-place overwrite without backup.`,
  },
  {
    documentSlug: "feasibility-report",
    heading: "Gate 1 recommendation",
    status: "VERIFICADO",
    sortOrder: 2,
    body: `Do not authorize implementation of the agent product.

Authorize only:

1. ADR-001 — hybrid headless-first + license split (planner permissive, Mutagen worker GPL unless esper is cleared).
2. POC-002 — synthetic header parse, no Bethesda fixtures.
3. A written POC-001 protocol for a future Windows runner.
4. Keep this research desk updated when experiments change a status label.

If those pass, Milestone 1 is still an inspector, not a quest generator.`,
  },
  {
    documentSlug: "feasibility-report",
    heading: "What this phase did not do",
    status: "VERIFICADO",
    sortOrder: 3,
    body: `Did not run Creation Kit, xEdit, PapyrusCompiler, Inspect.exe, or CKPE.
Did not download unverified binaries.
Did not modify any game files.
Did not implement adapters, planners, or click automation.
Did not invent compiler flags, CK APIs, or test results.

Any sentence in a later commit that claims those things happened in Phase 0+1 is false.`,
  },
];
