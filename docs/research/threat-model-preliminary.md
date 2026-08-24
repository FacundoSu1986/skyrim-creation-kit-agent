# Preliminary threat model

**PHASE:** 5 preview (required to refuse unsafe prototypes)  
**STATUS:** Design-level. No adversarial test was run.

## File threats

| Threat | Mitigation |
| --- | --- |
| Overwrite of the only plugin | Originals hashed and read-only. Writes only under `workspace/candidates`. |
| Partial / torn write | Write temp file, fsync, rename. Reopen and assert. |
| Wrong masters / header 1.71 mismatch | Explicit header policy. Refuse unknown versions. |
| FormID reuse / ESL overflow | Allocate inside the candidate. Prefer EditorIDs in plans. |
| Missing SEQ / unbound VMAD | Static checks; do not claim runtime success. |
| In-place edit without backup | Forbidden in MVP. houseCARL’s no-backup in-place lane is rejected. |

## Agent threats

| Threat | Mitigation |
| --- | --- |
| Hallucinated “do what you think” | Closed operation enum. Reject free-form commands. |
| Loops / repeated creates | Idempotent `ensure_*` keyed by EditorID. |
| Clicking through error dialogs | No click primitive. Unexpected dialogs abort. |
| Treating crash as success | Completion markers. Missing marker = failure. |

## System threats

| Threat | Mitigation |
| --- | --- |
| Hung CK / compiler / xEdit | Timeouts. Kill process group. Never wait forever. |
| Modal dialogs | Detect and fail-fast. |
| Locked files | Do not hold plugin handles at rest (houseCARL lesson). |
| Focus loss / UIA flake | UIA disabled by default; not on the critical path. |

## Security threats

| Threat | Mitigation |
| --- | --- |
| Command injection | Argument arrays, `shell=False` / no `cmd`. |
| Path traversal to `Data/` | Workspace root allowlist. |
| DLL hijacking | Do not drop `winhttp.dll`. Do not invent loaders. |
| Arbitrary Pascal / PowerShell | Allowlist by SHA-256 only. |
| Secret leakage | Structured logs with denylist. No Steam credentials. |
| Untrusted downloads | No auto-download of compilers or CKPE. |

## Integrity order (non-negotiable)

```
security > data integrity > correctness > reproducibility > tests > maintainability > performance > convenience
```

If a prototype violates the first three, stop.
