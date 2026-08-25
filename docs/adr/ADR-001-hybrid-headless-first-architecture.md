# ADR-001 — Hybrid headless-first architecture and tool separation

- **Status:** ACCEPTED (2026-08-25; see [Acceptance record](#acceptance-record))
- **Date:** 2026-08-23
- **Scope:** Product architecture for a Skyrim SE/AE authoring agent

## Context

Creation Kit is an official Windows editor but no stable public high-level authoring API has been verified. Most plugin record operations can be performed through deterministic file-format tooling, while CK-exclusive work remains narrow and high risk. The system must prioritize data integrity, reproducibility, and evidence over broad autonomous behavior.

Research scores the options as follows:

| Option | Score | Position |
| --- | ---: | --- |
| A — Pure vision agent | 30 | Rejected as spine |
| B — Windows UI Automation of CK | 47 | Narrow fallback only after inspection |
| C — In-process CKPE bridge | 39 | Research-only; legal/security concerns |
| D — Headless-first | **82** | Best isolated technical path |
| E — Hybrid orchestrator | 74 | **Recommended product shape** |

D is the primary route inside E. E is selected because it can name and isolate the few CK-exclusive capabilities without pretending headless coverage is complete.

## Decision

Adopt:

```text
HYBRID
+ HEADLESS-FIRST
+ TYPED OPERATIONS
+ ISOLATED WORKERS
+ CANDIDATE-ONLY WRITES
+ LAYERED VALIDATION
+ HUMAN APPROVAL
```

### Control flow

```text
USER
 ↓
INTENT NORMALIZER
 ↓
PLANNER / LLM
 ↓
TYPED ModPlan
 ↓
POLICY / SAFETY ENGINE
 ↓
CAPABILITY ROUTER
 ├─ Headless plugin worker
 ├─ Papyrus worker
 ├─ xEdit validator
 └─ CK worker [disabled by default]
 ↓
CANDIDATE WORKSPACE
 ↓
VALIDATOR
 ↓
HITL
 ├─ APPROVED
 └─ ROLLBACK / DISCARD
```

## Planner boundary

The planner decides **what** should happen and emits a typed plan. It must not directly execute PowerShell, `cmd`, Pascal, arbitrary subprocesses, coordinate clicks, or a generic `EXECUTE_COMMAND` operation.

`operation.kind` is a closed enum. Routing is deterministic and based on a capability registry whose status must reflect reality.

## Worker boundaries

### Plugin worker

Preferred for record-level reads/writes. A future Mutagen-backed worker should be isolated behind a protocol boundary. Process isolation is a technical architecture choice, **not** a legal conclusion about GPL obligations.

### Papyrus worker

Invokes the user's legal compiler copy with validated argument arrays, timeouts, captured stdout/stderr, and output verification. No shell.

### xEdit validator

Execute user-installed xEdit with allowlisted scripts and completion markers. Do not generate arbitrary Pascal from model output.

### Creation Kit worker

Disabled initially. First allowed experiment is read-only UI inspection (POC-001). No write automation until control identity and failure behavior are reproducible.

### CKPE

Research-only / `LEGAL_REVIEW_REQUIRED`. Not part of MVP.

### Vision

Rejected as primary architecture.

## Workspace and transaction model

```text
workspace/jobs/<request-id>/
  input/manifest.json
  originals/source.esp       # immutable
  candidates/candidate.esp
  temp/
  reports/
  receipts/
  logs/
```

Writes occur only to candidates. Originals are hashed before and after execution. Rollback means discarding the candidate.

## Evidence levels

- **E_NONE** — no gate satisfied; the plan/schema/policy was rejected before E0
- **E0** — plan/schema accepted
- **E1** — worker completed with a receipt
- **E2** — candidate reopened and assertions passed
- **E3** — independent static validation passed (for example xEdit)
- **E4** — human approved
- **E5** — runtime/in-game behavior verified

Never infer E3/E5 from E2.

## Failure policy

Fail closed on malformed plans, unknown capabilities, path escape, timeouts, crashes, missing completion markers, receipt mismatch, or changed originals.

Automatic retries are forbidden for potentially non-idempotent writes unless the operation has an explicit idempotency contract.

## Consequences

### Positive

- deterministic and testable critical path;
- reduced corruption surface;
- explicit legal/tool boundaries;
- auditability and rollback;
- CK-exclusive work remains isolated.

### Costs

- more protocol and validation work;
- external tool integration remains capability-specific;
- some editor-exclusive features may stay unsupported for a long time;
- license review remains necessary for selected backends.

## Acceptance gate

ADR-001 may move from `PROPOSED` to `ACCEPTED` once repository maintainers explicitly approve this architecture and no contradictory research evidence has emerged.

## Acceptance record

- **Status change:** PROPOSED → ACCEPTED
- **Date:** 2026-08-25
- **Authorized by:** repository owner, via explicit instruction accompanying the acceptance PR
- **Basis:**
  - POC-002 remains PASS (44/44 tests, `E2_REOPENED_ASSERTIONS_PASS`, synthetic TES4 scope).
  - No contradictory research evidence has emerged since the proposal.
  - The architecture is already reflected in validated practice: closed operation enum and truthful capability routing, candidate-only workspace with immutable originals, receipts, fail-closed orchestration, and the E_NONE/E0–E5 evidence ladder.

Acceptance authorizes the architecture **direction** only. It does not authorize implementation of any specific worker, bridge, or runtime integration. Each future unit of work still passes its own gate: ADR-002 + POC-IPC identifiers for isolated-worker IPC (never POC-003), POC-003 PapyrusCompiler dry-invoke, POC-004 xEdit validator — all currently `NO VERIFICADO`.

## Next authorized implementation

POC-002 is already validated and imported as research evidence. The next product implementation should not be started merely because this ADR exists; subsequent POCs must retain their canonical identifiers and pass their own gates.
