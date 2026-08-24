export const findingRows = [
  {
    category: "Creation Kit",
    claim:
      "Bethesda does not publish a supported authoring API, RPC, or general-purpose CLI for creating NPCs, quests, or items in SSE Creation Kit.",
    status: "VERIFICADO",
    evidence:
      "Official CK wiki documents a GUI editor workflow (Data dialog, active file, object window). No official API reference exists. Community consensus on r/skyrimmods is that 'the CK is the tool they made the game with. No API needed'. Steam EULA licenses the Editor as a desktop tool, not an SDK.",
    implication:
      "Any 'CK Bridge' that claims an official API would be invented. Do not design the MVP around a nonexistent CK API.",
  },
  {
    category: "Creation Kit",
    claim:
      "SSE Creation Kit is Steam app 1946180. A current community-confirmed version is 1.6.1378.1. CKPE lists 1.5.73.0, 1.6.1130.0, and 1.6.1378.1 as Active.",
    status: "VERIFICADO",
    evidence:
      "Steam community thread 2025-02-23; CKPE wiki version table; Nexus install article referencing steam AppID 1946180 and header 1.71 after 1.6.1130.",
    implication:
      "Any CK integration must be version-pinned. Treat 1.6.1378.1 as the current target, with 1.6.1130.0 as a still-common install.",
  },
  {
    category: "Creation Kit",
    claim:
      "A small set of CK command-line batch operations exists for Fallout 4 precombines/previs. This is not a general SSE authoring CLI.",
    status: "VERIFICADO",
    evidence:
      "ModernPrecombines manual documents CreationKit.exe -GeneratePrecombined:plugin.esp and -GeneratePreVisData. No equivalent documented general 'create actor' CLI for Skyrim SE was found.",
    implication:
      "Do not extrapolate FO4 batch flags into an SSE authoring API. HIPÓTESIS: SSE CK may have undocumented flags; that requires a local experiment, not an assumption.",
  },
  {
    category: "Plugin format",
    claim:
      "SSE plugins are ESM/ESP/ESL binary files with a documented community format (TES4 header, GRUP, records, fields). ESL flag is 0x00000200. SSE record version is 44. Plugins after game 1.6.1130 often use header 1.71.",
    status: "VERIFICADO",
    evidence:
      "UESP Mod File Format; UESP Special Edition page; Nexus CK install article on header 1.71.",
    implication:
      "Headless libraries can operate on the file format without launching CK for many record types.",
  },
  {
    category: "CKPE",
    claim:
      "CKPE exposes a C++ plugin loader (CKPEPlugins/*.dll) with version metadata and a Load callback. QueryInterface currently implements no authoring interfaces.",
    status: "VERIFICADO",
    evidence:
      "CKPE Plugin wiki: 'QueryInterface() function, which does not return anything useful yet, and no interfaces have been implemented.' TestPlugin is a logging/init sample, not an editor object model.",
    implication:
      "CKPE is not a ready-made Creation Kit SDK. A useful bridge would require reverse engineering EditorAPI internals — exactly the skill the wiki says is required.",
  },
  {
    category: "CKPE",
    claim:
      "CKPE loads via a winhttp.dll proxy / search-order technique. The author documents this as a Windows library-load behavior and warns never to replace the system file.",
    status: "VERIFICADO",
    evidence: "CKPE wiki Security section.",
    implication:
      "Shipping or instructing users to drop a winhttp.dll next to CreationKit.exe is a DLL-hijack-shaped deployment. High security and antivirus friction. Do not bundle this blindly.",
  },
  {
    category: "Legal",
    claim:
      "The current SSE Creation Kit EULA forbids reverse engineering, decompiling, disassembling, modifying, or creating derivative works of the Editor except where permitted by law.",
    status: "VERIFICADO",
    evidence: "Steam EULA 1946180 section 1.C Restrictions/Reservation of Rights.",
    implication:
      "A CKPE-style in-process plugin that patches CK is LEGAL_REVIEW_REQUIRED and may be incompatible with the EULA even if CKPE itself is LGPLv3.",
  },
  {
    category: "Legal",
    claim:
      "Users own their Game Mods but grant ZeniMax a broad irrevocable license. Mods must include a 'NOT MADE, GUARANTEED OR SUPPORTED BY ZENIMAX' notice. Commercial sale is restricted except Bethesda Creations.",
    status: "VERIFICADO",
    evidence: "Steam EULA 1946180 sections 2.A–2.D.",
    implication:
      "This project must not brand as official, must not redistribute Bethesda assets, and must not promise commercial mod marketplaces.",
  },
  {
    category: "Mutagen",
    claim:
      "Mutagen can analyze, create, and manipulate Skyrim SE/AE plugins in C# with typed records, FormKeys, load-order overlays, and binary write.",
    status: "VERIFICADO",
    evidence:
      "Official docs, GitHub README sample (GameEnvironment.Typical.Skyrim), NuGet Mutagen.Bethesda.Skyrim, Synthesis/Spriggit/houseCARL production use. Last Mutagen commit observed 2026-08-07.",
    implication:
      "This is the strongest deterministic backend for record-level operations. It does not replace CK for FaceGen, navmesh, or Render Window.",
  },
  {
    category: "Mutagen",
    claim:
      "Mutagen is GPL-3.0-only with no linking exception. A process that links Mutagen must be GPL-3.0.",
    status: "VERIFICADO",
    evidence:
      "GitHub license badge GPL-3.0; NuGet GPL-3.0-only; houseCARL README states this explicitly and chose GPL-3.0-only for that reason.",
    implication:
      "Architecture fork: (1) accept GPL for the Mutagen worker, or (2) isolate Mutagen in a separate licensed process, or (3) use a permissively licensed parser (esper-js MIT; C# esper license unverified).",
  },
  {
    category: "xEdit",
    claim:
      "SSEEdit/xEdit can load plugins, detect conflicts, check errors, clean ITMs, and run Pascal scripts unattended via -script and -autoexit.",
    status: "VERIFICADO",
    evidence:
      "TES5Edit README, whatsnew (-script, -autoexit, -quickedit, -autoload), STEP launch-argument table.",
    implication:
      "Excellent validator and allowlisted-script runner. Poor general agent backend if the agent can emit arbitrary Pascal.",
  },
  {
    category: "Papyrus",
    claim:
      "PapyrusCompiler.exe ships with Creation Kit and has a documented CLI: object, -i import, -o output, -f flags, -all, -quiet, -optimize.",
    status: "VERIFICADO",
    evidence:
      "Fallout CK wiki reprints compiler help; papyrus-lang wiki; community ScriptCompile.bat using TESV_Papyrus_Flags.flg for Skyrim.",
    implication:
      "Script compilation is a solved, deterministic adapter. Do not invent a compiler. Do not commit Bethesda .psc headers.",
  },
  {
    category: "UI Automation",
    claim:
      "Whether Creation Kit exposes useful UIA/MSAA controls is unknown until Inspect.exe / Accessibility Insights is run against a live CK process.",
    status: "NO VERIFICADO",
    evidence:
      "No published inspect dump of SSE CK 1.6.x was found. CK is a native Win32 editor historically. SkyrimForge treats UIA as a last-resort, coordinate-free fallback and disables it by default.",
    implication:
      "PoC-001 must be a read-only inspect experiment. Do not build a click bot first.",
  },
  {
    category: "UI Automation",
    claim:
      "WinAppDriver is not a viable new dependency. FlaUI (MIT) and pywinauto (UIA backend) are the realistic libraries if UIA is later justified.",
    status: "VERIFICADO",
    evidence:
      "Microsoft WinAppDriver issue #1550 (development paused); FlaUI MIT, v5 in 2025; pywinauto documents backend='uia'.",
    implication: "If a UIA experiment is approved, prefer FlaUI on a Windows worker or pywinauto in Python. Discard WinAppDriver.",
  },
  {
    category: "Existing work",
    claim:
      "The proposed product already exists in substantial form: houseCARL (headless Mutagen MCP), SkyrimForge (safety fabric + typed jobs + bounded CK/xEdit automation), and SkyrimCK-MCP (esper ESP writer for accessibility).",
    status: "VERIFICADO",
    evidence:
      "Public GitHub READMEs retrieved 2026-03-22. houseCARL 1.9.0; SkyrimForge 5.2.1 frozen / 6.x in bundle; SkyrimCK-MCP alpha.",
    implication:
      "Do not clone their architecture. Either differentiate (CK-exclusive ops research, license-clean core, stricter HITL) or stop and collaborate. Reinventing houseCARL is waste.",
  },
  {
    category: "Environment",
    claim:
      "This research environment is not a Windows machine with Creation Kit installed. No CK, xEdit, or PapyrusCompiler binary was executed here.",
    status: "VERIFICADO",
    evidence:
      "Sandbox is a Linux Next.js/PostgreSQL preview. No CreationKit.exe present. No binary experiments were run.",
    implication:
      "All runtime claims about CK window trees, exit codes, or crash rates remain NO VERIFICADO. Experiments are designed, not executed.",
  },
];
