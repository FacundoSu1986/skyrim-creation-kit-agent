# POC-003 pre-registration — PapyrusCompiler dry-invoke

- **Status:** `NO VERIFICADO` — criteria pre-registered 2026-09-01. **The experiment has not been executed.**
- **Profile:** `PAPYRUS_COMPILE_DRYRUN_V1`, defined by [ADR-004](../adr/ADR-004-external-tool-execution-contract.md) (PROPOSED).
- **Authorised by:** pending owner decision. This document does not start the work.

## Why this document exists

An acceptance criterion decided after the result is known is not a criterion; it is a
rationalisation. POC-003 is cheap to run and easy to over-claim, so its pass/fail rules
are written down first.

The concrete risk this pre-empts: if double-compile hashes differ, the temptation is to
reclassify determinism as "nice to have" and still report `PASS`. That reclassification
is pre-registered here as forbidden.

## Local environment observation (not a repository claim)

`PapyrusCompiler.exe` was located on this machine at:

```text
G:\Modding\Skyrim_Runtime_1.6.1170\Papyrus Compiler\PapyrusCompiler.exe
```

The invocation contract was read from Bethesda's own `ScriptCompile.bat` in the same
runtime directory, not invented:

```text
PapyrusCompiler.exe <source> -f=<flags.flg> -i=<imports> -o=<output>
```

`CreationKit.exe` is present in the same runtime, which additionally unblocks POC-001.

Both are **local facts about one machine**. CI has no access to `G:\`, so POC-003 is
locally executable but **not** CI-gateable as written. Making it CI-gateable requires a
separate decision about how the compiler is obtained on runners; that decision is out of
scope here and is not assumed to be solvable.

## Pre-registered acceptance criteria

Each row is mandatory unless marked otherwise. `PASS` requires every mandatory row to
pass. A single failing mandatory row makes the POC outcome `FAIL`, regardless of how
many other rows succeed.

| # | Criterion | Pass rule | Outcome code on failure |
| --- | --- | --- | --- |
| 1 | Fixed argv | Every argv element is determined by the profile; operation-specific values enter only as validated typed tokens resolved trusted-side under closed grammar and containment rules; no raw caller-controlled string reaches argv | `POLICY_VIOLATION` |
| 2 | No shell | Spawn uses `shell=False`; no shell process is introduced into the process tree rooted at the POC-003 tool launch | `POLICY_VIOLATION` |
| 3 | Executable integrity | Pinned SHA-256 of `PapyrusCompiler.exe` matches before spawn | `EXECUTABLE_HASH_MISMATCH` |
| 4 | Workspace containment | Every resolved output path lies strictly inside `candidates/` after `resolve()`; `temp/` is reserved for environment redirects | `WORKSPACE_VIOLATION` |
| 5 | Bounded output | stdout and stderr are capped during transfer, not after | `OUTPUT_LIMIT_EXCEEDED` |
| 6 | Deadline | A hang produces failure within the configured budget | `PROCESS_TIMEOUT` |
| 7 | Direct-child termination | After a timeout, the spawned compiler process is dead on Windows (the target platform for `PapyrusCompiler.exe`) | `PROCESS_TIMEOUT` (not reaped) |
| 8 | Descendant behaviour | Process tree is observed reliably AND after forced cleanup no descendant associated with the tool remains alive (see below) | `DESCENDANT_PROCESS_SURVIVED` (if alive) / `INTERNAL_ERROR` (unmeasurable) |
| 9 | Output freshness & creation | Expected output path is absent before spawn (fail-closed if pre-existing); exit code zero implies new expected `.pex` exists with size > 0 | `PRE_EXISTING_OUTPUT_PRESENT` / `EXPECTED_OUTPUT_MISSING` |
| 10 | Output hash | The `.pex` SHA-256 is recorded in evidence and independently recomputed from the produced artifact (recomputed == recorded) | `OUTPUT_HASH_MISMATCH` |
| 11 | Input immutability | All declared read-only inputs (source script in `input/`, allowlisted `flags.flg`, and import root via `IMPORT_ROOT_SNAPSHOT_V1`) have hashes recorded pre-spawn and remain unchanged across the run | `INPUT_HASH_MISMATCH` |
| 12 | No unexpected outputs | No file appears that the profile did not declare | `UNEXPECTED_OUTPUT_PRESENT` |
| 13 | Diagnostics capture | Compiler stdout and stderr are captured, bounded by stream caps, and recorded under `logs/` as untrusted evidence (no semantic filtering gated in v1) | `OUTPUT_LIMIT_EXCEEDED` / `POLICY_VIOLATION` |
| 14 | Determinism | Two compiles over identical input in separate workspaces agree | `DETERMINISM_MISMATCH` |
| 15 | Fixture provenance | No Bethesda-authored `.psc` is committed; the fixture is own-authored | `POLICY_VIOLATION` |

### The determinism rule, fixed now

```text
compile A  ->  SHA256_A
compile B  ->  SHA256_B

SHA256_A == SHA256_B   ->   DETERMINISTIC_OUTPUT: VERIFICADO
SHA256_A != SHA256_B   ->   DETERMINISTIC_OUTPUT: NO VERIFICADO
```

Criterion 14 is **mandatory**. Therefore:

> **If `SHA256_A != SHA256_B`, POC-003 cannot be reported as `PASS`.**

It is reported as `FAIL` with `DETERMINISM_MISMATCH`, and `DETERMINISTIC_OUTPUT` is
recorded as `NO VERIFICADO`. This is decided before execution and is not renegotiable
after seeing the hashes.

### Criterion 8 pass rule and outcome branches

```text
PASS:
process-tree observation is reliable AND
after forced cleanup no descendant associated with the tool remains alive.

If no descendants are ever created:
PASS, record that observation.

If descendants are created and all are cleaned:
PASS, record cleanup mechanism.

If observation is unreliable:
FAIL with INTERNAL_ERROR / WINDOWS_TREE_CLEANUP = NO VERIFICADO.

If any descendant survives:
FAIL / DESCENDANT_PROCESS_SURVIVED.
```

If criterion 8 cannot be demonstrated or a descendant survives:
- the profile does **not** claim tree cleanup;
- `WINDOWS_TREE_CLEANUP` remains `NO VERIFICADO` for `PAPYRUS_COMPILE_DRYRUN_V1`;
- POC-003 reports `FAIL` on criterion 8, unless the profile is changed to confine
  the tool in a Windows Job Object per ADR-004 E9(b), which is an architectural change requiring
  review — not a reporting decision.

The forbidden inference is:

```text
PapyrusCompiler is a direct child  =>  it has no descendants
```

That inference is exactly the one ADR-002 already refuses to make for WIPC, and ETEC
inherits the refusal.

### Criterion 11: Import root snapshot specification (IMPORT_ROOT_SNAPSHOT_V1)

Because `import root` is a directory tree rather than a single file, immutability is governed by `IMPORT_ROOT_SNAPSHOT_V1`.

For every regular file recursively reachable under the allowlisted import root:
1. Reject symlinks, junctions, and reparse points (unsupported; fail-closed).
2. Compute normalized root-relative path (forward-slash delimited, POSIX-style relative).
3. Compute SHA-256 of file bytes.
4. Sort entries lexicographically by normalized relative path.
5. Record the complete set of `(path, sha256)` tuples pre-spawn.

Post-run verification:
The exact set and every SHA-256 must match the pre-spawn record:
- Added file: `INPUT_HASH_MISMATCH`
- Removed file: `INPUT_HASH_MISMATCH`
- Changed file: `INPUT_HASH_MISMATCH`
- Uninspectable entry / I/O error: `INTERNAL_ERROR` (fail-closed)

## Non-goals

- Does not prove the compiled script is semantically correct, loadable, or safe.
- Does not prove anything about real Bethesda scripts; the fixture is own-authored.
- Does not demonstrate structural validity of the produced `.pex` file (`PEX_STRUCTURAL_VALIDITY: NO VERIFICADO`). A dedicated PEX parser/validator is future work.
- Does not demonstrate runtime or in-game loadability of the produced `.pex` file (`PEX_RUNTIME_VALIDITY: NO VERIFICADO`).
- Does not promote any candidate toward a live game directory. Promotion does not exist
  in this design.
- Does not validate `CreationKit.exe`; that is POC-001's domain.
- Does not close POC-IPC-001's `WINDOWS_TREE_CLEANUP` debt. Passing here says nothing
  about `PYTHON_ISOLATED_V1`.

## Status vocabulary for the result

Repository status remains `NO VERIFICADO` unless all mandatory criteria pass, in which case it may move to `PASS`.

`FAIL` is an evaluation gate verdict, not a repository status vocabulary identifier. A failed mandatory criterion means:
- the POC **must not be reported as `PASS`**;
- the specific failing outcome code is recorded in the evidence record;
- repository status remains `NO VERIFICADO`.

A run that cannot measure a mandatory criterion cannot be reported as `PASS` (failing outcome code recorded, repository status remains `NO VERIFICADO`).
