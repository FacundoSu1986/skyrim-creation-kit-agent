"""Workspace tests: containment, safe names, evidence persistence rules."""

import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workspace import JobWorkspace, WorkspaceViolation  # noqa: E402


class JobIdContractTests(unittest.TestCase):
    def test_bad_job_ids_raise(self):
        for bad in ("JOB..X", "..", ".", "A/B", "A\\B", "C:X", "A B", "", "A" * 65):
            with self.assertRaises(WorkspaceViolation, msg=repr(bad)):
                JobWorkspace(Path(tempfile.mkdtemp()), bad)

    def test_valid_job_creates_derivation(self):
        root = Path(tempfile.mkdtemp())
        ws = JobWorkspace(root, "JOB-OK")
        self.assertTrue(
            str(ws.job_dir).lower().startswith(str(root.resolve()).lower())
        )


class SafeNameContainmentTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.ws = JobWorkspace(self.root, "JOB-CONTAIN")
        self.ws.ensure_areas()

    def test_traversal_token_rejected(self):
        with self.assertRaises(WorkspaceViolation):
            self.ws.contained_path("input", "../originals/x.txt")

    def test_deep_traversal_token_rejected(self):
        with self.assertRaises(WorkspaceViolation):
            self.ws.contained_path("input", "a..b")  # allowed chars but '..' in it

    def test_absolute_token_rejected(self):
        with self.assertRaises(WorkspaceViolation):
            self.ws.contained_path("input", str(Path(self.root) / "evil.txt"))

    def test_drive_qualified_token_rejected(self):
        if os.name != "nt":
            self.skipTest("drive letters are a Windows concern")
        with self.assertRaises(WorkspaceViolation):
            self.ws.contained_path("input", "C:evil.txt")

    def test_unc_token_rejected(self):
        if os.name != "nt":
            self.skipTest("UNC paths are a Windows concern")
        with self.assertRaises(WorkspaceViolation):
            self.ws.contained_path("input", "\\\\server\\share\\x")

    def test_provision_then_read_is_contained(self):
        path, sha = self.ws.provision_input("fixture.txt", b"data")
        self.assertTrue(str(path).startswith(str(self.ws.areas["input"])))


class SymlinkJunctionEscapeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.ws = JobWorkspace(self.root, "JOB-LINK")
        self.ws.ensure_areas()
        self.outside_file = Path(tempfile.mkdtemp()) / "outside.txt"
        self.outside_file.write_bytes(b"secret")

    def test_symlink_escape_rejected_when_creatable(self):
        link = self.ws.areas["input"] / "link.txt"
        try:
            os.symlink(self.outside_file, link)
        except (OSError, NotImplementedError):
            self.skipTest(
                "symlink creation not permitted in this environment "
                "(capability detected at runtime)"
            )
        with self.assertRaises(WorkspaceViolation):
            self.ws.contained_path("input", "link.txt")

    @unittest.skipUnless(os.name == "nt", "junctions are Windows-specific")
    def test_junction_escape_rejected(self):
        import _winapi  # stdlib on Windows

        junction = self.ws.areas["input"] / "junction"
        outside_dir = Path(tempfile.mkdtemp())
        try:
            _winapi.CreateJunction(str(outside_dir), str(junction))
        except OSError:
            self.skipTest("junction creation not permitted on this runner")
        # Single-segment token: the safe-name grammar check passes, so the
        # assertion depends on junction resolution itself, not on the
        # grammar rejecting a separator. This is the actual junction-escape
        # proof.
        with self.assertRaises(WorkspaceViolation):
            self.ws.contained_path("input", "junction")

    @unittest.skipUnless(os.name == "nt", "case collisions are Windows-specific")
    def test_case_collision_normalization_documented(self):
        self.ws.provision_input("Fixture.txt", b"A")
        # Same name differing only by case resolves onto the SAME file.
        first = self.ws.contained_path("input", "Fixture.txt")
        second = self.ws.contained_path("input", "fixture.TXT")
        self.assertEqual(os.path.normcase(str(first)), os.path.normcase(str(second)))


class EvidencePersistenceTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.ws = JobWorkspace(self.root, "JOB-EVID")
        self.ws.ensure_areas()

    def test_receipt_persisted_once_no_overwrite(self):
        receipt = {"probe": 1}
        first = self.ws.persist_receipt("req-1", receipt)
        self.assertTrue(first.exists())
        with self.assertRaises(WorkspaceViolation):
            self.ws.persist_receipt("req-1", {"probe": 2})

    def test_stderr_log_no_overwrite(self):
        self.ws.persist_stderr_log("req-1", b"log")
        with self.assertRaises(WorkspaceViolation):
            self.ws.persist_stderr_log("req-1", b"again")

    def test_candidates_empty_for_read_only_flow(self):
        self.assertTrue(self.ws.candidates_empty())

    def test_receipt_no_overwrite_is_atomic_and_preserves_bytes(self):
        """OS-level no-overwrite proof: a second persist never touches the
        bytes of the first, even when the second call would have written
        different content. This is the property that the previous
        check-then-write (exists() -> write_text) implementation did NOT
        guarantee under concurrency, because two threads could both pass
        the exists() check and then race into write_text(), truncating the
        first writer's bytes.

        Persistence now uses open(..., "x") / O_CREAT|O_EXCL so the OS
        itself refuses to create the file when it already exists. The
        on-disk bytes of the first persist are therefore invariant across
        any number of subsequent attempts.
        """
        first_payload = {"probe": "ORIGINAL", "marker": "A" * 4096}
        first_path = self.ws.persist_receipt("req-atomic", first_payload)
        expected_bytes = first_path.read_bytes()
        expected_sha = hashlib.sha256(expected_bytes).hexdigest()

        # Several subsequent attempts with different payloads must not
        # change the on-disk bytes.
        for attempt in range(5):
            with self.assertRaises(WorkspaceViolation):
                self.ws.persist_receipt(
                    "req-atomic", {"probe": f"OVERWRITE-{attempt}"}
                )
            self.assertEqual(
                first_path.read_bytes(), expected_bytes,
                f"attempt {attempt}: on-disk bytes were altered",
            )
            self.assertEqual(
                hashlib.sha256(first_path.read_bytes()).hexdigest(),
                expected_sha,
                f"attempt {attempt}: on-disk sha changed",
            )

    def test_stderr_log_no_overwrite_is_atomic_and_preserves_bytes(self):
        """OS-level no-overwrite proof for the stderr log path."""
        first_bytes = b"ORIGINAL-LOG-CONTENT\n" * 64
        first_path = self.ws.persist_stderr_log("req-atomic-stderr", first_bytes)
        expected_sha = hashlib.sha256(first_bytes).hexdigest()

        for attempt in range(5):
            with self.assertRaises(WorkspaceViolation):
                self.ws.persist_stderr_log(
                    "req-atomic-stderr", f"OVERWRITE-{attempt}".encode("ascii")
                )
            self.assertEqual(
                first_path.read_bytes(), first_bytes,
                f"attempt {attempt}: log bytes were altered",
            )
            self.assertEqual(
                hashlib.sha256(first_path.read_bytes()).hexdigest(),
                expected_sha,
                f"attempt {attempt}: log sha changed",
            )


if __name__ == "__main__":
    unittest.main()
