#!/usr/bin/env python3
"""Fail-closed coverage gate for MANIFEST.sha256.

Why this exists
---------------
`sha256sum -c MANIFEST.sha256` verifies only the rows the manifest already
contains. A file inside the declared pin perimeter that was never added
produces no error and no warning -- it simply is not pinned. That is the exact
failure mode CONTRIBUTING.md documents for PR #15, and it cannot be caught by
any amount of hash checking. This tool closes the gap by comparing the
perimeter (what *must* be pinned) against the manifest (what *is* pinned).

Declared perimeter (single source of truth for CI; see CONTRIBUTING.md
"Manifest scope"):

- in-scope directories:  docs/, research/, public/licenses/, .github/, tools/
- in-scope root files:   AGENTS.md, CONTRIBUTING.md, SECURITY.md, README.md,
                        .gitignore, pyproject.toml

Out of scope (deliberate, recorded in CONTRIBUTING.md): the Discovery Desk
application (src/**), its root-level tests (tests/**), package*.json, and
anything Git-ignored (build output, __pycache__, .next/, node_modules/...).

Modes
-----
--check   (default) exit 1 on any of: unpinned in-scope file, stale row
          (row whose path is missing or outside the perimeter), duplicate row,
          malformed row, or hash mismatch against the file on disk.
--update  rewrite the manifest: refresh hashes for in-scope rows, drop stale
          rows, append missing in-scope paths at the end (existing order is
          preserved so the diff stays reviewable). Then re-verify; a non-zero
          exit means the update did not produce a self-consistent manifest.

Exit codes are 0 (clean), 1 (violation), 2 (tool could not run: missing git,
unreadable manifest, wrong working directory). "Could not run" is never
reported as success.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

IN_SCOPE_DIRS = (
    "docs",
    "research",
    "public/licenses",
    ".github",
    "tools",
)
IN_SCOPE_ROOT_FILES = (
    "AGENTS.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "README.md",
    ".gitignore",
    "pyproject.toml",
)

MANIFEST = REPO_ROOT / "MANIFEST.sha256"
SEP = "  "  # sha256sum text format uses two spaces before the path


def in_scope(rel: str) -> bool:
    """Whether a repository-relative posix path belongs to the pin perimeter."""
    if rel in IN_SCOPE_ROOT_FILES:
        return True
    return any(rel == d or rel.startswith(f"{d}/") for d in IN_SCOPE_DIRS)


def git_candidate_files() -> list[str]:
    """Tracked + untracked-not-ignored files, as posix paths relative to root.

    Using git (rather than walking the tree) is what makes generated build
    output and __pycache__ invisible here: .gitignore is the single source of
    truth for what is not a repository artifact.
    """
    try:
        out = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=REPO_ROOT,
            check=True,
            stdout=subprocess.PIPE,
        ).stdout
    except FileNotFoundError:
        print("ERROR: git is not available; coverage cannot be determined.", file=sys.stderr)
        raise SystemExit(2) from None
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: git ls-files failed: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return sorted(p for p in out.decode("utf-8", "surrogateescape").split("\0") if p)


def expected_set() -> set[str]:
    return {f"./{p}" for p in git_candidate_files() if in_scope(p)}


def parse_manifest() -> tuple[list[tuple[str, str]], list[str], list[str]]:
    """Return (rows, malformed, duplicates) where rows are (path, hash)."""
    if not MANIFEST.is_file():
        print(f"ERROR: manifest not found: {MANIFEST}", file=sys.stderr)
        raise SystemExit(2)
    rows: list[tuple[str, str]] = []
    malformed: list[str] = []
    seen: dict[str, int] = {}
    duplicates: list[str] = []
    for lineno, raw in enumerate(MANIFEST.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        digest, sep, path = line.partition(SEP)
        path = path.strip()
        if not sep or len(digest) != 64 or not path:
            malformed.append(f"line {lineno}: {raw!r}")
            continue
        if path in seen:
            duplicates.append(f"{path} (lines {seen[path]} and {lineno})")
            continue
        seen[path] = lineno
        rows.append((path, digest.lower()))
    return rows, malformed, duplicates


def digest_of(rel: str) -> str:
    return hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()


def strip_prefix(path: str) -> str:
    return path[2:] if path.startswith("./") else path


def check() -> int:
    rows, malformed, duplicates = parse_manifest()
    pinned = {p for p, _ in rows}
    expected = expected_set()

    unpinned = sorted(expected - pinned)
    stale_missing = sorted(p for p in pinned if not (REPO_ROOT / strip_prefix(p)).is_file())
    stale_out_of_scope = sorted(
        p for p in pinned
        if (REPO_ROOT / strip_prefix(p)).is_file() and not in_scope(strip_prefix(p))
    )
    mismatched = sorted(
        p for p, digest in rows
        if (REPO_ROOT / strip_prefix(p)).is_file() and digest_of(strip_prefix(p)) != digest
    )

    problems = 0

    def report(title: str, items: list[str], hint: str) -> None:
        nonlocal problems
        if not items:
            return
        problems += len(items)
        print(f"FAIL: {title} ({len(items)})")
        for item in items:
            print(f"  - {item}")
        print(f"  {hint}\n")

    if malformed:
        problems += len(malformed)
        print(f"FAIL: malformed manifest rows ({len(malformed)})")
        for item in malformed:
            print(f"  - {item}")
        print("  Rows must be '<64-hex-digest>  ./<path>' (two spaces).\n")

    report(
        "in-scope files are not pinned (silent bypass of the integrity gate)",
        unpinned,
        "Add them: python3 tools/check_manifest_coverage.py --update",
    )
    report(
        "stale rows: pinned path no longer exists (run would abort on sha256sum -c)",
        stale_missing,
        "Drop them: python3 tools/check_manifest_coverage.py --update",
    )
    report(
        "out-of-perimeter rows: pinned path is outside the declared scope",
        stale_out_of_scope,
        "Either widen the declared perimeter in the same change, or drop the row "
        "(python3 tools/check_manifest_coverage.py --update)",
    )
    report(
        "pinned baseline drifted: recorded hash does not match the file",
        mismatched,
        "Resolve the change explicitly; never blind-repin (CONTRIBUTING.md)",
    )
    if duplicates:
        problems += len(duplicates)
        print(f"FAIL: duplicate rows ({len(duplicates)})")
        for item in duplicates:
            print(f"  - {item}")
        print("  Appending without removing the old row leaves a stale entry.\n")

    if problems:
        print(f"MANIFEST COVERAGE: FAIL ({problems} problem(s)); {len(pinned)} rows, "
              f"{len(expected)} in-scope files")
        return 1
    print(f"MANIFEST COVERAGE: OK ({len(pinned)} pinned rows cover all {len(expected)} in-scope files)")
    return 0


def update() -> int:
    rows, _malformed, _duplicates = parse_manifest()
    expected = expected_set()
    kept: list[tuple[str, str]] = []
    for path, _digest in rows:
        if path in expected:
            kept.append((path, digest_of(strip_prefix(path))))
    kept_paths = {p for p, _ in kept}
    added = sorted(expected - kept_paths)
    body = [f"{digest}{SEP}{path}" for path, digest in kept]
    body += [f"{digest_of(strip_prefix(path))}{SEP}{path}" for path in added]
    MANIFEST.write_text("\n".join(body) + "\n", encoding="utf-8")
    print(f"MANIFEST UPDATED: {len(kept)} rows refreshed, {len(added)} added, "
          f"{len(rows) - len(kept)} stale rows dropped")
    if added:
        for path in added:
            print(f"  + {path}")
    return check()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="verify coverage and hashes (default)")
    group.add_argument("--update", action="store_true", help="pin missing files, drop stale rows, then re-check")
    args = parser.parse_args()
    if args.update:
        return update()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
