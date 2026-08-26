"""Shared test harness for POC-IPC-001 (not a test module)."""

import hashlib
import sys
import tempfile
import uuid
from pathlib import Path

POC_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = POC_DIR / "tests"
HELPERS_DIR = TESTS_DIR / "helper_workers"
FIXTURES_DIR = TESTS_DIR / "fixtures"

if str(POC_DIR) not in sys.path:
    sys.path.insert(0, str(POC_DIR))

FIXTURE_BYTES = (FIXTURES_DIR / "synthetic_fixture.txt").read_bytes()
FIXTURE_NAME = "synthetic_fixture.txt"
FIXTURE_SHA = hashlib.sha256(FIXTURE_BYTES).hexdigest()


def helper(name: str) -> str:
    return str(HELPERS_DIR / name)


def make_workspace(job_id: str | None = None):
    """Provisioned workspace in a fresh temp trusted root.

    Returns (ws, caller_parameters) where caller_parameters contains ONLY
    what the typed operation accepts ({input_name}) — closed-world safe.
    """
    from workspace import JobWorkspace

    root = Path(tempfile.mkdtemp(prefix="pocipc_trusted_"))
    job_id = job_id or f"JOB-{uuid.uuid4().hex[:12].upper()}"
    ws = JobWorkspace(root, job_id)
    ws.ensure_areas()
    ws.provision_input(FIXTURE_NAME, FIXTURE_BYTES)
    return ws, {"input_name": FIXTURE_NAME}


def make_orchestrator(ws):
    from orchestrator import default_orchestrator

    return default_orchestrator(ws.trusted_root)


def run_ok(ws, orch, **overrides):
    request = {
        "job_id": ws.job_dir.name,
        "operation": "INSPECT_SYNTHETIC_INPUT",
        "parameters": {"input_name": FIXTURE_NAME},
    }
    request.update(overrides)
    return orch.execute(request)


def expected_fixture_sha() -> str:
    return hashlib.sha256(FIXTURE_BYTES).hexdigest()
