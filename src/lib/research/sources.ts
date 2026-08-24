export const sourceRows = [
  {
    title: "Creation Kit Wiki — Getting Started / plugin model",
    url: "https://ck.uesp.net/wiki/Category:Getting_Started",
    publisher: "UESP / Creation Kit Wiki",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Primary community documentation of master/plugin model, active file, and CK workflow. Not an official Bethesda API reference.",
  },
  {
    title: "Creation Kit Wiki — Data file",
    url: "https://ck.uesp.net/wiki/Data_file",
    publisher: "UESP / Creation Kit Wiki",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Documents ESM vs ESP, and notes ESL light masters were introduced in SSE 1.5.3.",
  },
  {
    title: "UESP — Skyrim Mod File Format",
    url: "https://en.uesp.net/wiki/Skyrim_Mod:Mod_File_Format",
    publisher: "UESP",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Reverse-engineered binary layout of GRUP/records/fields, flags including ESL (0x200), record version 44 for SSE. Community documentation, not Bethesda-authored.",
  },
  {
    title: "UESP — Skyrim: Special Edition",
    url: "https://en.uesp.net/wiki/Skyrim:Special_Edition",
    publisher: "UESP",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Confirms SE plugins are not compatible with classic Skyrim and documents ESL introduction in patch 1.5.",
  },
  {
    title: "Steam — Skyrim SE Creation Kit EULA (app 1946180)",
    url: "https://store.steampowered.com//eula/1946180_eula_0",
    publisher: "ZeniMax / Steam",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Current editor EULA. Prohibits reverse engineering, modification, and commercial redistribution of Game Mods except Bethesda Creations. Grants ZeniMax a broad license to Game Mods.",
  },
  {
    title: "Steam discussion — latest CK version 1.6.1378.1",
    url: "https://steamcommunity.com/app/1946180/discussions/0/599645311739159964/",
    publisher: "Steam Community",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Community confirmation dated 2025-02-23 that latest SSE CK is 1.6.1378.1. Aligns with CKPE supported-version table.",
  },
  {
    title: "CKPE GitHub repository",
    url: "https://github.com/Perchik71/Creation-Kit-Platform-Extended",
    publisher: "perchik71",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "LGPLv3 from v0.6 (commit 9d93970). Loader-based platform. Explicit winhttp proxy / DLL search-order technique. Not an official Bethesda product.",
  },
  {
    title: "CKPE Wiki — Home / supported versions",
    url: "https://github.com/Perchik71/Creation-Kit-Platform-Extended/wiki",
    publisher: "perchik71",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "SSE CK versions: 1.5.73.0, 1.6.1130.0, 1.6.1378.1 marked Active. Documents Unicode, master-as-plugin, and security note about winhttp.",
  },
  {
    title: "CKPE Wiki — Plugin API",
    url: "https://github.com/Perchik71/Creation-Kit-Platform-Extended/wiki/CKPE-Plugin",
    publisher: "perchik71",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Documents C++ DLL plugin exports. QueryInterface() currently returns nothing useful; no high-level authoring interfaces implemented. Requires C/C++, x64 ASM, and reverse engineering.",
  },
  {
    title: "CKPE Nexus page",
    url: "https://www.nexusmods.com/skyrimspecialedition/mods/71371",
    publisher: "Nexus Mods",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Distribution page. Upload to other sites forbidden by author permissions. Win 8.1+ from build 951.",
  },
  {
    title: "Nexus article — How to Install Skyrim Creation Kit",
    url: "https://www.nexusmods.com/skyrimspecialedition/articles/12296",
    publisher: "Nexus Mods community article",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Documents header 1.71 for plugins created with SSE 1.6.1130+, steam_api64.dll coupling, and CKPE as the practical way older CK versions can read 1.71 plugins.",
  },
  {
    title: "Mutagen GitHub",
    url: "https://github.com/Mutagen-Modding/Mutagen",
    publisher: "Mutagen-Modding / Noggog",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "C# library for analyzing, creating, and manipulating Bethesda plugins. GPL-3.0. Active as of 2026-08-07.",
  },
  {
    title: "Mutagen official documentation",
    url: "https://mutagen-modding.github.io/Mutagen/",
    publisher: "Mutagen-Modding",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Confirms plugin create/read/write, FormKey/FormLink model, load order, overlays, and Skyrim SE support.",
  },
  {
    title: "Mutagen.Bethesda.Skyrim NuGet",
    url: "https://www.nuget.org/packages/Mutagen.Bethesda.Skyrim",
    publisher: "NuGet",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes: "Package listed as GPL-3.0-only. Multiple 0.5x alpha releases through late 2025.",
  },
  {
    title: "xEdit GitHub (TES5Edit/TES5Edit)",
    url: "https://github.com/TES5Edit/TES5Edit",
    publisher: "TES5Edit / ElminsterAU et al.",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "MPL-2.0. Pascal. Active 2026. Supports -SSE, -script, -autoexit, -autoload, -quickclean, -quickshowconflicts.",
  },
  {
    title: "xEdit official site / license note",
    url: "http://tes5edit.github.io/",
    publisher: "xEdit project",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Site text still mentions MPL 1.1; GitHub repository LICENSE is MPL-2.0. Treat license as MPL-2.0 with a documentation inconsistency.",
  },
  {
    title: "STEP Guide — xEdit launch arguments",
    url: "https://stepmodifications.org/wiki/Guide:XEdit",
    publisher: "STEP Modifications",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Documents -autoload, -quickclean, -quickautoclean, -quickshowconflicts, -IKnowWhatImDoing, -o, -D.",
  },
  {
    title: "Fallout CK wiki — PapyrusCompiler parameters",
    url: "https://fallout.wiki/wiki/Resource:Creation_Kit/Papyrus_FAQs",
    publisher: "Fallout Wiki (mirrors Bethesda compiler help text)",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Reproduces PapyrusCompiler.exe usage. FO4 binary version string is 2.8.0.4. Skyrim uses TESV_Papyrus_Flags.flg rather than Institute flags.",
  },
  {
    title: "joelday/papyrus-lang wiki — Papyrus Compiler",
    url: "https://github.com/joelday/papyrus-lang/wiki/Papyrus-Compiler",
    publisher: "papyrus-lang",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Documents CLI flags (-i, -o, -f, -all, -quiet, -optimize) and notes compiler ships with Creation Kit.",
  },
  {
    title: "Reddit — SE/AE Papyrus compiler include paths",
    url: "https://www.reddit.com/r/skyrimmods/comments/1f0pb0a/seae_papyrus_compiler_not_recognizing_skse/",
    publisher: "r/skyrimmods",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Community-confirmed invocation: PapyrusCompiler.exe file.psc -f=TESV_Papyrus_Flags.flg -i=Source -o=Scripts.",
  },
  {
    title: "houseCARL",
    url: "https://github.com/Avick3110/houseCARL",
    publisher: "Avick3110",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Mutagen-based MCP server. GPL-3.0-only because it links Mutagen. Active July 2026. Headless record authoring, not CK automation.",
  },
  {
    title: "SkyrimForge",
    url: "https://github.com/ShugokiFable/SkyrimForge",
    publisher: "ShugokiFable",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Safety-first MCP workbench. Frozen standalone 5.2.1; development moved into Ultimate-AI-Starter-Bundle. Closest prior art to this brief.",
  },
  {
    title: "SkyrimCK-MCP",
    url: "https://github.com/Pyrhame/SkyrimCK-MCP",
    publisher: "Pyrhame",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "MIT MCP server using esper to write ESP without CK. Accessibility-first. Alpha. Quests, packages, scenes, sounds.",
  },
  {
    title: "esper (C# Bethesda plugin parser)",
    url: "https://github.com/matortheeternal/esper",
    publisher: "matortheeternal",
    accessedOn: "2026-03-22",
    verification: "NO VERIFICADO",
    notes:
      "README does not clearly state a license. esper-cpp and esper-js are MIT. Treat C# esper license as LEGAL_REVIEW_REQUIRED until LICENSE file is confirmed.",
  },
  {
    title: "Spriggit",
    url: "https://github.com/Mutagen-Modding/Spriggit",
    publisher: "Mutagen-Modding",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes: "Converts plugins to YAML/JSON for Git. GPL-3.0 via Mutagen. Useful for diffs and reproducibility.",
  },
  {
    title: "LOOT Nexus / docs license",
    url: "https://www.nexusmods.com/site/mods/439",
    publisher: "LOOT Team",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes: "GPL-3.0 API and application. libloot C++ API exists. Relevant only for load-order, not authoring.",
  },
  {
    title: "pywinauto",
    url: "https://github.com/pywinauto/pywinauto",
    publisher: "pywinauto",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes: "Win32 + UIA backends. BSD-3 historically. Not tested against Creation Kit in this research.",
  },
  {
    title: "FlaUI",
    url: "https://github.com/FlaUI/FlaUI",
    publisher: "FlaUI",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes: "MIT .NET UI Automation wrapper. Active 2025. Preferred UIA library if a .NET worker is chosen.",
  },
  {
    title: "Microsoft — Inspect accessibility tool",
    url: "https://learn.microsoft.com/en-us/windows/win32/winauto/inspect-objects",
    publisher: "Microsoft Learn",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Official method to determine whether CK controls expose UIA/MSAA. Inspect is legacy; Accessibility Insights is the current recommendation.",
  },
  {
    title: "WinAppDriver status",
    url: "https://github.com/microsoft/WinAppDriver/issues/1550",
    publisher: "Microsoft",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes: "Official development paused. Do not adopt for new work.",
  },
  {
    title: "Fallout 4 precombine CK CLI (analogous, not SSE)",
    url: "https://github.com/Diskmaster/ModernPrecombines/blob/main/MANUAL.md",
    publisher: "Diskmaster / community",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes:
      "Documents CreationKit.exe -GeneratePrecombined and -GeneratePreVisData for Fallout 4. Not evidence of a general SSE authoring CLI.",
  },
  {
    title: "GitHub topic skyrim-modding",
    url: "https://github.com/topics/skyrim-modding",
    publisher: "GitHub",
    accessedOn: "2026-03-22",
    verification: "VERIFICADO",
    notes: "Confirms topics skyrim-modding, creation-kit, papyrus, xedit, mutagen are real and in use.",
  },
];
