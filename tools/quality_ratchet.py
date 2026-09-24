#!/usr/bin/env python3
"""Ratchet gate for static analysis of the research Python tree.

Why a ratchet instead of a clean sweep
-------------------------------------
`pyproject.toml` declared ruff and mypy as dev dependencies and never wired
them into CI, so the "tooling contract" was aspirational: ruff reported 17
findings and mypy could not even start (duplicate module names, because the
POC directories are namespace roots). The research code under `research/**` is
pinned evidence, so reformatting it to satisfy a linter would churn baselines
for no evidentiary gain. A ratchet resolves that: existing findings are
recorded as explicit, reviewable debt in `tools/quality-baseline.txt`, and any
**new** finding fails CI. Debt can only shrink, and shrinking it is a
celebrated diff; adding it requires editing the baseline, which is a visible,
pinned, reviewable act.

Checked rules (deliberately narrow, bug-shaped, not cosmetic)
--------------------------------------------------------------
- ruff `E4,E7,E9,F,B`: import position/shadowing, pyflakes (undefined names,
  unused/redefined bindings), and bugbear (misused defaults, raise-from,
  loop-variable capture).
- mypy: as configured in `[tool.mypy]`.
Formatting (`ruff format`) is intentionally NOT gated: reflowing a pinned
research baseline has no evidentiary value and would invalidate hashes for
style alone.

Modes
-----
--check   (default) exit 1 on any finding not present in the baseline; exit 0
          on equal or fewer findings (printing a "ratchet down" notice).
--update  recompute the baseline from the current tree and write it.
--explain print the live findings with locations (no gating).

Exit codes: 0 clean, 1 new debt, 2 tool missing or unparseable output. A
missing analyzer is a failure, never a pass: "could not measure" is not
"measured and fine".
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE = REPO_ROOT / "tools" / "quality-baseline.txt"

TARGETS = ("research", "tools")
RUFF_SELECT = "E4,E7,E9,F,B"

MYPY_LINE = re.compile(r"^(?P<path>[^:]+):\d+: error: .*?\[(?P<code>[a-z\-]+)\]$")
MYPY_SUMMARY = re.compile(r"^Found (?P<count>\d+) errors? in (?P<files>\d+) files?")
VERSION_LINE = re.compile(r"^(?P<tool>\w+)[ \t]+(?P<version>[\d.][\w.\-]*)")


def run(cmd: list[str]) -> str:
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        print(f"ERROR: {cmd[0]} is not installed; the quality gate cannot run.\n"
              f"       install with: python -m pip install -e \".[dev]\"", file=sys.stderr)
        raise SystemExit(2) from None
    # ruff/mypy exit 1 when they find issues, which is not a tool failure.
    if proc.returncode not in (0, 1):
        print(f"ERROR: {' '.join(cmd)} exited {proc.returncode}:\n"
              f"{proc.stdout.decode('utf-8', 'replace')}", file=sys.stderr)
        raise SystemExit(2) from None
    return proc.stdout.decode("utf-8", "replace")


def tool_version(tool: str, args: list[str]) -> str:
    out = run([tool, *args])
    for line in out.splitlines():
        match = VERSION_LINE.match(line.strip())
        if match:
            return match.group("version")
    return "unknown"


def ruff_findings() -> list[tuple[str, str]]:
    """Structured output, not prose: ruff's human format embeds fix hints that a
    line parser would either reject or silently drop."""
    out = run(["ruff", "check", *TARGETS, "--select", RUFF_SELECT, "--output-format",
               "json", "--no-cache"])
    try:
        payload = json.loads(out)
    except json.JSONDecodeError as exc:
        print(f"ERROR: could not parse ruff JSON output: {exc}\n{out[:400]}", file=sys.stderr)
        raise SystemExit(2) from None
    found: list[tuple[str, str]] = []
    for item in payload:
        code = item.get("code")
        filename = item.get("filename", "")
        if not code:
            print(f"ERROR: ruff finding without a rule code: {item!r}", file=sys.stderr)
            raise SystemExit(2)
        try:
            rel = Path(filename).resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = filename
        found.append((rel, f"ruff:{code}"))
    return found


def mypy_findings() -> list[tuple[str, str]]:
    """Parsed from the default format, then cross-checked against mypy's own
    `Found N errors` summary: a parse that quietly under-counts must not pass."""
    out = run(["mypy", *TARGETS])
    found: list[tuple[str, str]] = []
    declared: int | None = None
    for line in out.splitlines():
        stripped = line.strip()
        match = MYPY_LINE.match(stripped)
        if match:
            found.append((match.group("path"), f"mypy:{match.group('code')}"))
            continue
        summary = MYPY_SUMMARY.match(stripped)
        if summary:
            declared = int(summary.group("count"))
            continue
        if stripped.startswith("Success:") and declared is None:
            declared = 0
            continue
        # Diagnostics (`note:`, `warning:`) carry no gateable finding.
    if declared is None:
        print("ERROR: mypy produced no summary line; the finding count cannot be "
              f"cross-checked. Refusing to report a clean result.\n{out[:400]}", file=sys.stderr)
        raise SystemExit(2)
    if declared != len(found):
        print(f"ERROR: parsed {len(found)} mypy errors but mypy reported {declared}; "
              "the ratchet would under-count. Refusing to report a clean result.", file=sys.stderr)
        raise SystemExit(2)
    return found


def tally(findings: list[tuple[str, str]]) -> collections.Counter[str]:
    counts: collections.Counter[str] = collections.Counter()
    for path, code in findings:
        counts[f"{path}\t{code}"] += 1
    return counts


def current_state() -> tuple[collections.Counter[str], dict[str, str]]:
    counts = tally(ruff_findings()) + tally(mypy_findings())
    versions = {"ruff": tool_version("ruff", ["--version"]), "mypy": tool_version("mypy", ["--version"])}
    return counts, versions


def write_baseline(counts: collections.Counter[str], versions: dict[str, str]) -> None:
    header = [
        "# Static-analysis debt ledger for `ruff` + `mypy` over research/ and tools/.",
        "# Format: <path>\t<tool>:<rule>\t<count>   (counts are per path, line numbers excluded",
        "# so that unrelated edits cannot silently re-key a finding).",
        f"# Analyzers: ruff=={versions['ruff']} mypy=={versions['mypy']}",
        f"# Rules: ruff select = {RUFF_SELECT} (bug-shaped only); mypy = [tool.mypy] in pyproject.toml.",
        "# This file is inside the pin perimeter: relaxing it is a reviewable act.",
    ]
    rows = [f"{key}\t{counts[key]}" for key in sorted(counts)]
    BASELINE.write_text("\n".join(header + rows) + "\n", encoding="utf-8")
    print(f"baseline written: {len(rows)} keys, {sum(counts.values())} findings")


def read_baseline() -> tuple[collections.Counter[str], dict[str, str]]:
    if not BASELINE.is_file():
        print(f"ERROR: baseline not found: {BASELINE}\n"
              f"       create it with: python3 tools/quality_ratchet.py --update", file=sys.stderr)
        raise SystemExit(2)
    counts: collections.Counter[str] = collections.Counter()
    versions: dict[str, str] = {}
    for raw in BASELINE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            body = line.lstrip("# ").strip()
            if body.startswith("Analyzers:"):
                for token in body.split(":", 1)[1].split():
                    if "==" in token:
                        tool, _, version = token.partition("==")
                        versions[tool] = version
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            print(f"ERROR: malformed baseline line: {raw!r}", file=sys.stderr)
            raise SystemExit(2)
        path, code, count = parts
        try:
            counts[f"{path}\t{code}"] = int(count)
        except ValueError:
            print(f"ERROR: non-integer count in baseline: {raw!r}", file=sys.stderr)
            raise SystemExit(2) from None
    return counts, versions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true",
                   help="compare live findings against the recorded debt (default)")
    group.add_argument("--update", action="store_true", help="rewrite the baseline from the current tree")
    group.add_argument("--explain", action="store_true", help="print live findings with locations")
    args = parser.parse_args()

    if shutil.which("ruff") is None:
        print("ERROR: ruff not on PATH; install the dev extra. Refusing to report success.",
              file=sys.stderr)
        return 2
    if shutil.which("mypy") is None:
        print("ERROR: mypy not on PATH; install the dev extra. Refusing to report success.",
              file=sys.stderr)
        return 2

    if args.explain:
        out = run(["ruff", "check", *TARGETS, "--select", RUFF_SELECT, "--output-format",
                   "concise", "--no-cache"])
        print(out)
        print(run(["mypy", *TARGETS]))
        return 0

    counts, versions = current_state()

    if args.update:
        write_baseline(counts, versions)
        return 0

    allowed, baseline_versions = read_baseline()
    new = {k: v - allowed.get(k, 0) for k, v in counts.items() if v > allowed.get(k, 0)}
    gone = {k: allowed[k] - counts.get(k, 0) for k in allowed if counts.get(k, 0) < allowed[k]}

    for tool, pinned in sorted(baseline_versions.items()):
        live = versions.get(tool, "unknown")
        if live != pinned:
            print(f"NOTE: {tool} version {live} differs from the baseline pin {pinned}; "
                  f"rule sets can shift across versions, so re-read the diff carefully.")

    if new:
        print(f"QUALITY RATCHET: FAIL ({sum(new.values())} new finding(s) beyond the recorded debt)")
        for key in sorted(new):
            path, code = key.split("\t")
            print(f"  - {path}: {code} x{new[key]} (baseline {allowed[key]}, now {counts[key]})")
        print("\nFix the finding, or -- if the rule itself is wrong -- update the baseline in a\n"
              "separate, explicitly justified commit. Do not relax the baseline to make a PR green.")
        return 1

    total = sum(counts.values())
    if gone:
        print(f"QUALITY RATCHET: PASS with {total} findings; recorded debt shrank by "
              f"{sum(gone.values())} -> run python3 tools/quality_ratchet.py --update to bank it")
        return 0
    print(f"QUALITY RATCHET: PASS ({total} findings, exactly the recorded debt)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
