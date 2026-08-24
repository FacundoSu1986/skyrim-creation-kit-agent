# Licensing and legal audit

**PHASE:** 2 (preliminary)  
**STATUS:** Source-backed matrix. Several rows remain `LEGAL_REVIEW_REQUIRED`. This is not legal advice.

## Three different acts

| Act | Meaning | Typical risk |
| --- | --- | --- |
| Execute | Run a tool the user already installed | Lowest, if paths are controlled |
| Link | Compile/link a library into our process | Inherits that library’s copyleft |
| Distribute | Ship code or binaries to others | Highest; Bethesda files are forbidden |

These acts are not equivalent. Do not treat “we call xEdit” as “we can ship xEdit”.

## Creation Kit EULA (Steam 1946180)

Retrieved 2026-03-22 from https://store.steampowered.com//eula/1946180_eula_0

**VERIFICADO excerpts:**

- The Editor is licensed, not sold.
- Use is personal non-commercial, or Creations Paid Content.
- You may not reverse engineer, derive source, modify, disassemble, decompile, or create derivative works of the Editor (except where permitted by law).
- Distributed Game Mods grant ZeniMax a broad irrevocable license.
- Mods must state they are not made, guaranteed, or supported by ZeniMax.
- Charging for Game Mods is restricted except Bethesda Creations / written consent.

Implication: an in-process CKPE-style patch of the Editor is `LEGAL_REVIEW_REQUIRED` even if CKPE itself is LGPLv3.

## Matrix

| Component | License | Use | Modify | Distribute | Risk |
| --- | --- | --- | --- | --- | --- |
| Skyrim SE/AE | Proprietary | User’s legal copy as read-only input | No | No | Critical if assets leak into git |
| Creation Kit | ZeniMax EULA | Execute user’s install | EULA forbids RE/modify | No | Critical for in-process hooks |
| steam_api64.dll | Valve / game files | Present because CK needs it | No | No | High if we juggle DLLs |
| CKPE | LGPLv3 (v0.6+) + proprietary blobs | Optional user install | LGPL vs EULA overlay | Do not redistribute | Critical |
| Mutagen / Synthesis / Spriggit | GPL-3.0-only | Preferred headless engine | Allowed under GPL | Source obligation | High product-license impact |
| xEdit | MPL-2.0 (repo); site still says 1.1 | Execute user’s copy | Not required | Do not bundle | Medium |
| LOOT / libloot | GPL-3.0 | Optional later | No | Do not bundle | Medium if linked |
| esper C# | Unconfirmed | Possible MIT-like alternative | After LICENSE read | After LICENSE read | `LEGAL_REVIEW_REQUIRED` |
| esper-js / esper-cpp | MIT | Possible | Allowed | Allowed | Lower |
| PapyrusCompiler + vanilla .psc | Proprietary, ships with CK | Invoke locally | No | No | High if committed |
| FlaUI | MIT | Possible UIA worker | No need | OK | Low license |
| WinAppDriver | Unpublished server | None | Impossible | Do not adopt | Abandoned |

## Fixture rule

Do **not** store `Skyrim.esm`, DLC, vanilla `.psc`, FaceGen, or any Bethesda binary in this repository. Synthetic TES4 headers authored here are acceptable. esper’s own test fixtures require copying game files locally — do not follow that into git.

## Product license strategy (not chosen)

Live options after ADR-001:

1. Entire stack GPL-3.0 because it links Mutagen (houseCARL’s choice).
2. Permissive planner + separate GPL Mutagen worker process.
3. Permissive core + esper if `EXP-ESPER-LICENSE` confirms MIT.

Do not pick MIT for a process that statically links Mutagen.
