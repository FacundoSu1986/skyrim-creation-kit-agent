# Gate-1 findings

| Question | Status | Answer |
| --- | --- | --- |
| Does Creation Kit expose sufficient interfaces? | `VERIFICADO` | No official authoring API/RPC/general SSE create-record CLI was found. CKPE has a host API but no verified high-level authoring model. |
| Does UI Automation detect useful CK controls? | `NO_VERIFICADO` | Requires POC-001 on Windows. |
| Does CKPE offer a viable plugin path? | `LEGAL_REVIEW_REQUIRED` | Technically loadable; high-level authoring and EULA/legal issues unresolved. |
| Which operations can avoid CK? | `VERIFICADO` | Many record reads/writes, Papyrus compilation and static validation have non-CK paths. CK remains relevant for editor-exclusive features such as FaceGen/navmesh/Render Window. |
| Which licenses shape architecture? | `VERIFICADO` | CK EULA, Mutagen GPL-3.0-only, xEdit MPL-2.0, proprietary Bethesda assets/binaries. |
| What was the first reproducible POC? | `VERIFICADO` in this repository | POC-002 synthetic TES4 safety pipeline now passes 43 tests. |
| How do we avoid corruption? | `VERIFICADO` as policy; partially implemented | Immutable originals, candidate-only writes, hashes, closed operations, fail-closed behavior. |
| How do we rollback? | `VERIFICADO` as policy | Discard candidate; in-place edit forbidden for MVP. |
| How do we validate? | `VERIFICADO` as design | E0 plan → E1 worker receipt → E2 reopen/assert → E3 independent static validation → E4 HITL → E5 runtime. |
