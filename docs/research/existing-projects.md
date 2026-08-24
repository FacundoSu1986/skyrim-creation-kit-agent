# Existing projects

**PHASE:** 1  
**STATUS:** Prior art located. Do not copy architecture automatically.

## The uncomfortable finding

The product sketched in the brief already exists in substantial form.

### houseCARL

- URL: https://github.com/Avick3110/houseCARL
- Last activity observed: 2026-07-29
- License: **GPL-3.0-only** (required by Mutagen)
- Language: C# / .NET 9
- Architecture: local MCP server, Mutagen kept warm, reflection-generated schemas, new MO2 patch plugin by default
- Solves: read any record at load-order winner; create/remove records; dialogue graphs; SEQ; Papyrus compile/decompile; BSA; distributor grammars
- Does not solve: CK UI, FaceGen, navmesh, Render Window
- Risk: in-place edit lane keeps **no backup** — rejected by this brief’s rollback rule

### SkyrimForge

- URL: https://github.com/ShugokiFable/SkyrimForge
- Standalone frozen at 5.2.1 (2026-08); development moved into Ultimate-AI-Starter-Bundle
- License: not extracted from the README fetch → `LEGAL_REVIEW_REQUIRED`
- Language: Python + native helpers
- Architecture: MCP + CLI + GUI; typed JSON jobs; workspace snapshots; allowlisted xEdit; pinned workers; coordinate-free UIA disabled by default
- Solves: the safety fabric this brief describes (receipts, hashes, approval, no live Data writes)
- Plugin writer is intentionally narrow (KYWD, GLOB, FLST, OTFT)
- Risk: closest identity collision. Rebuilding Forge without a sharp delta is product failure.

### SkyrimCK-MCP

- URL: https://github.com/Pyrhame/SkyrimCK-MCP
- License: MIT
- Language: C# / .NET 8 over esper + balsa
- Purpose: make CK unnecessary for blind modders
- Solves: QUST (VMAD, aliases), PACK, SCEN, SNDR/SOUN, CELL/REFR — without opening CK
- Status: Alpha
- Lesson: several “CK-looking” record types are file-format problems

### Mutagen / Synthesis / Spriggit

- https://github.com/Mutagen-Modding/Mutagen
- GPL-3.0, active 2026
- Typed plugin I/O, patcher pipeline, YAML/JSON serialization for Git
- Not an agent product; the correct library layer if GPL is accepted

### xEdit / SSEEdit

- https://github.com/TES5Edit/TES5Edit
- MPL-2.0, active 2026-08
- Conflict editor + Pascal scripting + unattended CLI
- Execute, do not vendor

### CKPE

- https://github.com/Perchik71/Creation-Kit-Platform-Extended
- LGPLv3 since v0.6
- CK host / fixer, not an authoring SDK (`QueryInterface` empty)

### Sky-Claw

**NO VERIFICADO as a Skyrim CK project.** Search hits are unrelated agent models (SkyworkAI/skyclaw). Keep a stable adapter surface. Do not take the name.

## Learnings to extract, not copy

1. Headless record I/O is the real product.
2. Typed jobs beat screenshots.
3. New candidate plugins beat in-place edits.
4. Evidence tiers must be labeled (static ≠ runtime).
5. Accessibility is a first-class reason to avoid CK GUI.
6. Safety fabric is already prior art; do not claim novelty for receipts and hashes.
