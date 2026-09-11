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

Every compile goes through the **same ETEC runner** as the experiment
(:func:`runner.run_once`). There is deliberately no second launch boundary
here: executable-hash gate, flags-hash gate, Job Object confinement,
process-tree measurement, bounded streaming, input verification and workspace
policy all apply exactly as they do to a real run. After a run has been
accepted by the runner, the produced ``.pex`` is read locally for structured
forensic facts only — SHA-256, size, diff offsets and parsed header integers.
Raw PEX bytes are never printed or committed (they embed the host account and
machine name in clear text), and no determinism gate is evaluated by this
probe.

It needs the local `PapyrusCompiler.exe` and is therefore **not** part of the
hermetic unit suite and **not** run by CI.

Usage::

    set POC003_CONFIG=C:\\path\\to\\poc003.local.json
    python -m research.poc_003.pex_header_probe
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile

from . import profile, runner, workspace


def _reset_workspace(root: str) -> workspace.Workspace:
    """Recreate ``root`` as a clean POC-003 workspace.

    Reused across probe compiles (including the same-path pair) after making
    the previous tree writable, so no stale artifact can satisfy the
    PRE_EXISTING_OUTPUT_PRESENT gate.
    """
    if os.path.isdir(root):
        workspace.make_writable(root)
        # No ``ignore_errors``: a partially deleted tree is a forensic hazard,
        # not a nuisance. If the expected artifact is gone but a stale import
        # survives, the runner would accept that residual as the baseline state
        # and the next compile would "prove" something about a workspace that
        # was never actually clean.
        shutil.rmtree(root)
        if os.path.exists(root):
            raise RuntimeError(
                f"probe workspace could not be fully removed before re-creation: {root}"
            )
    return workspace.create_workspace(root)


def _stage_fixture(ws: workspace.Workspace, fixture_dir: str, token: str) -> None:
    """Populate ``input/`` (the source) and ``imports/`` (the extras)."""
    workspace.copy_fixture_tree(fixture_dir, ws.originals)
    for name in sorted(os.listdir(fixture_dir)):
        src = os.path.join(fixture_dir, name)
        if name == f"{token}.psc":
            shutil.copyfile(src, os.path.join(ws.input, name))
        else:
            shutil.copyfile(src, os.path.join(ws.imports, name))
    for area in workspace.READ_ONLY_DIRS:
        workspace.mark_read_only(ws.area(area))


def _compile_once(
    config: profile.LocalConfig, ws_root: str, token: str, fixture_dir: str
) -> tuple[bytes, runner.RunEvidence]:
    """One *runner-governed* compile; returns the produced artifact bytes.

    The pinned executable and flags digests are verified by the runner pre-
    spawn on every call; a mismatch aborts before anything executes.
    """
    ws = _reset_workspace(ws_root)
    _stage_fixture(ws, fixture_dir, token)
    request = runner.RunRequest(operation=profile.OP_COMPILE_FIXTURE, source_token=token)
    evidence = runner.run_once(config, ws, request)
    if not evidence.success:
        raise RuntimeError(
            f"runner rejected the compile: {evidence.outcome_code}: {evidence.failures}"
        )
    pex = os.path.join(ws.candidates, request.expected_output())
    with open(pex, "rb") as handle:
        return handle.read(), evidence


def _diff_offsets(a: bytes, b: bytes) -> list[int]:
    """Every differing byte offset, including the tail of the longer file.

    A byte present in one output and absent in the other is a difference at
    that offset, not an ignorable truncation.
    """
    shared = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    return shared + list(range(min(len(a), len(b)), max(len(a), len(b))))


def _header_observations(data: bytes) -> dict[str, object]:
    """Structured, non-raw facts about the produced artifact's header.

    The compiler embeds the host account name and machine name in clear text
    inside the artifact, so raw bytes are never returned, printed or committed.
    Only parsed integers, a magic constant and ASCII segment counts are
    reported. ``uint32_be_offset_0x0c`` is the field previously measured as a
    big-endian compile-time value; reporting it as a plain integer keeps the
    observation honest without normalizing it (criterion 14 is not evaluated
    here).
    """
    observations: dict[str, object] = {"size": len(data)}
    if len(data) >= 16:
        observations["magic_hex"] = data[:4].hex()
        observations["uint16_be_offset_0x04"] = int.from_bytes(data[0x04:0x06], "big")
        observations["uint16_be_offset_0x08"] = int.from_bytes(data[0x08:0x0A], "big")
        observations["uint32_be_offset_0x0c"] = int.from_bytes(data[0x0C:0x10], "big")
    printable = bytes(range(0x20, 0x7F))
    segment_count = 0
    in_segment = False
    for byte in data[:512]:
        if byte in printable:
            in_segment = True
        elif in_segment:
            segment_count += 1
            in_segment = False
    if in_segment:
        segment_count += 1
    observations["ascii_segments_in_prefix_512"] = segment_count
    return observations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=os.environ.get("POC003_CONFIG", ""))
    parser.add_argument("--token", default="Poc003Minimal")
    args = parser.parse_args(argv)
    if not args.config:
        parser.error("no local config: pass --config or set POC003_CONFIG")

    config = profile.LocalConfig.from_file(args.config)
    fixture_root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "fixtures", "fixture_success"
    )

    base = tempfile.mkdtemp(prefix="poc003-probe-")
    try:
        same = os.path.join(base, "same")
        first, _first_ev = _compile_once(config, same, args.token, fixture_root)
        second, _second_ev = _compile_once(config, same, args.token, fixture_root)
        long_path = os.path.join(base, "a-considerably-longer-path")
        third, _third_ev = _compile_once(config, long_path, args.token, fixture_root)

        report = {
            "same_path_run_1_sha256": _sha(first),
            "same_path_run_2_sha256": _sha(second),
            "same_path_equal": first == second,
            "same_path_diff_byte_count": len(_diff_offsets(first, second)),
            "same_path_diff_offsets": _diff_offsets(first, second)[:16],
            "longer_path_sha256": _sha(third),
            "longer_path_equal_to_run_1": first == third,
            "longer_path_diff_byte_count": len(_diff_offsets(first, third)),
            "longer_path_diff_offsets": _diff_offsets(first, third)[:16],
            "sizes": [len(first), len(second), len(third)],
            "run_1_header": _header_observations(first),
            "run_2_header": _header_observations(second),
            "run_3_header": _header_observations(third),
        }
        print(_render(report))
    finally:
        if os.path.isdir(base):
            workspace.make_writable(base)
            shutil.rmtree(base, ignore_errors=True)
    return 0


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _render(report: dict[str, object]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in report.items())


if __name__ == "__main__":
    raise SystemExit(main())
