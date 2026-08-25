# Roadmap

This roadmap is evidence-gated. Passing one proof does not authorize every later feature.

## Gate 1 — Research

**Status:** complete with verdict `VIABLE WITH LIMITATIONS`.

## ADR-001 — Product architecture

**Status:** `ACCEPTED` (2026-08-25).

Next architectural unit: ADR-002 + POC-IPC identifiers (isolated-worker IPC protocol and transactional boundaries). Acceptance does not by itself authorize any implementation.

## POC-002 — Synthetic TES4 safety pipeline

**Status:** **PASS**.

Demonstrates strict parsing and evidence semantics on a synthetic header fixture. It does not demonstrate real-plugin or runtime compatibility.

## Parallel / next experiments

### POC-001 — Creation Kit read-only UI inspection

Windows-only. Enumerate UIA/MSAA controls without coordinates and without saving. `BLOQUEADO` in non-Windows environments.

### POC-003 — PapyrusCompiler dry-invoke

Verify deterministic external compiler invocation, timeout behavior, stdout/stderr capture, output existence/hash, and no shell use.

### POC-004 — xEdit allowlisted validator

Verify a pinned allowlisted script with `-script -autoexit`, explicit completion evidence, timeout, and no generated Pascal.

### POC-IPC / ADR-002 — subprocess protocol and transaction boundary

Continue the IPC hardening work under a **non-conflicting identifier**. Previously reviewed versions remain `CHANGES_REQUIRED`; do not import them as passing code.

## Later product milestones

1. NL → validated `ModPlan` → one supported operation → candidate → reopen/assert → HITL.
2. Narrow record writes (for example MISC) after a dedicated writer POC.
3. Weapons / armor / recipes.
4. NPCs with explicit FaceGen limitations.
5. Leveled lists.
6. Papyrus + VMAD after their own validation gates.
7. Quests only after alias/SEQ/VMAD semantics are independently validated.

## Explicitly unsupported until new evidence exists

- navmesh automation;
- arbitrary worldspace/Render Window driving;
- coordinate click bots;
- unrestricted CK automation;
- CKPE as MVP spine.
