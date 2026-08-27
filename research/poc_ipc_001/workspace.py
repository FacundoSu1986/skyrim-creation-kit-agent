"""Trusted-side job workspace for POC-IPC-001.

TRUSTED_JOBS_ROOT enters only through this module's constructor (trusted
orchestrator configuration) — never through a request. All derived paths are
resolved and re-contained; safe-name tokens follow the ADR grammar including
the explicit ".." ban.
"""

import hashlib
import os
from pathlib import Path

from protocol import validate_safe_name

AREA_NAMES = ("input", "originals", "candidates", "temp", "reports", "receipts", "logs")


class WorkspaceViolation(Exception):
    """Raised when a path/token escapes its allowed containment."""


class JobWorkspace:
    """Trusted view of one job directory under TRUSTED_JOBS_ROOT."""

    def __init__(self, trusted_jobs_root: Path, job_id: str):
        if not validate_safe_name(job_id):
            raise WorkspaceViolation(f"job_id violates safe-name contract: {job_id!r}")
        self.trusted_root = Path(trusted_jobs_root).resolve()
        self.job_dir = (self.trusted_root / "jobs" / job_id).resolve()
        # Post-derivation containment re-check (defense in depth).
        if not self._is_contained(self.job_dir, self.trusted_root):
            raise WorkspaceViolation("derived job dir escaped the trusted root")
        self.areas = {name: self.job_dir / name for name in AREA_NAMES}

    # -- containment -------------------------------------------------------

    @staticmethod
    def _is_contained(candidate: Path, root: Path) -> bool:
        """Resolved containment, case-folded where the platform is insensitive."""
        c = os.path.normcase(str(candidate))
        r = os.path.normcase(str(root))
        return c == r or c.startswith(r + os.sep)

    def contained_path(self, area: str, token: str) -> Path:
        """Resolve area/token and re-contain; raises on any escape."""
        if not validate_safe_name(token):
            raise WorkspaceViolation(f"token violates safe-name contract: {token!r}")
        area_dir = self.areas[area]
        target = (area_dir / token).resolve()
        if not self._is_contained(target, area_dir.resolve()):
            raise WorkspaceViolation(
                f"resolved path escaped area '{area}': {target}"
            )
        return target

    def ensure_areas(self) -> None:
        for path in self.areas.values():
            path.mkdir(parents=True, exist_ok=True)

    def job_temp(self) -> Path:
        """Directory handed to the worker as TEMP/TMPDIR."""
        temp = self.areas["temp"]
        temp.mkdir(parents=True, exist_ok=True)
        return temp

    # -- provisioning ------------------------------------------------------

    def provision_input(self, token: str, data: bytes) -> tuple:
        """Write an input file trusted-side; returns (path, sha256_hex)."""
        target = self.contained_path("input", token)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return target, hashlib.sha256(data).hexdigest()

    def input_sha256(self, token: str) -> str:
        data = self.contained_path("input", token).read_bytes()
        return hashlib.sha256(data).hexdigest()

    # -- evidence persistence (orchestrator-only writes) -------------------

    def persist_receipt(self, request_id: str, receipt_obj: dict) -> Path:
        """Append-only, no-overwrite persistence of a VALIDATED receipt.

        The no-overwrite property is enforced atomically by the OS via
        open(..., "x"), not by a check-then-write window. A second
        persistence for the same request_id raises WorkspaceViolation
        before any byte of the existing file is touched.
        """
        import json

        dest = self.contained_path("receipts", f"{request_id}.json")
        try:
            with open(dest, "x", encoding="utf-8") as handle:
                handle.write(json.dumps(receipt_obj, indent=2, sort_keys=True))
        except FileExistsError as exc:
            raise WorkspaceViolation(
                f"receipt already exists: {dest.name}"
            ) from exc
        return dest

    def persist_stderr_log(self, request_id: str, stderr_bytes: bytes) -> Path:
        """Append-only, no-overwrite persistence of a worker stderr log.

        The no-overwrite property is enforced atomically by the OS via
        open(..., "xb"), not by a check-then-write window. A second
        persistence for the same request_id raises WorkspaceViolation
        before any byte of the existing file is touched.
        """
        dest = self.contained_path("logs", f"{request_id}.stderr.log")
        try:
            with open(dest, "xb") as handle:
                handle.write(stderr_bytes)
        except FileExistsError as exc:
            raise WorkspaceViolation(
                f"log already exists: {dest.name}"
            ) from exc
        return dest

    def candidates_empty(self) -> bool:
        candidates = self.areas["candidates"]
        if not candidates.exists():
            return True
        return not any(candidates.iterdir())
