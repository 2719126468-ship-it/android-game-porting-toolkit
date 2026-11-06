"""Safe, review-first unified-diff proposals and explicitly approved application."""
from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

MAX_SOURCE_BYTES = 1024 * 1024
MAX_DIFF_BYTES = 256 * 1024
MAX_PROPOSAL_BYTES = 2 * MAX_SOURCE_BYTES + 2 * MAX_DIFF_BYTES + 64 * 1024
PROPOSAL_ID_RE = re.compile(r"^[0-9a-f]{16}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PatchProposalError(ValueError):
    """A proposed patch cannot be safely represented or applied."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relative_parts(file_path: str) -> tuple[str, ...]:
    if not isinstance(file_path, str) or not file_path.strip():
        raise PatchProposalError("file_path must be a non-empty relative path")
    if "\x00" in file_path or "\\" in file_path or file_path.startswith("/"):
        raise PatchProposalError("file_path must use relative POSIX path syntax")
    raw_parts = file_path.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise PatchProposalError("file_path must not contain empty, dot, or parent path segments")
    relative = PurePosixPath(file_path)
    if relative.is_absolute():
        raise PatchProposalError("file_path must be relative")
    return relative.parts


def _resolve_patch_target(source_root: Path, file_path: str) -> Path:
    parts = _relative_parts(file_path)
    root = source_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise PatchProposalError("source_root must be a directory")
    target = root
    for component in parts:
        target = target / component
        if target.is_symlink():
            raise PatchProposalError("symbolic links are not valid patch targets")
    try:
        target = target.resolve(strict=True)
        target.relative_to(root)
    except (OSError, ValueError) as exc:
        raise PatchProposalError("patch target resolves outside source_root or does not exist") from exc
    if not target.is_file():
        raise PatchProposalError("patch target must be a regular file")
    return target


def _atomic_write(path: Path, data: bytes, mode: int | None = None) -> None:
    """Replace a file atomically using a temporary file in the same directory."""
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.agpt-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary_name, stat.S_IMODE(mode))
        if path.is_symlink() or not path.is_file():
            raise PatchProposalError("refusing to replace a missing or symbolic-link file")
        os.replace(temporary_name, path)
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            # Directory fsync is not available on every supported platform/filesystem.
            pass
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def create_patch_proposal(
    source_root: str | Path,
    project_root: str | Path,
    *,
    file_path: str,
    replacement_text: str,
    rationale: str,
    evidence: list[str] | None = None,
) -> dict[str, Any]:
    """Write a review-only proposal; never modify the original source tree."""
    if not isinstance(replacement_text, str) or "\x00" in replacement_text:
        raise PatchProposalError("replacement_text must be valid UTF-8 text")
    after_bytes = replacement_text.encode("utf-8")
    if len(after_bytes) > MAX_SOURCE_BYTES:
        raise PatchProposalError("replacement_text exceeds the 1 MiB safety limit")
    if not isinstance(rationale, str) or not rationale.strip():
        raise PatchProposalError("rationale is required")
    evidence_items = evidence if evidence is not None else []
    if not isinstance(evidence_items, list) or any(
        not isinstance(item, str) or not item.strip() for item in evidence_items
    ):
        raise PatchProposalError("evidence must be a list of non-empty strings")

    relative_parts = _relative_parts(file_path)
    relative_name = "/".join(relative_parts)
    root = Path(source_root).expanduser().resolve(strict=True)
    target = _resolve_patch_target(root, relative_name)
    if target.stat().st_size > MAX_SOURCE_BYTES:
        raise PatchProposalError("source file exceeds the 1 MiB safety limit")
    before_bytes = target.read_bytes()
    if len(before_bytes) > MAX_SOURCE_BYTES:
        raise PatchProposalError("source file exceeds the 1 MiB safety limit")
    if b"\x00" in before_bytes:
        raise PatchProposalError("binary files cannot receive text patch proposals")
    try:
        before_text = before_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchProposalError("source file is not valid UTF-8 text") from exc

    normalized_before = before_text.replace("\r\n", "\n").replace("\r", "\n")
    normalized_after = replacement_text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized_before == normalized_after:
        raise PatchProposalError("replacement_text does not change the source file")

    diff = "".join(
        difflib.unified_diff(
            before_text.splitlines(keepends=True),
            replacement_text.splitlines(keepends=True),
            fromfile=f"a/{relative_name}",
            tofile=f"b/{relative_name}",
            n=3,
        )
    )
    if len(diff.encode("utf-8")) > MAX_DIFF_BYTES:
        raise PatchProposalError("unified diff exceeds the 256 KiB safety limit")

    before_sha = _sha256(before_bytes)
    after_sha = _sha256(after_bytes)
    normalized_rationale = rationale.strip()
    proposal_id = hashlib.sha256(
        f"{relative_name}|{before_sha}|{after_sha}|{normalized_rationale}".encode("utf-8")
    ).hexdigest()[:16]
    project = Path(project_root).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise PatchProposalError("project_root must be a directory")
    patches_dir = project / "patches"
    proposals_dir = patches_dir / "proposals"
    if patches_dir.is_symlink() or proposals_dir.is_symlink():
        raise PatchProposalError("proposal directories must not be symbolic links")
    patches_dir.mkdir(exist_ok=True)
    proposals_dir.mkdir(exist_ok=True)
    proposal_path = proposals_dir / f"{proposal_id}.json"
    if proposal_path.exists() or proposal_path.is_symlink():
        raise FileExistsError(f"patch proposal already exists: {proposal_path}")

    proposal: dict[str, Any] = {
        "schema_version": "1.0",
        "proposal_id": proposal_id,
        "status": "proposed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "target_file": relative_name,
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "source_file_bytes": len(before_bytes),
        "rationale": normalized_rationale,
        "evidence": evidence_items,
        "replacement_text": replacement_text,
        "unified_diff": diff,
        "approval_required": True,
        "approved": False,
        "applied": False,
        "safety": {
            "review_only": True,
            "source_tree_modified": False,
            "patch_executor_available": True,
            "note": "Review the unified diff. Application requires an explicit --approve action.",
        },
    }
    proposal_path.write_text(
        json.dumps(proposal, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"proposal": proposal, "proposal_path": str(proposal_path.resolve())}


def apply_patch_proposal(
    source_root: str | Path,
    project_root: str | Path,
    proposal_id: str,
    *,
    approve: bool = False,
) -> dict[str, Any]:
    """Apply one proposal only after explicit approval and source-hash verification."""
    if not approve:
        raise PatchProposalError("patch application requires explicit approval with --approve")
    if not isinstance(proposal_id, str) or not PROPOSAL_ID_RE.fullmatch(proposal_id):
        raise PatchProposalError("proposal_id must be a 16-character lowercase hexadecimal ID")

    root = Path(source_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise PatchProposalError("source_root must be a directory")
    project = Path(project_root).expanduser().resolve(strict=True)
    if not project.is_dir():
        raise PatchProposalError("project_root must be a directory")
    patches_dir = project / "patches"
    proposals_dir = patches_dir / "proposals"
    if patches_dir.is_symlink() or proposals_dir.is_symlink():
        raise PatchProposalError("proposal directories must not be symbolic links")
    proposal_path = proposals_dir / f"{proposal_id}.json"
    if proposal_path.is_symlink() or not proposal_path.is_file():
        raise PatchProposalError("proposal file is missing or is a symbolic link")
    if proposal_path.stat().st_size > MAX_PROPOSAL_BYTES:
        raise PatchProposalError("proposal file exceeds the safety size limit")
    proposal_bytes = proposal_path.read_bytes()
    try:
        proposal = json.loads(proposal_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PatchProposalError("proposal file is not valid UTF-8 JSON") from exc
    if not isinstance(proposal, dict):
        raise PatchProposalError("proposal must be a JSON object")
    if proposal.get("schema_version") != "1.0" or proposal.get("proposal_id") != proposal_id:
        raise PatchProposalError("proposal schema or ID does not match")
    if proposal.get("status") != "proposed" or proposal.get("applied") is not False:
        raise PatchProposalError("proposal is not in the proposed state")
    if proposal.get("approval_required") is not True or proposal.get("approved") is not False:
        raise PatchProposalError("proposal approval state is invalid")
    safety = proposal.get("safety")
    if not isinstance(safety, dict) or safety.get("review_only") is not True:
        raise PatchProposalError("proposal safety metadata is invalid")

    target_file = proposal.get("target_file")
    rationale = proposal.get("rationale")
    before_sha = proposal.get("before_sha256")
    after_sha = proposal.get("after_sha256")
    if (
        not isinstance(target_file, str)
        or not isinstance(rationale, str)
        or not isinstance(before_sha, str)
        or not SHA256_RE.fullmatch(before_sha)
        or not isinstance(after_sha, str)
        or not SHA256_RE.fullmatch(after_sha)
    ):
        raise PatchProposalError("proposal target, rationale, or source hashes are invalid")
    expected_id = hashlib.sha256(
        f"{target_file}|{before_sha}|{after_sha}|{rationale}".encode("utf-8")
    ).hexdigest()[:16]
    if expected_id != proposal_id:
        raise PatchProposalError("proposal metadata does not match its ID")

    target_file = proposal.get("target_file")
    target = _resolve_patch_target(root, target_file)
    current_bytes = target.read_bytes()
    if len(current_bytes) > MAX_SOURCE_BYTES or b"\x00" in current_bytes:
        raise PatchProposalError("current source file is oversized or binary")
    before_sha = proposal.get("before_sha256")
    if not isinstance(before_sha, str) or _sha256(current_bytes) != before_sha:
        raise PatchProposalError("source file changed since proposal creation; generate a new proposal")

    replacement_text = proposal.get("replacement_text")
    if not isinstance(replacement_text, str) or "\x00" in replacement_text:
        raise PatchProposalError("proposal replacement_text is missing or invalid")
    replacement_bytes = replacement_text.encode("utf-8")
    if len(replacement_bytes) > MAX_SOURCE_BYTES:
        raise PatchProposalError("replacement_text exceeds the 1 MiB safety limit")
    after_sha = proposal.get("after_sha256")
    if not isinstance(after_sha, str) or not SHA256_RE.fullmatch(after_sha):
        raise PatchProposalError("replacement_text hash does not match proposal metadata")
    if _sha256(replacement_bytes) != after_sha:
        raise PatchProposalError("replacement_text hash does not match proposal metadata")
    try:
        current_text = current_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise PatchProposalError("current source file is not valid UTF-8 text") from exc
    expected_diff = "".join(
        difflib.unified_diff(
            current_text.splitlines(keepends=True),
            replacement_text.splitlines(keepends=True),
            fromfile=f"a/{target_file}",
            tofile=f"b/{target_file}",
            n=3,
        )
    )
    if len(expected_diff.encode("utf-8")) > MAX_DIFF_BYTES:
        raise PatchProposalError("recomputed unified diff exceeds the safety size limit")
    if proposal.get("unified_diff") != expected_diff:
        raise PatchProposalError("review diff does not match the approved source and replacement text")

    # Re-resolve and re-hash immediately before the atomic replacement.
    target = _resolve_patch_target(root, target_file)
    latest_bytes = target.read_bytes()
    if _sha256(latest_bytes) != before_sha:
        raise PatchProposalError("source file changed during approval; refusing to apply")
    original_mode = target.stat().st_mode
    _atomic_write(target, replacement_bytes, original_mode)
    if _sha256(target.read_bytes()) != after_sha:
        raise PatchProposalError("source patch was written but post-write verification failed")

    applied_at = datetime.now(timezone.utc).isoformat()
    proposal.update({
        "status": "applied",
        "approved": True,
        "approved_at": applied_at,
        "applied": True,
        "applied_at": applied_at,
    })
    proposal["safety"] = {
        "review_only": False,
        "source_tree_modified": True,
        "patch_executor_available": True,
        "note": "This proposal was explicitly approved and applied after source-hash verification.",
    }
    try:
        if proposal_path.is_symlink() or not proposal_path.is_file():
            raise PatchProposalError("proposal file changed during application")
        if _sha256(proposal_path.read_bytes()) != _sha256(proposal_bytes):
            raise PatchProposalError("proposal file changed during application")
        _atomic_write(
            proposal_path,
            (json.dumps(proposal, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            proposal_path.stat().st_mode,
        )
    except (OSError, PatchProposalError) as exc:
        raise PatchProposalError(
            f"source patch was applied, but proposal status could not be recorded: {exc}"
        ) from exc

    return {
        "success": True,
        "proposal_id": proposal_id,
        "target_file": target_file,
        "before_sha256": before_sha,
        "after_sha256": after_sha,
        "approved": True,
        "applied": True,
        "applied_at": applied_at,
        "proposal_path": str(proposal_path.resolve()),
    }
