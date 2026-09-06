"""File-set snapshots for POC-003.

``IMPORT_ROOT_SNAPSHOT_V1`` is specified normatively by the POC-003
pre-registration. Because the import root is a directory tree rather than a
single file, its immutability is governed by a recursive regular-file
snapshot, not by "the hash of a directory" (which has no defined meaning).

For every regular file recursively reachable under the root:

1. Reject symlinks, junctions and unsupported reparse points (fail closed).
2. Compute the normalized root-relative path (forward-slash, POSIX-style).
3. Compute SHA-256 of the file bytes.
4. Sort entries lexicographically by normalized relative path.
5. Record the complete set of ``(path, sha256)`` tuples.

An uninspectable entry is an ``INTERNAL_ERROR``, never a skipped entry.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass

FILE_ATTRIBUTE_REPARSE_POINT = 0x0400
_READ_CHUNK = 1024 * 1024


class SnapshotUninspectable(RuntimeError):
    """A declared input could not be inspected. Callers must fail closed."""


@dataclass(frozen=True)
class FileEntry:
    rel: str
    sha256: str
    size: int


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_reparse(path: str) -> bool:
    """True for symlinks, junctions and any unsupported reparse point.

    Both tests come from a single ``lstat`` so there is no second lookup that
    could disagree with the attributes actually being inspected. On Windows a
    junction is not a symlink: only the reparse attribute identifies it.
    """
    st = os.lstat(path)
    if stat.S_ISLNK(getattr(st, "st_mode", 0)):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT)


def _reject_if_reparse(path: str, root: str) -> None:
    if _is_reparse(path):
        raise SnapshotUninspectable(
            f"reparse point / symlink / junction rejected under {root}: {path}"
        )


def snapshot_tree(root: str) -> tuple[FileEntry, ...]:
    """Recursively snapshot every regular file under ``root``.

    Raises:
        SnapshotUninspectable: on any link, non-regular file, or I/O error.
    """
    root_abs = os.path.abspath(root)
    if not os.path.isdir(root_abs):
        raise SnapshotUninspectable(f"snapshot root is not a directory: {root_abs}")
    _reject_if_reparse(root_abs, root_abs)

    entries: list[FileEntry] = []
    for dirpath, dirnames, filenames in os.walk(root_abs, followlinks=False):
        for name in sorted(dirnames):
            _reject_if_reparse(os.path.join(dirpath, name), root_abs)
        for name in sorted(filenames):
            full = os.path.join(dirpath, name)
            _reject_if_reparse(full, root_abs)
            st = os.lstat(full)
            if not stat.S_ISREG(st.st_mode):
                raise SnapshotUninspectable(f"non-regular file under {root_abs}: {full}")
            rel = os.path.relpath(full, root_abs).replace(os.sep, "/")
            try:
                digest = sha256_file(full)
            except OSError as exc:
                raise SnapshotUninspectable(f"unreadable file {full}: {exc}") from exc
            entries.append(FileEntry(rel=rel, sha256=digest, size=st.st_size))
    return tuple(sorted(entries, key=lambda entry: entry.rel))


def signature(entries: tuple[FileEntry, ...]) -> str:
    """A single stable digest over a snapshot set."""
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(entry.rel.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(entry.sha256.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def diff(
    before: tuple[FileEntry, ...], after: tuple[FileEntry, ...]
) -> dict[str, list[str]]:
    """Classify a snapshot change as added / removed / modified paths."""
    before_map = {e.rel: e.sha256 for e in before}
    after_map = {e.rel: e.sha256 for e in after}
    added = sorted(set(after_map) - set(before_map))
    removed = sorted(set(before_map) - set(after_map))
    modified = sorted(
        rel for rel in set(before_map) & set(after_map) if before_map[rel] != after_map[rel]
    )
    return {"added": added, "removed": removed, "modified": modified}
