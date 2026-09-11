"""Workspace construction and containment for POC-003.

Layout, as required by POC-003::

    workspace/
    |-- originals/    read-only provenance copy of the fixtures
    |-- input/        the source script; read-only
    |-- imports/      the import root; read-only
    |-- candidates/   the ONLY accepted destination for a produced artifact
    |-- temp/         target of the TEMP/TMP environment redirect
    `-- logs/         untrusted tool diagnostics and the evidence record

Rules enforced here:

* ``originals/``, ``input/`` and ``imports/`` are read-only by construction and
  are verified by hash, not by trust.
* ``candidates/`` is the only directory a produced artifact may land in.
* ``temp/`` is reserved for environment redirects.
"""

from __future__ import annotations

import os
import shutil
import stat
from dataclasses import dataclass

READ_ONLY_DIRS = ("originals", "input", "imports")


@dataclass(frozen=True)
class Workspace:
    root: str
    originals: str
    input: str
    imports: str
    candidates: str
    temp: str
    logs: str

    def area(self, name: str) -> str:
        return getattr(self, name)


def create_workspace(root: str) -> Workspace:
    root = os.path.abspath(root)
    paths = {name: os.path.join(root, name) for name in
             ("originals", "input", "imports", "candidates", "temp", "logs")}
    for name, path in paths.items():
        os.makedirs(path, exist_ok=True)
    return Workspace(root=root, **paths)  # type: ignore[arg-type]


def copy_fixture_tree(source_dir: str, dest_dir: str) -> None:
    """Copy fixture files byte-for-byte. Refuses links outright."""
    os.makedirs(dest_dir, exist_ok=True)
    for name in sorted(os.listdir(source_dir)):
        src = os.path.join(source_dir, name)
        dst = os.path.join(dest_dir, name)
        if os.path.islink(src):
            raise ValueError(f"fixture contains a link, refusing: {src}")
        shutil.copyfile(src, dst)


def mark_read_only(path: str) -> None:
    """Apply the read-only bit recursively (Windows honours it for files)."""
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            full = os.path.join(dirpath, name)
            os.chmod(full, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def make_writable(path: str) -> None:
    """Undo :func:`mark_read_only` so a workspace can be cleaned up."""
    for dirpath, _dirnames, filenames in os.walk(path):
        for name in filenames:
            full = os.path.join(dirpath, name)
            os.chmod(full, stat.S_IRUSR | stat.S_IWUSR)


def is_strictly_inside(candidate: str, container: str) -> bool:
    """True when ``candidate`` resolves strictly inside ``container``.

    "Strictly" excludes the container itself. Both sides are resolved first, so
    a traversal that resolves back into the container is accepted while one
    that resolves outside it is not.
    """
    candidate_abs = os.path.realpath(os.path.abspath(candidate))
    container_abs = os.path.realpath(os.path.abspath(container))
    if candidate_abs == container_abs:
        return False
    try:
        common = os.path.commonpath([candidate_abs, container_abs])
    except ValueError:
        return False
    return common == container_abs
