# Automation options

**PHASE:** 1  
**STATUS:** Options catalogued. UIA against live CK is `NO VERIFICADO`.

## Headless-first rule

Before any GUI automation, ask whether the operation can be done with:

1. a structured file format
2. a library
3. a CLI
4. a deterministic external tool

If yes, prefer that path.

| Operation | Deterministic path | CK required? |
| --- | --- | --- |
| Read/create many records | Mutagen / esper | No |
| Compile Papyrus | `PapyrusCompiler.exe` | Compiler ships with CK; GUI not required |
| Conflict / error report | xEdit CLI + scripts | No |
| Text diff of a plugin | Spriggit | No |
| FaceGen export | None found | Yes |
| Navmesh | None found | Yes |
| Render Window placement | None found | Yes |
| Lip generation | FaceFXWrapper (third party) | Usually yes / special tool |

## Mutagen

**VERIFICADO.** C# library, GPL-3.0-only, actively maintained (observed 2026-08-07). Can analyze, create, and write Skyrim SE plugins with typed records, FormKeys, load order, and overlays. Used in production by Synthesis, Spriggit, and houseCARL.

Docs: https://mutagen-modding.github.io/Mutagen/

Limitation: linking forces GPL on that process. Does not do FaceGen, navmesh, or Render Window.

## esper

**VERIFICADO as a library that exists.** C# parser by matortheeternal, used by SkyrimCK-MCP. `esper-js` and `esper-cpp` are MIT. **C# esper LICENSE was not confirmed** in the README fetch → `LEGAL_REVIEW_REQUIRED` / `EXP-ESPER-LICENSE`.

## xEdit

**VERIFICADO.** MPL-2.0 repository. CLI includes `-SSE`, `-script:"file.pas"`, `-autoexit`, `-autoload`, `-quickedit`, `-quickclean`, `-quickshowconflicts`.

Use as a validator and allowlisted-script host. **Never** let an agent emit arbitrary Pascal.

## PapyrusCompiler

**VERIFICADO.** Official CLI, ships with CK.

```
PapyrusCompiler <script.psc> -f=TESV_Papyrus_Flags.flg -i=<imports> -o=<out>
```

Always: argument arrays, no shell, timeout, explicit paths, reject stale PEX. Do not commit Bethesda `.psc` headers.

Alternate compilers exist and document behavioral differences. They are not MVP.

## Windows UI Automation

**NO VERIFICADO** against Creation Kit.

Correct first instrument: Inspect.exe / Accessibility Insights ([Microsoft docs](https://learn.microsoft.com/en-us/windows/win32/winauto/inspect-objects)).

If a library is later justified:

- **FlaUI** — MIT, active 2025, preferred .NET wrapper
- **pywinauto** — `backend="uia"`
- **WinAppDriver** — abandoned, `DESCARTADO`

Jobs must be coordinate-free. Unexpected dialogs abort.

## Vision

Screenshots, VLMs, image matching, PyAutoGUI: DPI, theme, language, latency, non-determinism. Fallback of last resort. Not MVP. `DESCARTADO` as a spine.

## CKPE in-process bridge

Technically possible to load a DLL. No high-level Editor API today. EULA forbids reverse engineering the Editor. winhttp proxy is a DLL-search-order pattern. `BLOQUEADO` pending legal review.

## LOOT

GPL-3.0 load-order tool. Irrelevant to authoring correctness. Optional later adapter only.
