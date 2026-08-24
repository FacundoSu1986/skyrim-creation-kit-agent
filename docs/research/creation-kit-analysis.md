# Creation Kit analysis

**PHASE:** 1  
**STATUS:** Literature and primary-source review. No CK binary was executed in this environment.

## What Creation Kit is

Creation Kit (historically Construction Set) is Bethesda’s official Windows editor for viewing and editing game data. The Skyrim Special Edition editor is distributed on Steam as **app 1946180** and is expected to live beside the game install.

**VERIFICADO** — community-confirmed current version: **1.6.1378.1** (Steam Community thread, 2025-02-23).  
**VERIFICADO** — CKPE’s wiki marks SSE CK **1.5.73.0**, **1.6.1130.0**, and **1.6.1378.1** as Active.

The editor loads master files and plugins. Only one plugin is the **active file**; saves write that file. Multiple masters require INI flags (`bAllowMultipleMasterLoads`). Papyrus compilation is a child process. There is a Render Window, Object Window, Cell View, and a large set of modal record editors.

This is a desktop application. It is not an SDK.

Sources: [CK wiki Getting Started](https://ck.uesp.net/wiki/Category:Getting_Started), [CKPE wiki](https://github.com/Perchik71/Creation-Kit-Platform-Extended/wiki), Steam app 1946180.

## Plugin format the editor consumes

**VERIFICADO** via [UESP Mod File Format](https://en.uesp.net/wiki/Skyrim_Mod:Mod_File_Format):

- TES4 header, GRUP groups, records (type / size / flags / FormID / version), typed fields
- SSE record version **44**
- ESL light plugins from SSE 1.5, flag `0x00000200`
- After game/CK **1.6.1130**, plugins often use header **1.71**; older CK without CKPE cannot read them ([Nexus install article](https://www.nexusmods.com/skyrimspecialedition/articles/12296))

EditorIDs are the stable handle an agent should prefer. FormIDs are load-order sensitive once masters shift.

This format is independently implemented by Mutagen, xEdit, and esper. That is why headless authoring is possible.

## Interfaces that were not found

Searched and **not found** as official SSE authoring surfaces:

- a public Creation Kit SDK or PluginAPI from Bethesda
- a documented RPC or object-model for creating `NPC_` / `QUST` from code
- a general CLI such as `CreationKit.exe create-actor`
- official UI Automation support or AutomationId conventions

Found, but not a general authoring API:

- Fallout 4 batch flags (`-GeneratePrecombined`, `-GeneratePreVisData`, `-BuildCDX`) — documented by community FO4 previs guides, **not** evidence of an SSE create-record CLI
- `PapyrusCompiler.exe` CLI (a compiler)
- `Archive.exe` / BSArch
- CKPE’s third-party loader

**HIPÓTESIS:** SSE CK may have undocumented switches. `EXP-CK-CLI` must prove them. Product code must not mention invented flags.

## CKPE

**VERIFICADO** from the [CKPE repository](https://github.com/Perchik71/Creation-Kit-Platform-Extended) and [plugin wiki](https://github.com/Perchik71/Creation-Kit-Platform-Extended/wiki/CKPE-Plugin):

- LGPLv3 since v0.6 (commit `9d93970`); earlier GPLv3
- C++ DLLs in `CKPEPlugins\` export `CKPEPlugin_Version` and `CKPEPlugin_Load`
- **`QueryInterface()` returns nothing useful; no authoring interfaces are implemented**
- Author states required skills: C/C++, x64 ASM, reverse engineering
- Load technique: **winhttp.dll proxy**. Wiki warns never to replace the system file

CKPE is a research track, not an MVP backend.

## Related processes

Typical tree on a user’s machine (not observed here):

- `CreationKit.exe`
- optional `ckpe_loader.exe`
- `PapyrusCompiler.exe` under `Papyrus Compiler\`
- Steam API DLLs
- log files / `CreationKit.ini` / `CreationKitCustom.ini`

**NO VERIFICADO** in this environment: actual window class names, exit codes, and crash rates.
