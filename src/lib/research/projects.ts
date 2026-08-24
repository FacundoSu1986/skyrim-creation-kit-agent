export const projectRows = [
  {
    name: "houseCARL",
    url: "https://github.com/Avick3110/houseCARL",
    lastActivity: "2026-07-29 (observed on GitHub topic listing)",
    license: "GPL-3.0-only",
    language: "C# / .NET 9",
    architecture:
      "Local MCP server. Mutagen kept warm. Reflection-generated record schema. Writes new MO2 patch plugins by default; opt-in in-place edit with no backup.",
    solves:
      "Read any record at load-order winner; create/remove records; dialogue graphs; SEQ files; Papyrus compile/decompile; BSA via BSArch; SkyPatcher/SPID/KID authoring skills; Nexus catalogue lookup.",
    doesNotSolve:
      "Does not drive Creation Kit UI. Does not generate FaceGen, navmesh, or Render Window work. In-place lane keeps no backup.",
    projectStatus: "Active, v1.9.0 advertised",
    reusableCode:
      "Learnings only. Do not copy. Schema-via-reflection and 'new plugin, never touch originals' are sound patterns to re-derive.",
    risks:
      "GPL copyleft if linked. In-place edit without backup violates this brief's rollback rule. Overlaps MVP record authoring almost completely.",
  },
  {
    name: "SkyrimForge",
    url: "https://github.com/ShugokiFable/SkyrimForge",
    lastActivity: "2026-08-21; standalone frozen at 5.2.1, moved into Ultimate-AI-Starter-Bundle",
    license: "Not clearly extracted from the README fetch — LEGAL_REVIEW_REQUIRED",
    language: "Python + native helpers",
    architecture:
      "MCP + CLI + GUI. Typed JSON jobs. Workspace snapshots. Allowlisted xEdit scripts. Version-pinned JSON workers for LOOT/Wrye Bash/CK. Coordinate-free UIA fallback disabled by default.",
    solves:
      "Safety model this brief describes: receipts, hashes, approval, no live Data writes, Papyrus compile, FOMOD, Nexus rights gate, narrow plugin writes (KYWD, GLOB, FLST, OTFT).",
    doesNotSolve:
      "Does not claim a complete CK authoring API. Plugin writer is intentionally narrow. CK path is worker-contract + UIA, not a full Editor object model.",
    projectStatus: "Standalone unsupported; development continues in another repo",
    reusableCode:
      "Architectural lessons only. The Automation Fabric and evidence-tier language should be treated as prior art, not source to copy.",
    risks:
      "Closest collision with this project's identity. Building a second Forge without a sharp delta is product failure. License of 5.2.1 not verified in this pass.",
  },
  {
    name: "SkyrimCK-MCP",
    url: "https://github.com/Pyrhame/SkyrimCK-MCP",
    lastActivity: "2026-04-18 (pageAge on fetch)",
    license: "MIT",
    language: "C# / .NET 8",
    architecture:
      "Thin MCP over esper + balsa. Direct ESP write. Accessibility-first (screen readers cannot use CK GUI).",
    solves:
      "QUST with VMAD/aliases, PACK travel templates, SCEN, SNDR/SOUN, CELL/REFR overrides — without opening CK.",
    doesNotSolve:
      "Alpha; many record types unsupported. Depends on external esper/balsa clones. Not a safety fabric or HITL product.",
    projectStatus: "Alpha, purpose-built for SkyrimNVDA",
    reusableCode:
      "Lesson: CK GUI is not required for several 'CK-looking' record types. Sharp edges (SOUN wrapping, VMAD v2, SEQ) are real.",
    risks:
      "esper C# license unverified. Binary record writing without xEdit validation can produce plugins that load and still fail in-game.",
  },
  {
    name: "Mutagen + Synthesis + Spriggit",
    url: "https://github.com/Mutagen-Modding/Mutagen",
    lastActivity: "Mutagen 2026-08-07; Synthesis 2026-07-21; Spriggit 2026-07-10",
    license: "GPL-3.0",
    language: "C#",
    architecture:
      "Typed plugin library, patcher pipeline, and text serialization for Git.",
    solves:
      "Programmatic create/modify/analyze of plugins; reproducible patchers; YAML/JSON diffs of mods.",
    doesNotSolve:
      "No CK automation. No natural-language planner. No HITL product UX.",
    projectStatus: "Mature, actively maintained",
    reusableCode:
      "Preferred library if GPL is accepted. Spriggit is the obvious candidate-diff format.",
    risks:
      "GPL-3.0-only linking. Alpha package versioning on NuGet. Complex FormID/override semantics.",
  },
  {
    name: "xEdit / SSEEdit",
    url: "https://github.com/TES5Edit/TES5Edit",
    lastActivity: "2026-08-10",
    license: "MPL-2.0 (site text still mentions MPL 1.1)",
    language: "Pascal / Delphi",
    architecture:
      "Desktop module editor + Pascal scripting + CLI modes.",
    solves:
      "Conflict detection, error check, cleaning, scripted transforms, unattended -script -autoexit.",
    doesNotSolve:
      "Not an agent runtime. Arbitrary script execution is a security hole. No typed C#/Python API of Mutagen's quality.",
    projectStatus: "Mature, actively maintained",
    reusableCode:
      "Use as an external validator. Never embed or redistribute as if first-party.",
    risks:
      "Agent-generated Pascal must be forbidden. xEdit can edit masters if unlocked. Requires local Windows install of the user's own copy.",
  },
  {
    name: "CKPE (Creation Kit Platform Extended)",
    url: "https://github.com/Perchik71/Creation-Kit-Platform-Extended",
    lastActivity: "Releases observed through 2025–2026; wiki current",
    license: "LGPLv3 since v0.6; GPLv3 earlier; some proprietary resource files",
    language: "C++",
    architecture:
      "Loader + patches + optional user DLLs in CKPEPlugins. Reverse-engineered CK internals.",
    solves:
      "CK stability, load speed, Unicode, dark UI, master/plugin flexibility, log interception. Plugin host exists.",
    doesNotSolve:
      "Does not provide a high-level create_actor / create_quest API. QueryInterface empty.",
    projectStatus: "Active, Stable for listed CK versions",
    reusableCode:
      "Study TestPlugin for loader contract only. Do not vendor CKPE. Do not redistribute proprietary pak/d3dcompiler files.",
    risks:
      "EULA reverse-engineering conflict. winhttp proxy. Version fragility. Linking LGPLv3 has obligations.",
  },
  {
    name: "zEdit / esper",
    url: "https://github.com/matortheeternal/esper",
    lastActivity: "esper maintained as a library; zEdit last notable community update ~2021",
    license: "esper-js MIT; C# esper LICENSE not confirmed in this pass",
    language: "C# / JS",
    architecture:
      "xEdit-like record definitions (esp.json). Parser API similar to xEdit.",
    solves:
      "Lower-level plugin parse/write without GPL Mutagen.",
    doesNotSolve:
      "zEdit itself is not a modern agent platform. ESL history was painful. Less typed than Mutagen.",
    projectStatus: "Library useful; zEdit IDE largely stale",
    reusableCode:
      "Possible MIT path if C# esper license confirms. Verify before any link.",
    risks:
      "License ambiguity on C# esper. Smaller ecosystem than Mutagen. Easy to emit invalid subrecords.",
  },
  {
    name: "LOOT / libloot",
    url: "https://github.com/loot/loot",
    lastActivity: "0.29.1 observed 2026-06",
    license: "GPL-3.0",
    language: "C++ / Qt",
    architecture: "Load-order solver + masterlist + C++ API.",
    solves: "Sort plugins, report some metadata/errors.",
    doesNotSolve: "Does not create or edit plugin content.",
    projectStatus: "Active",
    reusableCode: "Optional later adapter. Not MVP.",
    risks: "GPL API. Irrelevant to authoring correctness.",
  },
  {
    name: "papyrus-lang / Advanced Papyrus / open compilers",
    url: "https://github.com/joelday/papyrus-lang",
    lastActivity: "Language tools community still active; several compiler rewrites exist",
    license: "Varies by project",
    language: "TypeScript / Rust / V / C#",
    architecture: "Editor tooling and alternate compilers around the official binary.",
    solves: "IDE compile, flags documentation, some decompile.",
    doesNotSolve: "Do not replace official compiler in MVP without a byte-level contract test.",
    projectStatus: "Mixed",
    reusableCode: "Use official PapyrusCompiler.exe. Optional later Champollion/Mutagen PEX decompile.",
    risks:
      "Alternate compilers document behavioral differences (string case, multiline strings). That is a correctness hazard.",
  },
  {
    name: "Sky-Claw (as named in the brief)",
    url: "multiple unrelated hits",
    lastActivity: "N/A",
    license: "N/A",
    language: "N/A",
    architecture:
      "No Skyrim Creation Kit project named Sky-Claw was found. Search hits are SkyworkAI/skyclaw (agent model) and unrelated Rust agent runtimes.",
    solves: "Nothing in this domain.",
    doesNotSolve: "Cannot integrate with a project that was not located.",
    projectStatus: "Not found as a Skyrim CK tool",
    reusableCode: "Keep a stable adapter interface so a future Sky-Claw can call this core. Do not import anything now.",
    risks:
      "Name collision with Skywork SkyClaw. Do not use SkyClaw/Sky-Claw as this product's name.",
  },
];
