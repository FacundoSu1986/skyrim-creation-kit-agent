"""Shared harness for the POC-003 hermetic suite (not a test module).

The suite never invokes ``PapyrusCompiler.exe``: ``python.exe`` stands in for
it, driven by ``_fake.py``. Everything else — spawn, argv construction,
deadline, bounded capture, containment, cleanup — is the real code path.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

POC_DIR = Path(__file__).resolve().parents[1]
RESEARCH_DIR = POC_DIR.parent
TESTS_DIR = POC_DIR / "tests"

for _p in (str(RESEARCH_DIR), str(TESTS_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from poc_003 import profile, snapshot, workspace  # noqa: E402
import _fake  # noqa: E402

FAKE_TOKEN = "Poc003Minimal"


class TempWorkspace:
    """A throwaway workspace plus a LocalConfig pointing at python.exe."""

    def __init__(self) -> None:
        self.base = tempfile.mkdtemp(prefix="poc003-test-")
        self.root = os.path.join(self.base, "ws")
        self.flags_path = os.path.join(self.base, "TESV_Papyrus_Flags.flg")
        with open(self.flags_path, "wb") as handle:
            handle.write(b"Flag Hidden 0\n")
        # A venv ``Scripts\python.exe`` is a shim that spawns the real
        # interpreter as a child. Using it here would give every stand-in an
        # incidental descendant, which is an artefact of the test environment
        # rather than of the harness, and it made descendant assertions
        # flaky. Use the base interpreter so the stand-in is one process.
        stand_in = getattr(sys, "_base_executable", None) or sys.executable
        if not os.path.isfile(stand_in):
            stand_in = sys.executable
        self.config = profile.LocalConfig(
            executable=os.path.abspath(stand_in),
            executable_sha256=snapshot.sha256_file(stand_in),
            flags=self.flags_path,
            flags_sha256=snapshot.sha256_file(self.flags_path),
        )
        self.ws = workspace.create_workspace(self.root)

    def install_fake(self, behaviour: str, token: str = FAKE_TOKEN) -> None:
        _fake.write_fake(os.path.join(self.ws.input, f"{token}.psc"), token, behaviour)

    def cleanup(self) -> None:
        workspace.make_writable(self.root)
        shutil.rmtree(self.base, ignore_errors=True)

    def __enter__(self) -> "TempWorkspace":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.cleanup()
