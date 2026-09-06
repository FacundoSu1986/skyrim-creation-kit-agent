# POC-003 fixtures

Every file in this directory is **own-authored, synthetic, minimal and
redistributable under this repository's MIT license**. No Bethesda-authored
`.psc` appears here, and none may be added: AGENTS.md forbids committing
vanilla `.psc` files, and POC-003 pre-registration criterion 15 makes fixture
provenance a mandatory gate.

| Fixture | Purpose | Expected behaviour |
| --- | --- | --- |
| `fixture_success/Poc003Minimal.psc` | positive control | compiles; produces `Poc003Minimal.pex` |
| `fixture_success/Poc003Types.psc` | import-root dependency | supplies the parent type resolved through `-i` |
| `fixture_compile_error/Poc003Broken.psc` | negative control | deterministic error: `script function getvalue already defined in the same state`; produces **no** artifact |
| `fixture_compile_error/Poc003Types.psc` | parity copy | keeps the import root identical across both fixtures |

`Poc003Hang.psc` is **not** stored here. It is generated deterministically at
run time (a large synthetic function farm) purely to give the deadline path a
job that genuinely outlives its budget; committing a multi-megabyte generated
file would add no evidence.

## Why the import root also contains the parent type

Measured during POC-003: `PapyrusCompiler.exe` resolves the compilation object
by script name through the import path list. A source script whose directory is
not reachable from `-i` fails with `unable to locate script <name>` even when
the path is given explicitly as the positional object. The profile therefore
passes `-i=<imports>;<input>`; see `profile.py`.
