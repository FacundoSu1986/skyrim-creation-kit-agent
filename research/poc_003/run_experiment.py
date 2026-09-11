"""Drive the pre-registered POC-003 experiment.

Runs, in order:

1. ``A``  — success fixture, clean workspace, normal deadline.
2. ``B``  — byte-identical input, a *second independent* clean workspace.
3. ``negative`` — intentionally invalid source; must fail closed.
4. ``long`` — large synthetic source, generous deadline; used to observe the
   process tree while the assembler is demonstrably alive.
5. ``timeout`` — same large source, short deadline; exercises the deadline,
   cleanup and descendant-survival gates.

Nothing here edits an acceptance criterion. It only collects evidence.

Usage::

    set POC003_CONFIG=C:\\path\\to\\poc003.local.json
    python -m research.poc_003.run_experiment --out C:\\path\\to\\evidence
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import shutil
import sys
import tempfile

from . import criteria, profile, runner, snapshot, workspace

#: Sized by measurement: ~17 s to compile on this machine, comfortably longer
#: than the 8 s deadline used by the timeout run. 100000 functions was tried
#: first and fails outright (exit 127), so the ceiling is real.
HANG_FUNCTIONS = 40_000
TIMEOUT_DEADLINE_S = 8.0

FIXTURE_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _generate_hang_source(path: str, functions: int) -> None:
    parts = ["Scriptname Poc003Hang\n"]
    for i in range(functions):
        parts.append(f"\nInt Function F{i}()\n\tReturn {i}\nEndFunction\n")
    with open(path, "w", encoding="ascii", newline="") as handle:
        handle.write("".join(parts))


def _fixture_hashes() -> dict[str, str]:
    """Hash every committed fixture. Criterion 15 is about provenance, so the
    hashes are recorded rather than asserted."""
    out: dict[str, str] = {}
    for dirpath, _dirnames, filenames in os.walk(FIXTURE_ROOT):
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, FIXTURE_ROOT).replace(os.sep, "/")
            out[rel] = snapshot.sha256_file(full)
    return out


def _prepare_workspace(root: str, fixture_dir: str, source_token: str) -> workspace.Workspace:
    ws = workspace.create_workspace(root)
    workspace.copy_fixture_tree(fixture_dir, ws.originals)
    for name in sorted(os.listdir(fixture_dir)):
        src = os.path.join(fixture_dir, name)
        if name == f"{source_token}.psc":
            shutil.copyfile(src, os.path.join(ws.input, name))
        else:
            shutil.copyfile(src, os.path.join(ws.imports, name))
    for area in workspace.READ_ONLY_DIRS:
        workspace.mark_read_only(ws.area(area))
    return ws


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=os.environ.get("POC003_CONFIG", ""),
        help="path to the trusted local config JSON (executable + hashes)",
    )
    parser.add_argument("--out", default="", help="directory for the evidence bundle")
    parser.add_argument("--workroot", default="", help="parent directory for workspaces")
    args = parser.parse_args(argv)

    if not args.config:
        parser.error("no local config: pass --config or set POC003_CONFIG")

    config = profile.LocalConfig.from_file(args.config)
    out_dir = os.path.abspath(args.out) if args.out else os.path.abspath("poc003-evidence")
    os.makedirs(out_dir, exist_ok=True)

    base = args.workroot or tempfile.mkdtemp(prefix="poc003-")
    print(f"[poc003] workspace root: {base}")

    started = _dt.datetime.now(_dt.timezone.utc)
    runs: dict[str, dict[str, object]] = {}

    plan = [
        ("A", "fixture_success", "Poc003Minimal", profile.DEFAULT_DEADLINE_S),
        ("B", "fixture_success", "Poc003Minimal", profile.DEFAULT_DEADLINE_S),
        ("negative", "fixture_compile_error", "Poc003Broken", profile.DEFAULT_DEADLINE_S),
        ("long", "fixture_success", "Poc003Hang", profile.DEFAULT_DEADLINE_S),
        ("timeout", "fixture_success", "Poc003Hang", TIMEOUT_DEADLINE_S),
    ]

    workspaces: dict[str, workspace.Workspace] = {}
    for label, fixture, token, deadline in plan:
        ws = _prepare_workspace(os.path.join(base, label), os.path.join(FIXTURE_ROOT, fixture), token)
        if token == "Poc003Hang":
            _generate_hang_source(os.path.join(ws.input, "Poc003Hang.psc"), HANG_FUNCTIONS)
            workspace.mark_read_only(ws.input)
        workspaces[label] = ws
        request = runner.RunRequest(
            operation=profile.OP_COMPILE_FIXTURE,
            source_token=token,
            deadline_s=deadline,
        )
        print(f"[poc003] run {label}: token={token} deadline={deadline}s ...", flush=True)
        evidence = runner.run_once(config, ws, request)
        runner.write_evidence(ws, evidence)
        runs[label] = evidence.to_dict()
        # The workspace lives under the host's temp directory. Its absolute
        # path is an implementation detail with no evidentiary value and it
        # would carry a host username into the committed record.
        runs[label]["workspace"] = "<WORKSPACE_ROOT>"
        print(
            f"[poc003] run {label}: success={evidence.success} "
            f"outcome={evidence.outcome_code} "
            f"exit={evidence.details.get('exit_code')} "
            f"elapsed={evidence.details.get('elapsed_s')}s",
            flush=True,
        )

    det_a = runs["A"]["details"].get("output_sha256")
    det_b = runs["B"]["details"].get("output_sha256")
    determinism = {
        "run_a_sha256": det_a,
        "run_b_sha256": det_b,
        "equal": bool(det_a) and bool(det_b) and det_a == det_b,
        "outcome_code": None if (det_a and det_b and det_a == det_b) else "DETERMINISM_MISMATCH",
    }

    bundle = {
        "meta": {
            "profile_id": profile.PROFILE_ID,
            "generated_utc": started.isoformat(),
            "host_os": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
            "executable_sha256": snapshot.sha256_file(config.executable),
            "flags_sha256": snapshot.sha256_file(config.flags),
            "hang_functions": HANG_FUNCTIONS,
            "timeout_deadline_s": TIMEOUT_DEADLINE_S,
            "workspace_parent": "<WORKSPACE_ROOT_PARENT>",
            "fixtures": _fixture_hashes(),
        },
        "runs": runs,
        "determinism": determinism,
    }

    bundle_path = os.path.join(out_dir, "poc003-bundle.json")
    with open(bundle_path, "w", encoding="utf-8") as handle:
        json.dump(bundle, handle, indent=2, sort_keys=True)

    # The 15 pre-registered criteria are evaluated mechanically, from the
    # bundle, by the same code in every run. Nothing is edited to fit the
    # observation: a failing row stays FAIL.
    rows = criteria.evaluate(bundle)
    summary = criteria.summarize(rows)
    criteria.write_matrix(rows, os.path.join(out_dir, "matrix.md"))
    with open(os.path.join(out_dir, "criteria.json"), "w", encoding="utf-8") as handle:
        json.dump(
            {"summary": summary, "rows": [row.as_dict() for row in rows]},
            handle,
            indent=2,
            sort_keys=True,
        )

    print()
    print(f"[poc003] criteria: {summary['passed']}/{summary['total']} PASS, "
          f"failing={summary['failing_numbers']}")
    print(f"[poc003] determinism: A={det_a}")
    print(f"[poc003] determinism: B={det_b}")
    print(f"[poc003] determinism: equal={determinism['equal']}")
    print(f"[poc003] bundle: {bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
