"""IMPORT_ROOT_SNAPSHOT_V1 and containment tests."""

import os
import stat
import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from poc_003 import snapshot, workspace  # noqa: E402


def _write(path: str, data: bytes) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


class SnapshotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp(prefix="poc003-snap-")

    def test_snapshot_is_sorted_and_complete(self):
        _write(os.path.join(self.root, "b.psc"), b"bbb")
        _write(os.path.join(self.root, "a.psc"), b"aaa")
        _write(os.path.join(self.root, "sub", "c.psc"), b"ccc")
        entries = snapshot.snapshot_tree(self.root)
        self.assertEqual(["a.psc", "b.psc", "sub/c.psc"], [e.rel for e in entries])
        self.assertEqual(3, len(entries))

    def test_detects_added_removed_modified(self):
        _write(os.path.join(self.root, "a.psc"), b"aaa")
        before = snapshot.snapshot_tree(self.root)
        _write(os.path.join(self.root, "b.psc"), b"bbb")
        _write(os.path.join(self.root, "a.psc"), b"aaa-modified")
        after = snapshot.snapshot_tree(self.root)
        changes = snapshot.diff(before, after)
        self.assertEqual(["b.psc"], changes["added"])
        self.assertEqual(["a.psc"], changes["modified"])
        self.assertEqual([], changes["removed"])

    def test_detects_removed(self):
        _write(os.path.join(self.root, "a.psc"), b"aaa")
        before = snapshot.snapshot_tree(self.root)
        os.remove(os.path.join(self.root, "a.psc"))
        after = snapshot.snapshot_tree(self.root)
        self.assertEqual(["a.psc"], snapshot.diff(before, after)["removed"])

    def test_signature_is_stable_and_order_sensitive(self):
        _write(os.path.join(self.root, "a.psc"), b"aaa")
        _write(os.path.join(self.root, "b.psc"), b"bbb")
        first = snapshot.signature(snapshot.snapshot_tree(self.root))
        second = snapshot.signature(snapshot.snapshot_tree(self.root))
        self.assertEqual(first, second)
        _write(os.path.join(self.root, "b.psc"), b"zzz")
        self.assertNotEqual(first, snapshot.signature(snapshot.snapshot_tree(self.root)))

    def test_rejects_reparse_point_entry(self):
        """A link under the import root is uninspectable, so it must fail closed."""
        _write(os.path.join(self.root, "a.psc"), b"aaa")
        with unittest.mock.patch.object(snapshot, "_is_reparse", return_value=True):
            with self.assertRaises(snapshot.SnapshotUninspectable):
                snapshot.snapshot_tree(self.root)

    def test_reparse_bit_is_actually_read(self):
        """The Windows reparse attribute must be honoured, not just islink()."""
        _write(os.path.join(self.root, "a.psc"), b"aaa")
        path = os.path.join(self.root, "a.psc")
        self.assertFalse(snapshot._is_reparse(path))
        fake = types.SimpleNamespace(
            st_mode=stat.S_IFREG,
            st_file_attributes=snapshot.FILE_ATTRIBUTE_REPARSE_POINT,
        )
        with unittest.mock.patch.object(snapshot.os, "lstat", return_value=fake):
            self.assertTrue(snapshot._is_reparse(path))

    def test_rejects_non_regular_file(self):
        with self.assertRaises(snapshot.SnapshotUninspectable):
            snapshot.snapshot_tree(os.path.join(self.root, "does-not-exist"))

    def test_missing_root_fails_closed(self):
        with self.assertRaises(snapshot.SnapshotUninspectable):
            snapshot.snapshot_tree(os.path.join(self.root, "nope"))


class ContainmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="poc003-cont-"))
        self.candidates = os.path.join(self.root, "candidates")
        os.makedirs(self.candidates, exist_ok=True)

    def test_accepts_path_inside(self):
        self.assertTrue(workspace.is_strictly_inside(os.path.join(self.candidates, "a.pex"), self.candidates))

    def test_rejects_container_itself(self):
        self.assertFalse(workspace.is_strictly_inside(self.candidates, self.candidates))

    def test_rejects_sibling_directory(self):
        sibling = os.path.join(self.root, "temp")
        os.makedirs(sibling, exist_ok=True)
        self.assertFalse(workspace.is_strictly_inside(os.path.join(sibling, "a.pex"), self.candidates))

    def test_rejects_traversal_that_escapes(self):
        escaped = os.path.join(self.candidates, "..", "..", "evil.pex")
        self.assertFalse(workspace.is_strictly_inside(escaped, self.candidates))


if __name__ == "__main__":
    unittest.main()
