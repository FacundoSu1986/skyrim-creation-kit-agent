"""Forensic probe: *why* two compiles of identical input disagree.

POC-003 criterion 14 compares two compiles of byte-identical input in
separate workspaces. The pre-registration fixes the consequence of a
difference (`DETERMINISM_MISMATCH`, `DETERMINISTIC_OUTPUT: NO VERIFICADO`)
but not its cause, and the cause matters: a difference caused by the harness
would be a defect to fix, while a difference caused by the tool is a property
to record.

This probe separates them. It compiles the same fixture repeatedly and:

1. twice in the **same** path, so any path-dependence is held constant;
2. in a **longer** path, so path-length sensitivity becomes visible;
3. reports, for every pair, the count and offsets of differing bytes.

It needs the local `PapyrusCompiler.exe` and is therefore **not** part of the
hermetic unit suite and **not** run by CI. It is launched as a direct child
with `shell=False`, exactly like the harness.

Usage::

    set POC003_CONFIG=C:\\path\\to\\poc003.local.json
    python -m research.poc_003.pex_header_probe
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile

from . import profile

#: Bytes of a produced .pex to retain for the diff. Enough to cover the whole
#: header of a minimal script, and small enough to stay out of any report.
PEX_PREFIX = 128


def _env(temp_dir: str) -> dict[str, str]:
    env = profile.build_environment(temp_dir)
    return env


def _compile(config: profile.LocalConfig, ws: str, token: str,
             source: str, imports: tuple[str, ...]) -> bytes:
    if os.path.isdir(ws):
        shutil.rmtree(ws, ignore_errors=True)
    inp = os.path.join(ws, "input")
    imp = os.path.join(ws, "imports")
    cand = os.path.join(ws, "candidates")
    for directory in (inp, imp, cand):
        os.makedirs(directory, exist_ok=True)
    shutil.copyfile(source, os.path.join(inp, f"{token}.psc"))
    for extra in imports:
        shutil.copyfile(extra, os.path.join(imp, os.path.basename(extra)))
    argv = [
        config.executable,
        os.path.join(inp, f"{token}.psc"),
        f"-f={config.flags}",
        f"-i={imp};{inp}",
        f"-o={cand}",
    ]
    proc = subprocess.run(
        argv,
        cwd=ws,
        env=_env(os.path.join(ws, "temp")),
        shell=False,
        capture_output=True,
        timeout=profile.DEFAULT_DEADLINE_S,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"compiler exited {proc.returncode}")
    produced = os.path.join(cand, f"{token}.pex")
    with open(produced, "rb") as handle:
        return handle.read()


def _diff_offsets(a: bytes, b: bytes) -> list[int]:
    return [i for i in range(min(len(a), len(b))) if a[i] != b[i]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=os.environ.get("POC003_CONFIG", ""))
    parser.add_argument("--token", default="Poc003Minimal")
    args = parser.parse_args(argv)
    if not args.config:
        parser.error("no local config: pass --config or set POC003_CONFIG")

    config = profile.LocalConfig.from_file(args.config)
    fixture_root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "fixture_success")
    source = os.path.join(fixture_root, f"{args.token}.psc")
    extras = tuple(
        os.path.join(fixture_root, name)
        for name in sorted(os.listdir(fixture_root))
        if name != f"{args.token}.psc" and name.endswith(".psc")
    )

    base = tempfile.mkdtemp(prefix="poc003-probe-")
    try:
        same = os.path.join(base, "same")
        first = _compile(config, same, args.token, source, extras)
        second = _compile(config, same, args.token, source, extras)
        long_path = os.path.join(base, "a-considerably-longer-path")
        third = _compile(config, long_path, args.token, source, extras)

        report = {
            "same_path_run_1_sha256": _sha(first),
            "same_path_run_2_sha256": _sha(second),
            "same_path_equal": first == second,
            "same_path_diff_byte_count": len(_diff_offsets(first, second)),
            "same_path_diff_offsets": _diff_offsets(first, second)[:16],
            "longer_path_sha256": _sha(third),
            "longer_path_equal_to_run_1": first == third,
            "longer_path_diff_byte_count": len(_diff_offsets(first, third)),
            "sizes": [len(first), len(second), len(third)],
        }
        # The retained prefix is raw tool output: it can embed the host's
        # username and machine name, so it is never printed in full.
        report["prefix_redacted"] = _redact(first[:PEX_PREFIX])
        print(_render(report))
    finally:
        shutil.rmtree(base, ignore_errors=True)
    return 0


def _sha(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _redact(prefix: bytes) -> str:
    """Render a hex prefix with embedded host identifiers masked."""
    return " ".join(f"{byte:02x}" for byte in prefix[:24]) + " ..."


def _render(report: dict[str, object]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in report.items())


if __name__ == "__main__":
    raise SystemExit(main())
