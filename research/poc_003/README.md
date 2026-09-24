# POC-003 — PapyrusCompiler dry-invoke harness

Implements and measures the closed profile `PAPYRUS_COMPILE_DRYRUN_V1` defined
by [ADR-004](../../docs/adr/ADR-004-external-tool-execution-contract.md) against
the criteria pre-registered in
[2026-09-01-poc-003-pre-registration.md](../../docs/research/2026-09-01-poc-003-pre-registration.md).

Result of the recorded run: [2026-09-06-poc-003-results.md](../../docs/research/2026-09-06-poc-003-results.md).
**POC-003 is not `PASS`** — 13 of 15 mandatory criteria passed and two failed:
criterion 12 (`UNEXPECTED_OUTPUT_PRESENT`: an interrupted run leaves an undeclared
`candidates/<token>.pas` behind) and criterion 14 (`DETERMINISM_MISMATCH`: repeated
compilations produce byte-different `.pex` artifacts).

## What this is not

- **Not** a general process runner. One executable, one argv shape, three
  allowlisted source tokens, one operation. There is no field through which a
  caller can name a binary or pass a raw string into argv.
- **Not** ADR-002 WIPC. `PapyrusCompiler.exe` cannot speak that protocol, and
  nothing here pretends otherwise (ADR-004 E1).
- **Not** production code. Research POC; not an authoring backend.
- **Not** a PEX validator. `PEX_STRUCTURAL_VALIDITY` and `PEX_RUNTIME_VALIDITY`
  remain `NO VERIFICADO`.

## Layout

```text
poc_003/
├── profile.py             the closed profile: argv, env, tokens, bounds
├── runner.py              one execution + trusted-side verdict computation
├── snapshot.py            IMPORT_ROOT_SNAPSHOT_V1 and containment
├── workspace.py           workspace layout and read-only enforcement
├── proctree.py            Toolhelp32 process-tree sampling
├── jobobject.py           Windows Job Object (KILL_ON_JOB_CLOSE) confinement
├── errors.py              ETEC outcome taxonomy, partitioned per ADR-004 E8
├── criteria.py            mechanical evaluation of the 15 criteria
├── run_experiment.py      drives the five pre-registered runs
├── pex_header_probe.py    forensic probe for the determinism failure
├── fixtures/              own-authored synthetic Papyrus sources
├── tests/                 hermetic suite; never invokes PapyrusCompiler
└── evidence/              recorded output of the executed run
```

## Running

The compiler is a **local dependency**: it is neither committed nor
redistributable. Point the harness at it with a config file that lives outside
the repository:

```json
{
  "executable": "C:\\\\path\\\\to\\\\PapyrusCompiler.exe",
  "executable_sha256": "<sha256>",
  "flags": "C:\\\\path\\\\to\\\\TESV_Papyrus_Flags.flg",
  "flags_sha256": "<sha256>"
}
```

```bash
# hermetic unit suite (no compiler required, CI-runnable)
# Windows only for three of its modules: test_probe, test_proctree and
# test_runner import ctypes.WinDLL at module scope, so off Windows they fail to
# import -- the run reports "Ran 64 tests ... FAILED (errors=3)", i.e. 61 real
# tests plus 3 loader errors, and the other 41 never execute. CI runs this suite
# on windows-latest, where all 105 run. A Linux run is not evidence about
# POC-003 in either direction.
python -m unittest discover -s research/poc_003/tests

# the real experiment (requires the local compiler)
set POC003_CONFIG=C:\path\to\poc003.local.json
python -m research.poc_003.run_experiment --out research\poc_003\evidence

# forensic probe for the determinism result
python -m research.poc_003.pex_header_probe
```

Never commit a produced `.pex`: the compiler embeds the host account name and
machine name in the artifact header.
