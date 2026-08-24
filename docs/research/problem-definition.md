# Problem definition

**PHASE:** 0  
**STATUS:** Research complete for Gate 1. No product implementation authorized.

## Principal problem

The problem is not “drive Creation Kit with an AI”.

The problem is: convert a high-level, often ambiguous Skyrim SE/AE modding intent into a sequence of **typed, reversible, evidence-backed operations** against plugin data and the few tools that can legally and correctly mutate that data.

A request such as “create a quest where an NPC in Whiterun gives a mission after level 20” is not one operation. It is a bundle of heterogeneous acts:

- a base actor (`NPC_`)
- a placed reference (`ACHR`) in a Whiterun cell
- a quest (`QUST`) with stages and conditions
- aliases that actually fill
- dialogue (`DIAL` / `INFO`) and possibly a `.seq` file
- optional Papyrus
- optional AI packages
- FaceGen assets if the NPC must not be grey-faced in-game

Some of those acts are binary record edits. Some are compiler invocations. Some remain exclusive to the official editor. Treating them as one GUI script is how plugins get corrupted.

## Users

Hypothesis, not interviewed:

- beginner modders who can describe content but cannot operate CK safely
- advanced modders who want reviewable diffs
- tool authors who need a stable adapter
- autonomous agents that must be denied arbitrary shell and arbitrary clicks
- accessibility users (CK GUI is hostile to screen readers; SkyrimCK-MCP already exists for that reason)
- researchers asking whether editor automation is honest

The first user of any write path must be the author of this system, on throwaway candidate plugins.

## What this is not

Not a replacement for Creation Kit.  
Not a complete editor.  
Not a click bot.  
Not a magical mod generator.  
Not affiliated with Bethesda, ZeniMax, Steam, or Nexus.

## MVP versus stop list

**MVP:** natural language → validated ModPlan → one supported write on a **candidate** plugin → reopen + hash + optional static validation → human approval.

Preferred first write: miscellaneous item or header inspect. **Not a quest.**

**Stop list:** Render Window, navmesh, worldspace, landscape, master-file surgery, in-place overwrite of the user’s only copy, arbitrary Pascal, arbitrary PowerShell, CKPE injection, invented APIs, fixed mouse coordinates.

## Evidence labels used everywhere

`VERIFICADO` · `NO VERIFICADO` · `HIPÓTESIS` · `EXPERIMENTAL` · `BLOQUEADO` · `DESCARTADO` · `LEGAL_REVIEW_REQUIRED`
